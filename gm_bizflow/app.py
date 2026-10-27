from __future__ import annotations
import os, sys, tempfile, subprocess
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from core import BizFlowDB

APP_NAME='GM BizFlow'
APP_VERSION='1.0.0'

def app_data_dir():
    base=os.environ.get('LOCALAPPDATA') or str(Path.home())
    p=Path(base)/'GM BizFlow'; p.mkdir(parents=True,exist_ok=True)
    (p/'receipts').mkdir(exist_ok=True); (p/'backups').mkdir(exist_ok=True)
    return p

DATA=app_data_dir(); DB=BizFlowDB(DATA/'gm_bizflow.db')

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title(f'{APP_NAME} {APP_VERSION}'); self.geometry('1380x820'); self.minsize(1120,680)
        self.cart={}; self.sale_type=tk.StringVar(value='WALK_IN'); self._style(); self._ui(); self.refresh_products(); self.refresh_cart()
    def _style(self):
        s=ttk.Style(self)
        try:s.theme_use('clam')
        except:pass
        bg='#f4f7fb'; self.configure(bg=bg)
        s.configure('TFrame',background=bg); s.configure('TLabel',background=bg,font=('Segoe UI',10)); s.configure('TButton',font=('Segoe UI',10),padding=7)
        s.configure('Treeview',rowheight=30,font=('Segoe UI',10),background='white',fieldbackground='white')
        s.configure('Treeview.Heading',font=('Segoe UI',10,'bold'))
        s.configure('Nav.TButton',font=('Segoe UI',10,'bold'),padding=9)
        s.configure('Pay.TButton',font=('Segoe UI',11,'bold'),padding=12)
    def _ui(self):
        top=ttk.Frame(self); top.pack(fill='x',padx=12,pady=(10,6))
        ttk.Label(top,text='GM BizFlow',font=('Segoe UI',22,'bold')).pack(side='left')
        ttk.Label(top,text='  POS • Inventory • Delivery',font=('Segoe UI',10)).pack(side='left',pady=(8,0))
        self.store_lbl=ttk.Label(top,text=DB.get_setting('store_name'),font=('Segoe UI',11,'bold')); self.store_lbl.pack(side='right')
        nav=ttk.Frame(self); nav.pack(fill='x',padx=12,pady=(0,8))
        for t,cmd in [('Products',self.open_products),('Stock In',self.open_stockin),('Suppliers',self.open_suppliers),('Delivery Orders',self.open_deliveries),('Expenses',self.add_expense),('Reports',self.open_reports),('Settings',self.open_settings)]:
            ttk.Button(nav,text=t,command=cmd,style='Nav.TButton').pack(side='left',padx=(0,5))
        ratebox=ttk.Label(nav,text=f"1 USD = {DB.rate():,.0f} LBP",font=('Segoe UI',10,'bold')); ratebox.pack(side='right'); self.rate_lbl=ratebox
        search=ttk.Frame(self); search.pack(fill='x',padx=12,pady=(0,8))
        self.q=tk.StringVar(); e=ttk.Entry(search,textvariable=self.q,font=('Segoe UI',15)); e.pack(side='left',fill='x',expand=True,ipady=7)
        e.bind('<Return>',self.scan_or_search); e.bind('<KeyRelease>',lambda _:self.refresh_products())
        ttk.Button(search,text='Scan / Add',command=self.scan_or_search).pack(side='left',padx=(7,0)); self.search_entry=e
        body=ttk.Frame(self); body.pack(fill='both',expand=True,padx=12,pady=(0,10))
        left=ttk.Frame(body); left.pack(side='left',fill='both',expand=True,padx=(0,8))
        self.products_tree=ttk.Treeview(left,columns=('barcode','name','category','price','stock'),show='headings',selectmode='browse')
        for c,w in [('barcode',150),('name',300),('category',140),('price',100),('stock',90)]: self.products_tree.heading(c,text=c.title()); self.products_tree.column(c,width=w,anchor='w' if c in ('barcode','name','category') else 'center')
        self.products_tree.pack(fill='both',expand=True); self.products_tree.bind('<Double-1>',self.add_selected_product)
        right=ttk.Frame(body,width=480); right.pack(side='right',fill='both'); right.pack_propagate(False)
        mode=ttk.Frame(right); mode.pack(fill='x',pady=(0,6))
        ttk.Radiobutton(mode,text='Walk-in Sale',variable=self.sale_type,value='WALK_IN',command=self.delivery_toggle).pack(side='left')
        ttk.Radiobutton(mode,text='Delivery Out',variable=self.sale_type,value='DELIVERY',command=self.delivery_toggle).pack(side='left',padx=12)
        self.delivery_frame=ttk.Frame(right)
        self.customer=tk.StringVar(); self.phone=tk.StringVar(); self.address=tk.StringVar()
        for lab,var in [('Customer',self.customer),('Phone',self.phone),('Address',self.address)]:
            row=ttk.Frame(self.delivery_frame); row.pack(fill='x',pady=2); ttk.Label(row,text=lab,width=9).pack(side='left'); ttk.Entry(row,textvariable=var).pack(side='left',fill='x',expand=True)
        self.cart_tree=ttk.Treeview(right,columns=('name','qty','price','total'),show='headings',height=10)
        for c,w in [('name',200),('qty',55),('price',80),('total',85)]: self.cart_tree.heading(c,text=c.title()); self.cart_tree.column(c,width=w,anchor='center' if c!='name' else 'w')
        self.cart_tree.pack(fill='both',expand=True)
        cb=ttk.Frame(right); cb.pack(fill='x',pady=6)
        ttk.Button(cb,text='+ Qty',command=lambda:self.change_qty(1)).pack(side='left'); ttk.Button(cb,text='− Qty',command=lambda:self.change_qty(-1)).pack(side='left',padx=4); ttk.Button(cb,text='Remove',command=self.remove_cart).pack(side='left')
        disc=ttk.Frame(right); disc.pack(fill='x'); ttk.Label(disc,text='Discount USD').pack(side='left'); self.discount=tk.StringVar(value='0'); ttk.Entry(disc,textvariable=self.discount,width=12,justify='right').pack(side='right'); self.discount.trace_add('write',lambda *_:self.refresh_cart())
        self.total_usd=tk.StringVar(); self.total_lbp=tk.StringVar(); ttk.Label(right,textvariable=self.total_usd,font=('Segoe UI',22,'bold')).pack(anchor='e',pady=(12,0)); ttk.Label(right,textvariable=self.total_lbp,font=('Segoe UI',12,'bold')).pack(anchor='e')
        pay=ttk.Frame(right); pay.pack(fill='x',pady=(10,0)); ttk.Button(pay,text='Cash USD + Receipt',style='Pay.TButton',command=lambda:self.checkout('USD')).pack(side='left',fill='x',expand=True); ttk.Button(pay,text='Cash LBP + Receipt',style='Pay.TButton',command=lambda:self.checkout('LBP')).pack(side='left',fill='x',expand=True,padx=(7,0))
        ttk.Button(right,text='Clear Sale',command=self.clear_cart).pack(fill='x',pady=(7,0)); self.delivery_toggle()
    def delivery_toggle(self):
        if self.sale_type.get()=='DELIVERY': self.delivery_frame.pack(fill='x',before=self.cart_tree,pady=(0,6))
        else:self.delivery_frame.pack_forget()
    def refresh_products(self):
        for i in self.products_tree.get_children():self.products_tree.delete(i)
        for p in DB.search_products(self.q.get(),200): self.products_tree.insert('', 'end',iid=str(p['id']),values=(p['barcode'],p['name'],p['category'],f"${p['price']:.2f}",f"{p['stock']:g}"))
    def scan_or_search(self,e=None):
        q=self.q.get().strip(); p=DB.product_by_barcode(q) if q else None
        if p:self.add_product(p['id']); self.q.set(''); self.refresh_products(); self.search_entry.focus_set()
        else:self.refresh_products()
    def add_selected_product(self,e=None):
        s=self.products_tree.selection()
        if s:self.add_product(int(s[0]))
    def add_product(self,pid):
        p=DB.product(pid); cur=self.cart.get(pid,{'qty':0})['qty']
        if cur+1>p['stock']: return messagebox.showwarning('Stock',f"Not enough stock for {p['name']}")
        self.cart[pid]={'product_id':pid,'name':p['name'],'qty':cur+1,'price':float(p['price'])}; self.refresh_cart()
    def refresh_cart(self):
        for i in self.cart_tree.get_children():self.cart_tree.delete(i)
        subtotal=0
        for pid,v in self.cart.items():
            line=v['qty']*v['price']; subtotal+=line; self.cart_tree.insert('', 'end',iid=str(pid),values=(v['name'],f"{v['qty']:g}",f"${v['price']:.2f}",f"${line:.2f}"))
        try:d=max(0,float(self.discount.get() or 0))
        except:d=0
        total=max(0,subtotal-d); self.total_usd.set(f"Total USD  ${total:.2f}"); self.total_lbp.set(f"Total LBP  {DB.usd_to_lbp(total):,.0f} LBP")
    def change_qty(self,d):
        s=self.cart_tree.selection()
        if not s:return
        pid=int(s[0]); n=self.cart[pid]['qty']+d; stock=float(DB.product(pid)['stock'])
        if n<=0:self.cart.pop(pid,None)
        elif n<=stock:self.cart[pid]['qty']=n
        else:messagebox.showwarning('Stock','Not enough stock')
        self.refresh_cart()
    def remove_cart(self):
        s=self.cart_tree.selection()
        if s:self.cart.pop(int(s[0]),None); self.refresh_cart()
    def clear_cart(self):self.cart.clear();self.discount.set('0');self.customer.set('');self.phone.set('');self.address.set('');self.refresh_cart()
    def checkout(self,currency):
        if not self.cart:return messagebox.showinfo('Sale','Cart is empty')
        if self.sale_type.get()=='DELIVERY' and not self.customer.get().strip():return messagebox.showwarning('Delivery','Customer name is required for Delivery Out')
        try:discount=float(self.discount.get() or 0)
        except:return messagebox.showerror('Discount','Invalid discount')
        try:
            sid=DB.create_sale(list(self.cart.values()),discount=discount,paid_currency=currency,sale_type=self.sale_type.get(),customer_name=self.customer.get(),phone=self.phone.get(),address=self.address.get(),delivery_status='OUT' if self.sale_type.get()=='DELIVERY' else '')
            p=DATA/'receipts'/f'receipt_{sid}.txt'; p.write_text(DB.receipt_text(sid),encoding='utf-8')
            self.print_receipt(p); messagebox.showinfo('Saved',f'Sale #{sid} saved successfully.'); self.clear_cart(); self.refresh_products()
        except Exception as ex:messagebox.showerror('Sale Error',str(ex))
    def print_receipt(self,path):
        if sys.platform=='win32':
            try:subprocess.Popen(['notepad.exe','/p',str(path)],creationflags=0x08000000)
            except Exception as ex:messagebox.showwarning('Printer',f'Receipt saved but print failed: {ex}')
    def open_products(self):ProductWindow(self)
    def open_suppliers(self):SupplierWindow(self)
    def open_stockin(self):StockInWindow(self)
    def open_deliveries(self):DeliveryWindow(self)
    def open_reports(self):ReportWindow(self)
    def add_expense(self):
        d=simpledialog.askstring('Expense','Description:',parent=self)
        if not d:return
        a=simpledialog.askfloat('Expense','Amount USD:',parent=self,minvalue=0)
        if a is not None:
            try:DB.add_expense(d,a);messagebox.showinfo('Expense','Expense saved.')
            except Exception as ex:messagebox.showerror('Expense',str(ex))
    def open_settings(self):SettingsWindow(self)

