document.querySelectorAll('article table').forEach(table=>{const wrap=document.createElement('div');wrap.className='table-scroll';table.before(wrap);wrap.append(table)});
const questions=[...document.querySelectorAll('details.question')];
if(questions.length){const bar=document.createElement('div');bar.className='qa-tools';for(const [text,open]of [['모든 답변 펼치기',true],['모든 답변 접기',false]]){const b=document.createElement('button');b.type='button';b.textContent=text;b.onclick=()=>questions.forEach(q=>q.open=open);bar.append(b)}questions[0].before(bar)}
