"""Build and validate one human-readable, machine-consumed product boundary."""
import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path

MARKETS = {'US','DE','UK','CA','FR','IT','ES','JP','AU'}
PAGE = {'live_page','page_export','screenshot'}

def validate(data):
    if data.get('version') != 2:
        raise ValueError('需要 version=2')
    asin=data.get('asin','')
    prelaunch=asin=='unassigned' and data.get('input_mode')=='materials' and bool(data.get('sku'))
    if not re.fullmatch(r'[A-Z0-9]{10}',asin) and not prelaunch:
        raise ValueError('需要有效 ASIN；未上架商品须用 asin=unassigned、SKU 和资料模式')
    if data.get('market') not in MARKETS or not data.get('variant'):
        raise ValueError('缺少站点或变体（未知填 unknown）')
    if data.get('input_mode') not in {'asin','materials','both'}:
        raise ValueError('input_mode 无效')
    sources = data.get('sources',[])
    by_id = {s['id']:s for s in sources}
    if len(by_id) != len(sources): raise ValueError('重复 source id')
    for s in sources:
        if s.get('kind') not in PAGE | {'material'}: raise ValueError('来源类别无效')
        if prelaunch and s['kind']!='material': raise ValueError('未上架商品不能伪称有对应 ASIN 页面')
        for key in ('asin','market','variant'):
            if s.get(key) != data[key]: raise ValueError(f'来源 {s["id"]} 商品身份不匹配: {key}')
        if prelaunch and s.get('sku')!=data['sku']:
            raise ValueError(f'来源 {s["id"]} SKU 不匹配')
        if not s.get('locator') or not s.get('content'): raise ValueError('来源缺少定位或实读内容')
        if s.get('captured_at') != 'unknown': date.fromisoformat(s['captured_at'])
    seen = set()
    for fact in data.get('facts',[]):
        if fact['id'] in seen: raise ValueError('重复 fact id')
        seen.add(fact['id'])
        if fact.get('state') not in {'supported','unsupported','unknown'}: raise ValueError('事实状态无效')
        if fact.get('category') not in {'type','feature','scenario','compatibility','limit','package'}: raise ValueError('事实分类无效')
        if not fact.get('claim') or not fact.get('source_ids'): raise ValueError('事实没有依据')
        for sid in fact['source_ids']:
            if sid not in by_id: raise ValueError('事实引用不存在的来源')
            quote = fact.get('quotes',{}).get(sid,'')
            if not quote or quote not in by_id[sid]['content']: raise ValueError(f'{fact["id"]} 摘录不在来源 {sid} 中')
    for conflict in data.get('conflicts',[]):
        ids = conflict['source_ids']
        if len(ids)<2 or any(s not in by_id for s in ids): raise ValueError('冲突缺少双方来源')
        winner = conflict.get('winner_source_id')
        if winner not in ids or not conflict.get('resolution'): raise ValueError('冲突未解决')
        if any(by_id[s]['kind'] in PAGE for s in ids) and by_id[winner]['kind'] not in PAGE:
            raise ValueError('资料冲突时必须以前台为准')
    page_required = data['input_mode'] in {'asin','both'}
    ready = bool(sources) and any(f['category']=='type' and f['state']=='supported' for f in data.get('facts',[]))
    if page_required and not any(s['kind'] in PAGE for s in sources): ready = False
    data['status'] = 'ready' if ready else 'blocked'
    return data

def render(data):
    identity=f'ASIN：{data["asin"]}　站点：{data["market"]}　变体：{data["variant"]}'
    if data.get('sku'): identity+=f'　SKU：{data["sku"]}'
    lines = ['# 产品边界','',identity,
             '', '状态：'+('可用于筛词' if data['status']=='ready' else '待核实：缺少页面证据或商品类型，停止正式筛词。')]
    for state,title in [('supported','已确认'),('unsupported','明确不支持'),('unknown','待核实')]:
        lines += ['',f'## {title}','']
        facts = [f for f in data.get('facts',[]) if f['state']==state]
        lines += [f'- {f["claim"]}（{f["id"]}；来源 {", ".join(f["source_ids"])}）' for f in facts] or ['暂无记录。']
    lines += ['','## 来源','']
    for s in data.get('sources',[]): lines.append(f'- {s["id"]}：{s["kind"]}；{s["locator"]}；证据时间 {s["captured_at"]}')
    lines += ['','## 冲突处理','']
    lines += [f'- {c["claim"]}：{c["resolution"]}；采用 {c["winner_source_id"]}' for c in data.get('conflicts',[])] or ['未发现需裁决的来源冲突。']
    lines += ['','## 结构化记录','', '```json',json.dumps(data,ensure_ascii=False,indent=2),'```','']
    return '\n'.join(lines)

def read(path, asin=None, market=None, variant=None, sku=None):
    text = Path(path).read_text(encoding='utf-8-sig')
    found = re.search(r'```json\n(.*?)\n```',text,re.S)
    if not found: raise ValueError('产品边界缺少结构化记录')
    data = validate(json.loads(found.group(1)))
    if text.replace('\r\n','\n') != render(data): raise ValueError('可读边界与结构化记录不一致；请重建')
    for k,v in [('asin',asin),('market',market),('variant',variant),('sku',sku)]:
        if v is not None and data[k] != v: raise ValueError(f'产品边界 {k} 不匹配')
    if data['status'] != 'ready': raise ValueError('产品边界待核实，禁止正式筛词')
    return data

def main():
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['build','check']); p.add_argument('--input',required=True)
    p.add_argument('--output'); p.add_argument('--asin'); p.add_argument('--market'); p.add_argument('--variant'); p.add_argument('--sku')
    args=p.parse_args()
    if args.action=='build':
        data=validate(json.loads(Path(args.input).read_text(encoding='utf-8-sig')))
        if not args.output: p.error('--output required')
        Path(args.output).parent.mkdir(parents=True,exist_ok=True)
        Path(args.output).write_text(render(data),encoding='utf-8')
    else: data=read(args.input,args.asin,args.market,args.variant,args.sku)
    print(json.dumps({'status':data['status'],'asin':data['asin']},ensure_ascii=False))

if __name__=='__main__': main()

