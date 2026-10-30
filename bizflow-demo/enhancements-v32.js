(function(){
'use strict';
if(typeof d==='undefined'||typeof $==='undefined') return;
const badge=document.querySelector('.badge'); if(badge) badge.textContent='Interactive Web Demo v3.2';

function capturePurchase(){
  return {
    supplier:$('ss')?.value||'', ref:$('sref')?.value||'', productText:$('spText')?.value||'', productId:$('sp')?.value||'',
    qty:$('sq')?.value||'1', cost:$('sc')?.value||'', fee:$('sfee')?.value||'0', feeNote:$('sfeeNote')?.value||''
  };
}
function restorePurchase(x, keepNewProduct=false){
  if(!x) return;
  if($('ss')) $('ss').value=x.supplier;
  if($('sref')) $('sref').value=x.ref;
  if(!keepNewProduct){ if($('spText')) $('spText').value=x.productText; if($('sp')) $('sp').value=x.productId; }
  if($('sq')) $('sq').value=x.qty;
  if($('sc')) $('sc').value=x.cost;
  if($('sfee')) $('sfee').value=x.fee;
  if($('sfeeNote')) $('sfeeNote').value=x.feeNote;
  if(typeof calcEffective==='function') calcEffective();
}

let newProductDraft=null;
document.addEventListener('click',e=>{
  const b=e.target.closest('button');
  if(!b) return;
  if(b.closest('#purchase') && b.textContent.trim()==='+ New Product') newProductDraft=capturePurchase();
},true);

const oldSaveProductV32=window.saveProduct;
if(typeof oldSaveProductV32==='function'){
  window.saveProduct=function(){
    const before=(d.products||[]).length;
    const draft=newProductDraft;
    const r=oldSaveProductV32();
    if((d.products||[]).length>before && draft && $('purchase')?.classList.contains('on')){
      restorePurchase(draft,true);
      newProductDraft=null;
    }
    return r;
  };
  try{saveProduct=window.saveProduct}catch(e){}
}

let quickStockDraft=null;
document.addEventListener('click',e=>{
  const b=e.target.closest('button');
  if(!b) return;
  if(b.id==='quickInBtn'||b.id==='quickOutBtn') quickStockDraft=capturePurchase();
  if(b.id==='quickStockCancel') quickStockDraft=null;
  if(b.id==='quickStockSave'){
    const draft=quickStockDraft;
    setTimeout(()=>{
      if(draft && !$('quickStockModal')?.classList.contains('on')){
        restorePurchase(draft,false);
        quickStockDraft=null;
      }
    },0);
  }
},true);

Object.assign(window,{capturePurchaseDraftV32:capturePurchase,restorePurchaseDraftV32:restorePurchase});
})();
