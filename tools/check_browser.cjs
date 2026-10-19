const {chromium}=require('playwright');
const fs=require('fs');
const http=require('http');const path=require('path');
const root=path.resolve(__dirname,'..');
const server=http.createServer((req,res)=>{let rel=decodeURIComponent(new URL(req.url,'http://localhost').pathname);if(rel.endsWith('/'))rel+='index.html';const file=path.join(root,rel);try{const body=fs.readFileSync(file);res.setHeader('Content-Type',file.endsWith('.html')?'text/html; charset=utf-8':file.endsWith('.css')?'text/css':file.endsWith('.js')?'text/javascript':'application/octet-stream');res.end(body)}catch{res.statusCode=404;res.end('Missing')}});
(async()=>{
 await new Promise(r=>server.listen(8765,'127.0.0.1',r));
 const browser=await chromium.launch({headless:true,...(process.env.CHROME_EXECUTABLE?{executablePath:process.env.CHROME_EXECUTABLE}:{}),args:['--no-sandbox']});
 const page=await browser.newPage();let result=[];
 for (let n=1;n<=35;n++){
  const errors=[];const handler=e=>errors.push(e.message);page.on('pageerror',handler);
  await page.setViewportSize({width:1365,height:1000});
  await page.goto(`http://127.0.0.1:8765/posts/kafka-study-${String(n).padStart(2,'0')}.html`,{waitUntil:'domcontentloaded'});
  await page.getByRole('button',{name:'답변 모두 펼치기',exact:true}).click();
  let allOpen=await page.locator('details').evaluateAll(ds=>ds.every(d=>d.open));
  await page.getByRole('button',{name:'답변 모두 접기',exact:true}).click();
  let allClosed=await page.locator('details').evaluateAll(ds=>ds.every(d=>!d.open));
  let desktop=await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth);
  
  await page.setViewportSize({width:390,height:844});
  let mobile=await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth);
  await page.locator('#revision-code').scrollIntoViewIfNeeded();
  
  result.push({lesson:n,allOpen,allClosed,desktop,mobile,errors});page.off('pageerror',handler);
 }
 await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded'});
 result.push({page:'index',mobile:await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)});
 fs.writeFileSync(path.join(root,'learning/browser-checks.json'),JSON.stringify(result,null,2));
 console.log(JSON.stringify({tested:result.length,failures:result.filter(x=>x.errors?.length||x.mobile===false||x.desktop===false||x.allOpen===false||x.allClosed===false)}));
 await browser.close();server.close();
 if(result.some(x=>x.errors?.length||x.mobile===false||x.desktop===false||x.allOpen===false||x.allClosed===false))process.exitCode=1;
})().catch(e=>{console.error(e);process.exit(1)});
