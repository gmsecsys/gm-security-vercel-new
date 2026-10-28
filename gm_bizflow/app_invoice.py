from __future__ import annotations
from datetime import datetime
from pathlib import Path
import customtkinter as ctk
from tkinter import messagebox, simpledialog
from app_fix import App as FixedApp
from app_modern import DB, DATA, BG, INK, MUT, ACCENT, GREEN, RED, money, clear_tree, NAV2

SOFT='#E7EFF5'
DANGER='#B94B4B'


class App(FixedApp):
    """Adds a dedicated invoice/sales-history page while preserving the existing dashboard and graphics."""

    def build_shell(self):
        super().build_shell()
        # Add a clear Sales History / Invoices destination without changing Dashboard layout/graphics.
        b=ctk.CTkButton(
            self.side,text='▧   Invoices / Sales History',anchor='w',height=42,corner_radius=9,
            fg_color='transparent',hover_color=NAV2,text_color='#E8F1F6',font=('Segoe UI',12,'bold'),
            command=lambda:self.show_page('invoices'))
        b.pack(fill='x',padx=12,pady=3)
        self.nav_buttons['invoices']=b
        self.build_invoices()
        self.invoice_period='today'
        self.invoice_custom=(None,None)

    def show_page(self,key):
        if key!='invoices':
            return super().show_page(key)
        for k,f in self.frames.items():f.grid_forget()
        self.frames['invoices'].grid(row=0,column=0,sticky='nsew')
        for k,b in self.nav_buttons.items():b.configure(fg_color=NAV2 if k=='invoices' else 'transparent')
        self.page_title.configure(text='Invoices / Sales History')
        self.current_page='invoices'
        self.refresh_invoices()

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

    def set_invoice_period(self,p):
        self.invoice_period=p;self.invoice_custom=(None,None);self.refresh_invoices()

    def invoice_custom_dates(self):
        a=simpledialog.askstring('Custom Invoice Dates','Start date (YYYY-MM-DD):',parent=self)
        if not a:return
        b=simpledialog.askstring('Custom Invoice Dates','End date (YYYY-MM-DD):',parent=self)
        if not b:return
        try:
            datetime.fromisoformat(a);datetime.fromisoformat(b)
        except Exception:
            return messagebox.showerror('Dates','Use YYYY-MM-DD',parent=self)
        self.invoice_period='custom';self.invoice_custom=(a,b);self.refresh_invoices()

    def refresh_invoices(self):
        if not hasattr(self,'invoice_table'):return
        clear_tree(self.invoice_table)
        a,b=self.invoice_custom if self.invoice_period=='custom' else (None,None)
        rows=DB.sales_history(self.invoice_period,a,b)
        q=(self.invoice_search.get().strip().lower() if hasattr(self,'invoice_search') else '')
        shown=[]
        for s in rows:
            hay=f"{s['id']} {s['customer_name']} {s['phone']} {s['sale_type']} {s['payment_method']}".lower()
            if q and q not in hay:continue
            shown.append(s)
            self.invoice_table.insert('', 'end',iid=str(s['id']),values=(
                f"#{s['id']}",s['created_at'].replace('T',' '),s['customer_name'] or 'Walk-in',s['phone'],
                'Delivery' if s['sale_type']=='DELIVERY' else 'Walk-in',s['payment_method'],s['paid_currency'],money(s['total']),s['delivery_status'] or 'Completed'))
        total=sum(float(x['total']) for x in shown)
        self.invoice_summary.configure(text=f"{len(shown)} invoice(s)  •  Total {money(total)}")

    def _selected_invoice_id(self):
        s=self.invoice_table.selection()
        if not s:
            messagebox.showinfo('Invoice','Select an invoice first.',parent=self);return None
        return int(s[0])

    def _invoice_file(self,sid):
        p=DATA/'receipts'/f'receipt_{sid}.txt'
        p.write_text(DB.receipt_text(sid),encoding='utf-8')
        return p

    def view_invoice(self):
        sid=self._selected_invoice_id()
        if not sid:return
        self.receipt_popup(sid,self._invoice_file(sid))

    def reprint_invoice(self):
        sid=self._selected_invoice_id()
        if not sid:return
        self.print_file(self._invoice_file(sid))
