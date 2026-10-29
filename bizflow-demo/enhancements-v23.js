(function(){
'use strict';
if(typeof d==='undefined'||typeof $==='undefined') return;
d.customers=d.customers||[];

const nav=document.getElementById('nav');
if(nav&&!nav.querySelector('[data-p="customers"]')){
  const btn=document.createElement('button'); btn.dataset.p='customers'; btn.innerHTML='👥 Customers';
  const productsBtn=nav.querySelector('[data-p="products"]'); nav.insertBefore(btn,productsBtn);
  btn.addEventListener('click',()=>go('customers'));
}
titles.customers='Customers';
const badge=document.querySelector('.badge'); if(badge) badge.textContent='Interactive Web Demo v2.3';

if(!document.getElementById('customers')){
 const sec=document.createElement('section'); sec.id='customers'; sec.className='page';
 sec.innerHTML=`<div class="g2"><div class="card"><h3>Add / Edit Customer</h3><div class="pad"><div class="form"><div><label>Customer Name</label><input id="cn" list="customerNames"></div><div><label>Account Number</label><input id="cacc" placeholder="Optional"></div><div><label>Phone</label><input id="cphone"></div><div><label>Email</label><input id="cemail" type="email"></div><div><label>Address</label><input id="caddress"></div><div><label>Default Currency</label><select id="ccurrency"><option value="USD">USD</option><option value="LBP">LBP</option></select></div></div><input type="hidden" id="cid"><div class="row section"><button class="btn primary" onclick="saveCustomer()">Save Customer</button><button class="btn ghost" onclick="clearCustomerForm()">Clear</button></div><datalist id="customerNames"></datalist></div></div><div class="card"><h3>Customer List</h3><div class="pad"><input id="customerSearch" placeholder="Search name, phone, email, account..." oninput="renderCustomers()"><div class="scroll section"><table><thead><tr><th>Name</th><th>Account</th><th>Phone</th><th>Email</th><th>Address</th><th>Currency</th><th></th></tr></thead><tbody id="customerTable"></tbody></table></div></div></div></div>`;
 const products=document.getElementById('products'); products.parentNode.insertBefore(sec,products);
}

const saleCustomer=document.getElementById('saleCustomer');
if(saleCustomer&&!document.getElementById('customerSuggestions')){
 saleCustomer.setAttribute('list','customerSuggestions'); saleCustomer.placeholder='Type name, phone, email...'; saleCustomer.setAttribute('oninput','customerPicked()');
 const dl=document.createElement('datalist'); dl.id='customerSuggestions'; saleCustomer.parentNode.appendChild(dl);
 const newBtn=document.createElement('button'); newBtn.className='btn ghost'; newBtn.type='button'; newBtn.textContent='+ New Customer'; newBtn.onclick=newCustomerFromSale; saleCustomer.parentNode.appendChild(newBtn);
}
const phone=document.getElementById('phone');
if(phone&&!document.getElementById('customerPhones')){const dl=document.createElement('datalist');dl.id='customerPhones';phone.setAttribute('list','customerPhones');phone.parentNode.appendChild(dl)}

const oldSp=document.getElementById('sp');
if(oldSp&&oldSp.tagName==='SELECT'){
 const wrap=document.createElement('div'); wrap.className='row';
 const inp=document.createElement('input'); inp.id='spText'; inp.setAttribute('list','productSuggestions'); inp.placeholder='Type product, model, SKU...'; inp.oninput=syncPurchaseProduct;
 const hidden=document.createElement('input'); hidden.type='hidden'; hidden.id='spHidden';
 const dl=document.createElement('datalist'); dl.id='productSuggestions';
 const nb=document.createElement('button'); nb.className='btn ghost'; nb.type='button'; nb.textContent='+ New Product'; nb.onclick=newProductFromPurchase;
 wrap.append(inp,nb,hidden,dl); oldSp.parentNode.replaceChild(wrap,oldSp);
}

window.customerPicked=function(){let q=$('saleCustomer').value.trim().toLowerCase();let c=d.customers.find(c=>[c.name,c.phone,c.email,c.account].some(v=>String(v||'').toLowerCase()===q))||d.customers.find(c=>String(c.name||'').toLowerCase()===q);if(c){$('saleCustomer').value=c.name;$('phone').value=c.phone||'';$('saleCustomer').dataset.customerId=c.id;$('saleCustomer').dataset.currency=c.currency||'USD'}else{$('saleCustomer').dataset.customerId='';$('saleCustomer').dataset.currency='USD'}};
window.newCustomerFromSale=function(){let n=$('saleCustomer').value.trim();go('customers');clearCustomerForm();$('cn').value=n;setTimeout(()=>$('cn').focus(),0)};
window.clearCustomerForm=function(){$('cid').value='';$('cn').value='';$('cacc').value='';$('cphone').value='';$('cemail').value='';$('caddress').value='';$('ccurrency').value='USD'};
window.saveCustomer=function(){let name=$('cn').value.trim();if(!name)return toast('Customer name required');let id=Number($('cid').value||0);let c=id?d.customers.find(x=>x.id===id):null;let data={name,account:$('cacc').value.trim(),phone:$('cphone').value.trim(),email:$('cemail').value.trim(),address:$('caddress').value.trim(),currency:$('ccurrency').value||'USD'};if(c)Object.assign(c,data);else d.customers.push({id:Date.now(),...data});save();clearCustomerForm();refresh();toast('Customer saved')};
window.editCustomer=function(id){let c=d.customers.find(x=>x.id===id);if(!c)return;$('cid').value=c.id;$('cn').value=c.name||'';$('cacc').value=c.account||'';$('cphone').value=c.phone||'';$('cemail').value=c.email||'';$('caddress').value=c.address||'';$('ccurrency').value=c.currency||'USD';go('customers')};
window.deleteCustomer=function(id){d.customers=d.customers.filter(c=>c.id!==id);save();refresh()};
window.renderCustomers=function(){let q=($('customerSearch')?.value||'').toLowerCase();let rows=d.customers.filter(c=>!q||[c.name,c.account,c.phone,c.email,c.address,c.currency].some(v=>String(v||'').toLowerCase().includes(q)));$('customerTable').innerHTML=rows.map(c=>`<tr><td><b>${esc(c.name)}</b></td><td>${esc(c.account||'')}</td><td>${esc(c.phone||'')}</td><td>${esc(c.email||'')}</td><td>${esc(c.address||'')}</td><td>${esc(c.currency||'USD')}</td><td><button class="btn ghost" onclick="editCustomer(${c.id})">Edit</button> <button class="btn danger" onclick="deleteCustomer(${c.id})">Delete</button></td></tr>`).join('')||'<tr><td colspan="7">No customers</td></tr>'};
window.renderCustomerSuggestions=function(){if($('customerSuggestions'))$('customerSuggestions').innerHTML=d.customers.map(c=>`<option value="${esc(c.name)}">${esc([c.phone,c.email,c.account].filter(Boolean).join(' • '))}</option>`).join('');if($('customerNames'))$('customerNames').innerHTML=d.customers.map(c=>`<option value="${esc(c.name)}">`).join('');if($('customerPhones'))$('customerPhones').innerHTML=d.customers.filter(c=>c.phone).map(c=>`<option value="${esc(c.phone)}">${esc(c.name)}</option>`).join('')};
window.productMatch=function(text){let q=String(text||'').trim().toLowerCase();if(!q)return null;return d.products.find(p=>[p.name,p.code,p.model].some(v=>String(v||'').toLowerCase()===q))||d.products.find(p=>[p.name,p.code,p.model].some(v=>String(v||'').toLowerCase().startsWith(q)))};
window.syncPurchaseProduct=function(){let p=productMatch($('spText').value);$('spHidden').value=p?p.id:''};
window.newProductFromPurchase=function(){let n=$('spText').value.trim();go('products');$('pn').value=n;setTimeout(()=>$('pn').focus(),0)};
window.renderTypeahead=function(){renderCustomerSuggestions();if($('productSuggestions'))$('productSuggestions').innerHTML=d.products.map(p=>`<option value="${esc(p.name)}">${esc([p.model,p.code,p.family,p.category].filter(Boolean).join(' • '))}</option>`).join('')};

const oldRefresh=window.refresh;
window.refresh=function(){oldRefresh();renderCustomers();renderTypeahead()};
const oldStockIn=window.stockIn;
window.stockIn=function(){if($('spHidden')){syncPurchaseProduct();const id=Number($('spHidden').value||0);if(!id)return toast('Select a product');const temp=document.createElement('select');temp.id='sp';temp.style.display='none';temp.innerHTML=`<option value="${id}" selected></option>`;document.body.appendChild(temp);try{return oldStockIn()}finally{temp.remove()}}return oldStockIn()};
const oldClear=window.clearSale;
window.clearSale=function(){oldClear();if($('saleCustomer')){$('saleCustomer').dataset.customerId='';$('saleCustomer').dataset.currency='USD'}};
const oldCheckout=window.checkout;
window.checkout=function(){customerPicked();return oldCheckout()};

refresh();
})();