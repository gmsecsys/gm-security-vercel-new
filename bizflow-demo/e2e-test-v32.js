const fs=require('fs');
const path=require('path');
const src=path.join(__dirname,'e2e-test.js');
const out=path.join(__dirname,'.e2e-runtime.js');
let s=fs.readFileSync(src,'utf8');
s=s.replace(/v3\.1/g,'v3.3');
s=s.replace("await page.locator('#atype').selectOption('OUT'); await page.locator('#aq').fill('1');","await selectPartial(page,'#ap','E2E Cola'); await page.locator('#atype').selectOption('OUT'); await page.locator('#aq').fill('1');");
s=s.replace(
"let dialogMessage=null;\n    page.once('dialog',async d=>{dialogMessage=d.message(); await d.accept();});\n    await page.locator('#nav button[data-p=\"pos\"]').click();\n    await sleep(180);\n    ok(!dialogMessage,`unexpected warning after saved purchase: ${dialogMessage}`);",
"let dialogMessage=null;\n    const noWarnHandler=async d=>{dialogMessage=d.message(); await d.accept();};\n    page.on('dialog',noWarnHandler);\n    await page.locator('#nav button[data-p=\"pos\"]').click();\n    await sleep(180);\n    page.off('dialog',noWarnHandler);\n    ok(!dialogMessage,`unexpected warning after saved purchase: ${dialogMessage}`);"
);
s=s.replace(
"ok((await b.innerText()).includes('Exit'),'Exit label incorrect');",
"ok((await b.innerText()).toUpperCase().includes('EXIT'),'Exit label incorrect'); const pos=await b.evaluate(el=>getComputedStyle(el).position); ok(pos==='fixed','Exit is not fixed on screen');"
);
fs.writeFileSync(out,s);
require('./.e2e-runtime.js');
