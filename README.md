# GM Security Pro Final v7

Static HTML/CSS/JS business app for GM Security Systems.

## Login
- Username: `admin`
- Password: `gm1234`

## v7 updates
- Grand totals remain USD only on quotation, invoice, receipt, and statement print templates.
- Exchange rate remains visible as reference only: `1 USD = 89,500 LBP`.
- LBP equivalent lines removed from customer-facing print/PDF templates.
- Notes section only appears if notes/terms were actually entered.
- Discount supports fixed amount or percentage.
- Suppliers now support Add/Edit/Delete.
- Visits now support Add/Edit/Delete.
- Receipt Edit/Delete remains active and recalculates invoice balances.
- Item flow remains Item # first, Description second, no auto IT numbers, amount recalculates immediately when qty/price changes.
- Print opens a clean A4 document without app sidebar/dashboard background.

## Upload to Vercel
Upload only:
- index.html
- styles.css
- app.js
- README.md
- TEST_REPORT.txt

Do not upload package.json, package-lock.json, vercel.json, src, public, or node_modules.
