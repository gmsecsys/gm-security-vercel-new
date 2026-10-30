(function(){
'use strict';
if(typeof d==='undefined'||typeof $==='undefined') return;

const badge=document.querySelector('.badge');
if(badge) badge.textContent='Interactive Web Demo v2.8';
d.suppliers=d.suppliers||[];

function purchaseDraft(){
  return {
    ref:$('sref')?.value||'',
    productText:$('spText')?.value||'',
    productId:$('sp')?.value||'',
    qty:$('sq')?.value||'1',
    cost:$('sc')?.value||'',
    fee:$('sfee')?.value||'0',
    feeNote:$('sfeeNote')?.value||''
  };
}
function restorePurchaseDraft(x,supplierId){
  if($('sref')) $('sref').value=x.ref;
  if($('spText')) $('spText').value=x.productText;
  if($('sp')) $('sp').value=x.productId;
  if($('sq')) $('sq').value=x.qty;
  if($('sc')) $('sc').value=x.cost;
  if($('sfee')) $('sfee').value=x.fee;
  if($('sfeeNote')) $('sfeeNote').value=x.feeNote;
  if($('ss')) $('ss').value=String(supplierId||'');
  if(typeof calcEffective==='function') calcEffective();
}

function ensureQuickSupplierModal(){
  if($('quickSupplierModal')) return;
  const modal=document.createElement('div');
  modal.id='quickSupplierModal';
  modal.className='modal';
  modal.innerHTML=`<div class="mb" style="width:520px"><h3>New Supplier</h3><div class="form one section"><div><label>Supplier Name</label><input id="quickSupplierName" autocomplete="off" placeholder="Supplier name"></div><div><label>Phone</label><input id="quickSupplierPhone" autocomplete="off" placeholder="Phone (optional)"></div></div><div class="row wrap section"><button class="btn primary" id="quickSupplierSave">Save & Select</button><button class="btn ghost" id="quickSupplierCancel">Cancel</button></div></div>`;
  document.body.appendChild(modal);
  $('quickSupplierSave').onclick=saveQuickSupplier;
  $('quickSupplierCancel').onclick=()=>modal.classList.remove('on');
  $('quickSupplierName').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();$('quickSupplierPhone').focus();}});
  $('quickSupplierPhone').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();saveQuickSupplier();}});
  modal.addEventListener('keydown',e=>{if(e.key==='Escape')modal.classList.remove('on');});
}

function openQuickSupplier(){
  ensureQuickSupplierModal();
  $('quickSupplierName').value='';
  $('quickSupplierPhone').value='';
  $('quickSupplierModal').classList.add('on');
  setTimeout(()=>$('quickSupplierName').focus(),0);
}

function saveQuickSupplier(){
  const name=$('quickSupplierName').value.trim();
  const phone=$('quickSupplierPhone').value.trim();
  if(!name) return toast('Supplier name required');
  const draft=purchaseDraft();
  let supplier=d.suppliers.find(s=>String(s.name||'').trim().toLowerCase()===name.toLowerCase());
  if(supplier){
    if(phone&&!supplier.phone) supplier.phone=phone;
    save();
    $('quickSupplierModal').classList.remove('on');
    if(typeof refresh==='function') refresh();
    restorePurchaseDraft(draft,supplier.id);
    toast('Existing supplier selected');
    return;
  }
  supplier={id:Date.now(),name,phone};
  d.suppliers.push(supplier);
  save();
  $('quickSupplierModal').classList.remove('on');
  if(typeof refresh==='function') refresh();
  restorePurchaseDraft(draft,supplier.id);
  toast('Supplier saved and selected');
}

function addSupplierShortcut(){
  const ss=$('ss');
  if(!ss||$('purchaseNewSupplierBtn')) return;
  const b=document.createElement('button');
  b.id='purchaseNewSupplierBtn';
  b.type='button';
  b.className='btn ghost';
  b.textContent='+ New Supplier';
  b.style.marginTop='7px';
  b.onclick=openQuickSupplier;
  ss.parentElement.appendChild(b);
}

const oldRefresh=window.refresh;
window.refresh=function(){oldRefresh();addSupplierShortcut();};
Object.assign(window,{openQuickSupplier,saveQuickSupplier});
addSupplierShortcut();
})();
