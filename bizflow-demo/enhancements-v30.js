(function(){
'use strict';
if(typeof $==='undefined') return;

const badge=document.querySelector('.badge');
if(badge) badge.textContent='Interactive Web Demo v3.0';

function ensureExitVisible(){
  const side=document.querySelector('.side');
  const nav=document.getElementById('nav');
  const btn=document.getElementById('quitAppBtn');
  if(!side||!nav||!btn) return;

  side.style.display='flex';
  side.style.flexDirection='column';
  side.style.height='100vh';
  side.style.overflow='hidden';
  nav.style.flex='1 1 auto';
  nav.style.minHeight='0';
  nav.style.overflowY='auto';
  nav.style.paddingBottom='8px';

  btn.textContent='⏻ Exit';
  btn.style.flex='0 0 auto';
  btn.style.marginTop='10px';
  btn.style.background='#b93f3f';
  btn.style.color='#fff';
  btn.style.border='1px solid #ffffff33';
  btn.style.boxShadow='0 -6px 18px #18395022';
  btn.style.position='relative';
  btn.style.zIndex='3';
}

function openExitFlow(){
  if(!window.confirm('Are you sure you want to exit?')) return;
  const modal=$('quitBackupModal');
  if(modal){
    const title=modal.querySelector('h3');
    const p=modal.querySelector('p');
    if(title) title.textContent='Exit GM BizFlow';
    if(p) p.textContent='Do you want to create a backup before exiting?';
    if($('backupQuitYes')) $('backupQuitYes').textContent='Backup & Exit';
    if($('backupQuitNo')) $('backupQuitNo').textContent='Exit Without Backup';
    if($('backupQuitCancel')) $('backupQuitCancel').textContent='Cancel';
    modal.classList.add('on');
    return;
  }
  if(typeof window.openQuitDialog==='function') window.openQuitDialog();
}

function wireExit(){
  const btn=$('quitAppBtn');
  if(!btn) return;
  btn.onclick=openExitFlow;
}

ensureExitVisible();
wireExit();
window.addEventListener('resize',ensureExitVisible);
Object.assign(window,{openExitFlow});
})();
