const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const port = 8000;
const results = [];
const issues = [];
const sleep = ms => new Promise(r => setTimeout(r, ms));

function mime(p){
  if(p.endsWith('.html')) return 'text/html; charset=utf-8';
  if(p.endsWith('.js')) return 'application/javascript; charset=utf-8';
  if(p.endsWith('.css')) return 'text/css; charset=utf-8';
  if(p.endsWith('.json')) return 'application/json; charset=utf-8';
  return 'application/octet-stream';
}
const server = http.createServer((req,res)=>{
  let u = decodeURIComponent(req.url.split('?')[0]);
  if(u.endsWith('/')) u += 'index.html';
  const f = path.resolve(root, '.'+u);
  if(!f.startsWith(root)){res.writeHead(403);return res.end('forbidden');}
  fs.readFile(f,(e,b)=>{
    if(e){res.writeHead(404);return res.end('not found');}
    res.writeHead(200,{'Content-Type':mime(f),'Cache-Control':'no-store'});res.end(b);
  });
});
function ok(cond,msg){ if(!cond) throw new Error(msg); }
async function step(name, fn){
  try { await fn(); results.push(['PASS',name]); console.log('PASS',name); return true; }
  catch(e){ results.push(['FAIL',name]); issues.push(`${name}: ${e.message}`); console.log('FAIL',name,'=>',e.message); return false; }
}
async function nav(page,p){ await page.locator(`#nav button[data-p="${p}"]`).click(); await sleep(120); }
async function toastText(page){ return (await page.locator('#toast').innerText().catch(()=>'')) || ''; }
async function selectPartial(page, selector, text){
  const value = await page.locator(`${selector} option`).evaluateAll((opts,t)=>{
    const o=opts.find(x=>(x.textContent||'').includes(t)); return o?o.value:null;
  },text);
  ok(value!==null && value!==undefined && value!=='',`option containing "${text}" not found in ${selector}`);
  await page.locator(selector).selectOption(value);
  return value;
}