class ProductWindow(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent);self.parent=parent;self.title('Products');self.geometry('1050x650');self.v={k:tk.StringVar() for k in ('barcode','name','category','cost','price','stock','image')};self.serial=tk.BooleanVar();self.ui();self.load()
    def ui(self):
        f=ttk.LabelFrame(self,text='Add / Edit Product');f.pack(fill='x',padx=8,pady=8)
        for i,(lab,k) in enumerate([('Barcode','barcode'),('Name','name'),('Category','category'),('Cost USD','cost'),('Sale USD','price'),('Opening Stock','stock')]):
            ttk.Label(f,text=lab).grid(row=0,column=i,padx=3,pady=2);ttk.Entry(f,textvariable=self.v[k],width=17).grid(row=1,column=i,padx=3,pady=3)
        ttk.Checkbutton(f,text='Track Serial Numbers',variable=self.serial).grid(row=2,column=0,columnspan=2,sticky='w',padx=3)
        ttk.Entry(f,textvariable=self.v['image'],width=45).grid(row=2,column=2,columnspan=3,sticky='ew',padx=3);ttk.Button(f,text='Optional Image…',command=self.pick_image).grid(row=2,column=5,padx=3)
        ttk.Button(f,text='Save Product',command=self.save).grid(row=1,column=6,padx=6)
        self.t=ttk.Treeview(self,columns=('barcode','name','category','cost','price','stock','serial'),show='headings')
        for c in self.t['columns']:self.t.heading(c,text=c.title())
        self.t.pack(fill='both',expand=True,padx=8,pady=8);self.t.bind('<Double-1>',self.pick)
        ttk.Button(self,text='Manage Serial Numbers',command=self.serials).pack(anchor='w',padx=8,pady=(0,8))
    def pick_image(self):
        p=filedialog.askopenfilename(parent=self,filetypes=[('Images','*.png;*.jpg;*.jpeg;*.webp'),('All','*.*')])
        if p:self.v['image'].set(p)
    def save(self):
        try:DB.upsert_product(self.v['barcode'].get(),self.v['name'].get(),self.v['category'].get(),float(self.v['cost'].get() or 0),float(self.v['price'].get() or 0),float(self.v['stock'].get() or 0),self.serial.get(),self.v['image'].get());self.load();self.parent.refresh_products()
        except Exception as ex:messagebox.showerror('Product',str(ex),parent=self)
    def load(self):
        for i in self.t.get_children():self.t.delete(i)
        for p in DB.search_products('',1000):self.t.insert('', 'end',iid=str(p['id']),values=(p['barcode'],p['name'],p['category'],f"{p['cost']:.2f}",f"{p['price']:.2f}",f"{p['stock']:g}",'Yes' if p['track_serial'] else 'No'))
    def pick(self,e=None):
        s=self.t.selection()
        if not s:return
        p=DB.product(int(s[0]))
        for k in ('barcode','name','category','cost','price','stock','image'):self.v[k].set(p[k])
        self.serial.set(bool(p['track_serial']))
    def serials(self):
        s=self.t.selection()
        if not s:return messagebox.showinfo('Serials','Select a product.',parent=self)
        SerialWindow(self,int(s[0]))

