'use strict';
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),http=require('http');
const root=path.resolve(__dirname,'..');
const server=http.createServer((req,res)=>{let rel=decodeURIComponent(new URL(req.url,'http://localhost').pathname);if(rel.endsWith('/'))rel+='index.html';try{let p=path.join(root,rel);res.setHeader('Content-Type',p.endsWith('.html')?'text/html; charset=utf-8':p.endsWith('.css')?'text/css':p.endsWith('.js')?'text/javascript':'application/octet-stream');res.end(fs.readFileSync(p))}catch{res.statusCode=404;res.end('Missing')}});
(async()=>{
 await new Promise(r=>server.listen(8766,'127.0.0.1',r));
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 const page=await browser.newPage();const rows=[];fs.mkdirSync(path.join(root,'mysql-screenshots'),{recursive:true});
 for(let n=1;n<=12;n++){
  const errors=[];const handler=e=>errors.push(e.message);page.on('pageerror',handler);
  await page.setViewportSize({width:1365,height:1000});
  await page.goto(`http://127.0.0.1:8766/posts/mysql-study-${String(n).padStart(2,'0')}.html`);
  const title=await page.title();
  await page.getByRole('button',{name:'답변 모두 펼치기',exact:true}).click();
  const allOpen=await page.locator('details').evaluateAll(ds=>ds.length===6&&ds.every(d=>d.open));
  await page.getByRole('button',{name:'답변 모두 접기',exact:true}).click();
  const allClosed=await page.locator('details').evaluateAll(ds=>ds.every(d=>!d.open));
  await page.locator('details summary').first().click();
  const individual=await page.locator('details').first().evaluate(d=>d.open);
  const desktop=await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth);
  const brokenAnchors=await page.locator('.study-toc a').evaluateAll(as=>as.filter(a=>!document.getElementById(a.hash.slice(1))).length);
  if([1,6,10].includes(n))await page.screenshot({path:path.join(root,`mysql-screenshots/${n}-desktop.png`)});
  await page.setViewportSize({width:390,height:844});
  const mobile=await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth);
  if([1,6,10].includes(n)){await page.screenshot({path:path.join(root,`mysql-screenshots/${n}-mobile.png`)});await page.locator('details').first().scrollIntoViewIfNeeded();await page.screenshot({path:path.join(root,`mysql-screenshots/${n}-answer.png`)});}
  rows.push({lesson:n,title,allOpen,allClosed,individual,desktop,mobile,brokenAnchors,errors});page.off('pageerror',handler);
 }
 await page.goto('http://127.0.0.1:8766/');await page.locator('#search').fill('MySQL');
 const visible=await page.locator('.post:visible').count();if(visible!==12)throw Error('Search should show 12 MySQL posts, got '+visible);
 await page.goto('http://127.0.0.1:8766/learning/mysql/');
 const cards=await page.locator('.series-card').count();if(cards!==12)throw Error('Missing lesson cards');
 const failures=rows.filter(x=>!x.allOpen||!x.allClosed||!x.individual||!x.desktop||!x.mobile||x.brokenAnchors||x.errors.length);
 fs.writeFileSync(path.join(root,'learning/mysql-browser-checks.json'),JSON.stringify({rows,searchResults:visible,failures},null,2));
 console.log(JSON.stringify({tested:rows.length,searchResults:visible,failures}));
 await browser.close();server.close();if(failures.length)process.exitCode=1;
})().catch(e=>{console.error(e);server.close();process.exit(1)});
