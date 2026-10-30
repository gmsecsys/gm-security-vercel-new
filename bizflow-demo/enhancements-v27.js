(function(){
'use strict';
if(typeof d==='undefined'||typeof $==='undefined') return;

const badge=document.querySelector('.badge');
if(badge) badge.textContent='Interactive Web Demo v2.7';
d.adjustments=d.adjustments||[];

function productOptions(){
  return (d.products||[]).filter(p=>p.active!==false).map(p=>`<option value="${p.id}">${esc(p.name)}${p.model?' — '+esc(p.model):''} — Stock ${Number(p.stock||0)}</option>`).join('');
}
function selectedPurchaseProductId(){
  const hidden=document.getElementById('sp');
  if(hidden&&Number(hidden.value)) return Number(hidden.value);
  const text=document.getElementById('spText')?.value||'';
  if(typeof productMatch==='function'){
    const p=productMatch(text); if(p) return Number(p.id);
  }
  return 0;
}
function ensureQuickStockModal(){
  if($('quickStockModal')) return;
  const modal=document.createElement('div');
  modal.id='quickStockModal'; modal.className='modal';
  modal.innerHTML=`<div class="mb" style="width:560px"><h3 id="quickStockTitle">Quick Stock Adjustment</h3><div class="form section"><div><label>Product</label><select id="quickStockProduct"></select></div><div><label>Quantity</label><input id="quickStockQty" type="number" min="1" step="1" value="1"></div><div><label>Reason</label><select id="quickStockReason"><option>Correction</option><option>Damaged</option><option>Return</option><option>Sample</option><option>Internal Use</option><option>Found Stock</option><option>Purchase Correction</option><option>Other</option></select></div><div><label>Note (optional)</label><input id="quickStockNote" placeholder="Why are you changing stock?"></div></div><div class="notice section" id="quickStockInfo">Current stock: —</div><div class="row wrap section"><button class="btn primary" id="quickStockSave">Save</button><button class="btn ghost" id="quickStockCancel">Cancel</button></div></div>`;
  document.body.appendChild(modal);
  $('quickStockProduct').onchange=updateQuickStockInfo;
  $('quickStockCancel').onclick=()=>modal.classList.remove('on');
  $('quickStockSave').onclick=saveQuickStock;
}
let quickStockType='IN';
function updateQuickStockInfo(){
  const id=Number($('quickStockProduct')?.value||0),p=(d.products||[]).find(x=>Number(x.id)===id);
  if($('quickStockInfo')) $('quickStockInfo').textContent=p?`Current stock: ${Number(p.stock||0)} • After ${quickStockType}: ${quickStockType==='IN'?Number(p.stock||0)+Number($('quickStockQty')?.value||1):Math.max(0,Number(p.stock||0)-Number($('quickStockQty')?.value||1))}`:'Current stock: —';
}
function openQuickStock(type){
  ensureQuickStockModal();
  quickStockType=type==='OUT'?'OUT':'IN';
  $('quickStockTitle').textContent=quickStockType==='IN'?'Quick Stock IN (+)':'Quick Stock OUT (−)';
  $('quickStockProduct').innerHTML=productOptions();
  const preferred=selectedPurchaseProductId();
  if(preferred&&[...$('quickStockProduct').options].some(o=>Number(o.value)===preferred)) $('quickStockProduct').value=String(preferred);
  $('quickStockQty').value=1;
  $('quickStockNote').value='';
  $('quickStockReason').value=quickStockType==='IN'?'Correction':'Damaged';
  $('quickStockQty').oninput=updateQuickStockInfo;
  updateQuickStockInfo();
  $('quickStockModal').classList.add('on');
  setTimeout(()=>$('quickStockQty').focus(),0);
}
function saveQuickStock(){
  const id=Number($('quickStockProduct').value||0),qty=Number($('quickStockQty').value||0),reason=$('quickStockReason').value,note=$('quickStockNote').value.trim();
  const p=(d.products||[]).find(x=>Number(x.id)===id);
  if(!p||qty<=0) return toast('Check product and quantity');
  if(quickStockType==='OUT'&&Number(p.stock||0)<qty) return toast('Not enough stock');
  const before=Number(p.stock||0);
  p.stock=before+(quickStockType==='IN'?qty:-qty);
  d.adjustments.push({id:Date.now(),ts:new Date().toISOString(),productId:p.id,type:quickStockType,qty,reason,note,source:'Purchase Quick Action'});
  save();
  $('quickStockModal').classList.remove('on');
  if(typeof refresh==='function') refresh();
  // Keep the purchase product selection and draft intact.
  if($('sp')) $('sp').value=String(p.id);
  if($('spText')&&!$('spText').value.trim()) $('spText').value=p.name;
  toast(`Stock ${quickStockType} saved: ${p.name} (${before} → ${p.stock})`);
}

function addPurchaseShortcuts(){
  const purchase=document.getElementById('purchase');
  if(!purchase||$('purchaseQuickStockActions')) return;
  const spText=$('spText');
  if(!spText) return;
  const row=spText.closest('.row')||spText.parentElement;
  const box=document.createElement('div');
  box.id='purchaseQuickStockActions';
  box.className='row wrap section';
  box.style.marginTop='8px';
  box.innerHTML='<span class="meta" style="margin-right:4px">Quick stock:</span><button type="button" class="btn green" id="quickInBtn">+ Stock IN</button><button type="button" class="btn danger" id="quickOutBtn">− Stock OUT</button>';
  row.insertAdjacentElement('afterend',box);
  $('quickInBtn').onclick=()=>openQuickStock('IN');
  $('quickOutBtn').onclick=()=>openQuickStock('OUT');
}

const oldRefresh=window.refresh;
window.refresh=function(){oldRefresh();addPurchaseShortcuts();if($('quickStockProduct')&&$('quickStockModal')?.classList.contains('on')){$('quickStockProduct').innerHTML=productOptions();updateQuickStockInfo();}};
Object.assign(window,{openQuickStock,saveQuickStock});
addPurchaseShortcuts();
})();