class SerialWindow(tk.Toplevel):
    def __init__(self,parent,pid):
        super().__init__(parent);self.pid=pid;self.title('Serial Numbers');self.geometry('600x480');self.v=tk.StringVar();f=ttk.Frame(self);f.pack(fill='x',padx=8,pady=8);ttk.Entry(f,textvariable=self.v).pack(side='left',fill='x',expand=True);ttk.Button(f,text='Add Serial',command=self.add).pack(side='left',padx=5);self.t=ttk.Treeview(self,columns=('serial','status'),show='headings');self.t.heading('serial',text='Serial');self.t.heading('status',text='Status');self.t.pack(fill='both',expand=True,padx=8,pady=8);self.load()
    def add(self):
        try:DB.add_serials(self.pid,[self.v.get()]);self.v.set('');self.load()
        except Exception as ex:messagebox.showerror('Serial',str(ex),parent=self)
    def load(self):
        for i in self.t.get_children():self.t.delete(i)
        with DB.connect() as c:rows=c.execute('SELECT serial_no,status FROM serials WHERE product_id=? ORDER BY id DESC',(self.pid,)).fetchall()
        for r in rows:self.t.insert('', 'end',values=(r['serial_no'],r['status']))

class SupplierWindow(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent);self.title('Suppliers');self.geometry('620x470');self.n=tk.StringVar();self.p=tk.StringVar();f=ttk.Frame(self);f.pack(fill='x',padx=8,pady=8);ttk.Entry(f,textvariable=self.n).pack(side='left',fill='x',expand=True);ttk.Entry(f,textvariable=self.p,width=18).pack(side='left',padx=4);ttk.Button(f,text='Add Supplier',command=self.add).pack(side='left');self.t=ttk.Treeview(self,columns=('name','phone'),show='headings');self.t.heading('name',text='Supplier');self.t.heading('phone',text='Phone');self.t.pack(fill='both',expand=True,padx=8,pady=8);self.load()
    def add(self):
        try:DB.add_supplier(self.n.get(),self.p.get());self.n.set('');self.p.set('');self.load()
        except Exception as ex:messagebox.showerror('Supplier',str(ex),parent=self)
    def load(self):
        for i in self.t.get_children():self.t.delete(i)
        for r in DB.suppliers():self.t.insert('', 'end',values=(r['name'],r['phone']))

