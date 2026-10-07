import { createServer } from 'node:http';
import { createReadStream } from 'node:fs';
import { mkdir, readFile, rename, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { isIP } from 'node:net';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const frontendRoot = path.join(root, 'frontend');
const port = Number(process.env.PORT || 4173);
const host = process.env.HOST || '127.0.0.1';
const dataDir = path.join(path.dirname(fileURLToPath(import.meta.url)), 'storage');
const eventsFile = path.join(dataDir, 'events.json');
const mime = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.csv': 'text/csv; charset=utf-8', '.svg': 'image/svg+xml' };
const rate = new Map();
let events = [];
let writeQueue = Promise.resolve();

try {
  const saved = JSON.parse(await readFile(eventsFile, 'utf8'));
  if (Array.isArray(saved)) events = saved.slice(-5000);
} catch (error) {
  if (error.code !== 'ENOENT') console.error('Could not read saved event data:', error.message);
}

function send(res, status, payload, headers = {}) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...headers });
  res.end(JSON.stringify(payload));
}

function limited(req) {
  const now = Date.now(), key = req.socket.remoteAddress || 'unknown';
  const bucket = rate.get(key) || { start: now, count: 0 };
  if (now - bucket.start > 60_000) { bucket.start = now; bucket.count = 0; }
  bucket.count++;
  rate.set(key, bucket);
  return bucket.count > 120;
}

function normalizeEvent(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Each event must be an object.');
  if ('password' in input || 'portalPassword' in input) throw new Error('Do not send passwords to the event API.');
  const timestamp = new Date(input.timestamp);
  const username = String(input.username || '').trim().slice(0, 254);
  const sourceIp = String(input.source_ip || '').trim();
  const country = String(input.country || '').trim().toUpperCase();
  const result = String(input.result || '').toLowerCase();
  if (!Number.isFinite(timestamp.getTime())) throw new Error('Event timestamp is invalid.');
  if (!username) throw new Error('Event username is required.');
  if (!isIP(sourceIp)) throw new Error('Event source_ip must be a valid IP address.');
  if (country && !/^[A-Z]{2}$/.test(country)) throw new Error('Country must be a two-letter code.');
  if (!['success', 'failure'].includes(result)) throw new Error('Result must be success or failure.');
  return {
    portal_event_id: String(input.portal_event_id || randomUUID()).slice(0, 80),
    timestamp: timestamp.toISOString(), username, source_ip: sourceIp, country,
    result, device: String(input.device || 'Unknown').slice(0, 120),
    user_agent: String(input.user_agent || '').slice(0, 200),
    action: 'VPN_SIGN_IN', simulation: 'user-portal',
    scenario: String(input.scenario || 'manual').slice(0, 40)
  };
}

async function readBody(req) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > 256 * 1024) throw new Error('Request body exceeds 256 KB.');
    chunks.push(chunk);
  }
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

function saveEvents() {
  writeQueue = writeQueue.then(async () => {
    await mkdir(dataDir, { recursive: true });
    const temporary = `${eventsFile}.${process.pid}.tmp`;
    await writeFile(temporary, JSON.stringify(events, null, 2), 'utf8');
    await rename(temporary, eventsFile);
  });
  return writeQueue;
}

async function serveStatic(req, res, pathname) {
  let decoded;
  try { decoded = decodeURIComponent(pathname); } catch { res.writeHead(400).end('Bad path'); return; }
  // Keep the former /data/ URLs working for tabs that still have a cached frontend bundle.
  const isDatasetFile = decoded.startsWith('/dataset/') || decoded.startsWith('/data/');
  const staticRoot = isDatasetFile ? path.join(root, 'dataset') : frontendRoot;
  const datasetPrefix = decoded.startsWith('/data/') ? '/data' : '/dataset';
  const relativeUrl = isDatasetFile ? decoded.slice(datasetPrefix.length) : decoded;
  const target = path.resolve(staticRoot, `.${relativeUrl === '/' ? '/index.html' : relativeUrl}`);
  const relative = path.relative(staticRoot, target);
  if (relative.startsWith('..') || path.isAbsolute(relative) || (isDatasetFile && (relative.startsWith('lanl') || relative.startsWith('models')))) {
    res.writeHead(404).end('Not found'); return;
  }
  let file = target;
  try {
    const info = await stat(file);
    if (info.isDirectory()) file = path.join(file, 'index.html');
    const fileInfo = await stat(file);
    if (!fileInfo.isFile()) throw new Error('Not a file');
  } catch { res.writeHead(404).end('Not found'); return; }
  res.writeHead(200, { 'Content-Type': mime[path.extname(file).toLowerCase()] || 'application/octet-stream', 'X-Content-Type-Options': 'nosniff' });
  createReadStream(file).pipe(res);
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  if (url.pathname.startsWith('/api/')) {
    if (limited(req)) return send(res, 429, { error: 'Too many requests. Try again shortly.' });
    if (url.pathname === '/api/health' && req.method === 'GET') return send(res, 200, { ok: true, service: 'SprayScope demo API', events: events.length });
    if (url.pathname === '/api/client-info' && req.method === 'GET') {
      const remoteAddress = String(req.socket.remoteAddress || '').replace(/^::ffff:/, '');
      return send(res, 200, { source_ip: remoteAddress || 'unknown' });
    }
    if (url.pathname === '/api/events' && req.method === 'GET') return send(res, 200, { events });
    if (url.pathname === '/api/events' && req.method === 'POST') {
      try {
        const body = await readBody(req);
        const batch = Array.isArray(body) ? body : body?.events;
        if (!Array.isArray(batch) || batch.length < 1 || batch.length > 500) return send(res, 400, { error: 'Send an events array containing 1 to 500 events.' });
        const normalized = batch.map(normalizeEvent);
        const known = new Set(events.map(e => e.portal_event_id));
        const fresh = normalized.filter(e => {
          if (known.has(e.portal_event_id)) return false;
          known.add(e.portal_event_id);
          return true;
        });
        events = [...events, ...fresh].slice(-5000);
        await saveEvents();
        return send(res, 201, { accepted: fresh.length, total: events.length });
      } catch (error) { return send(res, 400, { error: error.message || 'Invalid event request.' }); }
    }
    return send(res, 404, { error: 'API route not found.' });
  }
  if (req.method !== 'GET' && req.method !== 'HEAD') return res.writeHead(405).end('Method not allowed');
  return serveStatic(req, res, url.pathname);
});

server.listen(port, host, () => console.log(`SprayScope hackathon backend listening on http://localhost:${port}`));

