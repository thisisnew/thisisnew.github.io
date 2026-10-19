const {chromium}=require('playwright');const http=require('http'),fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'..');const server=http.createServer((req,res)=>{const rel=new URL(req.url,'http://localhost').pathname;const p=path.join(root,rel==='/'?'index.html':rel);try{res.setHeader('Content-Type',p.endsWith('.js')?'text/javascript':p.endsWith('.css')?'text/css':'text/html; charset=utf-8');res.end(fs.readFileSync(p))}catch{res.statusCode=404;res.end()}});
(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));const base='http://127.0.0.1:'+server.address().port;const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||undefined,args:process.env.CHROME_PATH?['--no-sandbox','--disable-dev-shm-usage']:[]});const page=await browser.newPage();const errors=[],rows=[];page.on('pageerror',e=>errors.push(e.message));await page.route('https://fonts.googleapis.com/**',r=>r.abort());await page.route('https://fonts.gstatic.com/**',r=>r.abort());
for(const width of [1440,390]){await page.setViewportSize({width,height:960});
 for(let n=0;n<23;n++){const url=base+'/posts/aws-study-'+String(n).padStart(2,'0')+'.html';await page.goto(url,{waitUntil:'domcontentloaded'});
 const q=page.locator('details.question');const count=await q.count();if(count<4)throw Error('Q&A count '+n);
 await page.getByRole('button',{name:'모든 답변 펼치기',exact:true}).click();if(await page.locator('details.question[open]').count()!==count)throw Error('expand '+n);
 await page.getByRole('button',{name:'모든 답변 접기',exact:true}).click();if(await page.locator('details.question[open]').count())throw Error('collapse '+n);
 await page.locator('summary').first().focus();await page.keyboard.press('Enter');if(!await q.first().getAttribute('open').then(x=>x!==null))throw Error('keyboard '+n);
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('overflow '+width+' '+n);
 if(await page.locator('body').getAttribute('data-series')!=='aws')throw Error('category '+n);
 rows.push({width,n,questions:count,expandCollapse:true,keyboard:true,noOverflow:true});
 if([0,7,18].includes(n)){await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:'/tmp/aws-'+n+'-'+width+'.png',fullPage:false})}
 }
 await page.goto(base+'/?category=aws#archive');if(await page.locator('.post:visible').count()!==23)throw Error('AWS filter');await page.fill('#search','RTO');if(await page.locator('.post:visible').count()<1)throw Error('search');await page.fill('#search','zzzznomatch');if(!await page.locator('#empty').isVisible())throw Error('empty');await page.fill('#search','');await page.reload();if(await page.locator('.post:visible').count()!==23)throw Error('persist');await page.screenshot({path:'/tmp/aws-archive-'+width+'.png',fullPage:false});
}
if(errors.length)throw Error(errors.join('\n'));const result={pages:23,viewports:[1440,390],errors,rows};fs.writeFileSync(path.join(root,'learning/aws/browser-checks.json'),JSON.stringify(result,null,2)+'\n');console.log('PASS 23 pages x 2 widths: expand/collapse, keyboard, overflow, categories/search/URL restore');await browser.close();server.close()})().catch(e=>{console.error(e);process.exit(1)});
