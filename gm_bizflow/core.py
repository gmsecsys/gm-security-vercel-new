from __future__ import annotations
import sqlite3, shutil, atexit
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timedelta

DEFAULT_RATE = 89500.0

class BizFlowDB:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
        atexit.register(self.daily_backup)

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback(); raise
        finally:
            c.close()

    def _has_column(self,c,table,col):
        return any(r['name']==col for r in c.execute(f'PRAGMA table_info({table})'))

    def init_db(self):
        with self.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL,phone TEXT DEFAULT '');
            CREATE TABLE IF NOT EXISTS products(
              id INTEGER PRIMARY KEY AUTOINCREMENT, barcode TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
              category TEXT DEFAULT '', cost REAL NOT NULL DEFAULT 0, price REAL NOT NULL DEFAULT 0,
              stock REAL NOT NULL DEFAULT 0, supplier_id INTEGER, track_serial INTEGER NOT NULL DEFAULT 0,
              image_path TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
              FOREIGN KEY(supplier_id) REFERENCES suppliers(id));
            CREATE TABLE IF NOT EXISTS serials(
              id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL, serial_no TEXT UNIQUE NOT NULL,
              status TEXT NOT NULL DEFAULT 'IN_STOCK', sale_id INTEGER,
              FOREIGN KEY(product_id) REFERENCES products(id));
            CREATE TABLE IF NOT EXISTS purchases(
              id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, supplier_id INTEGER,
              product_id INTEGER NOT NULL, qty REAL NOT NULL, unit_cost REAL NOT NULL, total REAL NOT NULL,
              FOREIGN KEY(supplier_id) REFERENCES suppliers(id), FOREIGN KEY(product_id) REFERENCES products(id));
            CREATE TABLE IF NOT EXISTS sales(
              id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, sale_type TEXT NOT NULL DEFAULT 'WALK_IN',
              subtotal REAL NOT NULL, discount REAL NOT NULL DEFAULT 0, total REAL NOT NULL,
              cost_total REAL NOT NULL, paid_currency TEXT NOT NULL, paid_amount REAL NOT NULL, lbp_rate REAL NOT NULL,
              customer_name TEXT DEFAULT '', phone TEXT DEFAULT '', address TEXT DEFAULT '', delivery_status TEXT DEFAULT '');
            CREATE TABLE IF NOT EXISTS sale_items(
              id INTEGER PRIMARY KEY AUTOINCREMENT, sale_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
              qty REAL NOT NULL, unit_cost REAL NOT NULL, unit_price REAL NOT NULL, total REAL NOT NULL,
              FOREIGN KEY(sale_id) REFERENCES sales(id), FOREIGN KEY(product_id) REFERENCES products(id));
            CREATE TABLE IF NOT EXISTS expenses(
              id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, description TEXT NOT NULL, amount REAL NOT NULL);
            ''')
            for col,ddl in [('payment_method',"TEXT NOT NULL DEFAULT 'CASH'"),('change_amount','REAL NOT NULL DEFAULT 0')]:
                if not self._has_column(c,'sales',col): c.execute(f'ALTER TABLE sales ADD COLUMN {col} {ddl}')
            defaults={'store_name':'GM BizFlow Store','store_phone':'','lbp_rate':str(DEFAULT_RATE),'show_images':'0','receipt_width':'42','receipt_footer':'Thank you for your visit'}
            for k,v in defaults.items(): c.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',(k,v))

    def get_setting(self,key,default=''):
        with self.connect() as c:r=c.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
        return r['value'] if r else default
    def set_setting(self,key,value):
        with self.connect() as c:c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,str(value)))
    def rate(self):
        try:return float(self.get_setting('lbp_rate',str(DEFAULT_RATE)))
        except:return DEFAULT_RATE
    def usd_to_lbp(self,usd,rate=None):return round(float(usd)*(self.rate() if rate is None else float(rate)))
    def lbp_to_usd(self,lbp,rate=None):return float(lbp)/(self.rate() if rate is None else float(rate))

    def add_supplier(self,name,phone=''):
        name=name.strip()
        if not name:raise ValueError('Supplier name is required')
        with self.connect() as c:
            cur=c.execute('INSERT INTO suppliers(name,phone) VALUES(?,?)',(name,phone.strip()));return cur.lastrowid
    def suppliers(self):
        with self.connect() as c:return c.execute('SELECT * FROM suppliers ORDER BY name').fetchall()

    def _auto_barcode(self,c):
        n=c.execute('SELECT COALESCE(MAX(id),0)+1 n FROM products').fetchone()['n'];return f'SKU-{int(n):06d}'
    def upsert_product(self,barcode,name,category='',cost=0,price=0,stock=0,track_serial=False,image_path='',supplier_id=None):
        barcode,name=(barcode or '').strip(),name.strip()
        if not name:raise ValueError('Product name is required')
        if min(float(cost),float(price),float(stock))<0:raise ValueError('Cost, price and stock must be non-negative')
        with self.connect() as c:
            if not barcode: barcode=self._auto_barcode(c)
            r=c.execute('SELECT id FROM products WHERE barcode=?',(barcode,)).fetchone()
            if r:
                c.execute('UPDATE products SET name=?,category=?,cost=?,price=?,stock=?,track_serial=?,image_path=?,supplier_id=? WHERE id=?',(name,category,float(cost),float(price),float(stock),int(bool(track_serial)),image_path,supplier_id,r['id']));return r['id']
            cur=c.execute('INSERT INTO products(barcode,name,category,cost,price,stock,track_serial,image_path,supplier_id) VALUES(?,?,?,?,?,?,?,?,?)',(barcode,name,category,float(cost),float(price),float(stock),int(bool(track_serial)),image_path,supplier_id));return cur.lastrowid
    def product(self,product_id):
        with self.connect() as c:return c.execute('SELECT * FROM products WHERE id=?',(product_id,)).fetchone()
    def product_by_barcode(self,barcode):
        with self.connect() as c:return c.execute('SELECT * FROM products WHERE barcode=? AND active=1',((barcode or '').strip(),)).fetchone()
    def search_products(self,q='',limit=100):
        q=(q or '').strip()
        with self.connect() as c:
            if not q:return c.execute('SELECT * FROM products WHERE active=1 ORDER BY name LIMIT ?',(limit,)).fetchall()
            p=f'%{q}%';return c.execute('SELECT * FROM products WHERE active=1 AND (barcode LIKE ? OR name LIKE ? OR category LIKE ?) ORDER BY name LIMIT ?',(p,p,p,limit)).fetchall()
    def add_serials(self,product_id,serial_numbers):
        vals=[s.strip() for s in serial_numbers if s and s.strip()]
        if len(vals)!=len(set(vals)):raise ValueError('Duplicate serial in input')
        with self.connect() as c:
            for s in vals:c.execute("INSERT INTO serials(product_id,serial_no,status) VALUES(?,?,'IN_STOCK')",(product_id,s))

    def stock_in(self,product_id,qty,unit_cost,supplier_id=None,serial_numbers=None):
        qty,unit_cost=float(qty),float(unit_cost)
        if qty<=0 or unit_cost<0:raise ValueError('Invalid quantity or cost')
        p=self.product(product_id)
        if not p:raise ValueError('Product not found')
        serial_numbers=serial_numbers or []
        if p['track_serial'] and int(qty)!=len(serial_numbers):raise ValueError('Serial-tracked products need one serial number per unit')
        old_stock=float(p['stock']);old_cost=float(p['cost']);new_stock=old_stock+qty
        avg=((old_stock*old_cost)+(qty*unit_cost))/new_stock if new_stock else unit_cost
        with self.connect() as c:
            cur=c.execute('INSERT INTO purchases(created_at,supplier_id,product_id,qty,unit_cost,total) VALUES(?,?,?,?,?,?)',(datetime.now().isoformat(timespec='seconds'),supplier_id,product_id,qty,unit_cost,qty*unit_cost))
            c.execute('UPDATE products SET stock=?,cost=?,supplier_id=COALESCE(?,supplier_id) WHERE id=?',(new_stock,avg,supplier_id,product_id))
            for s in serial_numbers:c.execute("INSERT INTO serials(product_id,serial_no,status) VALUES(?,?,'IN_STOCK')",(product_id,s.strip()))
            return cur.lastrowid
    def _available_serials(self,c,product_id,qty):return c.execute("SELECT id,serial_no FROM serials WHERE product_id=? AND status='IN_STOCK' ORDER BY id LIMIT ?",(product_id,int(qty))).fetchall()

    def create_sale(self,items,discount=0,paid_currency='USD',sale_type='WALK_IN',customer_name='',phone='',address='',delivery_status='',paid_amount=None,payment_method='CASH'):
        if not items:raise ValueError('Cart is empty')
        paid_currency=paid_currency.upper();payment_method=(payment_method or 'CASH').upper()
        if paid_currency not in ('USD','LBP'):raise ValueError('Currency must be USD or LBP')
        if payment_method not in ('CASH','CARD'):raise ValueError('Payment method must be CASH or CARD')
        discount=float(discount)
        if discount<0:raise ValueError('Discount cannot be negative')
        rate=self.rate();prepared=[];subtotal=0.;cost_total=0.
        with self.connect() as c:
            for it in items:
                pid=int(it['product_id']);qty=float(it.get('qty',1))
                if qty<=0:raise ValueError('Quantity must be positive')
                p=c.execute('SELECT * FROM products WHERE id=? AND active=1',(pid,)).fetchone()
                if not p:raise ValueError('Product not found')
                if qty>float(p['stock']):raise ValueError(f"Not enough stock for {p['name']}")
                serial_ids=[]
                if p['track_serial']:
                    if int(qty)!=qty:raise ValueError('Serial-tracked quantity must be whole units')
                    serials=self._available_serials(c,pid,qty)
                    if len(serials)!=int(qty):raise ValueError(f"Not enough serials for {p['name']}")
                    serial_ids=[r['id'] for r in serials]
                price=float(it.get('price',p['price']));line=qty*price
                prepared.append((p,qty,price,line,serial_ids));subtotal+=line;cost_total+=qty*float(p['cost'])
            total=max(0.,subtotal-discount);due=total if paid_currency=='USD' else self.usd_to_lbp(total,rate)
            paid=float(due if paid_amount is None else paid_amount)
            if payment_method=='CASH' and paid+1e-9<due:raise ValueError('Customer payment is less than total')
            change=max(0.,paid-due)
            cur=c.execute('''INSERT INTO sales(created_at,sale_type,subtotal,discount,total,cost_total,paid_currency,paid_amount,lbp_rate,customer_name,phone,address,delivery_status,payment_method,change_amount) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(datetime.now().isoformat(timespec='seconds'),sale_type,subtotal,discount,total,cost_total,paid_currency,paid,rate,customer_name,phone,address,delivery_status,payment_method,change))
            sale_id=cur.lastrowid
            for p,qty,price,line,serial_ids in prepared:
                c.execute('INSERT INTO sale_items(sale_id,product_id,qty,unit_cost,unit_price,total) VALUES(?,?,?,?,?,?)',(sale_id,p['id'],qty,p['cost'],price,line));c.execute('UPDATE products SET stock=stock-? WHERE id=?',(qty,p['id']))
                for sid in serial_ids:c.execute("UPDATE serials SET status='SOLD',sale_id=? WHERE id=?",(sale_id,sid))
            return sale_id

    def sale(self,sale_id):
        with self.connect() as c:
            sale=c.execute('SELECT * FROM sales WHERE id=?',(sale_id,)).fetchone();items=c.execute('SELECT si.*,p.name,p.barcode FROM sale_items si JOIN products p ON p.id=si.product_id WHERE sale_id=?',(sale_id,)).fetchall();serials=c.execute('SELECT p.name,s.serial_no FROM serials s JOIN products p ON p.id=s.product_id WHERE s.sale_id=? ORDER BY s.id',(sale_id,)).fetchall()
        return sale,items,serials
    def set_delivery_status(self,sale_id,status):
        with self.connect() as c:c.execute("UPDATE sales SET delivery_status=? WHERE id=? AND sale_type='DELIVERY'",(status,sale_id))
    def deliveries(self):
        with self.connect() as c:return c.execute("SELECT * FROM sales WHERE sale_type='DELIVERY' ORDER BY id DESC").fetchall()
    def add_expense(self,description,amount):
        description=description.strip();amount=float(amount)
        if not description or amount<0:raise ValueError('Invalid expense')
        with self.connect() as c:cur=c.execute('INSERT INTO expenses(created_at,description,amount) VALUES(?,?,?)',(datetime.now().isoformat(timespec='seconds'),description,amount));return cur.lastrowid

    def _bounds(self,period='all',start=None,end=None):
        now=datetime.now()
        if period=='today':a=now.replace(hour=0,minute=0,second=0,microsecond=0);b=now
        elif period=='week':a=(now-timedelta(days=now.weekday())).replace(hour=0,minute=0,second=0,microsecond=0);b=now
        elif period=='month':a=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0);b=now
        elif period=='custom' and start and end:
            a=datetime.fromisoformat(start);b=datetime.fromisoformat(end)+timedelta(days=1)
        else:return None,None
        return a.isoformat(timespec='seconds'),b.isoformat(timespec='seconds')
    def report(self,period='all',start=None,end=None):
        a,b=self._bounds(period,start,end);w='';args=[]
        if a:w=' WHERE created_at>=? AND created_at<?';args=[a,b]
        with self.connect() as c:
            s=c.execute('SELECT COALESCE(SUM(total),0) sales,COALESCE(SUM(cost_total),0) cogs,COUNT(*) cnt FROM sales'+w,args).fetchone();e=c.execute('SELECT COALESCE(SUM(amount),0) e FROM expenses'+w,args).fetchone()['e'];inv=c.execute('SELECT COALESCE(SUM(stock*cost),0) v FROM products WHERE active=1').fetchone()['v']
        gross=float(s['sales'])-float(s['cogs']);return {'sales':float(s['sales']),'cogs':float(s['cogs']),'gross_profit':gross,'expenses':float(e),'net_profit':gross-float(e),'inventory_value':float(inv),'sales_count':int(s['cnt'])}
    def dashboard_periods(self):return {p:self.report(p) for p in ('today','week','month')}
    def recent_sales(self,limit=8):
        with self.connect() as c:return c.execute('SELECT * FROM sales ORDER BY id DESC LIMIT ?',(limit,)).fetchall()
    def sales_last_days(self,days=7):
        start=(datetime.now()-timedelta(days=days-1)).replace(hour=0,minute=0,second=0,microsecond=0)
        out=[]
        with self.connect() as c:
            rows=c.execute('SELECT substr(created_at,1,10) d,COALESCE(SUM(total),0) total FROM sales WHERE created_at>=? GROUP BY substr(created_at,1,10)',(start.isoformat(timespec='seconds'),)).fetchall();m={r['d']:float(r['total']) for r in rows}
        for i in range(days):
            d=(start+timedelta(days=i));out.append((d.strftime('%a'),m.get(d.strftime('%Y-%m-%d'),0.)))
        return out
    def inventory(self):
        with self.connect() as c:return c.execute('SELECT p.*,COALESCE((SELECT unit_cost FROM purchases pu WHERE pu.product_id=p.id ORDER BY pu.id DESC LIMIT 1),p.cost) last_cost FROM products p WHERE p.active=1 ORDER BY p.name').fetchall()
    def purchase_history(self,period='all',start=None,end=None):
        a,b=self._bounds(period,start,end);w='';args=[]
        if a:w=' WHERE pu.created_at>=? AND pu.created_at<?';args=[a,b]
        with self.connect() as c:return c.execute('SELECT pu.*,p.name product_name,p.barcode,s.name supplier_name FROM purchases pu JOIN products p ON p.id=pu.product_id LEFT JOIN suppliers s ON s.id=pu.supplier_id'+w+' ORDER BY pu.id DESC',args).fetchall()
    def sales_history(self,period='all',start=None,end=None):
        a,b=self._bounds(period,start,end);w='';args=[]
        if a:w=' WHERE created_at>=? AND created_at<?';args=[a,b]
        with self.connect() as c:return c.execute('SELECT * FROM sales'+w+' ORDER BY id DESC',args).fetchall()
    def sales_by_product(self,period='all',start=None,end=None):
        a,b=self._bounds(period,start,end);cond='';args=[]
        if a:cond=' AND s.created_at>=? AND s.created_at<?';args=[a,b]
        with self.connect() as c:return c.execute('''SELECT p.name,p.barcode,SUM(si.qty) qty,SUM(si.total) sales,SUM(si.qty*si.unit_cost) cost,SUM(si.total-si.qty*si.unit_cost) profit FROM sale_items si JOIN sales s ON s.id=si.sale_id JOIN products p ON p.id=si.product_id WHERE 1=1'''+cond+' GROUP BY p.id,p.name,p.barcode ORDER BY sales DESC',args).fetchall()
    def supplier_report(self,period='all',start=None,end=None):
        a,b=self._bounds(period,start,end);cond='';args=[]
        if a:cond=' AND pu.created_at>=? AND pu.created_at<?';args=[a,b]
        with self.connect() as c:return c.execute('''SELECT COALESCE(s.name,'No Supplier') supplier,COUNT(pu.id) entries,SUM(pu.qty) qty,SUM(pu.total) purchases FROM purchases pu LEFT JOIN suppliers s ON s.id=pu.supplier_id WHERE 1=1'''+cond+' GROUP BY pu.supplier_id,s.name ORDER BY purchases DESC',args).fetchall()
    def cost_history(self,period='all',start=None,end=None):return self.purchase_history(period,start,end)

    def receipt_text(self,sale_id):
        sale,items,serials=self.sale(sale_id)
        if not sale:raise ValueError('Sale not found')
        width=max(32,min(56,int(self.get_setting('receipt_width','42'))));lines=[self.get_setting('store_name','GM BizFlow Store').center(width)];phone=self.get_setting('store_phone','').strip()
        if phone:lines.append(phone.center(width))
        lines+=['-'*width,f'Receipt #{sale_id}',sale['created_at'].replace('T',' '),'-'*width]
        for it in items:lines+=[it['name'][:width],f"{it['qty']:g} x ${it['unit_price']:.2f}".ljust(width-12)+f"${it['total']:.2f}".rjust(12)]
        lines+=['-'*width,f"Subtotal USD: ${sale['subtotal']:.2f}".rjust(width)]
        if sale['discount']:lines.append(f"Discount: -${sale['discount']:.2f}".rjust(width))
        lines += [f"TOTAL USD: ${sale['total']:.2f}".rjust(width),f"TOTAL LBP: {round(sale['total']*sale['lbp_rate']):,}".rjust(width),f"Payment: {sale['payment_method']}".rjust(width),f"Paid: {sale['paid_currency']} {sale['paid_amount']:,.2f}".rjust(width),f"Change: {sale['paid_currency']} {sale['change_amount']:,.2f}".rjust(width)]
        if sale['sale_type']=='DELIVERY':lines+=['-'*width,'DELIVERY OUT',sale['customer_name'][:width],sale['phone'][:width],sale['address'][:width]]
        if serials:lines+=['-'*width,'Serial Numbers:']+[f"{r['name'][:18]}: {r['serial_no']}" for r in serials]
        lines+=['-'*width,self.get_setting('receipt_footer','Thank you').center(width),'',''];return '\n'.join(lines)
    def backup(self,destination):
        destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True);source=sqlite3.connect(self.db_path);target=sqlite3.connect(destination)
        try:source.backup(target);target.commit()
        finally:target.close();source.close()
        return destination
    def daily_backup(self):
        try:
            d=self.db_path.parent/'backups';d.mkdir(parents=True,exist_ok=True);return self.backup(d/f"GM_BizFlow_{datetime.now():%Y-%m-%d}.db")
        except Exception:return None
