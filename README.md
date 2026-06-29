# GM Security Pro Final v6

Clean static version. Upload only these files to GitHub/Vercel:

- index.html
- styles.css
- app.js
- README.md
- TEST_REPORT.txt

Do not upload package.json, package-lock.json, vercel.json, src, public, or node_modules.

## Login
Username: admin
Password: gm1234

## v6 changes
- Added Delete button for Clients.
- Delete Client uses a confirmation message.
- If the client has existing quotations, invoices, or receipts, deleting removes only the client from the Clients list and keeps historical documents.
- Receipts still support View/Print, Edit, and Delete.
- Receipt delete/edit recalculates linked invoice paid/balance/status.
- Print/PDF uses a separate clean A4 print document and should not print dashboard/sidebar/background UI.
- Item flow remains: Item # first, Description second, quantity/price recalc amount immediately, Save Item only for new inventory items.

## Vercel settings
Framework: Other
Install Command: empty
Build Command: empty
Output Directory: .
