(function(){
'use strict';
if(typeof d==='undefined'||typeof $==='undefined') return;
const badge=document.querySelector('.badge'); if(badge) badge.textContent='Interactive Web Demo v3.1';

let purchaseDraftBeforeProduct=null;
function capturePurchaseDraft(){
  return {
    supplier:$('ss')?.value||'',
    ref:$('sref')?.value||'',
    qty:$('sq')?.value||'1',
    cost:$('sc')?.value||'',
    fee:$('sfee')?.value||'0',
    feeNote:$('sfeeNote')?.value||''
  };
}
function restorePurchaseDraftAfterProduct(x){
  if(!x) return;
  if($('ss')) $('ss').value=x.supplier;
  if($('sref')) $('sref').value=x.ref;
  if($('sq')) $('sq').value=x.qty;
  if($('sc')) $('sc').value=x.cost;
  if($('sfee')) $('sfee').value=x.fee;
  if($('sfeeNote')) $('sfeeNote').value=x.feeNote;
  if(typeof calcEffective==='function') calcEffective();
}

const oldNewProductFromPurchase=window.newProductFromPurchase;
if(typeof oldNewProductFromPurchase==='function'){
  window.newProductFromPurchase=function(){
    purchaseDraftBeforeProduct=capturePurchaseDraft();
    return oldNewProductFromPurchase();
  };
  try{newProductFromPurchase=window.newProductFromPurchase}catch(e){}
}

const oldSaveProduct=window.saveProduct;
if(typeof oldSaveProduct==='function'){
  window.saveProduct=function(){
    const before=(d.products||[]).length;
    const draft=purchaseDraftBeforeProduct;
    const r=oldSaveProduct();
    const created=(d.products||[]).length>before;
    if(created&&draft&&$('purchase')?.classList.contains('on')){
      restorePurchaseDraftAfterProduct(draft);
      purchaseDraftBeforeProduct=null;
    } else if(created){
      purchaseDraftBeforeProduct=null;
    }
    return r;
  };
  try{saveProduct=window.saveProduct}catch(e){}
}

function clearSavedPurchaseForm(){
  if($('ss')) $('ss').value='';
  if($('sref')) $('sref').value='';
  if($('spText')) $('spText').value='';
  if($('sp')) $('sp').value='';
  if($('sq')) $('sq').value='1';
  if($('sc')) $('sc').value='';
  if($('sfee')) $('sfee').value='0';
  if($('sfeeNote')) $('sfeeNote').value='';
  if(typeof calcEffective==='function') calcEffective();
}
const oldStockInV31=window.stockIn;
if(typeof oldStockInV31==='function'){
  window.stockIn=function(){
    const before=(d.purchases||[]).length;
    const r=oldStockInV31();
    if((d.purchases||[]).length>before){
      clearSavedPurchaseForm();
      setTimeout(()=>$('ss')?.focus(),0);
    }
    return r;
  };
  try{stockIn=window.stockIn}catch(e){}
}

Object.assign(window,{capturePurchaseDraft,clearSavedPurchaseForm});
})();
