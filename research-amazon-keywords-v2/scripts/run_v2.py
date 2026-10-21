"""Official V2 CLI: prepare -> agent judgments -> apply -> review -> export payload."""
import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from v2.data import aggregate,read_sources,dump,load,digest,CURRENCY

ROOT=Path(__file__).resolve().parents[1]

def boundary(path,asin,market,variant,sku=None):
    module_path=ROOT.parent/'define-product-boundary/scripts/boundary.py'
    if not module_path.exists(): raise ValueError('请将 define-product-boundary 与本 Skill 并列安装')
    spec=importlib.util.spec_from_file_location('boundary_v2',module_path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.read(path,asin,market,variant,sku)

def prepare(args):
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    product=boundary(args.boundary,args.asin,args.market,args.variant,args.sku)
    manifest=load(args.batch) if args.batch else None
    rows,diagnostics=read_sources(args.input,args.market,manifest,load(args.mapping) if args.mapping else None)
    candidates=aggregate(rows,bool(manifest))
    request={'version':2,'mode':'verified' if manifest else 'exploratory','product':product,'candidates':candidates,
             'boundary_sha256':digest(args.boundary),'batch':manifest}
    dump(out/'request.json',request); dump(out/'sources.json',rows); dump(out/'diagnostics.json',diagnostics)
    input_path=Path(args.input).resolve()
    source_files=[{'path':str((input_path/r['file']) if input_path.is_dir() else input_path),'sha256':r['file_sha256']}
                  for r in rows]
    source_files=list({s['path']:s for s in source_files}.values())
    dump(out/'manifest.json',{'request_sha256':digest(out/'request.json'),'sources_sha256':digest(out/'sources.json'),
                             'boundary_sha256':digest(args.boundary),'boundary_path':str(Path(args.boundary).resolve()),
                             'input_path':str(input_path),'source_files':source_files,
                             'batch_path':str(Path(args.batch).resolve()) if args.batch else None,
                             'batch_sha256':digest(args.batch) if args.batch else None,
                             'mapping_path':str(Path(args.mapping).resolve()) if args.mapping else None,
                             'mapping_sha256':digest(args.mapping) if args.mapping else None,
                             'rows':len(rows),'keywords':len(candidates),'mode':request['mode']})
    print(json.dumps({'rows':len(rows),'keywords':len(candidates),'mode':request['mode']},ensure_ascii=False))

def checked_request(work):
    m=load(work/'manifest.json')
    for f,key in [('request.json','request_sha256'),('sources.json','sources_sha256')]:
        if digest(work/f)!=m[key]: raise ValueError(f+' 已变化；重新准备判断')
    for path_key,hash_key in [('boundary_path','boundary_sha256'),('batch_path','batch_sha256'),('mapping_path','mapping_sha256')]:
        if m.get(path_key) and (not Path(m[path_key]).is_file() or digest(m[path_key])!=m[hash_key]):
            raise ValueError(path_key+' 已变化或丢失；重新准备判断')
    if m.get('source_files'):
        source_files={Path(x['path']).name for x in m['source_files']}
        root=Path(m['input_path'])
        current={p.name for p in root.iterdir() if p.suffix.lower() in {'.xlsx','.csv','.tsv','.xls','.xlsm','.xlsb','.ods','.zip'} and not p.name.startswith('~$')} if root.is_dir() else {root.name}
        if current!=source_files: raise ValueError('输入文件清单已变化；重新准备判断')
        for source in m['source_files']:
            path=Path(source['path'])
            if not path.is_file() or digest(path)!=source['sha256']:
                raise ValueError('输入文件已变化或丢失；重新准备判断: '+path.name)
    return load(work/'request.json')

def required_review_ids(merged):
    review_ids={x['id'] for x in merged if x['judgment']['decision']=='include' and x['judgment']['priority'] in {'P1','P2'}}
    other=[x for x in merged if x['id'] not in review_ids]
    for metric in ('search_volume','verified_competitors'):
        ranked=sorted([x for x in other if x['metrics'].get(metric) is not None],key=lambda x:x['metrics'][metric],reverse=True)
        review_ids.update(x['id'] for x in ranked[:20])
    return review_ids


def apply(work,judgments_path):
    req=checked_request(work); answer=load(judgments_path)
    if answer.get('request_sha256')!=digest(work/'request.json'): raise ValueError('回答不是本次请求')
    jj=answer.get('judgments',[]); byid={j['id']:j for j in jj}
    if len(byid)!=len(jj) or set(byid)!={c['id'] for c in req['candidates']}: raise ValueError('判断必须恰好覆盖全部候选ID')
    facts={f['id']:f for f in req['product']['facts']}
    merged=[]
    for c in req['candidates']:
        j=byid[c['id']]
        if j.get('decision') not in {'include','exclude','hold'}: raise ValueError('decision无效')
        if j.get('fit') not in {'supported','unknown','conflict'}: raise ValueError('fit无效')
        if not isinstance(j.get('reason'),str) or not j['reason'].strip() or not isinstance(j.get('fact_ids'),list) or not j['fact_ids'] or not all(isinstance(f,str) for f in j['fact_ids']) or not set(j['fact_ids'])<=set(facts): raise ValueError(c['keyword']+':缺少理由或事实依据')
        if j['decision']=='include':
            if j.get('priority') not in {'P1','P2','P3'} or j['fit']=='conflict': raise ValueError('冲突词或无优先级不能入表')
            if j.get('level') not in {'一级','二级','长尾'} or not j.get('tags') or not isinstance(j['tags'],list): raise ValueError('缺少层级/标签')
            if not isinstance(j.get('match'),str) or j['match'] not in {'Exact','Phrase','Broad','Exact / Phrase','Phrase / Exact'}: raise ValueError('match必须是字符串：Exact、Phrase、Broad、Exact / Phrase或Phrase / Exact')
            if not all(isinstance(t,str) and t.strip() for t in j['tags']): raise ValueError('tags必须是非空字符串列表')
            if j['priority']=='P3' and not j.get('test_hypothesis'): raise ValueError('P3必须明确测试假设')
            if j['fit']=='unknown' and not j.get('evidence_note'): raise ValueError('未知能力须披露')
            if not isinstance(j.get('order'),(int,float)) or isinstance(j.get('order'),bool) or not math.isfinite(j['order']): raise ValueError('缺少有效组内顺序')
        elif j.get('priority') is not None: raise ValueError('未入表词优先级须为null')
        # Candidate identities and metrics always come from the source, never the model response.
        merged.append({**c,'judgment':j})
    dump(work/'decisions.json',merged)
    dump(work/'decision-manifest.json',{'request_sha256':digest(work/'request.json'),'judgments_sha256':digest(judgments_path),'decisions_sha256':digest(work/'decisions.json')})
    review_ids=required_review_ids(merged)
    dump(work/'review-request.json',{'decisions_sha256':digest(work/'decisions.json'),'required_ids':sorted(review_ids),
          'instruction':'复核全部P1/P2及机会样本；另阅读全部候选列出核心概念词ID，无遗漏检查。逐条记录结论及理由，不自动批准。'})
    print(json.dumps({'candidates':len(merged),'included':sum(x['judgment']['decision']=='include' for x in merged),'review_required':len(review_ids)}))

def export_payload(work,review_path):
    req=checked_request(work); manifest=load(work/'decision-manifest.json')
    if digest(work/'decisions.json')!=manifest['decisions_sha256'] or manifest['request_sha256']!=digest(work/'request.json'): raise ValueError('判断已改变，须重新apply及复核')
    items=load(work/'decisions.json'); review=load(review_path); rr=load(work/'review-request.json')
    if rr.get('decisions_sha256')!=digest(work/'decisions.json') or set(rr.get('required_ids',[]))!=required_review_ids(items):
        raise ValueError('复核请求已变化或不完整；重新apply')
    if review.get('decisions_sha256')!=digest(work/'decisions.json'): raise ValueError('复核记录已过期')
    reviewed=review.get('items',[]); reviews={r['id']:r for r in reviewed}; allids={x['id'] for x in items}
    if len(reviews)!=len(reviewed) or not set(reviews)<=allids: raise ValueError('重复或未知复核ID')
    core=review.get('core_ids')
    if not isinstance(core,list) or not core or not set(core)<=allids or not review.get('core_review_note'): raise ValueError('需要完整核心概念检查与说明')
    expected=set(rr['required_ids'])|set(core)
    if not expected<=set(reviews): raise ValueError('P1/P2、核心词或机会样本复核不完整')
    if any(r.get('result')!='pass' or not r.get('reason') for r in reviewed): raise ValueError('复核尚有未解决问题')
    selected=sorted([x for x in items if x['judgment']['decision']=='include'],key=lambda x:(x['judgment']['priority'],x['judgment']['order'],x['keyword']))
    if not selected: raise ValueError('无入选词；请交付未入选说明，不生成空词库')
    if len(selected)>150 and not review.get('over_150_review'): raise ValueError('超过150须先复查并说明保留依据；禁止机械截断')
    columns=[('priority','优先级'),('keyword','关键词'),('translation','中文含义'),('level','层级'),('tags','需求标签')]
    definitions=[('search_volume','月搜索量'),('aba_rank','ABA周排名'),('verified_competitors','同批次竞品数'),('observed_asins','观测ASIN数（非同期）'),('related_count','原表相关产品数'),('purchase_rate','估算购买率'),('ppc','估算PPC（'+CURRENCY[req['product']['market']]+'）'),('ad_competitors','广告竞品数')]
    if req['mode']=='verified': definitions=[x for x in definitions if x[0]!='observed_asins']
    columns += [(k,t) for k,t in definitions if any(x['metrics'].get(k) is not None for x in selected)]
    columns += [('match','建议匹配'),('reason','入选理由')]
    notes=[]
    if req['mode']=='exploratory': notes.append('统计窗口未核对；数值取每词一条代表源行，不是跨期聚合。观测ASIN数不代表同期验证。')
    if any(x['metric_differences'] for x in selected): notes.append('同词来源的部分指标不一致，完整原值和选取来源见审计记录。')
    if any(x['metrics'].get('related_count') is not None for x in selected): notes.append('原表相关产品数可能包含目标清单之外的ASIN，与目标观测ASIN数含义不同。')
    if len(selected)>150: notes.append(review['over_150_review'])
    records=[]
    for x in selected:
        j=x['judgment']; evidence=j.get('evidence_note','')
        if all(x['metrics'].get(k) is None for k in ('search_volume','aba_rank','purchase_rate','ppc')): evidence+='；竞品效果未知，优先级依据商品匹配'
        records.append({**x['metrics'],**{k:j.get(k) for k in ('priority','level','match','reason')},'keyword':x['keyword'],
                        'translation':x['translation'],'tags':'、'.join(j['tags']),'evidence':evidence.strip('；')})
    if any(x['evidence'] for x in records): columns.append(('evidence','证据情况'))
    payload={'headers':[t for _,t in columns],'keys':[k for k,_ in columns],'rows':[[r.get(k) for k,_ in columns] for r in records],
             'notes':notes,'keyword_ids':[x['id'] for x in selected],'version':'2.0.0','mode':req['mode']}
    dump(work/'excel.json',payload)
    dump(work/'delivery-manifest.json',{'request_sha256':digest(work/'request.json'),'decisions_sha256':digest(work/'decisions.json'),
                'review_sha256':digest(review_path),'payload_sha256':digest(work/'excel.json'),'keywords':len(selected),'mode':req['mode']})
    print(json.dumps({'keywords':len(selected),'payload':str(work/'excel.json')},ensure_ascii=False))

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='action',required=True)
    a=sub.add_parser('prepare')
    for name in ('input','boundary','asin','market','output'): a.add_argument('--'+name,required=True)
    a.add_argument('--variant',default='unknown'); a.add_argument('--sku'); a.add_argument('--batch'); a.add_argument('--mapping')
    a=sub.add_parser('apply'); a.add_argument('--work',required=True); a.add_argument('--judgments',required=True)
    a=sub.add_parser('export'); a.add_argument('--work',required=True); a.add_argument('--review',required=True)
    args=p.parse_args()
    if args.action=='prepare': prepare(args)
    elif args.action=='apply': apply(Path(args.work),args.judgments)
    else: export_payload(Path(args.work),args.review)

if __name__=='__main__':
    try: main()
    except (ValueError,KeyError,OSError) as e: print('ERROR: '+str(e),file=sys.stderr); sys.exit(2)

