# GM Security Systems - Pro Final v12 Inventory Focus

Static HTML/CSS/JS version. No npm, no build, no package files.

## Login
Username: admin
Password: gm1234

## v12 Changes
- Inventory upgraded with tabs: Items, Movements, Low Stock.
- Added Stock In, Stock Out, and Adjustment flows.
- Added movement history with date, item, qty, from/to stock, supplier/client, reference, and notes.
- Inventory item fields improved: Item #, Description, Brand, Category, Supplier, Location/Shelf, Unit, Qty, Min Qty, Cost, Selling Price.
- Low stock page shows items where Qty <= Min Qty with quick Stock In.
- Invoice form has optional “Deduct stock from Inventory now” checkbox.
- Invoice stock deduction creates movement records and skips service items.
- Existing print, WhatsApp, login, receipt, date, and quotation/invoice logic preserved.

## Upload only
- index.html
- styles.css
- app.js
- README.md
- TEST_REPORT.txt

## v13 Mobile Safari Fix
- Fullscreen mobile modals for invoices, quotations, visits, clients, suppliers, inventory, receipts.
- Bigger touch buttons on iPhone.
- Inputs use 16px font to prevent Safari zoom/control issues.
- Modal body scrolls correctly with bottom safe-area padding.
- Item lines become one-column on mobile so edit/save is reachable.
- Table action buttons become mobile-friendly grid.
