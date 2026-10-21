"""Behavioral regression tests for the official V2 path (not legacy scores)."""
import hashlib
import importlib.util
import json
import shutil
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from v2.data import read_sources,aggregate
from run_v2 import boundary,prepare,apply,export_payload,checked_request

SPEC=importlib.util.spec_from_file_location('product_boundary_v2',ROOT.parent/'define-product-boundary/scripts/boundary.py')
BOUNDARY=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(BOUNDARY)

class OfficialV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=ROOT.parent/'.tmp'/'official-v2-tests'
        cls.tmp.mkdir(parents=True,exist_ok=True)
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)
    def setUp(self):
        self.job=self.tmp/self.id().split('.')[-1];self.job.mkdir(exist_ok=True)
    def tearDown(self):
        shutil.rmtree(self.job)
    def product(self,mode='materials',kind='material'):
        content='Wireless mouse. Receiver included.'
        return {'version':2,'asin':'B0TEST0001','market':'US','variant':'Sample','input_mode':mode,
                'sources':[{'id':'s1','kind':kind,'locator':'input.txt','asin':'B0TEST0001','market':'US','variant':'Sample','captured_at':'2024-01-01','content':content}],
                'facts':[{'id':'type','category':'type','claim':'无线鼠标','state':'supported','source_ids':['s1'],'quotes':{'s1':'Wireless mouse'}}], 'conflicts':[]}
    def test_only_asin_missing_page_blocks_and_screenshot_resumes(self):
        data=self.product('asin');self.assertEqual(BOUNDARY.validate(data)['status'],'blocked')
        path=self.job/'产品边界.md';path.write_text(BOUNDARY.render(data),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'待核实'):BOUNDARY.read(path)
        data=self.product('asin','screenshot');self.assertEqual(BOUNDARY.validate(data)['status'],'ready')
        path.write_text(BOUNDARY.render(data),encoding='utf8');self.assertEqual(BOUNDARY.read(path,'B0TEST0001','US','Sample')['status'],'ready')
        with self.assertRaisesRegex(ValueError,'不匹配'):BOUNDARY.read(path,'B0TEST0001','US','Other')
    def test_fact_quote_and_page_priority_enforced(self):
        data=self.product();data['facts'][0]['quotes']['s1']='not in actual material'
        with self.assertRaisesRegex(ValueError,'摘录'):BOUNDARY.validate(data)
        data=self.product('both');page=dict(data['sources'][0],id='s2',kind='live_page');data['sources'].append(page)
        data['conflicts']=[{'claim':'feature','source_ids':['s1','s2'],'winner_source_id':'s1','resolution':'资料为准'}]
        with self.assertRaisesRegex(ValueError,'前台'):BOUNDARY.validate(data)
    def test_missing_zero_and_lineage_with_csv(self):
        path=self.job/'sample.csv'
        path.write_text('Keyword,Monthly Search Volume,Purchase Rate,PPC Bid,Competitor ASIN\nwireless mouse,0,,0,B0TEST0001\nwireless mouse,,0,1.25,B0TEST0001\n',encoding='utf8')
        rows,diag=read_sources(path,'US')
        self.assertEqual(len(rows),2);self.assertEqual(rows[0]['metrics']['search_volume'],0)
        self.assertEqual(rows[1]['states']['search_volume'],'blank');self.assertEqual(rows[1]['metrics']['purchase_rate'],0)
        self.assertEqual(rows[0]['states']['purchase_rate'],'blank')
        candidates=aggregate(rows,False);self.assertEqual(len(candidates),1);self.assertEqual(len(candidates[0]['row_ids']),2)
        self.assertEqual(candidates[0]['metrics']['verified_competitors'],None)
    def test_invalid_metric_and_unrecognized_sheet_fail(self):
        path=self.job/'sample.csv';path.write_text('Keyword,Monthly Search Volume\nmouse,broken\n',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'输入未通过检查'):read_sources(path,'US')
        (self.job/'another.xls').write_bytes(b'unsupported')
        with self.assertRaisesRegex(ValueError,'未支持的表格格式'):read_sources(self.job,'US')
    def test_duplicate_source_headers_survive_audit(self):
        path=self.job/'sample.csv'
        path.write_text('Keyword,更新时间,更新时间\nmouse,first,second\n',encoding='utf8')
        rows,_=read_sources(path,'US')
        self.assertEqual([x['value'] for x in rows[0]['raw'] if x['header']=='更新时间'],['first','second'])
    def test_changed_boundary_or_source_invalidates_prepared_request(self):
        source=self.job/'input.csv'
        source.write_text('Keyword,Monthly Search Volume\nwireless mouse,12\n',encoding='utf8')
        product=self.job/'产品边界.md'
        product.write_text(BOUNDARY.render(BOUNDARY.validate(self.product())),encoding='utf8')
        work=self.job/'work'
        prepare(SimpleNamespace(input=str(source),boundary=str(product),asin='B0TEST0001',market='US',variant='Sample',sku=None,output=str(work),batch=None,mapping=None))
        checked_request(work)
        source.write_text('Keyword,Monthly Search Volume\nwireless mouse,13\n',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'输入文件已变化'):checked_request(work)
        source.write_text('Keyword,Monthly Search Volume\nwireless mouse,12\n',encoding='utf8')
        product.write_text(product.read_text(encoding='utf8')+'\n',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'boundary_path'):checked_request(work)
    def test_prelaunch_sku_identity_and_exploratory_related_asins(self):
        data=self.product();data['asin']='unassigned';data['sku']='DEMO-SKU-001'
        data['sources'][0].update(asin='unassigned',sku='DEMO-SKU-001')
        path=self.job/'产品边界.md';path.write_text(BOUNDARY.render(BOUNDARY.validate(data)),encoding='utf8')
        self.assertEqual(BOUNDARY.read(path,'unassigned','US','Sample','DEMO-SKU-001')['status'],'ready')
        with self.assertRaisesRegex(ValueError,'sku 不匹配'):BOUNDARY.read(path,'unassigned','US','Sample','OTHER')
        source=self.job/'input.csv';source.write_text('Keyword,Related ASINs\ncat toy,B0TEST0003/B0TEST0002\n',encoding='utf8')
        rows,_=read_sources(source,'US')
        self.assertEqual(rows[0]['asins'],['B0TEST0002','B0TEST0003'])
        self.assertIsNone(aggregate(rows,False)[0]['metrics']['verified_competitors'])
    def test_answer_coverage_and_conflict_fail_closed(self):
        req={'version':2,'mode':'exploratory','product':self.product(),'candidates':[{'id':'id1','keyword':'wireless mouse','metrics':{},'row_ids':['r1'],'asins':[],'translation':None,'metric_differences':[]}]}
        (self.job/'request.json').write_text(json.dumps(req,ensure_ascii=False),encoding='utf8')
        (self.job/'sources.json').write_text('[]',encoding='utf8')
        def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
        (self.job/'manifest.json').write_text(json.dumps({'request_sha256':digest(self.job/'request.json'),'sources_sha256':digest(self.job/'sources.json')}),encoding='utf8')
        j={'id':'id1','decision':'include','priority':'P1','level':'一级','tags':['核心'],'match':'Exact','reason':'无线鼠标核心购买需求','fact_ids':['type'],'fit':'conflict','test_hypothesis':'','evidence_note':'','order':1}
        answer=self.job/'judgments.json';answer.write_text(json.dumps({'request_sha256':digest(self.job/'request.json'),'judgments':[j]}),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'冲突'):apply(self.job,answer)
        j['fit']='supported';j['match']=['Exact','Phrase']
        answer.write_text(json.dumps({'request_sha256':digest(self.job/'request.json'),'judgments':[j]}),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'match必须'):apply(self.job,answer)
        j['match']='Exact';answer.write_text(json.dumps({'request_sha256':digest(self.job/'request.json'),'judgments':[j]}),encoding='utf8');apply(self.job,answer)
        review={'decisions_sha256':digest(self.job/'decisions.json'),'core_ids':['id1'],'core_review_note':'已核对','items':[{'id':'id1','result':'pass','reason':'符合核心形态'}]}
        rp=self.job/'review.json';rp.write_text(json.dumps(review,ensure_ascii=False),encoding='utf8')
        export_payload(self.job,rp)
        payload=json.loads((self.job/'excel.json').read_text(encoding='utf8'))
        self.assertEqual(payload['rows'][0][1],'wireless mouse')
        rr=self.job/'review-request.json';request=json.loads(rr.read_text(encoding='utf8'));request['required_ids']=[]
        rr.write_text(json.dumps(request,ensure_ascii=False),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'复核请求已变化'):export_payload(self.job,rp)
        request['required_ids']=['id1'];rr.write_text(json.dumps(request,ensure_ascii=False),encoding='utf8')
        review['decisions_sha256']='bad';rp.write_text(json.dumps(review,ensure_ascii=False),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'过期'):export_payload(self.job,rp)

if __name__=='__main__': unittest.main()

