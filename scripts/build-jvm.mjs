import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
let marked;
try { ({marked}=await import('marked')); } catch { ({marked}=await import(require.resolve('marked'))); }
const root=path.resolve(path.dirname(new URL(import.meta.url).pathname),'..');
const dir=path.join(root,'content/jvm');
const files=fs.readdirSync(dir).filter(x=>/^\d\d-.+\.md$/.test(x)).sort();
const lessons=files.map(f=>{const raw=fs.readFileSync(path.join(dir,f),'utf8');const [meta,...body]=raw.split('\n\n');return {...JSON.parse(meta),body:body.join('\n\n'),file:f};});
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
for(const l of lessons){
 const id=String(l.n).padStart(2,'0');
 for(const m of l.body.matchAll(/```java\n\/\/ file: ([A-Za-z0-9]+\.java)\n([\s\S]*?)```/g)){
  const dest=path.join(root,'examples/jvm',id);fs.mkdirSync(dest,{recursive:true});fs.writeFileSync(path.join(dest,m[1]),m[2]);
 }
 let html=marked.parse(l.body,{gfm:true});
 let k=0;const toc=[];html=html.replace(/<h2>(.*?)<\/h2>/g,(_,title)=>{const anchor='section-'+(++k);toc.push(`<li><a href="#${anchor}">${title}</a></li>`);return `<h2 id="${anchor}">${title}</h2>`;});
 const prev=lessons.find(x=>x.n===l.n-1),next=lessons.find(x=>x.n===l.n+1);
 const link=x=>`/posts/jvm-study-${String(x.n).padStart(2,'0')}.html`;
 const page=`<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="${esc(l.desc)}"><title>JVM ${id} · ${esc(l.title)} | thisisnew</title><link rel="canonical" href="https://thisisnew.github.io${link(l)}"><link rel="stylesheet" href="/assets/pixel-quest.css"><script src="/assets/series-category.js" defer></script><link rel="stylesheet" href="/assets/jvm-study.css"></head><body><main><a href="/">← 전체 글</a> · <a href="/posts/jvm-study-00.html">JVM 학습 지도</a><header><p class="meta">JVM QUEST · ${id} / 16 · JAVA 21 · 2026-10-19</p><h1>${esc(l.title)}</h1><p class="subtitle">${esc(l.desc)}</p><p class="note">기준: Java SE 21 사양과 HotSpot JDK 21. 첨부 자료의 JVMS 23·JDK 17 발췌는 이 기준으로 대조했습니다. 설명 속 장애 상황은 학습용 가상 사례입니다. 예제는 외부 라이브러리 없이 실행할 수 있습니다.</p></header><aside class="toc" aria-label="이 글의 목차"><h2>이 글에서 배울 것</h2><ol>${toc.join('')}</ol></aside><article>${html}</article><nav aria-label="연재 이동">${prev?`<a href="${link(prev)}">← ${esc(prev.title)}</a>`:'<a href="/">전체 글</a>'}${next?`<a href="${link(next)}">${esc(next.title)} →</a>`:'<a href="/posts/jvm-study-00.html">학습 지도 ↗</a>'}</nav><footer>thisisnew · JVM 학습 연재 · 공식 사양과 구현을 구분해 읽기</footer></main><script src="/assets/jvm-study.js" defer></script></body></html>`;
 const destination=path.join(root,'posts',`jvm-study-${id}.html`);
 // Preserve separately authored deep dives across incremental rebuilds.
 // This is a compatibility bridge; future revisions should migrate them to content/jvm.
 let finalPage=page;
 if(fs.existsSync(destination)){
  const existing=fs.readFileSync(destination,'utf8');
  const deepDive=existing.match(/<!-- JVM-DEEP-DIVE-20261020-\\d{2} --><section class="jvm-depth-expansion"[\\s\\S]*?<\\/section>/);
  if(deepDive)finalPage=page.replace('</article>',deepDive[0]+'</article>');
 }
 fs.writeFileSync(destination,finalPage);
}
const index=path.join(root,'index.html');let home=fs.readFileSync(index,'utf8');
const cards=lessons.map(l=>`<a class="post" data-category="jvm" data-order="${l.n}" href="posts/jvm-study-${String(l.n).padStart(2,'0')}.html"><div class="number">${String(l.n).padStart(2,'0')}</div><div><div class="tags">JAVA · JVM QUEST · ${l.n===0?'LEARNING MAP':`LESSON ${String(l.n).padStart(2,'0')}`}</div><h3>${esc(l.title)}</h3><p>${esc(l.desc)}</p><div class="date">2026.10.19 · Java 21 · ${l.n===0?'학습 안내':`연재 ${l.n}/16`}</div></div><div class="arrow">↗</div></a>`).join('\n');
const block=`<!-- JVM-SERIES-START -->\n${cards}\n<!-- JVM-SERIES-END -->`;
if(home.includes('<!-- JVM-SERIES-START -->'))home=home.replace(/<!-- JVM-SERIES-START -->[\s\S]*?<!-- JVM-SERIES-END -->/,block);else home=home.replace('<div id="articles">','<div id="articles">\n'+block);
home=home.replace(/(<small id="count">)\d+/,(_,prefix)=>prefix+String((home.match(/class="post"/g)||[]).length).padStart(2,'0'));
fs.writeFileSync(index,home);
console.log(`Generated ${lessons.length} JVM pages and home cards.`);