class StockInWindow(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent);self.parent=parent;self.title('Stock In / Purchase');self.geometry('700x500');self.products=DB.search_products('',1000);self.sups=DB.suppliers();self.p=tk.StringVar();self.s=tk.StringVar();self.qty=tk.StringVar(value='1');self.cost=tk.StringVar();self.ui()
    def ui(self):
        f=ttk.Frame(self);f.pack(fill='both',expand=True,padx=18,pady=18)
        for lab,var,vals in [('Product',self.p,[x['name'] for x in self.products]),('Supplier',self.s,[x['name'] for x in self.sups])]:ttk.Label(f,text=lab).pack(anchor='w');ttk.Combobox(f,textvariable=var,values=vals,width=55,state='readonly').pack(fill='x',pady=(2,8))
        ttk.Label(f,text='Quantity').pack(anchor='w');ttk.Entry(f,textvariable=self.qty).pack(fill='x',pady=(2,8));ttk.Label(f,text='Unit Cost USD').pack(anchor='w');ttk.Entry(f,textvariable=self.cost).pack(fill='x',pady=(2,8));ttk.Label(f,text='Serials (one per line, only if tracked)').pack(anchor='w');self.sertext=tk.Text(f,height=6);self.sertext.pack(fill='x',pady=(2,8));ttk.Button(f,text='SAVE PURCHASE / ADD STOCK',command=self.save).pack(fill='x',ipady=8)
    def save(self):
        pm={x['name']:x['id'] for x in self.products};sm={x['name']:x['id'] for x in self.sups}
        if self.p.get() not in pm:return
        try:DB.stock_in(pm[self.p.get()],float(self.qty.get()),float(self.cost.get()),sm.get(self.s.get()),self.sertext.get('1.0','end').splitlines());messagebox.showinfo('Stock In','Purchase saved and inventory updated.',parent=self);self.parent.refresh_products();self.destroy()
        except Exception as ex:messagebox.showerror('Stock In',str(ex),parent=self)

