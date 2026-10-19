import fs from 'node:fs';
import path from 'node:path';
import {marked} from 'marked';
const root=path.resolve(path.dirname(new URL(import.meta.url).pathname),'..');
const dir=path.join(root,'content/aws');
const lessons=fs.readdirSync(dir).filter(x=>/^\d\d-.*\.md$/.test(x)).sort().map(file=>{const [meta,...body]=fs.readFileSync(path.join(dir,file),'utf8').split('\n\n');return {...JSON.parse(meta),body:body.join('\n\n'),file}});
if(lessons.length!==23||lessons.some((x,i)=>x.n!==i))throw Error('Expected all 23 sequential lessons');
const sources=JSON.parse(fs.readFileSync(path.join(root,'learning/aws/pdf-manifest.json'),'utf8'));
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const url=l=>`/posts/aws-study-${String(l.n).padStart(2,'0')}.html`;
const map='| 편 | 학습 글 | 대응 PDF | 원문 쪽수 |\n|---|---|---|---:|\n'+lessons.map(l=>`| ${String(l.n).padStart(2,'0')} | [${l.title}](${url(l)}) | ${sources[l.n].file} | ${sources[l.n].pages} |`).join('\n');
const audit=[];
for(const l of lessons){
 let html=marked.parse(l.body.replace('<!-- AWS-INDEX -->',map),{gfm:true});
 html=html.replaceAll('<details>','<details class="question">').replace(/(<summary>[\s\S]*?<\/summary>)([\s\S]*?)(<\/details>)/g,'$1<div class="answer">$2</div>$3');
 const toc=[];let k=0;html=html.replace(/<h2>(.*?)<\/h2>/g,(_,t)=>{const id='section-'+(++k);toc.push(`<li><a href="#${id}">${t}</a></li>`);return `<h2 id="${id}">${t}</h2>`});
 const prev=lessons[l.n-1],next=lessons[l.n+1];
 const stage=l.n===0?'LEARNING MAP':l.n<=13?'CORE':'DEEP DIVE';
 const page=`<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="${esc(l.desc)}"><title>AWS ${String(l.n).padStart(2,'0')} · ${esc(l.title)} | thisisnew</title><link rel="canonical" href="https://thisisnew.github.io${url(l)}"><link rel="stylesheet" href="/assets/pixel-quest.css"><link rel="stylesheet" href="/assets/jvm-study.css"><link rel="stylesheet" href="/assets/aws-study.css"><script src="/assets/series-category.js" defer></script></head><body data-series="aws"><main><a href="/">← 전체 글</a> · <a href="/posts/aws-study-00.html">AWS 학습 지도</a><header><p class="meta">AWS QUEST · ${String(l.n).padStart(2,'0')} / 22 · ${stage} · 2026-10-20</p><h1>${esc(l.title)}</h1><p class="subtitle">${esc(l.desc)}</p><p class="note">첨부 공부팩 ${esc(sources[l.n].file)} (${sources[l.n].pages}쪽)의 주제를 재구성한 해설입니다. 공식 문서 확인일: 2026-10-20. 장애 사례와 수치는 학습용 가정이며 AWS 실계정 실험 결과가 아닙니다.</p></header><aside class="toc" aria-label="이 글의 목차"><h2>이번 퀘스트에서 배울 것</h2><ol>${toc.join('')}</ol></aside><article>${html}</article><nav aria-label="연재 이동">${prev?`<a href="${url(prev)}">← ${esc(prev.title)}</a>`:'<a href="/?category=aws#archive">AWS 전체 목록</a>'}${next?`<a href="${url(next)}">${esc(next.title)} →</a>`:'<a href="/posts/aws-study-00.html">학습 지도 ↗</a>'}</nav><footer>AWS SAA 학습 연재 · <a href="/learning/aws/verification.html">출처·범위·검증 기록</a></footer></main><script src="/assets/jvm-study.js" defer></script></body></html>`;
 fs.writeFileSync(path.join(root,url(l)),page);
 audit.push({n:l.n,title:l.title,source:sources[l.n].file,pdfPages:sources[l.n].pages,characters:l.body.length,sections:k,questions:(html.match(/<details/g)||[]).length,officialLinks:[...l.body.matchAll(/\]\((https:\/\/[^)]+)\)/g)].map(x=>x[1])});
}
let home=fs.readFileSync(path.join(root,'index.html'),'utf8');
const cards=lessons.map(l=>`<a class="post" data-category="aws" data-order="${l.n}" href="posts/aws-study-${String(l.n).padStart(2,'0')}.html"><div class="number">${String(l.n).padStart(2,'0')}</div><div><div class="tags">AWS QUEST · ${l.n===0?'LEARNING MAP':l.n<=13?'CORE':'DEEP DIVE'}</div><h3>${esc(l.title)}</h3><p>${esc(l.desc)}</p><div class="date">2026.10.20 · SAA-C03 · ${l.n===0?'학습 안내':`${l.n}/22`}</div></div><div class="arrow">↗</div></a>`).join('\n');
const block=`<!-- AWS-SERIES-START -->\n${cards}\n<!-- AWS-SERIES-END -->`;
if(home.includes('<!-- AWS-SERIES-START -->'))home=home.replace(/<!-- AWS-SERIES-START -->[\s\S]*?<!-- AWS-SERIES-END -->/,block);else home=home.replace('<div id="articles">','<div id="articles">\n'+block);
if(!home.includes('data-category-link="aws"'))home=home.replace('<a href="#about">','<a href="#archive" data-category-link="aws">▤ AWS / SAA</a><a href="#about">');
if(!home.includes('data-filter="aws"'))home=home.replace(/(<button class="chip" data-filter="jvm"[\s\S]*?<\/button>)/,'$1<button class="chip" data-filter="aws" aria-pressed="false">AWS / SAA <span class="category-count">23</span></button>');
home=home.replace("jvm:'JVM / Java'","jvm:'JVM / Java',aws:'AWS / SAA'").replace('mysql:1,jvm:2','mysql:1,jvm:2,aws:3').replaceAll('Kafka → MySQL → JVM / Java ·','Kafka → MySQL → JVM / Java → AWS / SAA ·');
const count=(home.match(/class="post"/g)||[]).length;
home=home.replace(/(<small id="count">)\d+/,`$1${count}`).replace(/(전체 <span class="category-count">)\d+/,`$1${count}`);
// Idempotence when rebuilding the same category definitions.
home=home.replaceAll("aws:'AWS / SAA',aws:'AWS / SAA'","aws:'AWS / SAA'").replaceAll('aws:3,aws:3','aws:3');
fs.writeFileSync(path.join(root,'index.html'),home);
fs.writeFileSync(path.join(root,'learning/aws/lesson-audit.json'),JSON.stringify(audit,null,2)+'\n');
console.log(`Generated ${lessons.length} AWS pages; ${audit.reduce((a,x)=>a+x.questions,0)} Q&A; ${count} total archive entries.`);
