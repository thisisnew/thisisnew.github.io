'use strict';
// All answers remain available without JavaScript via native <details>.
(() => {
  const main = document.querySelector('main');
  if (!main) return;
  const bar = document.createElement('div');
  bar.className = 'study-actions';
  for (const [label, open] of [['답변 모두 펼치기', true], ['답변 모두 접기', false]]) {
    const b = document.createElement('button'); b.type = 'button'; b.textContent = label;
    b.addEventListener('click', () => main.querySelectorAll('details').forEach(d => {d.open = open;}));
    bar.appendChild(b);
  }
  const toc = document.createElement('nav');toc.className='study-toc';toc.setAttribute('aria-label','전체 학습 목차');
  const label = document.createElement('strong');label.textContent='전체 학습 목차';toc.append(label);
  main.querySelectorAll('h2').forEach((h,i) => {
    if (!h.id) h.id='study-heading-'+i;
    const a=document.createElement('a');a.href='#'+h.id;a.textContent=h.textContent;toc.append(a);
  });
  const title = main.querySelector('h1');
  title.after(bar,toc);
})();