class DeliveryWindow(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent);self.title('Delivery Orders');self.geometry('950x560');self.t=ttk.Treeview(self,columns=('id','date','customer','phone','address','total','status'),show='headings')
        for c in self.t['columns']:self.t.heading(c,text=c.title())
        self.t.pack(fill='both',expand=True,padx=8,pady=8);b=ttk.Frame(self);b.pack(fill='x',padx=8,pady=(0,8));ttk.Button(b,text='Mark Delivered',command=lambda:self.status('DELIVERED')).pack(side='left');ttk.Button(b,text='Mark Out',command=lambda:self.status('OUT')).pack(side='left',padx=5);self.load()
    def load(self):
        for i in self.t.get_children():self.t.delete(i)
        with DB.connect() as c:rows=c.execute("SELECT * FROM sales WHERE sale_type='DELIVERY' ORDER BY id DESC").fetchall()
        for r in rows:self.t.insert('', 'end',iid=str(r['id']),values=(r['id'],r['created_at'][:16],r['customer_name'],r['phone'],r['address'],f"${r['total']:.2f}",r['delivery_status']))
    def status(self,s):
        x=self.t.selection()
        if x:DB.set_delivery_status(int(x[0]),s);self.load()

class ReportWindow(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent);self.title('Profit & Loss / Inventory');self.geometry('1000x620');r=DB.report();ttk.Label(self,text=f"Sales ${r['sales']:.2f}   COGS ${r['cogs']:.2f}   Gross ${r['gross_profit']:.2f}   Expenses ${r['expenses']:.2f}   Net ${r['net_profit']:.2f}   Inventory ${r['inventory_value']:.2f}",font=('Segoe UI',12,'bold')).pack(pady=12);self.t=ttk.Treeview(self,columns=('barcode','name','stock','cost','price','value'),show='headings')
        for c in self.t['columns']:self.t.heading(c,text=c.title())
        self.t.pack(fill='both',expand=True,padx=8,pady=8)
        for p in DB.inventory():self.t.insert('', 'end',values=(p['barcode'],p['name'],f"{p['stock']:g}",f"${p['cost']:.2f}",f"${p['price']:.2f}",f"${p['stock']*p['cost']:.2f}"))

