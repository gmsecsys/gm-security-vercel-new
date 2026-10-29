/* GM Security Systems - Receipt on Quotation / Down Payment patch */
(function(){
  if (typeof App === 'undefined' || typeof Logic === 'undefined') return;

  const originalConvertQuote = App.convertQuote.bind(App);
  const originalRenderList = App.renderList.bind(App);

  App.openReceiptForm = function(targetId='', receiptId=''){
    const rec = receiptId ? this.data.receipts.find(r=>r.id===receiptId) : null;
    const selectedTargetId = rec?.invoiceId || targetId || '';
    const inv = this.data.invoices.find(i=>i.id===selectedTargetId);
    const quote = this.data.quotes.find(q=>q.id===selectedTargetId);
    const target = inv || quote;
    const client = target ? this.getClientByName(target.client) : this.getClientByName(rec?.client||'');
    const rate = rec?.exchangeRate || target?.exchangeRate || client?.exchangeRate || this.data.settings.exchangeRate || 89500;
    const defaultAmount = rec ? rec.amount : (inv ? inv.balance : 0);
    const invoiceOptions = this.data.invoices.map(i=>`<option value="${i.id}" ${selectedTargetId===i.id?'selected':''}>${i.id} — Invoice</option>`).join('');
    const quoteOptions = this.data.quotes.filter(q=>q.status!=='Converted').map(q=>`<option value="${q.id}" ${selectedTargetId===q.id?'selected':''}>${q.id} — Quotation / Down Payment</option>`).join('');
    this.modal(receiptId?'Edit Receipt':'Receipt',`<div class="form-grid"><div class="field"><label>Invoice / Quotation</label><select id="rInv"><option value="">Manual / Customer Account</option><optgroup label="Invoices">${invoiceOptions}</optgroup><optgroup label="Quotations">${quoteOptions}</optgroup></select></div><div class="field"><label>Client</label><input id="rClient" value="${rec?.client||target?.client||''}"></div><div class="field"><label>Date</label><input id="rDate" type="date" value="${rec?.date||Logic.today()}"></div><div class="field"><label>Method</label><select id="rMethod">${['Cash','Bank Transfer','OMT / Wish','Check','Other'].map(m=>`<option ${((rec?.method||'Cash')===m)?'selected':''}>${m}</option>`).join('')}</select></div><div class="field"><label>Currency</label><select id="rCurrency"><option ${(rec?.currency||target?.currency||'USD')==='USD'?'selected':''}>USD</option><option ${(rec?.currency||target?.currency)==='LBP'?'selected':''}>LBP</option></select></div><div class="field"><label>Exchange Rate LBP / USD</label><input id="rRate" type="number" value="${rate}"></div><div class="field"><label>Amount Paid $</label><input id="rAmount" type="number" min="0" step="0.01" value="${defaultAmount}"></div><div class="field"><label>Notes</label><input id="rNotes" value="${rec?.notes||''}"></div></div><p class="muted small">A receipt may be issued against a quotation before any invoice exists. When that quotation is converted to an invoice, the receipt is automatically transferred to the new invoice and counted once.</p><button class="btn green" onclick="App.saveReceipt('${receiptId||''}')">${receiptId?'Update Receipt':'Save Receipt'}</button>`);
  };

  App.saveReceipt = function(receiptId=''){
    const amount = Number(rAmount.value||0);
    if (!(amount > 0)) { this.toast('Enter a valid payment amount'); return; }
    const targetId = rInv.value;
    const inv = this.data.invoices.find(i=>i.id===targetId);
    const quote = this.data.quotes.find(q=>q.id===targetId);
    const clientName = (rClient.value||inv?.client||quote?.client||'').trim();
    if (!clientName) { this.toast('Select or enter a client'); return; }
    const rec = {id:receiptId||Logic.docNo('RC',this.data.receipts),invoiceId:targetId,client:clientName,date:rDate.value,method:rMethod.value,currency:rCurrency.value,exchangeRate:Number(rRate.value||this.data.settings.exchangeRate||89500),amount,balance:0,notes:rNotes.value};
    if (receiptId) {
      const idx = this.data.receipts.findIndex(r=>r.id===receiptId);
      if (idx>=0) this.data.receipts[idx]=rec;
    } else this.data.receipts.push(rec);
    this.recalcInvoicePayments();
    this.save();
    this.closeModal();
    this.render();
    this.toast(quote ? 'Down payment receipt saved on quotation' : (receiptId?'Receipt updated':'Receipt created'));
  };

  App.convertQuote = function(id){
    const beforeIds = new Set(this.data.invoices.map(i=>i.id));
    originalConvertQuote(id);
    const inv = [...this.data.invoices].reverse().find(i=>!beforeIds.has(i.id) && i.sourceQuoteId===id) || [...this.data.invoices].reverse().find(i=>i.sourceQuoteId===id);
    if (!inv) return;
    let moved = 0;
    this.data.receipts.forEach(r=>{
      if (r.invoiceId===id) { r.invoiceId=inv.id; moved++; }
    });
    if (moved) {
      this.recalcInvoicePayments();
      this.save();
      this.render();
      this.toast(`Converted to invoice; ${moved} down payment receipt${moved===1?'':'s'} linked automatically`);
    }
  };

  App.renderList = function(type){
    originalRenderList(type);
    if (type==='quotes') {
      const el=document.getElementById('list_quotes');
      if (!el) return;
      el.querySelectorAll('tbody tr').forEach(row=>{
        const id=row.querySelector('td')?.textContent?.trim();
        const q=this.data.quotes.find(x=>x.id===id);
        const actions=row.querySelector('td:last-child');
        if(q && actions && q.status!=='Converted' && !actions.querySelector('.quote-receipt-btn')){
          actions.insertAdjacentHTML('beforeend',`<button class="btn green mini quote-receipt-btn" onclick="App.openReceiptForm('${q.id}')">Receipt / Down Payment</button>`);
        }
      });
    }
  };

  App.recalcInvoicePayments = function(){
    this.data.invoices.forEach(inv=>{
      inv.paid=this.data.receipts.filter(r=>r.invoiceId===inv.id).reduce((a,r)=>a+Number(r.amount||0),0);
      Logic.normalizeInvoice(inv);
      this.data.receipts.filter(r=>r.invoiceId===inv.id).forEach(r=>r.balance=inv.balance);
    });
  };
})();
