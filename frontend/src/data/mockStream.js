// Structured illustrative VPN events. No IP geolocation or live traffic is fetched.
export function createAnalystMock(){
  const out=[],now=Date.now();
  const add=(minutesAgo,user,sourceIp,country,device,result='success',userAgent='Windows / Chrome')=>out.push({timestamp:new Date(now-minutesAgo*60000).toISOString(),username:user,source_ip:sourceIp,result,country,user_agent:userAgent,device,action:'LOGIN'});
  const staff=['maria.chen','john.doe','alice.rao','sam.patel','nina.khan','omar.hassan','leo.martin','zoe.wilson','daniel.kim','ava.singh','ethan.brooks','maya.jones','noah.park','ella.ross','liam.gray','ivy.morgan','amir.shah'];
  const officeIps=['198.51.100.10','198.51.100.11','198.51.100.12','198.51.100.13'];
  for(let i=0;i<32;i++){const user=staff[i%staff.length],age=4+(i*7)%54,success=i%6!==2;add(age,user,officeIps[i%officeIps.length],'US',i%4===0?'macOS / Safari':'Windows / Chrome',success?'success':'failure',i%4===0?'macOS / Safari':'Windows / Chrome');}
  // One focused password-spray pattern: a single source touches 17 distinct accounts.
  for(let i=0;i<17;i++)add(12-(i*.48),staff[i],'203.0.113.88','DE','Unknown / VPN client','failure','Unknown client');
  // Repeated failures concentrated on one account from one source.
  for(let i=0;i<12;i++)add(8-(i*.22),'admin.ops', '192.0.2.44','US','Linux / OpenSSH','failure','OpenSSH');
  // Two successful logins too far apart geographically for their short interval.
  add(3,'jordan.taylor','198.51.100.50','US','iPhone / Edge','success','iOS / Edge');
  add(2,'jordan.taylor','203.0.113.50','GB','Unknown / Edge','success','Unknown / Edge');
  return out.sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp));
}