class SettingsWindow(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent);self.parent=parent;self.title('Settings');self.geometry('550x480');self.vars={k:tk.StringVar(value=DB.get_setting(k)) for k in ('store_name','store_phone','lbp_rate','receipt_width','receipt_footer')};self.show=tk.BooleanVar(value=DB.get_setting('show_images','0')=='1');f=ttk.Frame(self);f.pack(fill='both',expand=True,padx=18,pady=18)
        for lab,k in [('Business / Store Name','store_name'),('Phone','store_phone'),('LBP per 1 USD','lbp_rate'),('Receipt Width (32-56)','receipt_width'),('Receipt Footer','receipt_footer')]:ttk.Label(f,text=lab).pack(anchor='w');ttk.Entry(f,textvariable=self.vars[k]).pack(fill='x',pady=(2,9))
        ttk.Checkbutton(f,text='Show product images when available',variable=self.show).pack(anchor='w',pady=6);ttk.Button(f,text='Save Settings',command=self.save).pack(fill='x',ipady=7);ttk.Button(f,text='Backup Database…',command=self.backup).pack(fill='x',pady=6)
    def save(self):
        try:float(self.vars['lbp_rate'].get())
        except:return messagebox.showerror('Settings','Invalid LBP rate',parent=self)
        for k,v in self.vars.items():DB.set_setting(k,v.get())
        DB.set_setting('show_images','1' if self.show.get() else '0');self.parent.store_lbl.config(text=DB.get_setting('store_name'));self.parent.rate_lbl.config(text=f"1 USD = {DB.rate():,.0f} LBP");self.parent.refresh_cart();messagebox.showinfo('Settings','Saved.',parent=self)
    def backup(self):
        p=filedialog.asksaveasfilename(parent=self,defaultextension='.db',initialfile=f"gm_bizflow_backup_{datetime.now():%Y%m%d}.db",filetypes=[('Database','*.db')])
        if p:DB.backup(p);messagebox.showinfo('Backup','Backup created.',parent=self)

def self_test():
    td=tempfile.TemporaryDirectory(); d=BizFlowDB(Path(td.name)/'smoke.db'); d.set_setting('lbp_rate','89500'); s=d.add_supplier('Test Supplier'); p=d.upsert_product('TEST-001','Test Item','Test',5,10,0); d.stock_in(p,3,5,s); sid=d.create_sale([{'product_id':p,'qty':1}],paid_currency='LBP'); assert d.product(p)['stock']==2; assert d.sale(sid)[0]['paid_amount']==895000; assert 'TOTAL LBP' in d.receipt_text(sid); td.cleanup(); print('GM BizFlow SELF-TEST OK'); return 0

if __name__=='__main__':
    if '--self-test' in sys.argv:raise SystemExit(self_test())
    App().mainloop()
