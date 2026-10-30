const fs=require('fs');
const path=require('path');
const src=path.join(__dirname,'e2e-test.js');
const out=path.join(__dirname,'.e2e-runtime.js');
let s=fs.readFileSync(src,'utf8');
s=s.replace(/v3\.1/g,'v3.2');
s=s.replace("await page.locator('#atype').selectOption('OUT'); await page.locator('#aq').fill('1');","await selectPartial(page,'#ap','E2E Cola'); await page.locator('#atype').selectOption('OUT'); await page.locator('#aq').fill('1');");
fs.writeFileSync(out,s);
require('./.e2e-runtime.js');
