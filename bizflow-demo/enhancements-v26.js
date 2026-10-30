(function(){
'use strict';
if(typeof d==='undefined'||typeof $==='undefined'||typeof go==='undefined') return;

const badge=document.querySelector('.badge');
if(badge) badge.textContent='Interactive Web Demo v2.6';

let preserveDraftNavigation=false;
let suppressCancelConfirm=false;

function currentPage(){return document.querySelector('.page.on')?.id||'dashboard'}
function val(id){return document.getElementById(id)?.value??''}
function num(id){return Number(val(id)||0)}
function nonblank(ids){return ids.some(id=>String(val(id)).trim()!=='')}

function pageHasUnsavedData(page){
  if(page==='pos'){
    return Object.keys(cart||{}).length>0 || num('disc')!==0 || num('paid')!==0 || nonblank(['saleCustomer','phone']);
  }
  if(page==='purchase'){
    return nonblank(['sref','spText','sc','sfeeNote']) || num('sq')!==1 || num('sfee')!==0 || (val('ss')&&val('ss')!=='0');
  }
  if(page==='products'){
    return nonblank(['pb','pn','pf','psf','pc','pm','pco','pp','pst']) || (val('ps')&&val('ps')!=='0');
  }
  if(page==='customers'){
    return nonblank(['cid','cn','cacc','cphone','cemail','caddress']) || val('ccurrency')==='LBP';
  }
  if(page==='suppliers') return nonblank(['sn','sph']);
  if(page==='adjust') return nonblank(['anote']) || num('aq')!==1;
  if(page==='reports') return nonblank(['ed','ea']);
  if(page==='settings'){
    if(!d.settings) return false;
    return String(val('store'))!==String(d.settings.store||'') || String(val('storeph'))!==String(d.settings.phone||'') || Number(val('setrate')||0)!==Number(d.settings.rate||0) || String(val('footer'))!==String(d.settings.footer||'');
  }
  return false;
}

function anyUnsavedData(){
  return ['pos','purchase','products','customers','suppliers','adjust','reports','settings'].some(pageHasUnsavedData);
}

const coreClearSale=clearSale;
function discardPageDraft(page){
  suppressCancelConfirm=true;
  try{
    if(page==='pos'){
      coreClearSale();
    } else if(page==='purchase'){
      if($('sref'))$('sref').value=''; if($('spText'))$('spText').value=''; if($('sp'))$('sp').value=''; if($('sq'))$('sq').value=1; if($('sc'))$('sc').value=''; if($('sfee'))$('sfee').value=0; if($('sfeeNote'))$('sfeeNote').value=''; if($('ss'))$('ss').value=''; if(typeof calcEffective==='function')calcEffective();
    } else if(page==='products'){
      ['pb','pn','pf','psf','pc','pm','pco','pp','pst'].forEach(id=>{if($(id))$(id).value=''}); if($('ps'))$('ps').value=''; if($('pl'))$('pl').value=3;
    } else if(page==='customers'){
      if(typeof window.clearCustomerForm==='function')window.clearCustomerForm();
    } else if(page==='suppliers'){
      if($('sn'))$('sn').value=''; if($('sph'))$('sph').value='';
    } else if(page==='adjust'){
      if($('aq'))$('aq').value=1; if($('anote'))$('anote').value='';
    } else if(page==='reports'){
      if($('ed'))$('ed').value=''; if($('ea'))$('ea').value='';
    } else if(page==='settings'){
      if($('store'))$('store').value=d.settings.store||''; if($('storeph'))$('storeph').value=d.settings.phone||''; if($('setrate'))$('setrate').value=d.settings.rate||89500; if($('footer'))$('footer').value=d.settings.footer||'';
    }
  } finally { suppressCancelConfirm=false; }
}

const coreGo=go;
go=function(page){
  const from=currentPage();
  if(from!==page && !preserveDraftNavigation && pageHasUnsavedData(from)){
    const ok=window.confirm('You have unsaved changes. Are you sure you want to cancel?');
    if(!ok) return false;
    discardPageDraft(from);
  }
  preserveDraftNavigation=false;
  coreGo(page);
  return true;
};
window.go=go;

document.addEventListener('click',function(e){
  const btn=e.target.closest('button');
  if(!btn) return;
  if(btn.id==='checkoutNewCustomerBtn'||btn.id==='checkoutNewProductBtn'||(btn.closest('#purchase')&&btn.textContent.trim()==='+ New Product')){
    preserveDraftNavigation=true;
  }
},true);

clearSale=function(){
  if(!suppressCancelConfirm && pageHasUnsavedData('pos')){
    if(!window.confirm('Are you sure you want to cancel this sale?')) return false;
  }
  coreClearSale();
  return true;
};
window.clearSale=clearSale;

const coreCheckout=checkout;
checkout=function(){
  const before=(d.sales||[]).length;
  suppressCancelConfirm=true;
  try{ coreCheckout(); } finally { suppressCancelConfirm=false; }
  return (d.sales||[]).length>before;
};
window.checkout=checkout;

const coreHoldSale=holdSale;
holdSale=function(){
  const before=(d.held||[]).length;
  suppressCancelConfirm=true;
  try{ coreHoldSale(); } finally { suppressCancelConfirm=false; }
  return (d.held||[]).length>before;
};
window.holdSale=holdSale;

window.addEventListener('beforeunload',function(e){
  if(!anyUnsavedData()) return;
  e.preventDefault();
  e.returnValue='';
});

function backupFilename(){
  const stamp=new Date().toISOString().replace(/[:.]/g,'-');
  return 'GM_BizFlow_Backup_'+stamp+'.json';
}
function downloadBackup(){
  try{ if(typeof save==='function')save(); }catch(e){}
  const payload={app:'GM BizFlow',version:'2.6',createdAt:new Date().toISOString(),data:d};
  const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=url;a.download=backupFilename();document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);
}
function showExitedScreen(backedUp){
  document.body.innerHTML=`<div style="min-height:100vh;display:grid;place-items:center;background:#eef3f8;font-family:Segoe UI,Arial,sans-serif;color:#203040"><div style="background:white;border:1px solid #dce5ed;border-radius:16px;padding:34px;max-width:520px;text-align:center;box-shadow:0 10px 30px #1f3d5615"><h2 style="margin-top:0">GM BizFlow is closed</h2><p>${backedUp?'Backup downloaded successfully. ':''}You can safely close this tab.</p><button onclick="location.reload()" style="border:0;border-radius:9px;padding:10px 14px;background:#2f6d96;color:white;font-weight:700;cursor:pointer">Reopen GM BizFlow</button></div></div>`;
}
function openQuitDialog(){
  if(anyUnsavedData()){
    const ok=window.confirm('You have unsaved changes. Are you sure you want to cancel them and quit?');
    if(!ok) return;
    ['pos','purchase','products','customers','suppliers','adjust','reports','settings'].forEach(p=>{if(pageHasUnsavedData(p))discardPageDraft(p)});
  }
  const modal=$('quitBackupModal');
  if(modal) modal.classList.add('on');
}
function finishQuit(withBackup){
  if(withBackup) downloadBackup();
  const modal=$('quitBackupModal');if(modal)modal.classList.remove('on');
  showExitedScreen(withBackup);
}

const side=document.querySelector('.side');
if(side&&!$('quitAppBtn')){
  side.style.display='flex';side.style.flexDirection='column';
  const nav=document.getElementById('nav');if(nav)nav.style.flex='1';
  const q=document.createElement('button');q.id='quitAppBtn';q.type='button';q.textContent='⏻ Quit';q.style.cssText='width:100%;border:1px solid #ffffff33;border-radius:9px;padding:11px 12px;background:#b93f3f;color:#fff;font-weight:800;cursor:pointer;margin-top:12px;text-align:left';q.onclick=openQuitDialog;side.appendChild(q);
}

if(!$('quitBackupModal')){
  const modal=document.createElement('div');modal.id='quitBackupModal';modal.className='modal';modal.innerHTML=`<div class="mb" style="width:520px"><h3>Quit GM BizFlow</h3><p style="line-height:1.5">Do you want to create a backup before quitting?</p><div class="row wrap section"><button class="btn primary" id="backupQuitYes">Backup & Quit</button><button class="btn danger" id="backupQuitNo">Quit Without Backup</button><button class="btn ghost" id="backupQuitCancel">Cancel</button></div></div>`;document.body.appendChild(modal);
  $('backupQuitYes').onclick=()=>finishQuit(true);
  $('backupQuitNo').onclick=()=>finishQuit(false);
  $('backupQuitCancel').onclick=()=>modal.classList.remove('on');
}

Object.assign(window,{downloadBackup,openQuitDialog,finishQuit});
})();
