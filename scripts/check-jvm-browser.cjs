const {chromium}=require('playwright');
const fs=require('fs');
const path=require('path');
const root=path.resolve(__dirname,'..');
(async()=>{
 const server=require('http').createServer((req,res)=>{let file=path.join(root,decodeURIComponent(req.url.split('?')[0]));if(file.endsWith('/'))file+='index.html';try{res.setHeader('Content-Type',file.endsWith('.css')?'text/css':file.endsWith('.js')?'application/javascript':'text/html; charset=utf-8');res.end(fs.readFileSync(file));}catch{res.statusCode=404;res.end('missing')}});
 await new Promise(r=>server.listen(8877,'127.0.0.1',r));
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||undefined,args:['--no-sandbox']});
 const errors=[],rows=[];
 for(const width of [390,1440]){
  const page=await browser.newPage({viewport:{width,height:900}});
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://fonts.googleapis.com/**',r=>r.abort());
  for(let n=0;n<=16;n++){
   await page.goto(`http://127.0.0.1:8877/posts/jvm-study-${String(n).padStart(2,'0')}.html`,{waitUntil:'domcontentloaded'});
   const questions=await page.locator('details.question').count();
   if(n){
    await page.getByRole('button',{name:'모든 답변 펼치기',exact:true}).click();
    if(await page.locator('details.question[open]').count()!==questions)errors.push(`expand ${width}/${n}`);
    await page.getByRole('button',{name:'모든 답변 접기',exact:true}).click();
    if(await page.locator('details.question[open]').count()!==0)errors.push(`collapse ${width}/${n}`);
    await page.locator('summary').first().focus();await page.keyboard.press('Enter');
    if(await page.locator('details.question[open]').count()!==1)errors.push(`keyboard ${width}/${n}`);
   }
   const state=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,skin:getComputedStyle(document.body).backgroundColor,h1:document.querySelector('h1').textContent}));
   if(state.overflow)errors.push(`overflow ${width}/${n}`);
   rows.push({width,lesson:n,questions,...state});
   if([0,5,13,16].includes(n))await page.screenshot({path:`/tmp/jvm-${n}-${width}.png`});
  }
  await page.goto('http://127.0.0.1:8877/',{waitUntil:'domcontentloaded'});
  const cardCount=await page.locator('.post').count();
  if(Number(await page.locator('#count').textContent())!==cardCount)errors.push(`initial count ${width}`);
  await page.locator('#search').fill('JVM');
  const found=await page.locator('.post:not([hidden])').count();
  if(found!==17)errors.push(`JVM search ${found}`);
  await page.close();
 }
 await browser.close();server.close();
 fs.writeFileSync(path.join(root,'learning/jvm-browser-checks.json'),JSON.stringify({pages:rows.length,errors,results:rows},null,2)+'\n');
 console.log(JSON.stringify({pages:rows.length,errors}));if(errors.length)process.exitCode=1;
})();
