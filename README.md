# GM Security Pro Final v14

Mobile Safari action fix.

## Main fix
- iPhone Safari compatibility fix for New/Edit/Delete buttons.
- Static app now explicitly maps DOM ids to window so Safari can run all action buttons reliably.
- Added global window.App and window.Logic for inline action handlers.
- Fixed modal/render/drawLines DOM references so forms open and work on iPhone Safari.

## Existing features preserved
- Login
- Invoices / quotations / receipts
- Detailed WhatsApp copy templates
- A4 print templates
- Inventory stock movements
- Visits add/edit/delete
- Clients / suppliers / inventory delete
- Beirut timezone dates
- Invoice/quotation date rules

## Login
Username: admin
Password: gm1234

## Upload to GitHub
Upload these files only:
- index.html
- styles.css
- app.js
- README.md
- TEST_REPORT.txt

Vercel: static project, no install command, no build command.
