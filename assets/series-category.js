/* Shared category identity for every lesson, including regenerated pages. */
const seriesMatch=location.pathname.match(/\/(kafka|mysql|jvm|aws|redis)-study-(\d+)\.html$/);
if(seriesMatch){
 const key=seriesMatch[1],label={kafka:'Kafka',mysql:'MySQL',jvm:'JVM / Java',aws:'AWS / SAA',redis:'Redis'}[key];
 document.body.dataset.series=key;
 const main=document.querySelector('main');
 if(main){const link=document.createElement('a');link.className='series-home';link.href='/?category='+key+'#archive';link.textContent=label+' · 전체 학습 목록 →';main.prepend(link)}
}
