from __future__ import annotations
import csv, os, sys, tempfile, subprocess
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import customtkinter as ctk
from core import BizFlowDB

APP_NAME='GM BizFlow'
APP_VERSION='2.0.0'
NAV='#203E57'; NAV2='#294F6C'; BG='#EEF3F8'; CARD='#FFFFFF'; INK='#1E3142'; MUT='#738493'; ACCENT='#2F6D96'; GREEN='#2F9A6B'; RED='#C95353'; LINE='#DDE6ED'

ctk.set_appearance_mode('light')
ctk.set_default_color_theme('blue')

def app_data_dir():
    base=os.environ.get('LOCALAPPDATA') or str(Path.home())
    p=Path(base)/'GM BizFlow';p.mkdir(parents=True,exist_ok=True)
    (p/'receipts').mkdir(exist_ok=True);(p/'backups').mkdir(exist_ok=True);(p/'exports').mkdir(exist_ok=True)
    return p

DATA=app_data_dir();DB=BizFlowDB(DATA/'gm_bizflow.db')

def money(v):return f'${float(v or 0):,.2f}'
def clear_tree(t):
    for i in t.get_children():t.delete(i)

def style_tree():
    s=ttk.Style();
    try:s.theme_use('clam')
    except:pass
    s.configure('Biz.Treeview',background='white',fieldbackground='white',foreground=INK,rowheight=31,borderwidth=0,font=('Segoe UI',10))
    s.configure('Biz.Treeview.Heading',background='#E9F0F5',foreground=INK,font=('Segoe UI',10,'bold'),relief='flat')
    s.map('Biz.Treeview',background=[('selected','#D8EAF5')],foreground=[('selected',INK)])

