from __future__ import annotations
import sqlite3, json, shutil
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime

DEFAULT_RATE = 89500.0

class BizFlowDB:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

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
            defaults = {'store_name':'GM BizFlow Store','store_phone':'','lbp_rate':str(DEFAULT_RATE),
                        'show_images':'0','receipt_width':'42','receipt_footer':'Thank you for your visit'}
            for k,v in defaults.items():
                c.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',(k,v))

    def get_setting(self,key,default=''):
        with self.connect() as c:
            r=c.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
        return r['value'] if r else default

    def set_setting(self,key,value):
        with self.connect() as c:
            c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,str(value)))

    def rate(self):
        try:return float(self.get_setting('lbp_rate',str(DEFAULT_RATE)))
        except:return DEFAULT_RATE

    def usd_to_lbp(self,usd,rate=None): return round(float(usd)*(self.rate() if rate is None else float(rate)))
    def lbp_to_usd(self,lbp,rate=None): return float(lbp)/(self.rate() if rate is None else float(rate))

    def add_supplier(self,name,phone=''):
        name=name.strip()
        if not name: raise ValueError('Supplier name is required')
        with self.connect() as c:
            cur=c.execute('INSERT INTO suppliers(name,phone) VALUES(?,?)',(name,phone.strip()))
            return cur.lastrowid

    def suppliers(self):
        with self.connect() as c:return c.execute('SELECT * FROM suppliers ORDER BY name').fetchall()

    def upsert_product(self,barcode,name,category='',cost=0,price=0,stock=0,track_serial=False,image_path='',supplier_id=None):
        barcode,name=barcode.strip(),name.strip()
        if not barcode or not name: raise ValueError('Barcode and product name are required')
        if min(float(cost),float(price),float(stock)) < 0: raise ValueError('Cost, price and stock must be non-negative')
        with self.connect() as c:
            r=c.execute('SELECT id FROM products WHERE barcode=?',(barcode,)).fetchone()
            if r:
                c.execute('''UPDATE products SET name=?,category=?,cost=?,price=?,stock=?,track_serial=?,image_path=?,supplier_id=? WHERE id=?''',
                          (name,category,float(cost),float(price),float(stock),int(bool(track_serial)),image_path,supplier_id,r['id']))
                return r['id']
            cur=c.execute('''INSERT INTO products(barcode,name,category,cost,price,stock,track_serial,image_path,supplier_id)
                             VALUES(?,?,?,?,?,?,?,?,?)''',(barcode,name,category,float(cost),float(price),float(stock),int(bool(track_serial)),image_path,supplier_id))
            return cur.lastrowid

    def product(self,product_id):
        with self.connect() as c:return c.execute('SELECT * FROM products WHERE id=?',(product_id,)).fetchone()

    def product_by_barcode(self,barcode):
        with self.connect() as c:return c.execute('SELECT * FROM products WHERE barcode=? AND active=1',(barcode.strip(),)).fetchone()

    def search_products(self,q='',limit=100):
        q=q.strip()
        with self.connect() as c:
            if not q:return c.execute('SELECT * FROM products WHERE active=1 ORDER BY name LIMIT ?',(limit,)).fetchall()
            p=f'%{q}%'
            return c.execute('''SELECT * FROM products WHERE active=1 AND (barcode LIKE ? OR name LIKE ? OR category LIKE ?) ORDER BY name LIMIT ?''',(p,p,p,limit)).fetchall()

    def add_serials(self,product_id,serial_numbers):
        vals=[s.strip() for s in serial_numbers if s and s.strip()]
        if len(vals)!=len(set(vals)): raise ValueError('Duplicate serial in input')
        with self.connect() as c:
            for s in vals:c.execute("INSERT INTO serials(product_id,serial_no,status) VALUES(?,?,'IN_STOCK')",(product_id,s))

    def stock_in(self,product_id,qty,unit_cost,supplier_id=None,serial_numbers=None):
        qty,unit_cost=float(qty),float(unit_cost)
        if qty<=0 or unit_cost<0: raise ValueError('Invalid quantity or cost')
        p=self.product(product_id)
        if not p: raise ValueError('Product not found')
        serial_numbers=serial_numbers or []
        if p['track_serial'] and int(qty)!=len(serial_numbers):
            raise ValueError('Serial-tracked products need one serial number per unit')
        with self.connect() as c:
            cur=c.execute('''INSERT INTO purchases(created_at,supplier_id,product_id,qty,unit_cost,total) VALUES(?,?,?,?,?,?)''',
                          (datetime.now().isoformat(timespec='seconds'),supplier_id,product_id,qty,unit_cost,qty*unit_cost))
            c.execute('UPDATE products SET stock=stock+?,cost=?,supplier_id=COALESCE(?,supplier_id) WHERE id=?',(qty,unit_cost,supplier_id,product_id))
            for s in serial_numbers:c.execute("INSERT INTO serials(product_id,serial_no,status) VALUES(?,?,'IN_STOCK')",(product_id,s.strip()))
            return cur.lastrowid

    def _available_serials(self,c,product_id,qty):
        return c.execute("SELECT id,serial_no FROM serials WHERE product_id=? AND status='IN_STOCK' ORDER BY id LIMIT ?",(product_id,int(qty))).fetchall()

    def create_sale(self,items,discount=0,paid_currency='USD',sale_type='WALK_IN',customer_name='',phone='',address='',delivery_status=''):
        if not items: raise ValueError('Cart is empty')
        paid_currency=paid_currency.upper()
        if paid_currency not in ('USD','LBP'): raise ValueError('Currency must be USD or LBP')
        discount=float(discount)
        if discount<0: raise ValueError('Discount cannot be negative')
        rate=self.rate()
        prepared=[]; subtotal=0.0; cost_total=0.0
        with self.connect() as c:
            for it in items:
                pid=int(it['product_id']); qty=float(it.get('qty',1))
                if qty<=0: raise ValueError('Quantity must be positive')
                p=c.execute('SELECT * FROM products WHERE id=? AND active=1',(pid,)).fetchone()
                if not p: raise ValueError('Product not found')
                if qty>float(p['stock']): raise ValueError(f"Not enough stock for {p['name']}")
                serial_ids=[]
                if p['track_serial']:
                    if int(qty)!=qty: raise ValueError('Serial-tracked quantity must be whole units')
                    serials=self._available_serials(c,pid,qty)
                    if len(serials)!=int(qty): raise ValueError(f"Not enough serials for {p['name']}")
                    serial_ids=[r['id'] for r in serials]
                price=float(it.get('price',p['price']))
                line=qty*price
                prepared.append((p,qty,price,line,serial_ids))
                subtotal+=line; cost_total+=qty*float(p['cost'])
            total=max(0.0,subtotal-discount)
            paid_amount=total if paid_currency=='USD' else self.usd_to_lbp(total,rate)
            cur=c.execute('''INSERT INTO sales(created_at,sale_type,subtotal,discount,total,cost_total,paid_currency,paid_amount,lbp_rate,
                             customer_name,phone,address,delivery_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                          (datetime.now().isoformat(timespec='seconds'),sale_type,subtotal,discount,total,cost_total,paid_currency,paid_amount,rate,
                           customer_name,phone,address,delivery_status))
            sale_id=cur.lastrowid
            for p,qty,price,line,serial_ids in prepared:
                c.execute('INSERT INTO sale_items(sale_id,product_id,qty,unit_cost,unit_price,total) VALUES(?,?,?,?,?,?)',
                          (sale_id,p['id'],qty,p['cost'],price,line))
                c.execute('UPDATE products SET stock=stock-? WHERE id=?',(qty,p['id']))
                for sid in serial_ids:c.execute("UPDATE serials SET status='SOLD',sale_id=? WHERE id=?",(sale_id,sid))
            return sale_id

    def sale(self,sale_id):
        with self.connect() as c:
            sale=c.execute('SELECT * FROM sales WHERE id=?',(sale_id,)).fetchone()
            items=c.execute('''SELECT si.*,p.name,p.barcode FROM sale_items si JOIN products p ON p.id=si.product_id WHERE sale_id=?''',(sale_id,)).fetchall()
            serials=c.execute('''SELECT p.name,s.serial_no FROM serials s JOIN products p ON p.id=s.product_id WHERE s.sale_id=? ORDER BY s.id''',(sale_id,)).fetchall()
        return sale,items,serials

    def set_delivery_status(self,sale_id,status):
        with self.connect() as c:c.execute("UPDATE sales SET delivery_status=? WHERE id=? AND sale_type='DELIVERY'",(status,sale_id))

    def add_expense(self,description,amount):
        description=description.strip(); amount=float(amount)
        if not description or amount<0: raise ValueError('Invalid expense')
        with self.connect() as c:
            cur=c.execute('INSERT INTO expenses(created_at,description,amount) VALUES(?,?,?)',(datetime.now().isoformat(timespec='seconds'),description,amount))
            return cur.lastrowid

    def report(self):
        with self.connect() as c:
            s=c.execute('SELECT COALESCE(SUM(total),0) sales, COALESCE(SUM(cost_total),0) cogs FROM sales').fetchone()
            exp=c.execute('SELECT COALESCE(SUM(amount),0) e FROM expenses').fetchone()['e']
            inv=c.execute('SELECT COALESCE(SUM(stock*cost),0) v FROM products WHERE active=1').fetchone()['v']
        gross=float(s['sales'])-float(s['cogs']); net=gross-float(exp)
        return {'sales':float(s['sales']),'cogs':float(s['cogs']),'gross_profit':gross,'expenses':float(exp),'net_profit':net,'inventory_value':float(inv)}

    def inventory(self):
        with self.connect() as c:return c.execute('SELECT * FROM products WHERE active=1 ORDER BY name').fetchall()

    def receipt_text(self,sale_id):
        sale,items,serials=self.sale(sale_id)
        if not sale: raise ValueError('Sale not found')
        width=max(32,min(56,int(self.get_setting('receipt_width','42'))))
        lines=[self.get_setting('store_name','GM BizFlow Store').center(width)]
        phone=self.get_setting('store_phone','').strip()
        if phone:lines.append(phone.center(width))
        lines += ['-'*width,f"Receipt #{sale_id}",sale['created_at'].replace('T',' '),'-'*width]
        for it in items:
            lines.append(it['name'][:width])
            lines.append(f"{it['qty']:g} x ${it['unit_price']:.2f}".ljust(width-12)+f"${it['total']:.2f}".rjust(12))
        lines += ['-'*width,f"Subtotal USD: ${sale['subtotal']:.2f}".rjust(width)]
        if sale['discount']:lines.append(f"Discount: -${sale['discount']:.2f}".rjust(width))
        lines += [f"TOTAL USD: ${sale['total']:.2f}".rjust(width),f"TOTAL LBP: {round(sale['total']*sale['lbp_rate']):,}".rjust(width),
                  f"Paid: {sale['paid_currency']} {sale['paid_amount']:,.0f}".rjust(width)]
        if sale['sale_type']=='DELIVERY':
            lines += ['-'*width,'DELIVERY OUT',sale['customer_name'][:width],sale['phone'][:width],sale['address'][:width]]
        if serials:
            lines += ['-'*width,'Serial Numbers:']+[f"{r['name'][:18]}: {r['serial_no']}" for r in serials]
        lines += ['-'*width,self.get_setting('receipt_footer','Thank you').center(width),'','']
        return '\n'.join(lines)

    def backup(self,destination):
        destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(self.db_path,destination); return destination
