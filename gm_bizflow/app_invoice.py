from __future__ import annotations
from datetime import datetime
import json
import customtkinter as ctk
from tkinter import messagebox, simpledialog
from app_fix import App as FixedApp
from app_modern import DB, DATA, BG, INK, MUT, ACCENT, GREEN, RED, money, clear_tree, NAV2

SOFT='#E7EFF5'
DANGER='#B94B4B'


class App(FixedApp):
    """Final usability layer: invoice history plus persistent Hold/Resume Sale. Dashboard/graphics remain unchanged."""

    def build_shell(self):
        super().build_shell()
        b=ctk.CTkButton(
            self.side,text='▧   Invoices / Sales History',anchor='w',height=42,corner_radius=9,
            fg_color='transparent',hover_color=NAV2,text_color='#E8F1F6',font=('Segoe UI',12,'bold'),
            command=lambda:self.show_page('invoices'))
        b.pack(fill='x',padx=12,pady=3)
        self.nav_buttons['invoices']=b
        self.build_invoices()
        self.invoice_period='today';self.invoice_custom=(None,None)
        self.build_hold_controls()

    def show_page(self,key):
        if key!='invoices':return super().show_page(key)
        for k,f in self.frames.items():f.grid_forget()
        self.frames['invoices'].grid(row=0,column=0,sticky='nsew')
        for k,b in self.nav_buttons.items():b.configure(fg_color=NAV2 if k=='invoices' else 'transparent')
        self.page_title.configure(text='Invoices / Sales History');self.current_page='invoices';self.refresh_invoices()

    # ---------- INVOICES / SALES HISTORY ----------
    def build_invoices(self):
        f=ctk.CTkFrame(self.pages,fg_color=BG,corner_radius=0);self.frames['invoices']=f
        bar=self.card(f);bar.pack(fill='x',pady=(0,10))
        ctk.CTkLabel(bar,text='Show invoices from:',text_color=MUT,font=('Segoe UI',10,'bold')).pack(side='left',padx=(12,6),pady=12)
        for txt,val in [('Today','today'),('Week','week'),('Month','month'),('All','all')]:
            ctk.CTkButton(bar,text=txt,width=72,fg_color=SOFT,text_color=INK,hover_color='#D9E6EE',command=lambda v=val:self.set_invoice_period(v)).pack(side='left',padx=3,pady=12)
        ctk.CTkButton(bar,text='Custom Dates',width=105,fg_color=SOFT,text_color=INK,command=self.invoice_custom_dates).pack(side='left',padx=3,pady=12)
        self.invoice_search=ctk.CTkEntry(bar,placeholder_text='Search receipt #, customer, phone...',width=260)
        self.invoice_search.pack(side='left',padx=10,pady=12);self.invoice_search.bind('<KeyRelease>',lambda e:self.refresh_invoices())
        ctk.CTkButton(bar,text='View Invoice',width=105,fg_color=ACCENT,command=self.view_invoice).pack(side='right',padx=(4,12),pady=12)
        ctk.CTkButton(bar,text='Reprint',width=85,fg_color=SOFT,text_color=INK,command=self.reprint_invoice).pack(side='right',padx=4,pady=12)
        card=self.card(f);card.pack(fill='both',expand=True)
        head=ctk.CTkFrame(card,fg_color='transparent');head.pack(fill='x',padx=14,pady=(12,6))
        ctk.CTkLabel(head,text='Saved Sales / Invoices',text_color=INK,font=('Segoe UI',15,'bold')).pack(side='left')
        self.invoice_summary=ctk.CTkLabel(head,text='',text_color=MUT,font=('Segoe UI',10));self.invoice_summary.pack(side='right')
        self.invoice_table=self.table(card,('receipt','date','customer','phone','type','payment','currency','total','status'),[75,155,160,120,90,90,80,95,90],16)
        self.invoice_table.pack(fill='both',expand=True,padx=10,pady=(0,10));self.invoice_table.bind('<Double-1>',lambda e:self.view_invoice())

    def set_invoice_period(self,p):self.invoice_period=p;self.invoice_custom=(None,None);self.refresh_invoices()

    def invoice_custom_dates(self):
        a=simpledialog.askstring('Custom Invoice Dates','Start date (YYYY-MM-DD):',parent=self)
        if not a:return
        b=simpledialog.askstring('Custom Invoice Dates','End date (YYYY-MM-DD):',parent=self)
        if not b:return
        try:datetime.fromisoformat(a);datetime.fromisoformat(b)
        except Exception:return messagebox.showerror('Dates','Use YYYY-MM-DD',parent=self)
        self.invoice_period='custom';self.invoice_custom=(a,b);self.refresh_invoices()

    def refresh_invoices(self):
        if not hasattr(self,'invoice_table'):return
        clear_tree(self.invoice_table);a,b=self.invoice_custom if self.invoice_period=='custom' else (None,None);rows=DB.sales_history(self.invoice_period,a,b)
        q=(self.invoice_search.get().strip().lower() if hasattr(self,'invoice_search') else '');shown=[]
        for s in rows:
            hay=f"{s['id']} {s['customer_name']} {s['phone']} {s['sale_type']} {s['payment_method']}".lower()
            if q and q not in hay:continue
            shown.append(s);self.invoice_table.insert('', 'end',iid=str(s['id']),values=(f"#{s['id']}",s['created_at'].replace('T',' '),s['customer_name'] or 'Walk-in',s['phone'],'Delivery' if s['sale_type']=='DELIVERY' else 'Walk-in',s['payment_method'],s['paid_currency'],money(s['total']),s['delivery_status'] or 'Completed'))
        self.invoice_summary.configure(text=f"{len(shown)} invoice(s)  •  Total {money(sum(float(x['total']) for x in shown))}")

    def _selected_invoice_id(self):
        s=self.invoice_table.selection()
        if not s:messagebox.showinfo('Invoice','Select an invoice first.',parent=self);return None
        return int(s[0])

    def _invoice_file(self,sid):
        p=DATA/'receipts'/f'receipt_{sid}.txt';p.write_text(DB.receipt_text(sid),encoding='utf-8');return p

    def view_invoice(self):
        sid=self._selected_invoice_id()
        if sid:self.receipt_popup(sid,self._invoice_file(sid))

    def reprint_invoice(self):
        sid=self._selected_invoice_id()
        if sid:self.print_file(self._invoice_file(sid))

    # ---------- HOLD / RESUME SALE ----------
    def build_hold_controls(self):
        pos=self.frames.get('pos')
        if not pos:return
        bar=ctk.CTkFrame(pos,fg_color='transparent');bar.grid(row=2,column=0,columnspan=2,sticky='ew',pady=(8,0));bar.grid_columnconfigure(0,weight=1)
        self.hold_count_label=ctk.CTkLabel(bar,text='',text_color=MUT,font=('Segoe UI',9));self.hold_count_label.grid(row=0,column=0,sticky='w')
        ctk.CTkButton(bar,text='Hold Sale',width=105,height=32,fg_color=SOFT,text_color=INK,command=self.hold_sale).grid(row=0,column=1,padx=4)
        ctk.CTkButton(bar,text='Resume Held Sale',width=135,height=32,fg_color=SOFT,text_color=INK,command=self.resume_held_sale).grid(row=0,column=2,padx=(4,0))
        self.refresh_hold_count()

    def _holds(self):
        try:return json.loads(DB.get_setting('held_sales','[]'))
        except Exception:return []

    def _save_holds(self,holds):DB.set_setting('held_sales',json.dumps(holds))

    def refresh_hold_count(self):
        if hasattr(self,'hold_count_label'):
            n=len(self._holds());self.hold_count_label.configure(text=f'{n} held sale(s)' if n else 'No held sales')

    def hold_sale(self):
        if not self.cart:return messagebox.showinfo('Hold Sale','Current cart is empty.',parent=self)
        name=simpledialog.askstring('Hold Sale','Optional name / note for this held sale:',parent=self) or ''
        holds=self._holds();next_id=max([int(x.get('id',0)) for x in holds]+[0])+1
        data={'id':next_id,'created_at':datetime.now().isoformat(timespec='seconds'),'note':name,'cart':list(self.cart.values()),'discount':self.discount.get(),'paid_currency':self.paid_currency.get(),'pay_method':self.pay_method.get(),'customer':self.customer.get(),'phone':self.phone.get(),'address':self.address.get(),'delivery':bool(self.delivery_var.get())}
        holds.append(data);self._save_holds(holds);self.clear_sale();self.refresh_hold_count();messagebox.showinfo('Hold Sale',f'Sale held as #{next_id}.',parent=self)

    def resume_held_sale(self):
        holds=self._holds()
        if not holds:return messagebox.showinfo('Held Sales','There are no held sales.',parent=self)
        w=ctk.CTkToplevel(self);w.title('Resume Held Sale');w.geometry('680x430');w.transient(self);w.grab_set()
        ctk.CTkLabel(w,text='Held Sales',font=('Segoe UI',18,'bold'),text_color=INK).pack(anchor='w',padx=16,pady=(14,6))
        t=self.table(w,('id','date','note','items','total'),[60,150,180,80,100],9);t.pack(fill='both',expand=True,padx=16,pady=8)
        for h in holds:
            total=sum(float(x.get('qty',1))*float(x.get('price',0)) for x in h.get('cart',[]))
            try:total=max(0,total-float(h.get('discount') or 0))
            except Exception:pass
            t.insert('', 'end',iid=str(h['id']),values=(h['id'],h.get('created_at','').replace('T',' '),h.get('note',''),len(h.get('cart',[])),money(total)))
        btn=ctk.CTkFrame(w,fg_color='transparent');btn.pack(fill='x',padx=16,pady=(0,14))
        def load_selected():
            s=t.selection()
            if not s:return messagebox.showinfo('Held Sales','Select a held sale.',parent=w)
            hid=int(s[0]);h=next((x for x in holds if int(x['id'])==hid),None)
            if not h:return
            self.cart={int(x['product_id']):dict(x) for x in h.get('cart',[])};self.discount.set(str(h.get('discount','0')));self.paid_currency.set(h.get('paid_currency','USD'));self.pay_method.set(h.get('pay_method','CASH'));self.customer.set(h.get('customer',''));self.phone.set(h.get('phone',''));self.address.set(h.get('address',''));self.delivery_var.set(bool(h.get('delivery',False)));self.delivery_fields_toggle();self.paid_amount.set('0');self.refresh_cart();self._save_holds([x for x in holds if int(x['id'])!=hid]);self.refresh_hold_count();w.destroy();self.show_page('pos')
        def delete_selected():
            s=t.selection()
            if not s:return
            hid=int(s[0])
            if not messagebox.askyesno('Delete Held Sale',f'Delete held sale #{hid}?',parent=w):return
            new=[x for x in holds if int(x['id'])!=hid];self._save_holds(new);self.refresh_hold_count();w.destroy()
        ctk.CTkButton(btn,text='Resume Selected',fg_color=ACCENT,command=load_selected).pack(side='right')
        ctk.CTkButton(btn,text='Delete Held',fg_color=DANGER,command=delete_selected).pack(side='right',padx=8)