class App(ctk.CTk):
    def __init__(self):
        super().__init__();style_tree();self.title(f'{APP_NAME} {APP_VERSION}');self.geometry('1440x880');self.minsize(1180,720);self.configure(fg_color=BG)
        self.cart={};self.current_page='dashboard';self.report_period='month';self.report_custom=(None,None)
        self.protocol('WM_DELETE_WINDOW',self.on_exit);self.build_shell();self.show_page('dashboard')

    def on_exit(self):
        try:DB.daily_backup()
        finally:self.destroy()

    def build_shell(self):
        self.grid_columnconfigure(1,weight=1);self.grid_rowconfigure(0,weight=1)
        self.side=ctk.CTkFrame(self,width=230,corner_radius=0,fg_color=NAV);self.side.grid(row=0,column=0,sticky='nsew');self.side.grid_propagate(False)
        logo=ctk.CTkFrame(self.side,fg_color='transparent');logo.pack(fill='x',padx=18,pady=(20,18))
        mark=ctk.CTkFrame(logo,width=48,height=48,corner_radius=12,fg_color='#FFFFFF');mark.pack(side='left');mark.pack_propagate(False)
        ctk.CTkLabel(mark,text='GM',text_color=NAV,font=('Segoe UI',18,'bold')).pack(expand=True)
        lf=ctk.CTkFrame(logo,fg_color='transparent');lf.pack(side='left',padx=10)
        ctk.CTkLabel(lf,text='GM BizFlow',text_color='white',font=('Segoe UI',20,'bold')).pack(anchor='w');ctk.CTkLabel(lf,text='POS • Inventory • Reports',text_color='#BDD0DE',font=('Segoe UI',10)).pack(anchor='w')
        self.nav_buttons={}
        items=[('dashboard','Dashboard','▦'),('pos','POS / Checkout','▣'),('products','Products','□'),('stock','Stock In','↓'),('suppliers','Suppliers','◇'),('delivery','Delivery Out','→'),('reports','Reports','▤'),('settings','Settings','⚙')]
        for key,label,icon in items:
            b=ctk.CTkButton(self.side,text=f'{icon}   {label}',anchor='w',height=42,corner_radius=9,fg_color='transparent',hover_color=NAV2,text_color='#E8F1F6',font=('Segoe UI',12,'bold'),command=lambda k=key:self.show_page(k));b.pack(fill='x',padx=12,pady=3);self.nav_buttons[key]=b
        ctk.CTkLabel(self.side,text=f'Version {APP_VERSION}',text_color='#90A9BA',font=('Segoe UI',9)).pack(side='bottom',pady=14)
        self.main=ctk.CTkFrame(self,fg_color=BG,corner_radius=0);self.main.grid(row=0,column=1,sticky='nsew');self.main.grid_rowconfigure(1,weight=1);self.main.grid_columnconfigure(0,weight=1)
        top=ctk.CTkFrame(self.main,height=68,fg_color=BG,corner_radius=0);top.grid(row=0,column=0,sticky='ew',padx=24,pady=(12,0));top.grid_columnconfigure(0,weight=1)
        self.page_title=ctk.CTkLabel(top,text='Dashboard',text_color=INK,font=('Segoe UI',26,'bold'));self.page_title.grid(row=0,column=0,sticky='w')
        self.store_label=ctk.CTkLabel(top,text=DB.get_setting('store_name'),text_color=ACCENT,font=('Segoe UI',12,'bold'));self.store_label.grid(row=0,column=1,padx=10)
        self.rate_label=ctk.CTkLabel(top,text=f'1 USD = {DB.rate():,.0f} LBP',fg_color='#E2EFF7',corner_radius=12,text_color=ACCENT,font=('Segoe UI',11,'bold'),padx=12,pady=6);self.rate_label.grid(row=0,column=2)
        self.pages=ctk.CTkFrame(self.main,fg_color=BG,corner_radius=0);self.pages.grid(row=1,column=0,sticky='nsew',padx=24,pady=(6,20));self.pages.grid_rowconfigure(0,weight=1);self.pages.grid_columnconfigure(0,weight=1)
        self.frames={}
        self.build_dashboard();self.build_pos();self.build_products();self.build_stock();self.build_suppliers();self.build_delivery();self.build_reports();self.build_settings()

    def card(self,parent,**kw):return ctk.CTkFrame(parent,fg_color=CARD,corner_radius=14,border_width=1,border_color=LINE,**kw)
    def metric(self,parent,title):
        f=self.card(parent);ctk.CTkLabel(f,text=title,text_color=MUT,font=('Segoe UI',11,'bold')).pack(anchor='w',padx=16,pady=(14,0));v=ctk.CTkLabel(f,text='$0.00',text_color=INK,font=('Segoe UI',25,'bold'));v.pack(anchor='w',padx=16,pady=(4,2));s=ctk.CTkLabel(f,text='',text_color=MUT,font=('Segoe UI',9));s.pack(anchor='w',padx=16,pady=(0,12));return f,v,s
    def table(self,parent,cols,widths=None,height=10):
        t=ttk.Treeview(parent,columns=cols,show='headings',style='Biz.Treeview',height=height)
        for i,c in enumerate(cols):t.heading(c,text=c.replace('_',' ').title());t.column(c,width=(widths[i] if widths else 120),anchor='w')
        return t

    def show_page(self,key):
        for k,f in self.frames.items():f.grid_forget()
        self.frames[key].grid(row=0,column=0,sticky='nsew')
        for k,b in self.nav_buttons.items():b.configure(fg_color=NAV2 if k==key else 'transparent')
        titles={'dashboard':'Dashboard','pos':'POS / Checkout','products':'Products','stock':'Stock In','suppliers':'Suppliers','delivery':'Delivery Out','reports':'Report Center','settings':'Settings'};self.page_title.configure(text=titles[key]);self.current_page=key
        getattr(self,f'refresh_{key}',lambda:None)()

    # DASHBOARD
    def build_dashboard(self):
        f=ctk.CTkFrame(self.pages,fg_color=BG,corner_radius=0);self.frames['dashboard']=f
        top=ctk.CTkFrame(f,fg_color='transparent');top.pack(fill='x');self.dmetrics={}
        for i,k in enumerate([('today','Sales Today'),('week','Sales This Week'),('month','Sales This Month')]):
            top.grid_columnconfigure(i,weight=1);c,v,s=self.metric(top,k[1]);c.grid(row=0,column=i,sticky='ew',padx=(0 if i==0 else 6,0 if i==2 else 6));self.dmetrics[k[0]]=(v,s)
        second=ctk.CTkFrame(f,fg_color='transparent');second.pack(fill='x',pady=12)
        for i,k in enumerate([('gross','Gross Profit'),('expenses','Expenses'),('net','Net Profit'),('inventory','Inventory Value')]):
            second.grid_columnconfigure(i,weight=1);c,v,s=self.metric(second,k[1]);c.grid(row=0,column=i,sticky='ew',padx=(0 if i==0 else 5,0 if i==3 else 5));self.dmetrics[k[0]]=(v,s)
        low=ctk.CTkFrame(f,fg_color='transparent');low.pack(fill='both',expand=True);low.grid_columnconfigure(0,weight=1);low.grid_columnconfigure(1,weight=1);low.grid_rowconfigure(0,weight=1)
        chart=self.card(low);chart.grid(row=0,column=0,sticky='nsew',padx=(0,6));ctk.CTkLabel(chart,text='7-Day Sales',text_color=INK,font=('Segoe UI',15,'bold')).pack(anchor='w',padx=16,pady=(14,4));self.sales_canvas=tk.Canvas(chart,bg='white',highlightthickness=0,height=250);self.sales_canvas.pack(fill='both',expand=True,padx=12,pady=(0,12))
        recent=self.card(low);recent.grid(row=0,column=1,sticky='nsew',padx=(6,0));ctk.CTkLabel(recent,text='Recent Sales',text_color=INK,font=('Segoe UI',15,'bold')).pack(anchor='w',padx=16,pady=(14,6));self.recent_table=self.table(recent,('date','total','profit','type'),[170,90,90,90],7);self.recent_table.pack(fill='both',expand=True,padx=12,pady=(0,12))

    def refresh_dashboard(self):
        p=DB.dashboard_periods()
        for k in ('today','week','month'):
            self.dmetrics[k][0].configure(text=money(p[k]['sales']));self.dmetrics[k][1].configure(text=f"{p[k]['sales_count']} sales")
        allr=DB.report();self.dmetrics['gross'][0].configure(text=money(allr['gross_profit']));self.dmetrics['gross'][1].configure(text='All-time gross profit');self.dmetrics['expenses'][0].configure(text=money(allr['expenses']));self.dmetrics['expenses'][1].configure(text='All expenses');self.dmetrics['net'][0].configure(text=money(allr['net_profit']));self.dmetrics['net'][1].configure(text='Gross − expenses');self.dmetrics['inventory'][0].configure(text=money(allr['inventory_value']));low=sum(1 for x in DB.inventory() if float(x['stock'])<=3);self.dmetrics['inventory'][1].configure(text=f'{low} low-stock items')
        clear_tree(self.recent_table)
        for s in DB.recent_sales():self.recent_table.insert('', 'end',values=(s['created_at'].replace('T',' '),money(s['total']),money(float(s['total'])-float(s['cost_total'])),'Delivery' if s['sale_type']=='DELIVERY' else 'Walk-in'))
        self.draw_chart()
    def draw_chart(self):
        c=self.sales_canvas;c.delete('all');data=DB.sales_last_days();c.update_idletasks();w=max(c.winfo_width(),500);h=max(c.winfo_height(),220);m=30;maxv=max([v for _,v in data]+[1]);bw=(w-2*m)/len(data)*.55;gap=(w-2*m)/len(data)
        c.create_line(m,h-35,w-m,h-35,fill='#CFDCE5')
        for i,(lab,val) in enumerate(data):
            x=m+i*gap+gap*.22;y=h-35-(h-65)*(val/maxv);c.create_rectangle(x,y,x+bw,h-35,fill='#2F6D96',outline='');c.create_text(x+bw/2,h-18,text=lab,fill='#708392',font=('Segoe UI',9));c.create_text(x+bw/2,max(12,y-10),text=f'${val:.0f}',fill=INK,font=('Segoe UI',8,'bold'))

    # POS
    def build_pos(self):
        f=ctk.CTkFrame(self.pages,fg_color=BG,corner_radius=0);self.frames['pos']=f;f.grid_columnconfigure(0,weight=3);f.grid_columnconfigure(1,weight=2);f.grid_rowconfigure(1,weight=1)
        self.pos_search=ctk.CTkEntry(f,placeholder_text='Search product or scan barcode...',height=42,font=('Segoe UI',13));self.pos_search.grid(row=0,column=0,columnspan=2,sticky='ew',pady=(0,10));self.pos_search.bind('<KeyRelease>',lambda e:self.refresh_pos_products());self.pos_search.bind('<Return>',self.scan_enter)
        left=self.card(f);left.grid(row=1,column=0,sticky='nsew',padx=(0,7));ctk.CTkLabel(left,text='Products',text_color=INK,font=('Segoe UI',15,'bold')).pack(anchor='w',padx=14,pady=(12,6));self.pos_products=self.table(left,('barcode','name','category','price','stock'),[130,240,130,90,70],15);self.pos_products.pack(fill='both',expand=True,padx=10,pady=(0,10));self.pos_products.bind('<Double-1>',lambda e:self.add_selected_product())
        right=self.card(f);right.grid(row=1,column=1,sticky='nsew',padx=(7,0));right.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(right,text='Current Sale',text_color=INK,font=('Segoe UI',15,'bold')).grid(row=0,column=0,sticky='w',padx=14,pady=(12,6));self.cart_table=self.table(right,('name','qty','price','total'),[180,50,80,90],7);self.cart_table.grid(row=1,column=0,sticky='nsew',padx=10);right.grid_rowconfigure(1,weight=1)
        qf=ctk.CTkFrame(right,fg_color='transparent');qf.grid(row=2,column=0,sticky='ew',padx=10,pady=7)
        for txt,cmd in [('+ Qty',lambda:self.cart_qty(1)),('− Qty',lambda:self.cart_qty(-1)),('Remove',self.cart_remove)]:ctk.CTkButton(qf,text=txt,width=80,height=30,fg_color='#E8F0F5',text_color=INK,hover_color='#DCE8F0',command=cmd).pack(side='left',padx=(0,5))
        opts=ctk.CTkFrame(right,fg_color='#F7FAFC',corner_radius=10);opts.grid(row=3,column=0,sticky='ew',padx=10,pady=(0,8));opts.grid_columnconfigure((1,3),weight=1)
        ctk.CTkLabel(opts,text='Discount USD',text_color=MUT).grid(row=0,column=0,padx=8,pady=6,sticky='w');self.discount=ctk.StringVar(value='0');de=ctk.CTkEntry(opts,textvariable=self.discount,width=90);de.grid(row=0,column=1,padx=6,pady=6,sticky='ew');self.discount.trace_add('write',lambda *_:self.refresh_cart())
        ctk.CTkLabel(opts,text='Payment',text_color=MUT).grid(row=0,column=2,padx=8);self.pay_method=ctk.StringVar(value='CASH');ctk.CTkOptionMenu(opts,values=['CASH','CARD'],variable=self.pay_method,command=lambda _:self.refresh_change()).grid(row=0,column=3,padx=6,pady=6,sticky='ew')
        ctk.CTkLabel(opts,text='Paid Currency',text_color=MUT).grid(row=1,column=0,padx=8,pady=6,sticky='w');self.paid_currency=ctk.StringVar(value='USD');ctk.CTkOptionMenu(opts,values=['USD','LBP'],variable=self.paid_currency,command=lambda _:self.refresh_change()).grid(row=1,column=1,padx=6,pady=6,sticky='ew')
        ctk.CTkLabel(opts,text='Customer Paid',text_color=MUT).grid(row=1,column=2,padx=8);self.paid_amount=ctk.StringVar(value='0');pe=ctk.CTkEntry(opts,textvariable=self.paid_amount);pe.grid(row=1,column=3,padx=6,pady=6,sticky='ew');self.paid_amount.trace_add('write',lambda *_:self.refresh_change())
        self.delivery_var=ctk.BooleanVar(value=False);ctk.CTkCheckBox(opts,text='Delivery Out',variable=self.delivery_var,command=self.delivery_fields_toggle,text_color=INK).grid(row=2,column=0,columnspan=2,padx=8,pady=8,sticky='w')
        self.customer=ctk.StringVar();self.phone=ctk.StringVar();self.address=ctk.StringVar();self.del_fields=ctk.CTkFrame(opts,fg_color='transparent');self.del_fields.grid(row=3,column=0,columnspan=4,sticky='ew',padx=6,pady=(0,6));self.del_fields.grid_columnconfigure((0,1,2),weight=1)
        for i,(ph,var) in enumerate([('Customer',self.customer),('Phone',self.phone),('Address',self.address)]):ctk.CTkEntry(self.del_fields,placeholder_text=ph,textvariable=var).grid(row=0,column=i,sticky='ew',padx=3)
        self.del_fields.grid_remove()
        totals=ctk.CTkFrame(right,fg_color='transparent');totals.grid(row=4,column=0,sticky='ew',padx=14,pady=3);totals.grid_columnconfigure(0,weight=1)
        self.total_label=ctk.CTkLabel(totals,text='Total USD  $0.00',text_color=INK,font=('Segoe UI',24,'bold'));self.total_label.grid(row=0,column=0,sticky='w');self.lbp_label=ctk.CTkLabel(totals,text='0 LBP',text_color=MUT,font=('Segoe UI',11,'bold'));self.lbp_label.grid(row=1,column=0,sticky='w');self.change_label=ctk.CTkLabel(totals,text='Change  $0.00',text_color=GREEN,font=('Segoe UI',17,'bold'));self.change_label.grid(row=0,column=1,rowspan=2,sticky='e')
        buttons=ctk.CTkFrame(right,fg_color='transparent');buttons.grid(row=5,column=0,sticky='ew',padx=10,pady=(6,10));buttons.grid_columnconfigure((0,1),weight=1)
        ctk.CTkButton(buttons,text='Complete Sale',height=44,fg_color=ACCENT,hover_color=NAV2,font=('Segoe UI',12,'bold'),command=self.checkout).grid(row=0,column=0,sticky='ew',padx=(0,4));ctk.CTkButton(buttons,text='Clear',height=44,fg_color='#E6EEF4',text_color=INK,hover_color='#D8E4EC',command=self.clear_sale).grid(row=0,column=1,sticky='ew',padx=(4,0))

    def refresh_pos(self):self.refresh_pos_products();self.refresh_cart()
    def refresh_pos_products(self):
        if not hasattr(self,'pos_products'):return
        clear_tree(self.pos_products);q=self.pos_search.get() if hasattr(self,'pos_search') else ''
        for p in DB.search_products(q,300):self.pos_products.insert('', 'end',iid=str(p['id']),values=(p['barcode'],p['name'],p['category'],money(p['price']),f"{p['stock']:g}"))
    def scan_enter(self,e=None):
        q=self.pos_search.get().strip();p=DB.product_by_barcode(q)
        if p:self.add_product(p['id']);self.pos_search.delete(0,'end');self.refresh_pos_products()
    def add_selected_product(self):
        s=self.pos_products.selection();
        if s:self.add_product(int(s[0]))
    def add_product(self,pid):
        p=DB.product(pid);cur=self.cart.get(pid,{'qty':0})['qty']
        if cur+1>float(p['stock']):return messagebox.showwarning('Stock',f"Not enough stock for {p['name']}")
        self.cart[pid]={'product_id':pid,'name':p['name'],'qty':cur+1,'price':float(p['price'])};self.refresh_cart()
    def cart_qty(self,d):
        s=self.cart_table.selection()
        if not s:return
        pid=int(s[0]);n=self.cart[pid]['qty']+d;stock=float(DB.product(pid)['stock'])
        if n<=0:self.cart.pop(pid,None)
        elif n<=stock:self.cart[pid]['qty']=n
        else:messagebox.showwarning('Stock','Not enough stock')
        self.refresh_cart()
    def cart_remove(self):
        s=self.cart_table.selection()
        if s:self.cart.pop(int(s[0]),None);self.refresh_cart()
    def totals(self):
        sub=sum(v['qty']*v['price'] for v in self.cart.values())
        try:d=max(0,float(self.discount.get() or 0))
        except:d=0
        return sub,max(0,sub-d)
    def refresh_cart(self):
        if not hasattr(self,'cart_table'):return
        clear_tree(self.cart_table)
        for pid,v in self.cart.items():self.cart_table.insert('', 'end',iid=str(pid),values=(v['name'],f"{v['qty']:g}",money(v['price']),money(v['qty']*v['price'])))
        _,t=self.totals();self.total_label.configure(text=f'Total USD  {money(t)}');self.lbp_label.configure(text=f'{DB.usd_to_lbp(t):,} LBP');self.refresh_change()
    def refresh_change(self):
        if not hasattr(self,'change_label'):return
        _,t=self.totals();cur=self.paid_currency.get();due=t if cur=='USD' else DB.usd_to_lbp(t)
        if self.pay_method.get()=='CARD':paid=due
        else:
            try:paid=float(self.paid_amount.get() or 0)
            except:paid=0
        diff=paid-due
        if diff>=0:self.change_label.configure(text=f"Change  {money(diff) if cur=='USD' else f'{diff:,.0f} LBP'}",text_color=GREEN)
        else:self.change_label.configure(text=f"Remaining  {money(-diff) if cur=='USD' else f'{-diff:,.0f} LBP'}",text_color=RED)
    def delivery_fields_toggle(self):
        if self.delivery_var.get():self.del_fields.grid()
        else:self.del_fields.grid_remove()
    def clear_sale(self):
        self.cart.clear();self.discount.set('0');self.paid_amount.set('0');self.customer.set('');self.phone.set('');self.address.set('');self.delivery_var.set(False);self.delivery_fields_toggle();self.refresh_cart()
    def checkout(self):
        if not self.cart:return messagebox.showinfo('Sale','Cart is empty')
        if self.delivery_var.get() and not self.customer.get().strip():return messagebox.showwarning('Delivery','Customer name is required')
        try:discount=float(self.discount.get() or 0);_,total=self.totals();cur=self.paid_currency.get();due=total if cur=='USD' else DB.usd_to_lbp(total);paid=due if self.pay_method.get()=='CARD' else float(self.paid_amount.get() or 0)
        except:return messagebox.showerror('Payment','Check discount and customer paid values')
        try:
            sid=DB.create_sale(list(self.cart.values()),discount=discount,paid_currency=cur,paid_amount=paid,payment_method=self.pay_method.get(),sale_type='DELIVERY' if self.delivery_var.get() else 'WALK_IN',customer_name=self.customer.get(),phone=self.phone.get(),address=self.address.get(),delivery_status='PENDING' if self.delivery_var.get() else '')
            p=DATA/'receipts'/f'receipt_{sid}.txt';p.write_text(DB.receipt_text(sid),encoding='utf-8');self.receipt_popup(sid,p);self.clear_sale();self.refresh_pos_products();self.refresh_dashboard()
        except Exception as ex:messagebox.showerror('Sale Error',str(ex))
    def receipt_popup(self,sid,path):
        w=ctk.CTkToplevel(self);w.title(f'Receipt #{sid}');w.geometry('480x650');box=ctk.CTkTextbox(w,font=('Consolas',11));box.pack(fill='both',expand=True,padx=12,pady=12);box.insert('1.0',DB.receipt_text(sid));box.configure(state='disabled');ctk.CTkButton(w,text='Print Receipt',command=lambda:self.print_file(path)).pack(fill='x',padx=12,pady=(0,12))
    def print_file(self,path):
        if sys.platform=='win32':
            try:subprocess.Popen(['notepad.exe','/p',str(path)],creationflags=0x08000000)
            except Exception as ex:messagebox.showwarning('Printer',str(ex))

    # PRODUCTS
    def build_products(self):
        f=ctk.CTkFrame(self.pages,fg_color=BG,corner_radius=0);self.frames['products']=f
        form=self.card(f);form.pack(fill='x',pady=(0,10));self.pvars={k:ctk.StringVar() for k in ('barcode','name','category','cost','price','stock')};self.pserial=ctk.BooleanVar(value=False)
        fields=[('Barcode (optional)','barcode'),('Product Name','name'),('Category','category'),('Avg Cost USD','cost'),('Selling Price USD','price'),('Opening Stock','stock')]
        for i,(lab,k) in enumerate(fields):
            ctk.CTkLabel(form,text=lab,text_color=MUT,font=('Segoe UI',10,'bold')).grid(row=0,column=i,padx=7,pady=(12,2),sticky='w');ctk.CTkEntry(form,textvariable=self.pvars[k],width=150).grid(row=1,column=i,padx=7,pady=(0,12),sticky='ew');form.grid_columnconfigure(i,weight=1)
        ctk.CTkCheckBox(form,text='Track serial numbers',variable=self.pserial,text_color=INK).grid(row=2,column=0,columnspan=2,padx=8,pady=(0,12),sticky='w');ctk.CTkButton(form,text='Save Product',fg_color=ACCENT,command=self.save_product).grid(row=2,column=5,padx=8,pady=(0,12),sticky='e')
        tablecard=self.card(f);tablecard.pack(fill='both',expand=True);ctk.CTkLabel(tablecard,text='Product List',text_color=INK,font=('Segoe UI',15,'bold')).pack(anchor='w',padx=14,pady=(12,6));self.product_table=self.table(tablecard,('barcode','name','category','avg_cost','last_cost','price','stock','value'),[120,210,120,90,90,90,70,100],15);self.product_table.pack(fill='both',expand=True,padx=10,pady=(0,10));self.product_table.bind('<Double-1>',self.load_product)
    def refresh_products(self):
        clear_tree(self.product_table)
        for p in DB.inventory():self.product_table.insert('', 'end',iid=str(p['id']),values=(p['barcode'],p['name'],p['category'],money(p['cost']),money(p['last_cost']),money(p['price']),f"{p['stock']:g}",money(float(p['stock'])*float(p['cost']))))
    def save_product(self):
        try:DB.upsert_product(self.pvars['barcode'].get(),self.pvars['name'].get(),self.pvars['category'].get(),float(self.pvars['cost'].get() or 0),float(self.pvars['price'].get() or 0),float(self.pvars['stock'].get() or 0),self.pserial.get());self.refresh_products();self.refresh_pos_products();messagebox.showinfo('Products','Product saved')
        except Exception as ex:messagebox.showerror('Product',str(ex))
    def load_product(self,e=None):
        s=self.product_table.selection()
        if not s:return
        p=DB.product(int(s[0]));
        for k in ('barcode','name','category','cost','price','stock'):self.pvars[k].set(p[k])
        self.pserial.set(bool(p['track_serial']))

    # STOCK
    def build_stock(self):
        f=ctk.CTkFrame(self.pages,fg_color=BG,corner_radius=0);self.frames['stock']=f
        form=self.card(f);form.pack(fill='x',pady=(0,10));self.stock_product=ctk.StringVar();self.stock_supplier=ctk.StringVar();self.stock_qty=ctk.StringVar(value='1');self.stock_cost=ctk.StringVar();self.stock_serials=ctk.StringVar()
        for i,(lab,var) in enumerate([('Product',self.stock_product),('Supplier',self.stock_supplier),('Quantity',self.stock_qty),('Unit Cost USD',self.stock_cost),('Serials comma-separated',self.stock_serials)]):
            ctk.CTkLabel(form,text=lab,text_color=MUT,font=('Segoe UI',10,'bold')).grid(row=0,column=i,padx=7,pady=(12,2),sticky='w');
            if i<2:
                om=ctk.CTkOptionMenu(form,variable=var,values=['']);om.grid(row=1,column=i,padx=7,pady=(0,12),sticky='ew');
                if i==0:self.stock_product_menu=om
                else:self.stock_supplier_menu=om
            else:ctk.CTkEntry(form,textvariable=var).grid(row=1,column=i,padx=7,pady=(0,12),sticky='ew')
            form.grid_columnconfigure(i,weight=1)
        ctk.CTkButton(form,text='Add Stock',fg_color=GREEN,command=self.do_stock_in).grid(row=2,column=4,padx=8,pady=(0,12),sticky='e')
        card=self.card(f);card.pack(fill='both',expand=True);ctk.CTkLabel(card,text='Purchase / Stock-In History',text_color=INK,font=('Segoe UI',15,'bold')).pack(anchor='w',padx=14,pady=(12,6));self.purchase_table=self.table(card,('date','supplier','product','qty','unit_cost','total'),[150,160,210,70,90,100],15);self.purchase_table.pack(fill='both',expand=True,padx=10,pady=(0,10))
    def refresh_stock(self):
        self.product_map={p['name']:p['id'] for p in DB.inventory()};self.supplier_map={s['name']:s['id'] for s in DB.suppliers()};pv=list(self.product_map) or [''];sv=['No Supplier']+list(self.supplier_map);self.stock_product_menu.configure(values=pv);self.stock_supplier_menu.configure(values=sv)
        if self.stock_product.get() not in pv:self.stock_product.set(pv[0]);
        if self.stock_supplier.get() not in sv:self.stock_supplier.set(sv[0])
        clear_tree(self.purchase_table)
        for r in DB.purchase_history():self.purchase_table.insert('', 'end',values=(r['created_at'].replace('T',' '),r['supplier_name'] or 'No Supplier',r['product_name'],f"{r['qty']:g}",money(r['unit_cost']),money(r['total'])))
    def do_stock_in(self):
        try:
            pid=self.product_map[self.stock_product.get()];sid=self.supplier_map.get(self.stock_supplier.get());serials=[x.strip() for x in self.stock_serials.get().split(',') if x.strip()];DB.stock_in(pid,float(self.stock_qty.get()),float(self.stock_cost.get()),sid,serials);self.stock_serials.set('');self.refresh_stock();self.refresh_products();self.refresh_pos_products();messagebox.showinfo('Stock In','Stock saved. Average cost updated.')
        except Exception as ex:messagebox.showerror('Stock In',str(ex))

    # SUPPLIERS
    def build_suppliers(self):
        f=ctk.CTkFrame(self.pages,fg_color=BG,corner_radius=0);self.frames['suppliers']=f
        form=self.card(f);form.pack(fill='x',pady=(0,10));self.sup_name=ctk.StringVar();self.sup_phone=ctk.StringVar();ctk.CTkEntry(form,placeholder_text='Supplier name',textvariable=self.sup_name).pack(side='left',fill='x',expand=True,padx=(12,6),pady=12);ctk.CTkEntry(form,placeholder_text='Phone',textvariable=self.sup_phone,width=220).pack(side='left',padx=6,pady=12);ctk.CTkButton(form,text='Add Supplier',fg_color=ACCENT,command=self.add_supplier).pack(side='left',padx=(6,12),pady=12)
        card=self.card(f);card.pack(fill='both',expand=True);self.supplier_table=self.table(card,('supplier','phone','purchase_entries','purchase_total'),[260,180,130,140],15);self.supplier_table.pack(fill='both',expand=True,padx=10,pady=10)
    def refresh_suppliers(self):
        clear_tree(self.supplier_table);tot={r['supplier']:(r['entries'],r['purchases']) for r in DB.supplier_report()}
        for s in DB.suppliers():e,p=tot.get(s['name'],(0,0));self.supplier_table.insert('', 'end',values=(s['name'],s['phone'],e,money(p)))
    def add_supplier(self):
        try:DB.add_supplier(self.sup_name.get(),self.sup_phone.get());self.sup_name.set('');self.sup_phone.set('');self.refresh_suppliers();self.refresh_stock()
        except Exception as ex:messagebox.showerror('Supplier',str(ex))

    # DELIVERY
    def build_delivery(self):
        f=ctk.CTkFrame(self.pages,fg_color=BG,corner_radius=0);self.frames['delivery']=f
        bar=ctk.CTkFrame(f,fg_color='transparent');bar.pack(fill='x',pady=(0,8));ctk.CTkButton(bar,text='Mark OUT',fg_color=GREEN,command=lambda:self.delivery_status('OUT')).pack(side='left');ctk.CTkButton(bar,text='Mark PENDING',fg_color='#E7EFF5',text_color=INK,command=lambda:self.delivery_status('PENDING')).pack(side='left',padx=6)
        card=self.card(f);card.pack(fill='both',expand=True);self.delivery_table=self.table(card,('id','date','customer','phone','address','total','status'),[70,150,160,120,240,90,90],15);self.delivery_table.pack(fill='both',expand=True,padx=10,pady=10)
    def refresh_delivery(self):
        clear_tree(self.delivery_table)
        for s in DB.deliveries():self.delivery_table.insert('', 'end',iid=str(s['id']),values=(s['id'],s['created_at'].replace('T',' '),s['customer_name'],s['phone'],s['address'],money(s['total']),s['delivery_status']))
    def delivery_status(self,status):
        s=self.delivery_table.selection()
        if s:DB.set_delivery_status(int(s[0]),status);self.refresh_delivery()

    # REPORTS
    def build_reports(self):
        f=ctk.CTkFrame(self.pages,fg_color=BG,corner_radius=0);self.frames['reports']=f
        bar=self.card(f);bar.pack(fill='x',pady=(0,10));self.report_type=ctk.StringVar(value='Profit & Loss');types=['Profit & Loss','Sales Report','Sales by Product','Purchase Report','Supplier Report','Inventory Report','Cost History'];ctk.CTkOptionMenu(bar,values=types,variable=self.report_type,width=210,command=lambda _:self.refresh_reports()).pack(side='left',padx=12,pady=12)
        for txt,val in [('Today','today'),('Week','week'),('Month','month'),('All','all')]:ctk.CTkButton(bar,text=txt,width=72,fg_color='#E7EFF5',text_color=INK,hover_color='#D9E6EE',command=lambda v=val:self.set_report_period(v)).pack(side='left',padx=3)
        ctk.CTkButton(bar,text='Custom Dates',width=105,fg_color='#E7EFF5',text_color=INK,command=self.custom_dates).pack(side='left',padx=3);ctk.CTkButton(bar,text='Export CSV',width=100,fg_color=ACCENT,command=self.export_report).pack(side='right',padx=(4,12));ctk.CTkButton(bar,text='Print',width=80,fg_color='#E7EFF5',text_color=INK,command=self.print_report).pack(side='right',padx=4);ctk.CTkButton(bar,text='+ Expense',width=95,fg_color='#F3E8D7',text_color='#7F5A21',command=self.add_expense).pack(side='right',padx=4)
        met=ctk.CTkFrame(f,fg_color='transparent');met.pack(fill='x',pady=(0,10));self.rmetrics={}
        for i,(k,label) in enumerate([('sales','Sales'),('cogs','COGS'),('gross_profit','Gross Profit'),('expenses','Expenses'),('net_profit','Net Profit'),('inventory_value','Inventory Value')]):
            met.grid_columnconfigure(i,weight=1);c,v,s=self.metric(met,label);c.grid(row=0,column=i,sticky='ew',padx=3);v.configure(font=('Segoe UI',17,'bold'));self.rmetrics[k]=v
        card=self.card(f);card.pack(fill='both',expand=True);self.report_caption=ctk.CTkLabel(card,text='Profit & Loss',text_color=INK,font=('Segoe UI',15,'bold'));self.report_caption.pack(anchor='w',padx=14,pady=(12,6));self.report_holder=ctk.CTkFrame(card,fg_color='white');self.report_holder.pack(fill='both',expand=True,padx=10,pady=(0,10));self.report_table=None;self.report_rows=[];self.report_cols=[]
    def set_report_period(self,p):self.report_period=p;self.report_custom=(None,None);self.refresh_reports()
    def custom_dates(self):
        a=simpledialog.askstring('Custom Report','Start date (YYYY-MM-DD):',parent=self);b=simpledialog.askstring('Custom Report','End date (YYYY-MM-DD):',parent=self)
        try:
            datetime.fromisoformat(a);datetime.fromisoformat(b);self.report_period='custom';self.report_custom=(a,b);self.refresh_reports()
        except:messagebox.showerror('Dates','Use YYYY-MM-DD')
    def _rp(self):return (self.report_period,*self.report_custom)
    def refresh_reports(self):
        period,a,b=self._rp();r=DB.report(period,a,b)
        for k,v in self.rmetrics.items():v.configure(text=money(r[k]))
        typ=self.report_type.get();self.report_caption.configure(text=f'{typ} — {period.title()}')
        if typ=='Profit & Loss':cols=['metric','amount'];rows=[('Sales',money(r['sales'])),('COGS',money(r['cogs'])),('Gross Profit',money(r['gross_profit'])),('Expenses',money(r['expenses'])),('Net Profit',money(r['net_profit'])),('Inventory Value',money(r['inventory_value'])),('Sales Count',r['sales_count'])]
        elif typ=='Sales Report':cols=['date','receipt','type','customer','payment','total','profit'];rows=[(x['created_at'].replace('T',' '),x['id'],x['sale_type'],x['customer_name'],x['payment_method'],money(x['total']),money(float(x['total'])-float(x['cost_total']))) for x in DB.sales_history(period,a,b)]
        elif typ=='Sales by Product':cols=['product','barcode','qty','sales','cost','profit'];rows=[(x['name'],x['barcode'],f"{x['qty']:g}",money(x['sales']),money(x['cost']),money(x['profit'])) for x in DB.sales_by_product(period,a,b)]
        elif typ=='Purchase Report':cols=['date','supplier','product','qty','unit_cost','total'];rows=[(x['created_at'].replace('T',' '),x['supplier_name'] or 'No Supplier',x['product_name'],f"{x['qty']:g}",money(x['unit_cost']),money(x['total'])) for x in DB.purchase_history(period,a,b)]
        elif typ=='Supplier Report':cols=['supplier','entries','qty','purchases'];rows=[(x['supplier'],x['entries'],f"{x['qty']:g}",money(x['purchases'])) for x in DB.supplier_report(period,a,b)]
        elif typ=='Inventory Report':cols=['barcode','product','category','stock','avg_cost','last_cost','sell_price','value'];rows=[(x['barcode'],x['name'],x['category'],f"{x['stock']:g}",money(x['cost']),money(x['last_cost']),money(x['price']),money(float(x['stock'])*float(x['cost']))) for x in DB.inventory()]
        else:cols=['date','product','supplier','qty','cost','total'];rows=[(x['created_at'].replace('T',' '),x['product_name'],x['supplier_name'] or 'No Supplier',f"{x['qty']:g}",money(x['unit_cost']),money(x['total'])) for x in DB.cost_history(period,a,b)]
        self.render_report_table(cols,rows)
    def render_report_table(self,cols,rows):
        if self.report_table:self.report_table.destroy()
        self.report_cols=cols;self.report_rows=rows;self.report_table=self.table(self.report_holder,tuple(cols),[150 if c in ('date','product','supplier','customer') else 110 for c in cols],15);self.report_table.pack(fill='both',expand=True)
        for row in rows:self.report_table.insert('', 'end',values=row)
    def export_report(self):
        name=self.report_type.get().replace(' ','_');path=filedialog.asksaveasfilename(parent=self,defaultextension='.csv',initialfile=f'{name}_{datetime.now():%Y%m%d}.csv',filetypes=[('CSV','*.csv')])
        if not path:return
        with open(path,'w',newline='',encoding='utf-8-sig') as f:w=csv.writer(f);w.writerow(self.report_cols);w.writerows(self.report_rows)
        messagebox.showinfo('Export',f'Saved:\n{path}')
    def print_report(self):
        p=DATA/'exports'/f"report_{datetime.now():%Y%m%d_%H%M%S}.txt";lines=[f'{APP_NAME} — {self.report_type.get()}',f'Generated: {datetime.now():%Y-%m-%d %H:%M}',' | '.join(self.report_cols),'-'*100]+[' | '.join(map(str,r)) for r in self.report_rows];p.write_text('\n'.join(lines),encoding='utf-8');self.print_file(p)
    def add_expense(self):
        d=simpledialog.askstring('Expense','Description:',parent=self)
        if not d:return
        a=simpledialog.askfloat('Expense','Amount USD:',parent=self,minvalue=0)
        if a is not None:DB.add_expense(d,a);self.refresh_reports();self.refresh_dashboard()

    # SETTINGS
    def build_settings(self):
        f=ctk.CTkFrame(self.pages,fg_color=BG,corner_radius=0);self.frames['settings']=f;card=self.card(f);card.pack(fill='x');ctk.CTkLabel(card,text='Business Settings',text_color=INK,font=('Segoe UI',17,'bold')).pack(anchor='w',padx=18,pady=(16,8));self.setvars={k:ctk.StringVar() for k in ('store_name','store_phone','lbp_rate','receipt_footer')}
        for lab,k in [('Store / Business Name','store_name'),('Phone','store_phone'),('LBP per 1 USD','lbp_rate'),('Receipt Footer','receipt_footer')]:ctk.CTkLabel(card,text=lab,text_color=MUT,font=('Segoe UI',10,'bold')).pack(anchor='w',padx=18);ctk.CTkEntry(card,textvariable=self.setvars[k],height=38).pack(fill='x',padx=18,pady=(3,10))
        row=ctk.CTkFrame(card,fg_color='transparent');row.pack(fill='x',padx=18,pady=(2,18));ctk.CTkButton(row,text='Save Settings',fg_color=ACCENT,command=self.save_settings).pack(side='left');ctk.CTkButton(row,text='Backup Now',fg_color='#E7EFF5',text_color=INK,command=self.backup_now).pack(side='left',padx=8);self.backup_info=ctk.CTkLabel(row,text='Daily backup also runs automatically on Exit.',text_color=MUT);self.backup_info.pack(side='left',padx=10)
    def refresh_settings(self):
        for k in self.setvars:self.setvars[k].set(DB.get_setting(k))
    def save_settings(self):
        try:float(self.setvars['lbp_rate'].get())
        except:return messagebox.showerror('Settings','Invalid LBP rate')
        for k,v in self.setvars.items():DB.set_setting(k,v.get())
        self.store_label.configure(text=DB.get_setting('store_name'));self.rate_label.configure(text=f'1 USD = {DB.rate():,.0f} LBP');messagebox.showinfo('Settings','Settings saved')
    def backup_now(self):
        p=DB.daily_backup();messagebox.showinfo('Backup',f'Backup saved:\n{p}' if p else 'Backup failed')


def self_test():
    td=tempfile.TemporaryDirectory();d=BizFlowDB(Path(td.name)/'smoke.db');d.set_setting('lbp_rate','89500');s=d.add_supplier('Test Supplier');p=d.upsert_product('','Test Item','Test',5,10,0);d.stock_in(p,3,5,s);d.stock_in(p,1,9,s);assert round(float(d.product(p)['cost']),2)==6.00;sid=d.create_sale([{'product_id':p,'qty':1}],paid_currency='USD',paid_amount=20,payment_method='CASH');sale=d.sale(sid)[0];assert round(sale['change_amount'],2)==10.00;assert d.product(p)['stock']==3;assert DB is not None;td.cleanup();print('GM BizFlow MODERN SELF-TEST OK');return 0

if __name__=='__main__':
    if '--self-test' in sys.argv:raise SystemExit(self_test())
    App().mainloop()
