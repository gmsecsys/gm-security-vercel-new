(function(){
'use strict';
if(typeof $==='undefined') return;
const badge=document.querySelector('.badge');
if(badge) badge.textContent='Interactive Web Demo v3.3';

function pinExit(){
  const btn=$('quitAppBtn');
  const nav=$('nav');
  if(!btn) return;
  btn.textContent='⏻ EXIT';
  btn.style.position='fixed';
  btn.style.left='15px';
  btn.style.bottom='max(14px, env(safe-area-inset-bottom))';
  btn.style.width='220px';
  btn.style.margin='0';
  btn.style.padding='12px 14px';
  btn.style.background='#b93f3f';
  btn.style.color='#fff';
  btn.style.border='1px solid #ffffff44';
  btn.style.borderRadius='10px';
  btn.style.fontWeight='900';
  btn.style.fontSize='14px';
  btn.style.textAlign='left';
  btn.style.cursor='pointer';
  btn.style.zIndex='99999';
  btn.style.boxShadow='0 8px 24px #00000033';
  if(nav) nav.style.paddingBottom='76px';
}

pinExit();
setTimeout(pinExit,0);
setTimeout(pinExit,250);
window.addEventListener('resize',pinExit);
window.addEventListener('orientationchange',()=>setTimeout(pinExit,100));
})();
