(function(){
'use strict';
if(typeof d==='undefined'||typeof $==='undefined') return;

d.customers=d.customers||[];
d.products=d.products||[];
d.products.forEach(p=>{if(p.active===undefined)p.active=true;p.family=p.family||'General';p.subfamily=p.subfamily||'General';p.category=p.category||'General';p.model=p.model||''});
let returnFlow=null;
const badge=document.querySelector('.badge'); if(badge) badge.textContent='Interactive Web Demo v2.5';

// Customers module
const nav=document.getElementById('nav');
if(nav&&!nav.querySelector('[data-p="customers"]')){
  const btn=document.createElement('button');btn.dataset.p='customers';btn.innerHTML='👥 Customers';
  const productsBtn=nav.querySelector('[data-p="products"]');nav.insertBefore(btn,productsBtn);btn.addEventListener('click',()=>go('customers'));
}
titles.customers='Customers';
if(!document.getElementById('customers')){
  const sec=document.createElement('section');sec.id='customers';sec.className='page';
  sec.innerHTML=`<div class="g2"><div class="card"><h3>Add / Edit Customer</h3><div class="pad"><div class="form"><div><label>Customer Name</label><input id="cn" list="customerNames"></div><div><label>Account Number</label><input id="cacc" placeholder="Optional"></div><div><label>Phone</label><input id="cphone"></div><div><label>Email</label><input id="cemail" type="email"></div><div><label>Address</label><input id="caddress"></div><div><label>Default Currency</label><select id="ccurrency"><option value="USD">USD</option><option value="LBP">LBP</option></select></div></div><input type="hidden" id="cid"><div class="row section"><button class="btn primary" onclick="saveCustomer()">Save Customer</button><button class="btn ghost" onclick="clearCustomerForm()">Clear</button></div><datalist id="customerNames"></datalist></div></div><div class="card"><h3>Customer List</h3><div class="pad"><input id="customerSearch" placeholder="Search name, phone, email, account..." oninput="renderCustomers()"><div class="scroll section"><table><thead><tr><th>Name</th><th>Account</th><th>Phone</th><th>Email</th><th>Address</th><th>Currency</th><th></th></tr></thead><tbody id="customerTable"></tbody></table></div></div></div></div>`;
  const products=document.getElementById('products');products.parentNode.insertBefore(sec,products);
}

// POS quick actions + customer helpers
const search=document.getElementById('search');
if(search){
  search.placeholder='Search / scan product, SKU or barcode...';
  search.addEventListener('keydown',productSearchKey);
  if(!document.getElementById('checkoutNewProductBtn')){
    const b=document.createElement('button');b.id='checkoutNewProductBtn';b.className='btn ghost';b.type='button';b.textContent='+ New Product';b.onclick=newProductFromCheckout;search.parentNode.insertBefore(b,search.nextSibling);
  }
  if(!document.getElementById('posShortcutHelp')){
    const h=document.createElement('div');h.id='posShortcutHelp';h.className='help';h.textContent='Scanner: scan + Enter • F2 product search • F4 customer • F8 complete sale • F9 hold sale';search.parentNode.parentNode.insertBefore(h,search.parentNode.nextSibling);
  }
}
const saleCustomer=document.getElementById('saleCustomer');
if(saleCustomer){
  saleCustomer.setAttribute('list','customerSuggestions');saleCustomer.placeholder='Type name, phone, email, account...';saleCustomer.oninput=customerPicked;
  if(!document.getElementById('customerSuggestions')){const dl=document.createElement('datalist');dl.id='customerSuggestions';saleCustomer.parentNode.appendChild(dl)}
  if(!document.getElementById('checkoutNewCustomerBtn')){const b=document.createElement('button');b.id='checkoutNewCustomerBtn';b.className='btn ghost';b.type='button';b.textContent='+ New Customer';b.onclick=newCustomerFromSale;saleCustomer.parentNode.appendChild(b)}
}
const phone=document.getElementById('phone');
if(phone&&!document.getElementById('customerPhones')){const dl=document.createElement('datalist');dl.id='customerPhones';phone.setAttribute('list','customerPhones');phone.parentNode.appendChild(dl)}

// Sale currency, change/remaining and payment reactivity
const payMethod=document.getElementById('payMethod');if(payMethod)payMethod.onchange=()=>renderCart();
const paid=document.getElementById('paid');if(paid)paid.oninput=()=>renderCart();
if(payMethod&&!document.getElementById('saleCurrency')){
  const dwrap=document.createElement('div');dwrap.innerHTML='<label>Sale Currency</label><select id="saleCurrency"><option value="USD">USD</option><option value="LBP">LBP</option></select>';payMethod.parentNode.parentNode.insertBefore(dwrap,payMethod.parentNode.nextSibling);dwrap.querySelector('select').onchange=()=>renderCart();
}
const totalEl=document.getElementById('tot');
if(totalEl&&!document.getElementById('balance')){
  const r=document.createElement('div');r.className='sumrow';r.innerHTML='<span id="balanceLabel">Remaining</span><b id="balance">$0.00</b>';totalEl.parentNode.insertAdjacentElement('afterend',r);
}

// Receipt print/reprint
const modalBox=document.querySelector('#modal .mb');
if(modalBox&&!document.getElementById('printReceiptBtn')){
  const closeBtn=modalBox.querySelector('button');const b=document.createElement('button');b.id='printReceiptBtn';b.className='btn primary section';b.textContent='Print / Reprint';b.onclick=printReceipt;modalBox.insertBefore(b,closeBtn);
  const st=document.createElement('style');st.textContent='@media print{body.gmbf-print .app,body.gmbf-print .toast{display:none!important}body.gmbf-print .modal{display:block!important;position:static!important;background:#fff!important}body.gmbf-print .mb{width:auto!important;max-height:none!important;border-radius:0!important;padding:0!important}body.gmbf-print .mb h3,body.gmbf-print .mb button{display:none!important}body.gmbf-print .receipt{border:0!important}}';document.head.appendChild(st);
}

// Purchase product search + shortcut
const oldSp=document.getElementById('sp');
if(oldSp&&oldSp.tagName==='SELECT'){
  const wrap=document.createElement('div');wrap.className='row';
  const inp=document.createElement('input');inp.id='spText';inp.setAttribute('list','productSuggestions');inp.placeholder='Type / scan product, model, SKU...';inp.oninput=syncPurchaseProduct;inp.addEventListener('keydown',purchaseProductKey);
  const hidden=document.createElement('input');hidden.type='hidden';hidden.id='sp';
  const dl=document.createElement('datalist');dl.id='productSuggestions';
  const nb=document.createElement('button');nb.className='btn ghost';nb.type='button';nb.textContent='+ New Product';nb.onclick=newProductFromPurchase;
  wrap.append(inp,nb,hidden,dl);oldSp.parentNode.replaceChild(wrap,oldSp);
} else if(document.getElementById('spText')) {
  document.getElementById('spText').addEventListener('keydown',purchaseProductKey);
}

function looksLikeBarcode(v){return /^[0-9A-Za-z._-]{4,}$/.test(v||'')&&!/\s/.test(v||'')}
function saleMoney(n,currency=(document.getElementById('saleCurrency')?.value||'USD'),rate=Number(document.getElementById('rate')?.value||d.settings.rate||89500)){return currency==='LBP'?'LBP '+Math.round(Number(n||0)*rate).toLocaleString():'$'+Number(n||0).toFixed(2)}
function productMatch(text){let q=String(text||'').trim().toLowerCase();if(!q)return null;let rows=d.products.filter(p=>p.active!==false);return rows.find(p=>[p.name,p.code,p.model].some(v=>String(v||'').toLowerCase()===q))||rows.find(p=>[p.name,p.code,p.model].some(v=>String(v||'').toLowerCase().startsWith(q)))}
function customerPicked(){let q=$('saleCustomer').value.trim().toLowerCase();let c=d.customers.find(c=>[c.name,c.phone,c.email,c.account].some(v=>String(v||'').toLowerCase()===q))||d.customers.find(c=>String(c.name||'').toLowerCase()===q);if(c){$('saleCustomer').value=c.name;$('phone').value=c.phone||'';$('saleCustomer').dataset.customerId=c.id;$('saleCustomer').dataset.currency=c.currency||'USD';if($('saleCurrency'))$('saleCurrency').value=c.currency||'USD';renderCart()}else{$('saleCustomer').dataset.customerId='';$('saleCustomer').dataset.currency='USD'}}
function newCustomerFromSale(){let n=$('saleCustomer').value.trim();returnFlow={type:'customerFromSale'};go('customers');clearCustomerForm();$('cn').value=n;setTimeout(()=>$('cn').focus(),0)}
function clearCustomerForm(){$('cid').value='';$('cn').value='';$('cacc').value='';$('cphone').value='';$('cemail').value='';$('caddress').value='';$('ccurrency').value='USD'}
function saveCustomer(){let name=$('cn').value.trim();if(!name)return toast('Customer name required');let id=Number($('cid').value||0),c=id?d.customers.find(x=>x.id===id):null,data={name,account:$('cacc').value.trim(),phone:$('cphone').value.trim(),email:$('cemail').value.trim(),address:$('caddress').value.trim(),currency:$('ccurrency').value||'USD'};if(c)Object.assign(c,data);else{c={id:Date.now(),...data};d.customers.push(c)}save();clearCustomerForm();refresh();if(returnFlow?.type==='customerFromSale'){returnFlow=null;go('pos');$('saleCustomer').value=c.name;$('phone').value=c.phone||'';$('saleCustomer').dataset.customerId=c.id;$('saleCustomer').dataset.currency=c.currency||'USD';if($('saleCurrency'))$('saleCurrency').value=c.currency||'USD';renderCart();toast('Customer saved and selected');return}toast('Customer saved')}
function editCustomer(id){let c=d.customers.find(x=>x.id===id);if(!c)return;$('cid').value=c.id;$('cn').value=c.name||'';$('cacc').value=c.account||'';$('cphone').value=c.phone||'';$('cemail').value=c.email||'';$('caddress').value=c.address||'';$('ccurrency').value=c.currency||'USD';go('customers')}
function deleteCustomer(id){d.customers=d.customers.filter(c=>c.id!==id);save();refresh()}
function renderCustomers(){let q=($('customerSearch')?.value||'').toLowerCase(),rows=d.customers.filter(c=>!q||[c.name,c.account,c.phone,c.email,c.address,c.currency].some(v=>String(v||'').toLowerCase().includes(q)));$('customerTable').innerHTML=rows.map(c=>`<tr><td><b>${esc(c.name)}</b></td><td>${esc(c.account||'')}</td><td>${esc(c.phone||'')}</td><td>${esc(c.email||'')}</td><td>${esc(c.address||'')}</td><td>${esc(c.currency||'USD')}</td><td><button class="btn ghost" onclick="editCustomer(${c.id})">Edit</button> <button class="btn danger" onclick="deleteCustomer(${c.id})">Delete</button></td></tr>`).join('')||'<tr><td colspan="7">No customers</td></tr>'}
function renderCustomerSuggestions(){let opts=[];d.customers.forEach(c=>{[[c.name,[c.phone,c.email,c.account]],[c.phone,[c.name,c.email]],[c.email,[c.name,c.phone]],[c.account,[c.name,c.phone]]].forEach(([v,m])=>{if(v)opts.push(`<option value="${esc(v)}">${esc((m||[]).filter(Boolean).join(' • '))}</option>`)})});if($('customerSuggestions'))$('customerSuggestions').innerHTML=opts.join('');if($('customerNames'))$('customerNames').innerHTML=d.customers.map(c=>`<option value="${esc(c.name)}">`).join('');if($('customerPhones'))$('customerPhones').innerHTML=d.customers.filter(c=>c.phone).map(c=>`<option value="${esc(c.phone)}">${esc(c.name)}</option>`).join('')}
function syncPurchaseProduct(){let p=productMatch($('spText').value);$('sp').value=p?p.id:''}
function newProductFromPurchase(){let n=$('spText').value.trim();returnFlow={type:'productFromPurchase'};go('products');if(looksLikeBarcode(n))$('pb').value=n;else $('pn').value=n;setTimeout(()=>$(looksLikeBarcode(n)?'pb':'pn').focus(),0)}
function newProductFromCheckout(){let n=$('search').value.trim();returnFlow={type:'productFromCheckout'};go('products');if(looksLikeBarcode(n))$('pb').value=n;else $('pn').value=n;setTimeout(()=>$(looksLikeBarcode(n)?'pb':'pn').focus(),0)}
function renderTypeahead(){renderCustomerSuggestions();if(!$('productSuggestions'))return;let opts=[];d.products.filter(p=>p.active!==false).forEach(p=>{[[p.name,[p.model,p.code,p.family,p.category]],[p.code,[p.name,p.model]],[p.model,[p.name,p.code]]].forEach(([v,m])=>{if(v)opts.push(`<option value="${esc(v)}">${esc((m||[]).filter(Boolean).join(' • '))}</option>`)})});$('productSuggestions').innerHTML=opts.join('')}
function productSearchKey(e){if(e.key!=='Enter')return;e.preventDefault();let q=$('search').value.trim().toLowerCase();if(!q)return;let exact=d.products.find(p=>p.active!==false&&String(p.code||'').toLowerCase()===q);if(!exact){let matches=d.products.filter(p=>p.active!==false&&[p.name,p.model].some(v=>String(v||'').toLowerCase()===q));if(matches.length===1)exact=matches[0]}if(exact){addToCart(exact.id);$('search').value='';renderProducts();toast('Added: '+exact.name)}else toast('Product / barcode not found')}
function purchaseProductKey(e){if(e.key!=='Enter')return;e.preventDefault();syncPurchaseProduct();if($('sp').value){let p=d.products.find(x=>x.id===Number($('sp').value));if(p)$('spText').value=p.name;setTimeout(()=>$('sq').focus(),0)}else toast('Product / barcode not found')}
function printReceipt(){document.body.classList.add('gmbf-print');window.print();setTimeout(()=>document.body.classList.remove('gmbf-print'),150)}
function archiveProduct(id){let p=d.products.find(x=>x.id===id);if(!p)return;p.active=p.active===false;save();refresh();toast(p.active?'Product restored':'Product archived')}

// Override core POS functions for faster/safe checkout.
renderProducts=function(){let q=($('search')?.value||'').toLowerCase();$('pg').innerHTML=d.products.filter(p=>p.active!==false&&(!q||[p.name,p.code,p.family,p.subfamily,p.category,p.model].some(v=>String(v||'').toLowerCase().includes(q)))).map(p=>`<div class="prod" onclick="addToCart(${p.id})"><div class="pn">${esc(p.name)} ${p.model?'<span class="tag">'+esc(p.model)+'</span>':''}</div><div class="meta">${esc(p.family||'General')} › ${esc(p.subfamily||'General')} › ${esc(p.category||'General')} • ${esc(p.code||'SKU-'+p.id)}</div><div class="price">${money(p.price)}</div><div class="${p.stock<=p.low?'low':''}">${p.stock} in stock</div></div>`).join('')}
addToCart=function(id){let p=d.products.find(x=>x.id===id);if(!p||p.active===false)return;let q=cart[id]?.qty||0;if(q>=p.stock)return toast('Not enough stock');cart[id]=cart[id]||{...p,qty:0};cart[id].qty++;renderCart();setTimeout(()=>$('search')?.focus(),0)}
renderCart=function(){$('cart').innerHTML=Object.values(cart).map(i=>`<div class="cartitem"><div><b>${esc(i.name)} ${esc(i.model||'')}</b><div class="meta">${esc(i.code||'')}</div></div><div><div class="qty"><button onclick="changeQty(${i.id},-1)">−</button><b>${i.qty}</b><button onclick="changeQty(${i.id},1)">+</button></div><b>${saleMoney(i.qty*i.price)}</b></div></div>`).join('')||'<div class="meta">Cart is empty</div>';let x=total(),cur=$('saleCurrency')?.value||'USD',rate=Number($('rate')?.value||89500),paidEntered=Number($('paid')?.value||0),paidUSD=cur==='LBP'?paidEntered/rate:paidEntered,delta=paidUSD-x.total;$('subt').textContent=saleMoney(x.sub,cur,rate);$('tot').textContent=saleMoney(x.total,cur,rate);if($('balance')){$('balanceLabel').textContent=delta>=0?'Change':'Remaining';$('balance').textContent=saleMoney(Math.abs(delta),cur,rate)}}
clearSale=function(){cart={};$('disc').value=0;$('paid').value=0;$('saleCustomer').value='';$('saleCustomer').dataset.customerId='';$('saleCustomer').dataset.currency='USD';$('phone').value='';if($('saleCurrency'))$('saleCurrency').value='USD';renderCart();setTimeout(()=>$('search')?.focus(),0)}
checkout=function(){if(!Object.keys(cart).length)return toast('Cart empty');let x=total(),cur=$('saleCurrency')?.value||'USD',rate=Number($('rate').value||89500),paidEntered=Number($('paid').value||0),paidUSD=cur==='LBP'?paidEntered/rate:paidEntered,payment=$('payMethod').value;if(payment==='Cash'&&paidUSD+0.000001<x.total)return toast('Cash received is less than total');let items=Object.values(cart).map(i=>({id:i.id,name:i.name,model:i.model,qty:i.qty,price:i.price,cost:i.cost||0}));for(const i of items){let p=d.products.find(x=>x.id===i.id);if(!p||p.stock<i.qty)return toast('Not enough stock');p.stock-=i.qty}let sale={id:Date.now(),ts:new Date().toISOString(),items,total:x.total,cost:items.reduce((a,i)=>a+i.qty*i.cost,0),customer:$('saleCustomer').value.trim(),customerId:Number($('saleCustomer').dataset.customerId||0)||null,phone:$('phone').value.trim(),currency:cur,rate,payment,paid:payment==='Cash'?paidEntered:(cur==='LBP'?Math.round(x.total*rate):x.total),changeUSD:payment==='Cash'?Math.max(0,paidUSD-x.total):0};d.sales.push(sale);save();showReceipt(sale);clearSale();refresh()}
receiptText=function(s){let cur=s.currency||'USD',rate=s.rate||d.settings.rate||89500,sm=n=>saleMoney(n,cur,rate);return [d.settings.store,d.settings.phone||'','----------------------------','Receipt #'+String(s.id).slice(-6),...s.items.flatMap(i=>[(i.name+' '+(i.model||'')).trim(),`${i.qty} x ${sm(i.price)} = ${sm(i.qty*i.price)}`]),'----------------------------','TOTAL: '+sm(s.total),'Payment: '+(s.payment||'Cash'),s.payment==='Cash'?'Paid: '+(cur==='LBP'?'LBP '+Math.round(Number(s.paid||0)).toLocaleString():money(s.paid||0)):'',s.payment==='Cash'&&s.changeUSD?'Change: '+sm(s.changeUSD):'',s.customer?'Customer: '+s.customer:'',s.phone?'Phone: '+s.phone:'','----------------------------',d.settings.footer].filter(Boolean).join('\n')}
previewCurrent=function(){if(!Object.keys(cart).length)return toast('Cart empty');let x=total(),cur=$('saleCurrency')?.value||'USD';showReceipt({id:'PREVIEW',items:Object.values(cart),total:x.total,customer:$('saleCustomer').value,phone:$('phone').value,payment:$('payMethod').value,currency:cur,rate:Number($('rate').value||89500),paid:Number($('paid').value||0)})}
holdSale=function(){if(!Object.keys(cart).length)return toast('Cart empty');d.held.push({id:Date.now(),cart,discount:Number($('disc').value||0),customer:$('saleCustomer').value,customerId:$('saleCustomer').dataset.customerId||'',phone:$('phone').value,paid:$('paid').value,payment:$('payMethod').value,currency:$('saleCurrency')?.value||'USD'});save();clearSale();toast('Sale held')}
resumeHeld=function(){if(!d.held.length)return toast('No held sales');let h=d.held.pop();cart=h.cart||{};$('disc').value=h.discount||0;$('saleCustomer').value=h.customer||'';$('phone').value=h.phone||'';$('paid').value=h.paid||0;$('payMethod').value=h.payment||'Cash';if($('saleCurrency'))$('saleCurrency').value=h.currency||'USD';$('saleCustomer').dataset.customerId=h.customerId||'';save();renderCart();toast('Held sale resumed')}

saveProduct=function(){let name=$('pn').value.trim(),enteredCode=$('pb').value.trim();if(!name)return toast('Product name required');if(enteredCode&&d.products.some(p=>String(p.code||'').toLowerCase()===enteredCode.toLowerCase()))return toast('Barcode / SKU already exists');let p={id:Date.now(),code:enteredCode||('SKU-'+String(Date.now()).slice(-6)),name,family:$('pf').value.trim()||'General',subfamily:$('psf').value.trim()||'General',category:$('pc').value.trim()||'General',model:$('pm').value.trim(),supplierId:Number($('ps').value)||null,cost:Number($('pco').value||0),price:Number($('pp').value||0),stock:Number($('pst').value||0),low:Number($('pl').value||3),active:true};d.products.push(p);save();['pb','pn','pf','psf','pc','pm','pco','pp','pst'].forEach(id=>$(id).value='');refresh();if(returnFlow?.type==='productFromPurchase'){returnFlow=null;go('purchase');$('spText').value=p.name;syncPurchaseProduct();toast('Product saved and selected');return}if(returnFlow?.type==='productFromCheckout'){returnFlow=null;go('pos');$('search').value='';if(p.stock>0)addToCart(p.id);else{$('search').value=p.name;renderProducts()}toast(p.stock>0?'Product saved and added':'Product saved — opening stock is 0');return}toast('Product saved')}
renderProductTable=function(){let f=$('ff').value,sf=$('sff').value,c=$('cf').value,rows=d.products.filter(p=>(!f||p.family===f)&&(!sf||p.subfamily===sf)&&(!c||p.category===c));$('pt').innerHTML=rows.map(p=>`<tr><td><b>${esc(p.name)}</b><div class="meta">${esc(p.model||'')}</div></td><td>${esc(p.family)} › ${esc(p.subfamily)} › ${esc(p.category)}</td><td>${esc(p.code||'')}</td><td>${p.stock}</td><td>${money(p.cost)}</td><td>${money(p.price)}</td><td><b>${p.active===false?'Archived':'Active'}</b><br><button class="btn ghost" onclick="archiveProduct(${p.id})">${p.active===false?'Restore':'Archive'}</button></td></tr>`).join('')||'<tr><td colspan="7">No products</td></tr>'}
const oldStockIn=stockIn;stockIn=function(){syncPurchaseProduct();if(!$('sp').value)return toast('Select a product');return oldStockIn()}
renderInvoices=function(){let type=$('invPeriod').value,q=$('invSearch').value.toLowerCase(),rows=d.sales.slice().reverse();if(type!=='all'){let start=periodStart(type);rows=rows.filter(s=>new Date(s.ts)>=start)}rows=rows.filter(s=>{let c=d.customers.find(x=>x.id===s.customerId);return !q||String(s.id).includes(q)||(s.customer||'').toLowerCase().includes(q)||(s.phone||'').toLowerCase().includes(q)||(c&&[c.email,c.account,c.address].some(v=>String(v||'').toLowerCase().includes(q)))});$('invoiceTable').innerHTML=rows.map(s=>`<tr><td>${String(s.id).slice(-6)}</td><td>${new Date(s.ts).toLocaleString()}</td><td>${esc(s.customer||'Walk-in')}</td><td>${esc(s.phone||'')}</td><td>${esc(s.payment||'Cash')}</td><td>${saleMoney(s.total,s.currency||'USD',s.rate||d.settings.rate)}</td><td><button class="btn ghost" onclick="showSale(${s.id})">View</button></td></tr>`).join('')||'<tr><td colspan="7">No sales</td></tr>'}

const oldRefresh=refresh;refresh=function(){oldRefresh();renderCustomers();renderTypeahead();if($('saleCurrency')&&!$('saleCurrency').value)$('saleCurrency').value='USD'}
const oldGo=go;go=function(p){oldGo(p);if(p==='pos')setTimeout(()=>$('search')?.focus(),0)}

document.addEventListener('keydown',e=>{if(e.key==='F2'){e.preventDefault();go('pos');setTimeout(()=>$('search').focus(),0)}else if(e.key==='F4'){e.preventDefault();go('pos');setTimeout(()=>$('saleCustomer').focus(),0)}else if(e.key==='F8'&&$('pos').classList.contains('on')){e.preventDefault();checkout()}else if(e.key==='F9'&&$('pos').classList.contains('on')){e.preventDefault();holdSale()}});

Object.assign(window,{customerPicked,newCustomerFromSale,clearCustomerForm,saveCustomer,editCustomer,deleteCustomer,renderCustomers,syncPurchaseProduct,newProductFromPurchase,newProductFromCheckout,productSearchKey,purchaseProductKey,printReceipt,archiveProduct});
refresh();
})();