// Small representative authentication log sample. This is not a download of LogHub.
export function createDemo(){
  const events=[],base=Date.now()-60*60*1000;
  const add=(m,user,ip,result,country='US',label='normal')=>events.push({timestamp:new Date(base+m*60000).toISOString(),username:user,source_ip:ip,result,country,user_agent:'VPN Client / Windows',device:'Workstation',label});
  for(let m=0;m<60;m+=2){add(m,`analyst${m%9+1}@cybernova.test`,`198.51.100.${20+m%8}`,m%7?'success':'failure');}
  for(let m=12;m<19;m++){for(let n=0;n<2;n++)add(m,`finance${(m-12)*2+n+1}@cybernova.test`,'203.0.113.77','failure','', 'password_spray');}
  for(let m=34;m<37;m++)for(let n=0;n<4;n++)add(m,`admin@cybernova.test`,'192.0.2.44','failure','','brute_force');
  add(42,'exec@cybernova.test','198.51.100.5','success','US','impossible_travel');add(43,'exec@cybernova.test','203.0.113.8','success','GB','impossible_travel');
  return events.sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp));
}