(async()=>{
  await new Promise(r=>server.listen(port,'127.0.0.1',r));
  const browser = await chromium.launch({headless:true});
  const context = await browser.newContext({acceptDownloads:true, viewport:{width:1440,height:950}});
  const page = await context.newPage();
  const jsErrors=[];
  page.on('pageerror',e=>jsErrors.push(e.message));
  page.on('console',m=>{ if(m.type()==='error') jsErrors.push('console: '+m.text()); });
  await page.goto(`http://127.0.0.1:${port}/bizflow-demo/?e2e=1`,{waitUntil:'networkidle'});
  await page.evaluate(()=>localStorage.removeItem('gmbf_live'));
  await page.reload({waitUntil:'networkidle'});

  await step('App loads latest v3.1 with all main pages', async()=>{
    ok((await page.locator('.badge').innerText()).includes('v3.1'),'badge is not v3.1');
    const pages=['dashboard','pos','invoices','products','purchase','adjust','suppliers','delivery','reports','settings'];
    for(const p of pages) ok(await page.locator(`#${p}`).count()===1,`missing page ${p}`);
    ok(await page.locator('#customers').count()===1,'missing Customers page');
  });

  await step('Exit button is visible and pinned inside viewport', async()=>{
    const b=page.locator('#quitAppBtn'); ok(await b.count()===1,'Exit button missing');
    ok(await b.isVisible(),'Exit button not visible');
    const bb=await b.boundingBox(); ok(bb && bb.y+bb.height<=950,'Exit button falls below viewport');
    ok((await b.innerText()).includes('Exit'),'Exit label incorrect');
  });

  await step('Purchase quick New Supplier preserves draft and auto-selects supplier', async()=>{
    await nav(page,'purchase');
    await page.locator('#sref').fill('TEST-INV-001');
    await page.locator('#sq').fill('5');
    await page.locator('#sc').fill('10');
    await page.locator('#sfee').fill('1.25');
    await page.locator('#sfeeNote').fill('Delivery');
    await page.locator('#purchaseNewSupplierBtn').click();
    ok(await page.locator('#quickSupplierModal').isVisible(),'New Supplier modal did not open');
    await page.locator('#quickSupplierName').fill('E2E Supplier');
    await page.locator('#quickSupplierPhone').fill('03 111 222');
    await page.locator('#quickSupplierSave').click();
    ok((await page.locator('#ss option:checked').innerText()).includes('E2E Supplier'),'supplier not auto-selected');
    ok(await page.locator('#sref').inputValue()==='TEST-INV-001','purchase reference lost');
    ok(await page.locator('#sq').inputValue()==='5','purchase quantity lost');
    ok(await page.locator('#sc').inputValue()==='10','purchase cost lost');
    ok(await page.locator('#sfee').inputValue()==='1.25','purchase fee lost');
  });

  await step('Purchase shortcut creates new Product and returns to Purchase with full draft intact', async()=>{
    await page.locator('#spText').fill('E2E Cola');
    await page.locator('#purchase button', {hasText:'+ New Product'}).click();
    await sleep(100);
    ok(await page.locator('#products').evaluate(el=>el.classList.contains('on')),'did not navigate to Products');
    ok(await page.locator('#pn').inputValue()==='E2E Cola','product name not carried over');
    await page.locator('#pb').fill('990000000001');
    await page.locator('#pf').fill('Drinks');
    await page.locator('#psf').fill('Soft Drinks');
    await page.locator('#pc').fill('Cola');
    await page.locator('#pm').fill('330ml');
    await page.locator('#ps').selectOption({label:'E2E Supplier'});
    await page.locator('#pco').fill('10');
    await page.locator('#pp').fill('15');
    await page.locator('#pst').fill('2');
    await page.locator('#pl').fill('1');
    await page.getByRole('button',{name:'Save Product'}).click();
    await sleep(150);
    ok(await page.locator('#purchase').evaluate(el=>el.classList.contains('on')),'did not return to Purchase');
    ok(await page.locator('#spText').inputValue()==='E2E Cola','new product not selected');
    ok(await page.locator('#sref').inputValue()==='TEST-INV-001','purchase reference lost after product create');
    ok((await page.locator('#ss option:checked').innerText()).includes('E2E Supplier'),'supplier selection lost');
    ok(await page.locator('#sq').inputValue()==='5','purchase quantity lost after product create');
    ok(await page.locator('#sc').inputValue()==='10','purchase cost lost after product create');
    ok(await page.locator('#sfee').inputValue()==='1.25','purchase fee lost after product create');
  });

  await step('Supplier purchase posts stock and weighted effective cost then clears saved draft', async()=>{
    await page.getByRole('button',{name:'Add Purchase / Stock'}).click();
    await sleep(150);
    const state=await page.evaluate(()=>({p:d.products.find(x=>x.code==='990000000001'), purchases:d.purchases.filter(x=>d.products.find(p=>p.id===x.productId)?.code==='990000000001')}));
    ok(state.p.stock===7,`expected stock 7, got ${state.p.stock}`);
    ok(Math.abs(state.p.cost-10.892857142857142)<0.0001,`weighted avg cost wrong: ${state.p.cost}`);
    ok(state.purchases.length===1,'purchase record missing');
    ok(Math.abs(state.purchases[0].effective-11.25)<0.001,'effective unit cost wrong');
    ok((await page.locator('#purchaseHistory').innerText()).includes('TEST-INV-001'),'purchase history missing reference');
    ok(await page.locator('#sref').inputValue()==='','saved purchase reference was not cleared');
    ok(await page.locator('#spText').inputValue()==='','saved purchase product was not cleared');
    ok(await page.locator('#ss').inputValue()==='','saved purchase supplier was not cleared');
  });

  await step('Quick Stock IN and OUT work inside Purchase without leaving page', async()=>{
    await page.getByRole('button',{name:'+ Stock IN'}).click();
    await selectPartial(page,'#quickStockProduct','E2E Cola');
    await page.locator('#quickStockQty').fill('3');
    await page.locator('#quickStockReason').selectOption({label:'Correction'});
    await page.locator('#quickStockSave').click();
    let stock=await page.evaluate(()=>d.products.find(x=>x.code==='990000000001').stock);
    ok(stock===10,`Stock IN expected 10, got ${stock}`);
    await page.getByRole('button',{name:'− Stock OUT'}).click();
    await selectPartial(page,'#quickStockProduct','E2E Cola');
    await page.locator('#quickStockQty').fill('2');
    await page.locator('#quickStockReason').selectOption({label:'Damaged'});
    await page.locator('#quickStockSave').click();
    stock=await page.evaluate(()=>d.products.find(x=>x.code==='990000000001').stock);
    ok(stock===8,`Stock OUT expected 8, got ${stock}`);
    ok(await page.locator('#purchase').evaluate(el=>el.classList.contains('on')),'left Purchase page during quick stock');
  });

  await step('Leaving a saved Purchase does not show false unsaved-changes warning', async()=>{
    let dialogMessage=null;
    page.once('dialog',async d=>{dialogMessage=d.message(); await d.accept();});
    await page.locator('#nav button[data-p="pos"]').click();
    await sleep(180);
    ok(!dialogMessage,`unexpected warning after saved purchase: ${dialogMessage}`);
    ok(await page.locator('#pos').evaluate(el=>el.classList.contains('on')),'did not reach POS');
  });

  await step('Checkout shortcut creates Customer and returns with customer selected', async()=>{
    await page.locator('#checkoutNewCustomerBtn').click();
    await sleep(100);
    ok(await page.locator('#customers').evaluate(el=>el.classList.contains('on')),'did not open Customers workflow');
    await page.locator('#cn').fill('E2E Customer');
    await page.locator('#cacc').fill('ACC-1001');
    await page.locator('#cphone').fill('70 123 456');
    await page.locator('#cemail').fill('e2e@example.com');
    await page.locator('#caddress').fill('Beirut');
    await page.locator('#ccurrency').selectOption('USD');
    await page.getByRole('button',{name:'Save Customer'}).click();
    await sleep(120);
    ok(await page.locator('#pos').evaluate(el=>el.classList.contains('on')),'did not return to POS');
    ok(await page.locator('#saleCustomer').inputValue()==='E2E Customer','customer not selected after create');
    ok(await page.locator('#phone').inputValue()==='70 123 456','customer phone not carried to sale');
  });

  await step('Barcode scan + Enter twice adds item and increments quantity', async()=>{
    const s=page.locator('#search');
    await s.fill('990000000001'); await s.press('Enter');
    await s.fill('990000000001'); await s.press('Enter');
    const cart=await page.locator('#cart').innerText();
    ok(cart.includes('E2E Cola'),'barcode did not add product');
    ok(/\b2\b/.test(cart),'second scan did not increment quantity to 2');
  });

  await step('Hold and Resume Sale preserves cart/customer/payment details', async()=>{
    await page.locator('#paid').fill('40');
    await page.getByRole('button',{name:'Hold Sale'}).click();
    ok((await page.locator('#cart').innerText()).includes('Cart is empty'),'cart not cleared after hold');
    await page.getByRole('button',{name:'Resume Held Sale'}).click();
    const cart=await page.locator('#cart').innerText();
    ok(cart.includes('E2E Cola'),'held cart not restored');
    ok(await page.locator('#saleCustomer').inputValue()==='E2E Customer','held customer not restored');
    ok(await page.locator('#paid').inputValue()==='40','held payment amount not restored');
  });

  await step('Cash underpayment is blocked; valid checkout posts sale and receipt', async()=>{
    await page.locator('#paid').fill('10');
    const before=await page.evaluate(()=>d.sales.length);
    await page.getByRole('button',{name:'Complete Sale'}).click();
    await sleep(80);
    ok((await toastText(page)).includes('less than total'),'underpayment was not blocked');
    ok(await page.evaluate(()=>d.sales.length)===before,'sale posted despite underpayment');
    await page.locator('#paid').fill('40');
    await page.getByRole('button',{name:'Complete Sale'}).click();
    await sleep(100);
    ok(await page.locator('#modal').evaluate(el=>el.classList.contains('on')),'receipt modal not shown');
    ok((await page.locator('#rt').innerText()).includes('E2E Cola'),'receipt missing product');
    ok(await page.evaluate(()=>d.sales.length)===before+1,'sale not recorded');
    const stock=await page.evaluate(()=>d.products.find(x=>x.code==='990000000001').stock);
    ok(stock===6,`stock expected 6 after sale, got ${stock}`);
    await page.getByRole('button',{name:'Close'}).click();
  });

  await step('Invoices history View/Reprint and Delivery Out show completed sale', async()=>{
    await nav(page,'invoices');
    ok((await page.locator('#invoiceTable').innerText()).includes('E2E Customer'),'invoice history missing customer');
    await page.locator('#invoiceTable').getByRole('button',{name:'View'}).first().click();
    ok(await page.locator('#modal').evaluate(el=>el.classList.contains('on')),'invoice view did not open receipt');
    ok(await page.locator('#printReceiptBtn').count()===1,'Print/Reprint button missing');
    await page.getByRole('button',{name:'Close'}).click();
    await nav(page,'delivery');
    const dt=await page.locator('#dt').innerText();
    ok(dt.includes('E2E Customer') && dt.includes('Pending'),'Delivery Out missing sale');
  });

  await step('Product duplicate barcode is rejected and Archive/Restore works', async()=>{
    await nav(page,'products');
    const count=await page.evaluate(()=>d.products.length);
    await page.locator('#pb').fill('990000000001');
    await page.locator('#pn').fill('Duplicate Product');
    await page.getByRole('button',{name:'Save Product'}).click();
    await sleep(70);
    ok((await toastText(page)).includes('already exists'),'duplicate barcode not rejected');
    ok(await page.evaluate(()=>d.products.length)===count,'duplicate product was created');
    await page.locator('#pb').fill(''); await page.locator('#pn').fill('');
    let row=page.locator('#pt tr').filter({hasText:'E2E Cola'}).first();
    await row.getByRole('button',{name:'Archive'}).click();
    row=page.locator('#pt tr').filter({hasText:'E2E Cola'}).first();
    ok((await row.innerText()).includes('Archived'),'archive failed');
    await row.getByRole('button',{name:'Restore'}).click();
    row=page.locator('#pt tr').filter({hasText:'E2E Cola'}).first();
    ok((await row.innerText()).includes('Active'),'restore failed');
  });

  await step('Unsaved-change protection cancels accidental navigation and can discard on confirmation', async()=>{
    await page.locator('#pn').fill('Unsaved Draft Product');
    page.once('dialog',async d=>{ok(d.message().includes('unsaved changes'),'wrong unsaved warning'); await d.dismiss();});
    await page.locator('#nav button[data-p="dashboard"]').click();
    await sleep(80);
    ok(await page.locator('#products').evaluate(el=>el.classList.contains('on')),'navigation occurred after Cancel');
    page.once('dialog',async d=>{await d.accept();});
    await page.locator('#nav button[data-p="dashboard"]').click();
    await sleep(80);
    ok(await page.locator('#dashboard').evaluate(el=>el.classList.contains('on')),'navigation did not occur after confirming discard');
  });

  await step('Direct Stock Adjustment page records IN/OUT correctly', async()=>{
    await nav(page,'adjust');
    await selectPartial(page,'#ap','E2E Cola');
    await page.locator('#atype').selectOption('IN'); await page.locator('#aq').fill('1'); await page.locator('#areason').selectOption({label:'Correction'}); await page.getByRole('button',{name:'Save Adjustment'}).click();
    let stock=await page.evaluate(()=>d.products.find(x=>x.code==='990000000001').stock); ok(stock===7,`direct IN expected 7 got ${stock}`);
    await page.locator('#atype').selectOption('OUT'); await page.locator('#aq').fill('1'); await page.locator('#areason').selectOption({label:'Sample'}); await page.getByRole('button',{name:'Save Adjustment'}).click();
    stock=await page.evaluate(()=>d.products.find(x=>x.code==='990000000001').stock); ok(stock===6,`direct OUT expected 6 got ${stock}`);
  });

  await step('Supplier page can add and delete an unused supplier', async()=>{
    await nav(page,'suppliers');
    await page.locator('#sn').fill('Temporary Supplier'); await page.locator('#sph').fill('01 000 000'); await page.getByRole('button',{name:'Save Supplier'}).click();
    ok((await page.locator('#st').innerText()).includes('Temporary Supplier'),'direct supplier add failed');
    const row=page.locator('#st tr').filter({hasText:'Temporary Supplier'}).first(); await row.getByRole('button',{name:'Delete'}).click();
    ok(!(await page.locator('#st').innerText()).includes('Temporary Supplier'),'supplier delete failed');
  });

  await step('Reports center runs key reports, Excel export and customer letter', async()=>{
    await nav(page,'reports');
    ok(await page.locator('#reportType option').count()===9,'expected 9 reports');
    await page.locator('#reportPeriod').selectOption('all');
    await page.locator('#reportType').selectOption('sales'); await page.locator('#runReportBtn').click();
    ok((await page.locator('#reportBody').innerText()).includes('E2E Customer'),'Sales Report missing sale');
    const dlPromise=page.waitForEvent('download'); await page.locator('#exportExcelBtn').click(); const dl=await dlPromise; ok(dl.suggestedFilename().endsWith('.xls'),'Excel export filename is not .xls');
    await page.locator('#reportType').selectOption('customerStatement');
    await selectPartial(page,'#reportCustomer','E2E Customer'); await page.locator('#runReportBtn').click();
    ok((await page.locator('#reportBody').innerText()).includes('E2E Cola'),'Customer Statement missing sale items');
    const popupPromise=context.waitForEvent('page'); await page.locator('#customerLetterBtn').click(); const popup=await popupPromise; await popup.waitForLoadState('domcontentloaded'); ok((await popup.locator('body').innerText()).includes('E2E Customer'),'Customer letter missing customer'); await popup.close();
    await page.locator('#reportType').selectOption('pl'); await page.locator('#runReportBtn').click(); ok((await page.locator('#reportBody').innerText()).includes('Sales Revenue'),'P&L failed');
    await page.locator('#reportType').selectOption('supplierPurchases'); await selectPartial(page,'#reportSupplier','E2E Supplier'); await page.locator('#runReportBtn').click(); ok((await page.locator('#reportBody').innerText()).includes('TEST-INV-001'),'Supplier Purchase report missing invoice');
    await page.locator('#reportType').selectOption('inventory'); await page.locator('#runReportBtn').click(); ok((await page.locator('#reportBody').innerText()).includes('E2E Cola'),'Inventory report missing product');
    await page.locator('#reportType').selectOption('stockMovement'); await page.locator('#reportPeriod').selectOption('all'); await page.locator('#runReportBtn').click(); ok((await page.locator('#reportBody').innerText()).includes('E2E Cola'),'Stock Movement report missing product');
  });

  await step('Expense entry feeds Profit & Loss and Settings save persists', async()=>{
    await nav(page,'reports');
    await page.locator('#ed').fill('E2E Rent'); await page.locator('#ea').fill('3'); await page.getByRole('button',{name:'Add Expense'}).click();
    await page.locator('#reportPeriod').selectOption('all'); await page.locator('#reportType').selectOption('pl'); await page.locator('#runReportBtn').click();
    ok((await page.locator('#reportBody').innerText()).includes('$3.00'),'P&L did not include expense');
    await nav(page,'settings'); await page.locator('#store').fill('E2E Store'); await page.locator('#storeph').fill('01 234 567'); await page.getByRole('button',{name:'Save Settings'}).click();
    ok((await page.evaluate(()=>d.settings.store))==='E2E Store','settings did not persist');
  });

  await step('Exit flow asks confirmation, supports Cancel, Backup & Exit, and visible closed state', async()=>{
    let first=''; page.once('dialog',async d=>{first=d.message(); await d.accept();});
    await page.locator('#quitAppBtn').click(); await sleep(80); ok(first==='Are you sure you want to exit?',`wrong exit confirm: ${first}`); ok(await page.locator('#quitBackupModal').evaluate(el=>el.classList.contains('on')),'backup modal not shown');
    await page.locator('#backupQuitCancel').click(); ok(!(await page.locator('#quitBackupModal').evaluate(el=>el.classList.contains('on'))),'Cancel did not close exit modal');
    page.once('dialog',async d=>{await d.accept();}); await page.locator('#quitAppBtn').click();
    const backupPromise=page.waitForEvent('download'); await page.locator('#backupQuitYes').click(); const b=await backupPromise; ok(b.suggestedFilename().startsWith('GM_BizFlow_Backup_')&&b.suggestedFilename().endsWith('.json'),'backup filename invalid');
    ok((await page.locator('body').innerText()).includes('GM BizFlow is closed'),'closed screen not shown');
  });

  if(jsErrors.length) issues.push('JavaScript console/page errors: '+jsErrors.join(' | '));
  console.log('\n=== GM BIZFLOW E2E SUMMARY ===');
  for(const [s,n] of results) console.log(`${s}: ${n}`);
  if(issues.length){ console.log('\n=== ISSUES ==='); issues.forEach((x,i)=>console.log(`${i+1}. ${x}`)); }
  else console.log('\nNO ISSUES FOUND');

  await browser.close(); server.close();
  process.exit(issues.length?1:0);
})().catch(async e=>{ console.error('FATAL',e); try{server.close()}catch{} process.exit(2); });
