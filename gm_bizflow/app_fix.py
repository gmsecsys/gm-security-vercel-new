from __future__ import annotations
import customtkinter as ctk
from tkinter import messagebox
from app_modern import App as BaseApp, DB, BG, INK, MUT, ACCENT, GREEN, RED, money, clear_tree

DANGER='#B94B4B'
SOFT='#E7EFF5'

class App(BaseApp):
    """Usability/safety fixes only. Dashboard and overall graphics stay unchanged."""

    def _confirm(self,title,text):
        return messagebox.askyesno(title,text,parent=self)

    def _delete_sale(self,sale_id):
        sale,items,_=DB.sale(sale_id)
        if not sale:return
        with DB.connect() as c:
            for it in items:
                c.execute('UPDATE products SET stock=stock+? WHERE id=?',(it['qty'],it['product_id']))
            c.execute("UPDATE serials SET status='IN_STOCK',sale_id=NULL WHERE sale_id=?",(sale_id,))
            c.execute('DELETE FROM sale_items WHERE sale_id=?',(sale_id,))
            c.execute('DELETE FROM sales WHERE id=?',(sale_id,))

    def _delete_purchase(self,purchase_id):
        with DB.connect() as c:
            r=c.execute('SELECT pu.*,p.name,p.stock,p.track_serial FROM purchases pu JOIN products p ON p.id=pu.product_id WHERE pu.id=?',(purchase_id,)).fetchone()
            if not r:raise ValueError('Stock entry not found')
            if float(r['stock'])+1e-9<float(r['qty']):raise ValueError('Cannot reverse this Stock In because some of that quantity has already been sold/used. Use a stock adjustment instead.')
            if r['track_serial']:
                cnt=c.execute("SELECT COUNT(*) n FROM serials WHERE product_id=? AND status='IN_STOCK'",(r['product_id'],)).fetchone()['n']
                if int(cnt)<int(r['qty']):raise ValueError('Cannot reverse this Stock In because one or more serial-number units are no longer in stock.')
                ids=[x['id'] for x in c.execute("SELECT id FROM serials WHERE product_id=? AND status='IN_STOCK' ORDER BY id DESC LIMIT ?",(r['product_id'],int(r['qty']))).fetchall()]
                for sid in ids:c.execute('DELETE FROM serials WHERE id=?',(sid,))
            c.execute('UPDATE products SET stock=stock-? WHERE id=?',(r['qty'],r['product_id']))
            c.execute('DELETE FROM purchases WHERE id=?',(purchase_id,))
            p=c.execute('SELECT stock,cost FROM products WHERE id=?',(r['product_id'],)).fetchone()
            hist=c.execute('SELECT qty,unit_cost FROM purchases WHERE product_id=? ORDER BY id',(r['product_id'],)).fetchall()
            if hist:
                q=sum(float(x['qty']) for x in hist);v=sum(float(x['qty'])*float(x['unit_cost']) for x in hist);avg=v/q if q else 0
                c.execute('UPDATE products SET cost=? WHERE id=?',(avg,r['product_id']))

    # PRODUCTS — same design, clearer field descriptions + delete.
    def build_products(self):
        f=ctk.CTkFrame(self.pages,fg_color=BG,corner_radius=0);self.frames['products']=f
        form=self.card(f);form.pack(fill='x',pady=(0,10));self.pvars={k:ctk.StringVar() for k in ('barcode','name','category','cost','price','stock')};self.pserial=ctk.BooleanVar(value=False)
        fields=[
            ('Barcode (optional)','barcode','Scan/type barcode or leave blank for automatic SKU'),
            ('Product Name','name','Name shown in POS and reports'),
            ('Category','category','Example: Snacks, Household, Tools'),
            ('Average Cost USD','cost','Opening cost; later Stock In updates weighted average automatically'),
            ('Selling Price USD','price','Price charged to customer'),
            ('Opening Stock','stock','Quantity already in stock when creating the item')]
        for i,(lab,k,hint) in enumerate(fields):
            form.grid_columnconfigure(i,weight=1)
            ctk.CTkLabel(form,text=lab,text_color=MUT,font=('Segoe UI',10,'bold')).grid(row=0,column=i,padx=7,pady=(12,2),sticky='w')
            ctk.CTkEntry(form,textvariable=self.pvars[k],placeholder_text=hint,width=150).grid(row=1,column=i,padx=7,pady=(0,3),sticky='ew')
            ctk.CTkLabel(form,text=hint,text_color=MUT,font=('Segoe UI',8),wraplength=165,justify='left').grid(row=2,column=i,padx=7,pady=(0,9),sticky='nw')
        ctk.CTkCheckBox(form,text='Track serial numbers',variable=self.pserial,text_color=INK).grid(row=3,column=0,columnspan=2,padx=8,pady=(0,12),sticky='w')
        ctk.CTkButton(form,text='Save Product',fg_color=ACCENT,command=self.save_product).grid(row=3,column=4,padx=6,pady=(0,12),sticky='e')
        ctk.CTkButton(form,text='Clear Fields',fg_color=SOFT,text_color=INK,command=self.clear_product_fields).grid(row=3,column=5,padx=6,pady=(0,12),sticky='e')
        tablecard=self.card(f);tablecard.pack(fill='both',expand=True)
        h=ctk.CTkFrame(tablecard,fg_color='transparent');h.pack(fill='x',padx=14,pady=(12,6));ctk.CTkLabel(h,text='Product List',text_color=INK,font=('Segoe UI',15,'bold')).pack(side='left');ctk.CTkLabel(h,text='Double-click a row to edit it.',text_color=MUT,font=('Segoe UI',9)).pack(side='left',padx=12);ctk.CTkButton(h,text='Delete Product',width=120,fg_color=DANGER,command=self.delete_product).pack(side='right')
        self.product_table=self.table(tablecard,('barcode','name','category','avg_cost','last_cost','price','stock','value'),[120,210,120,90,90,90,70,100],15);self.product_table.pack(fill='both',expand=True,padx=10,pady=(0,10));self.product_table.bind('<Double-1>',self.load_product)

    def clear_product_fields(self):
        for v in self.pvars.values():v.set('')
        self.pserial.set(False)

    def delete_product(self):
        s=self.product_table.selection()
        if not s:return messagebox.showinfo('Delete Product','Select a product first.',parent=self)
        pid=int(s[0]);p=DB.product(pid)
        if not self._confirm('Delete Product',f"Remove '{p['name']}' from active Products and Stock?\n\nOld sales/purchase history will stay in reports."):return
        with DB.connect() as c:c.execute('UPDATE products SET active=0 WHERE id=?',(pid,))
        self.clear_product_fields();self.refresh_products();self.refresh_pos_products();self.refresh_stock();self.refresh_dashboard()

    # STOCK IN — same layout, clearer descriptions + safe reverse/delete.
    def build_stock(self):
        f=ctk.CTkFrame(self.pages,fg_color=BG,corner_radius=0);self.frames['stock']=f
        form=self.card(f);form.pack(fill='x',pady=(0,10));self.stock_product=ctk.StringVar();self.stock_supplier=ctk.StringVar();self.stock_qty=ctk.StringVar(value='1');self.stock_cost=ctk.StringVar();self.stock_serials=ctk.StringVar()
        specs=[('Product',self.stock_product,'Choose which product is entering stock'),('Supplier',self.stock_supplier,'Who supplied this stock'),('Quantity',self.stock_qty,'Number of units received'),('Unit Cost USD',self.stock_cost,'Purchase cost for one unit'),('Serial Numbers',self.stock_serials,'Only when serial tracking is enabled; comma-separated')]
        for i,(lab,var,hint) in enumerate(specs):
            form.grid_columnconfigure(i,weight=1);ctk.CTkLabel(form,text=lab,text_color=MUT,font=('Segoe UI',10,'bold')).grid(row=0,column=i,padx=7,pady=(12,2),sticky='w')
            if i<2:
                om=ctk.CTkOptionMenu(form,variable=var,values=['']);om.grid(row=1,column=i,padx=7,pady=(0,3),sticky='ew')
                if i==0:self.stock_product_menu=om
                else:self.stock_supplier_menu=om
            else:ctk.CTkEntry(form,textvariable=var,placeholder_text=hint).grid(row=1,column=i,padx=7,pady=(0,3),sticky='ew')
            ctk.CTkLabel(form,text=hint,text_color=MUT,font=('Segoe UI',8),wraplength=180,justify='left').grid(row=2,column=i,padx=7,pady=(0,9),sticky='nw')
        ctk.CTkButton(form,text='Add Stock',fg_color=GREEN,command=self.do_stock_in).grid(row=3,column=4,padx=8,pady=(0,12),sticky='e')
        card=self.card(f);card.pack(fill='both',expand=True);h=ctk.CTkFrame(card,fg_color='transparent');h.pack(fill='x',padx=14,pady=(12,6));ctk.CTkLabel(h,text='Purchase / Stock-In History',text_color=INK,font=('Segoe UI',15,'bold')).pack(side='left');ctk.CTkLabel(h,text='Delete reverses the selected entry only if the quantity is still available.',text_color=MUT,font=('Segoe UI',9)).pack(side='left',padx=12);ctk.CTkButton(h,text='Delete / Reverse',width=130,fg_color=DANGER,command=self.delete_stock_entry).pack(side='right')
        self.purchase_table=self.table(card,('id','date','supplier','product','qty','unit_cost','total'),[65,150,150,200,70,90,100],15);self.purchase_table.pack(fill='both',expand=True,padx=10,pady=(0,10))

    def refresh_stock(self):
        self.product_map={p['name']:p['id'] for p in DB.inventory()};self.supplier_map={s['name']:s['id'] for s in DB.suppliers()};pv=list(self.product_map) or [''];sv=['No Supplier']+list(self.supplier_map);self.stock_product_menu.configure(values=pv);self.stock_supplier_menu.configure(values=sv)
        if self.stock_product.get() not in pv:self.stock_product.set(pv[0])
        if self.stock_supplier.get() not in sv:self.stock_supplier.set(sv[0])
        clear_tree(self.purchase_table)
        for r in DB.purchase_history():self.purchase_table.insert('', 'end',iid=str(r['id']),values=(r['id'],r['created_at'].replace('T',' '),r['supplier_name'] or 'No Supplier',r['product_name'],f"{r['qty']:g}",money(r['unit_cost']),money(r['total'])))

    def delete_stock_entry(self):
        s=self.purchase_table.selection()
        if not s:return messagebox.showinfo('Delete Stock Entry','Select a Stock In row first.',parent=self)
        rid=int(s[0]);vals=self.purchase_table.item(s[0],'values')
        if not self._confirm('Delete Stock Entry',f"Reverse Stock In #{rid}?\nProduct: {vals[3]}\nQuantity: {vals[4]}\n\nThis will remove that quantity from current stock."):return
        try:self._delete_purchase(rid);self.refresh_stock();self.refresh_products();self.refresh_pos_products();self.refresh_dashboard()
        except Exception as ex:messagebox.showerror('Delete Stock Entry',str(ex),parent=self)

    # SUPPLIERS — explicit labels + delete.
    def build_suppliers(self):
        f=ctk.CTkFrame(self.pages,fg_color=BG,corner_radius=0);self.frames['suppliers']=f
        form=self.card(f);form.pack(fill='x',pady=(0,10));form.grid_columnconfigure(0,weight=2);form.grid_columnconfigure(1,weight=1)
        self.sup_name=ctk.StringVar();self.sup_phone=ctk.StringVar()
        ctk.CTkLabel(form,text='Supplier Name',text_color=MUT,font=('Segoe UI',10,'bold')).grid(row=0,column=0,padx=12,pady=(12,2),sticky='w');ctk.CTkLabel(form,text='Phone Number',text_color=MUT,font=('Segoe UI',10,'bold')).grid(row=0,column=1,padx=6,pady=(12,2),sticky='w')
        ctk.CTkEntry(form,placeholder_text='Example: ABC Trading',textvariable=self.sup_name).grid(row=1,column=0,sticky='ew',padx=12,pady=(0,3));ctk.CTkEntry(form,placeholder_text='Example: 03 123 456',textvariable=self.sup_phone).grid(row=1,column=1,sticky='ew',padx=6,pady=(0,3));ctk.CTkButton(form,text='Add Supplier',fg_color=ACCENT,command=self.add_supplier).grid(row=1,column=2,padx=12)
        ctk.CTkLabel(form,text='Company/person you purchase goods from',text_color=MUT,font=('Segoe UI',8)).grid(row=2,column=0,padx=12,pady=(0,10),sticky='w');ctk.CTkLabel(form,text='Supplier contact number',text_color=MUT,font=('Segoe UI',8)).grid(row=2,column=1,padx=6,pady=(0,10),sticky='w')
        card=self.card(f);card.pack(fill='both',expand=True);h=ctk.CTkFrame(card,fg_color='transparent');h.pack(fill='x',padx=14,pady=(12,6));ctk.CTkLabel(h,text='Supplier List',text_color=INK,font=('Segoe UI',15,'bold')).pack(side='left');ctk.CTkButton(h,text='Delete Supplier',width=125,fg_color=DANGER,command=self.delete_supplier).pack(side='right');self.supplier_table=self.table(card,('supplier','phone','purchase_entries','purchase_total'),[260,180,130,140],15);self.supplier_table.pack(fill='both',expand=True,padx=10,pady=(0,10))

    def refresh_suppliers(self):
        clear_tree(self.supplier_table);tot={r['supplier']:(r['entries'],r['purchases']) for r in DB.supplier_report()}
        for s in DB.suppliers():e,p=tot.get(s['name'],(0,0));self.supplier_table.insert('', 'end',iid=str(s['id']),values=(s['name'],s['phone'],e,money(p)))

    def delete_supplier(self):
        s=self.supplier_table.selection()
        if not s:return messagebox.showinfo('Delete Supplier','Select a supplier first.',parent=self)
        sid=int(s[0]);name=self.supplier_table.item(s[0],'values')[0]
        if not self._confirm('Delete Supplier',f"Delete supplier '{name}'?\n\nPurchase history stays but will show No Supplier."):return
        with DB.connect() as c:
            c.execute('UPDATE purchases SET supplier_id=NULL WHERE supplier_id=?',(sid,));c.execute('UPDATE products SET supplier_id=NULL WHERE supplier_id=?',(sid,));c.execute('DELETE FROM suppliers WHERE id=?',(sid,))
        self.refresh_suppliers();self.refresh_stock();self.refresh_reports()

    # DELIVERY — keep existing graphics, add delete/reverse control.
    def build_delivery(self):
        f=ctk.CTkFrame(self.pages,fg_color=BG,corner_radius=0);self.frames['delivery']=f
        bar=ctk.CTkFrame(f,fg_color='transparent');bar.pack(fill='x',pady=(0,8));ctk.CTkButton(bar,text='Mark OUT',fg_color=GREEN,command=lambda:self.delivery_status('OUT')).pack(side='left');ctk.CTkButton(bar,text='Mark PENDING',fg_color=SOFT,text_color=INK,command=lambda:self.delivery_status('PENDING')).pack(side='left',padx=6);ctk.CTkButton(bar,text='Delete / Reverse Delivery',fg_color=DANGER,command=self.delete_delivery).pack(side='right')
        card=self.card(f);card.pack(fill='both',expand=True);self.delivery_table=self.table(card,('id','date','customer','phone','address','total','status'),[70,150,160,120,240,90,90],15);self.delivery_table.pack(fill='both',expand=True,padx=10,pady=10)

    def delete_delivery(self):
        s=self.delivery_table.selection()
        if not s:return messagebox.showinfo('Delete Delivery','Select a delivery first.',parent=self)
        sid=int(s[0]);vals=self.delivery_table.item(s[0],'values')
        if not self._confirm('Delete Delivery',f"Delete delivery / sale #{sid} for {vals[2]}?\n\nSold quantities will be returned to stock."):return
        self._delete_sale(sid);self.refresh_delivery();self.refresh_products();self.refresh_pos_products();self.refresh_dashboard();self.refresh_reports()

    # REPORTS — same center, add Expense Report and Delete/Reverse Selected.
    def build_reports(self):
        f=ctk.CTkFrame(self.pages,fg_color=BG,corner_radius=0);self.frames['reports']=f
        bar=self.card(f);bar.pack(fill='x',pady=(0,10));self.report_type=ctk.StringVar(value='Profit & Loss');types=['Profit & Loss','Sales Report','Sales by Product','Purchase Report','Supplier Report','Inventory Report','Cost History','Expense Report'];ctk.CTkOptionMenu(bar,values=types,variable=self.report_type,width=210,command=lambda _:self.refresh_reports()).pack(side='left',padx=12,pady=12)
        for txt,val in [('Today','today'),('Week','week'),('Month','month'),('All','all')]:ctk.CTkButton(bar,text=txt,width=72,fg_color=SOFT,text_color=INK,hover_color='#D9E6EE',command=lambda v=val:self.set_report_period(v)).pack(side='left',padx=3)
        ctk.CTkButton(bar,text='Custom Dates',width=105,fg_color=SOFT,text_color=INK,command=self.custom_dates).pack(side='left',padx=3);ctk.CTkButton(bar,text='Export CSV',width=100,fg_color=ACCENT,command=self.export_report).pack(side='right',padx=(4,12));ctk.CTkButton(bar,text='Print',width=80,fg_color=SOFT,text_color=INK,command=self.print_report).pack(side='right',padx=4);ctk.CTkButton(bar,text='+ Expense',width=95,fg_color='#F3E8D7',text_color='#7F5A21',command=self.add_expense).pack(side='right',padx=4);ctk.CTkButton(bar,text='Delete / Reverse Selected',width=155,fg_color=DANGER,command=self.delete_report_selected).pack(side='right',padx=4)
        met=ctk.CTkFrame(f,fg_color='transparent');met.pack(fill='x',pady=(0,10));self.rmetrics={}
        for i,(k,label) in enumerate([('sales','Sales'),('cogs','COGS'),('gross_profit','Gross Profit'),('expenses','Expenses'),('net_profit','Net Profit'),('inventory_value','Inventory Value')]):met.grid_columnconfigure(i,weight=1);c,v,s=self.metric(met,label);c.grid(row=0,column=i,sticky='ew',padx=3);v.configure(font=('Segoe UI',17,'bold'));self.rmetrics[k]=v
        card=self.card(f);card.pack(fill='both',expand=True);self.report_caption=ctk.CTkLabel(card,text='Profit & Loss',text_color=INK,font=('Segoe UI',15,'bold'));self.report_caption.pack(anchor='w',padx=14,pady=(12,6));self.report_holder=ctk.CTkFrame(card,fg_color='white');self.report_holder.pack(fill='both',expand=True,padx=10,pady=(0,10));self.report_table=None;self.report_rows=[];self.report_cols=[]

    def refresh_reports(self):
        period,a,b=self._rp();r=DB.report(period,a,b)
        for k,v in self.rmetrics.items():v.configure(text=money(r[k]))
        typ=self.report_type.get();self.report_caption.configure(text=f'{typ} — {period.title()}')
        if typ=='Profit & Loss':cols=['metric','amount'];rows=[('Sales',money(r['sales'])),('COGS',money(r['cogs'])),('Gross Profit',money(r['gross_profit'])),('Expenses',money(r['expenses'])),('Net Profit',money(r['net_profit'])),('Inventory Value',money(r['inventory_value'])),('Sales Count',r['sales_count'])]
        elif typ=='Sales Report':cols=['id','date','type','customer','payment','total','profit'];rows=[(x['id'],x['created_at'].replace('T',' '),x['sale_type'],x['customer_name'],x['payment_method'],money(x['total']),money(float(x['total'])-float(x['cost_total']))) for x in DB.sales_history(period,a,b)]
        elif typ=='Sales by Product':cols=['product','barcode','qty','sales','cost','profit'];rows=[(x['name'],x['barcode'],f"{x['qty']:g}",money(x['sales']),money(x['cost']),money(x['profit'])) for x in DB.sales_by_product(period,a,b)]
        elif typ=='Purchase Report':cols=['id','date','supplier','product','qty','unit_cost','total'];rows=[(x['id'],x['created_at'].replace('T',' '),x['supplier_name'] or 'No Supplier',x['product_name'],f"{x['qty']:g}",money(x['unit_cost']),money(x['total'])) for x in DB.purchase_history(period,a,b)]
        elif typ=='Supplier Report':cols=['supplier','entries','qty','purchases'];rows=[(x['supplier'],x['entries'],f"{x['qty']:g}",money(x['purchases'])) for x in DB.supplier_report(period,a,b)]
        elif typ=='Inventory Report':cols=['barcode','product','category','stock','avg_cost','last_cost','sell_price','value'];rows=[(x['barcode'],x['name'],x['category'],f"{x['stock']:g}",money(x['cost']),money(x['last_cost']),money(x['price']),money(float(x['stock'])*float(x['cost']))) for x in DB.inventory()]
        elif typ=='Cost History':cols=['id','date','product','supplier','qty','cost','total'];rows=[(x['id'],x['created_at'].replace('T',' '),x['product_name'],x['supplier_name'] or 'No Supplier',f"{x['qty']:g}",money(x['unit_cost']),money(x['total'])) for x in DB.cost_history(period,a,b)]
        else:
            aa,bb=DB._bounds(period,a,b);w='';args=[]
            if aa:w=' WHERE created_at>=? AND created_at<?';args=[aa,bb]
            with DB.connect() as c:er=c.execute('SELECT * FROM expenses'+w+' ORDER BY id DESC',args).fetchall()
            cols=['id','date','description','amount'];rows=[(x['id'],x['created_at'].replace('T',' '),x['description'],money(x['amount'])) for x in er]
        self.render_report_table(cols,rows)

    def delete_report_selected(self):
        if not self.report_table:return
        s=self.report_table.selection()
        if not s:return messagebox.showinfo('Delete / Reverse','Select a row first.',parent=self)
        vals=self.report_table.item(s[0],'values');typ=self.report_type.get()
        try:
            if typ=='Sales Report':
                sid=int(vals[0])
                if not self._confirm('Reverse Sale',f'Reverse sale #{sid}?\nSold quantities will return to stock.'):return
                self._delete_sale(sid)
            elif typ in ('Purchase Report','Cost History'):
                pid=int(vals[0])
                if not self._confirm('Reverse Stock In',f'Reverse Stock In #{pid}?'):return
                self._delete_purchase(pid)
            elif typ=='Inventory Report':
                barcode=str(vals[0]);p=DB.product_by_barcode(barcode)
                if not p:return
                if not self._confirm('Delete Product',f"Remove '{p['name']}' from active stock?"):return
                with DB.connect() as c:c.execute('UPDATE products SET active=0 WHERE id=?',(p['id'],))
            elif typ=='Expense Report':
                eid=int(vals[0])
                if not self._confirm('Delete Expense',f'Delete expense #{eid}?'):return
                with DB.connect() as c:c.execute('DELETE FROM expenses WHERE id=?',(eid,))
            else:return messagebox.showinfo('Delete / Reverse','This report is summary/read-only. Open the related detailed report or module to delete a record.',parent=self)
            self.refresh_reports();self.refresh_dashboard();self.refresh_products();self.refresh_pos_products();self.refresh_stock();self.refresh_delivery();self.refresh_suppliers()
        except Exception as ex:messagebox.showerror('Delete / Reverse',str(ex),parent=self)
