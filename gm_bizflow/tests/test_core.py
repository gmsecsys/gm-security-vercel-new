import tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import BizFlowDB

class BizFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=BizFlowDB(Path(self.tmp.name)/'test.db')
        self.db.set_setting('lbp_rate','89500')
        self.sup=self.db.add_supplier('ABC Trading','03123456')
        self.p1=self.db.upsert_product('111','Pot Set','Kitchen',10,25,0,False)
        self.p2=self.db.upsert_product('222','Electric Kettle','Electronics',15,30,0,True)
    def tearDown(self): self.tmp.cleanup()
    def test_currency(self):
        self.assertEqual(self.db.usd_to_lbp(10),895000)
        self.assertAlmostEqual(self.db.lbp_to_usd(895000),10)
    def test_stock_and_serials(self):
        self.db.stock_in(self.p1,10,11,self.sup)
        self.db.stock_in(self.p2,2,16,self.sup,['SN1','SN2'])
        self.assertEqual(self.db.product(self.p1)['stock'],10)
        self.assertEqual(self.db.product(self.p2)['stock'],2)
    def test_sale_and_profit(self):
        self.db.stock_in(self.p1,10,10,self.sup)
        sid=self.db.create_sale([{'product_id':self.p1,'qty':2}],discount=5,paid_currency='LBP')
        sale,items,_=self.db.sale(sid)
        self.assertEqual(sale['total'],45)
        self.assertEqual(sale['paid_amount'],45*89500)
        self.assertEqual(self.db.product(self.p1)['stock'],8)
        self.db.add_expense('Fuel',5)
        r=self.db.report(); self.assertEqual(r['sales'],45); self.assertEqual(r['cogs'],20); self.assertEqual(r['net_profit'],20)
    def test_delivery_and_receipt(self):
        self.db.stock_in(self.p1,3,10,self.sup)
        sid=self.db.create_sale([{'product_id':self.p1,'qty':1}],sale_type='DELIVERY',customer_name='John',phone='03',address='Jounieh',delivery_status='OUT')
        txt=self.db.receipt_text(sid)
        self.assertIn('TOTAL USD',txt); self.assertIn('TOTAL LBP',txt); self.assertIn('DELIVERY OUT',txt); self.assertIn('John',txt)
    def test_serial_sale(self):
        self.db.stock_in(self.p2,2,15,self.sup,['SER-A','SER-B'])
        sid=self.db.create_sale([{'product_id':self.p2,'qty':1}],paid_currency='USD')
        _,_,ser=self.db.sale(sid)
        self.assertEqual(len(ser),1); self.assertEqual(ser[0]['serial_no'],'SER-A')
    def test_search(self):
        self.assertEqual(self.db.product_by_barcode('111')['name'],'Pot Set')
        self.assertEqual(len(self.db.search_products('Pot')),1)

if __name__=='__main__': unittest.main()
