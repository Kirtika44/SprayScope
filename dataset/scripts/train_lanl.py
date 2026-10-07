"""Train and evaluate a LANL authentication anomaly model.

Labels are exact auth-event matches from LANL's redteam.txt.gz.  This is an
offline research benchmark; LANL data has no public IP or country fields and
must not be represented as VPN/impossible-travel validation.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
import joblib


ROOT = Path(__file__).resolve().parents[2]
AUTH_DEFAULT = ROOT / "dataset" / "lanl" / "auth.txt.gz"
REDTEAM_DEFAULT = ROOT / "dataset" / "lanl" / "redteam.txt.gz"
OUT_DEFAULT = ROOT / "dataset" / "models" / "lanl"
NEGATIVE_SAMPLE_RATE = 0.0001
RANDOM_SEED = 20261006
AUTH_RELEASE_BYTES = 7_626_505_158


def load_labels(path: Path):
    labels = set()
    raw_rows = 0
    with gzip.open(path, "rt", encoding="ascii", newline="") as f:
        for row in csv.reader(f):
            if len(row) != 4:
                raise ValueError(f"Malformed red-team row: {row!r}")
            raw_rows += 1
            t, username, src, dst = row
            labels.add((int(t), username, src, dst))
    if len(labels) < 20:
        raise ValueError(f"Only {len(labels)} unique red-team labels found.")
    return labels, raw_rows


def build_features(row, src_user_counts, dst_user_counts, src_host_counts, dst_host_counts):
    t, src_user, dst_user, src_host, dst_host, auth_type, logon_type, orientation, result = row
    features = {
        "auth_type=" + auth_type: 1.0,
        "logon_type=" + logon_type: 1.0,
        "orientation=" + orientation: 1.0,
        "result=" + result: 1.0,
        "same_user": float(src_user == dst_user),
        "same_host": float(src_host == dst_host),
        "src_user_seen": float(src_user in src_user_counts),
        "dst_user_seen": float(dst_user in dst_user_counts),
        "src_host_seen": float(src_host in src_host_counts),
        "dst_host_seen": float(dst_host in dst_host_counts),
        "log_src_user_events": math.log1p(src_user_counts[src_user]),
        "log_dst_user_events": math.log1p(dst_user_counts[dst_user]),
        "log_src_host_events": math.log1p(src_host_counts[src_host]),
        "log_dst_host_events": math.log1p(dst_host_counts[dst_host]),
    }
    return features


def update_counts(row, src_user_counts, dst_user_counts, src_host_counts, dst_host_counts):
    _, src_user, dst_user, src_host, dst_host, *_ = row
    src_user_counts[src_user] += 1
    dst_user_counts[dst_user] += 1
    src_host_counts[src_host] += 1
    dst_host_counts[dst_host] += 1


def best_f1_threshold(y_true, scores, sample_weight):
    candidates = np.unique(np.quantile(scores, np.linspace(0.0, 1.0, 201)))
    best = (0.0, 0.5)
    for threshold in candidates:
        pred = scores >= threshold
        score = f1_score(y_true, pred, sample_weight=sample_weight, zero_division=0)
        if score > best[0]:
            best = (float(score), float(threshold))
    return best[1]


def evaluate(y, scores, threshold, weights):
    pred = scores >= threshold
    cm = confusion_matrix(y, pred, labels=[0, 1], sample_weight=weights)
    return {
        "events_evaluated_unweighted_sample": int(len(y)),
        "positives_in_sample": int(np.sum(y)),
        "negative_sampling_weight": int(round(float(weights[y == 0][0]))) if np.any(y == 0) else None,
        "threshold": float(threshold),
        "precision": float(precision_score(y, pred, sample_weight=weights, zero_division=0)),
        "recall": float(recall_score(y, pred, sample_weight=weights, zero_division=0)),
        "f1": float(f1_score(y, pred, sample_weight=weights, zero_division=0)),
        "accuracy": float(accuracy_score(y, pred, sample_weight=weights)),
        "average_precision": float(average_precision_score(y, scores, sample_weight=weights)),
        "roc_auc": float(roc_auc_score(y, scores, sample_weight=weights)),
        "confusion_matrix_weighted": {
            "tn": float(cm[0, 0]), "fp": float(cm[0, 1]),
            "fn": float(cm[1, 0]), "tp": float(cm[1, 1]),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth", type=Path, default=AUTH_DEFAULT)
    parser.add_argument("--redteam", type=Path, default=REDTEAM_DEFAULT)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    parser.add_argument("--negative-sample-rate", type=float, default=NEGATIVE_SAMPLE_RATE)
    args = parser.parse_args()

    if not args.auth.is_file() or not args.redteam.is_file():
        raise SystemExit("Required files: dataset/lanl/auth.txt.gz and dataset/lanl/redteam.txt.gz")
    if not (0 < args.negative_sample_rate <= 0.01):
        raise SystemExit("negative sample rate must be >0 and <=0.01")

    labels, raw_label_rows = load_labels(args.redteam)
    attack_times = sorted({key[0] for key in labels})
    train_end = attack_times[int(len(attack_times) * 0.70)]
    validation_end = attack_times[int(len(attack_times) * 0.85)]
    last_attack_time = attack_times[-1]
    rng = random.Random(RANDOM_SEED)

    xs = {name: [] for name in ("train", "validation", "test")}
    ys = {name: [] for name in ("train", "validation", "test")}
    weights = {name: [] for name in ("train", "validation", "test")}
    counters = [defaultdict(int) for _ in range(4)]
    matched_labels = set()
    row_count = 0
    previous_time = -1

    print(f"Reading LANL auth log through last labeled attack at t={last_attack_time:,}...", flush=True)
    with gzip.open(args.auth, "rt", encoding="ascii", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) != 9:
                continue
            try:
                event_time = int(row[0])
            except ValueError:
                continue
            if event_time < previous_time:
                raise SystemExit("Authentication events are not time-sorted; refusing a leaky temporal split.")
            previous_time = event_time
            if event_time > last_attack_time:
                break

            source_key = (event_time, row[1], row[3], row[4])
            destination_key = (event_time, row[2], row[3], row[4])
            matched_key = source_key if source_key in labels else destination_key if destination_key in labels else None
            is_attack = matched_key is not None
            if matched_key is not None:
                matched_labels.add(matched_key)
            split = "train" if event_time < train_end else "validation" if event_time < validation_end else "test"
            if is_attack or rng.random() < args.negative_sample_rate:
                feat = build_features(row, *counters)
                xs[split].append(feat)
                ys[split].append(int(is_attack))
                weights[split].append(1.0 if is_attack else 1.0 / args.negative_sample_rate)
            update_counts(row, *counters)
            row_count += 1
            if row_count % 10_000_000 == 0:
                print(f"Processed {row_count:,} auth events; matched {len(matched_labels)}/{len(labels)} labels", flush=True)

    if len(matched_labels) < 20:
        raise SystemExit(f"Only {len(matched_labels)} labels matched auth rows; check dataset version/files.")
    print(f"Feature rows: train={len(ys['train']):,}, validation={len(ys['validation']):,}, test={len(ys['test']):,}; labels matched={len(matched_labels)}/{len(labels)}", flush=True)

    vectorizer = DictVectorizer(sparse=True, dtype=np.float32)
    x_train = vectorizer.fit_transform(xs["train"])
    x_validation = vectorizer.transform(xs["validation"])
    x_test = vectorizer.transform(xs["test"])
    y_train = np.asarray(ys["train"], dtype=np.int8)
    y_validation = np.asarray(ys["validation"], dtype=np.int8)
    y_test = np.asarray(ys["test"], dtype=np.int8)
    w_validation = np.asarray(weights["validation"], dtype=np.float64)
    w_test = np.asarray(weights["test"], dtype=np.float64)

    if len(np.unique(y_train)) < 2 or len(np.unique(y_validation)) < 2 or len(np.unique(y_test)) < 2:
        raise SystemExit("A temporal split has only one class. Need more LANL labels/events to evaluate.")

    model = LogisticRegression(max_iter=500, class_weight="balanced", solver="liblinear", random_state=RANDOM_SEED)
    model.fit(x_train, y_train)
    validation_scores = model.predict_proba(x_validation)[:, 1]
    threshold = best_f1_threshold(y_validation, validation_scores, w_validation)
    test_scores = model.predict_proba(x_test)[:, 1]
    test_metrics = evaluate(y_test, test_scores, threshold, w_test)

    args.out.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "model": model}, args.out / "lanl_auth_logistic.joblib")
    report = {
        "dataset": "LANL Comprehensive Multi-Source Cyber-Security Events (auth + redteam)",
        "dataset_source": "https://csr.lanl.gov/data/cyber1/",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": "scikit-learn LogisticRegression",
        "split": "chronological by unique redteam event timestamps: first 70% train, next 15% validation, final 15% holdout test",
        "label_definition": "exact auth event tuple match to redteam time, username, source computer, destination computer; known attacks only",
        "auth_archive_bytes_present": args.auth.stat().st_size,
        "auth_archive_complete": args.auth.stat().st_size >= AUTH_RELEASE_BYTES,
        "auth_rows_scanned": row_count,
        "redteam_label_rows": raw_label_rows,
        "redteam_labels_unique": len(labels),
        "redteam_duplicate_rows": raw_label_rows - len(labels),
        "redteam_labels_matched": len(matched_labels),
        "negative_sampling_rate": args.negative_sample_rate,
        "metrics": test_metrics,
        "limitations": [
            "Holdout metrics use inverse-probability weights for sampled negative events.",
            "Unlabeled behavior is treated as benign; LANL redteam labels cover only known compromises.",
            "LANL has anonymized users/computers and no public source IP or country, so this is not VPN or impossible-travel validation.",
        ],
    }
    (args.out / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

