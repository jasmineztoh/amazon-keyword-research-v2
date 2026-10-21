"""Package only the two reviewed V2 Skills, excluding business inputs/results."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[2]
FILES=[
 'define-product-boundary/SKILL.md',
 'define-product-boundary/agents/openai.yaml',
 'define-product-boundary/scripts/boundary.py',
 'research-amazon-keywords-v2/SKILL.md',
 'research-amazon-keywords-v2/agents/openai.yaml',
 'research-amazon-keywords-v2/references/contract-v2.md',
 'research-amazon-keywords-v2/scripts/run_v2.py',
 'research-amazon-keywords-v2/scripts/export_v2.mjs',
 'research-amazon-keywords-v2/scripts/export_v2_fallback.py',
 'research-amazon-keywords-v2/scripts/v2/__init__.py',
 'research-amazon-keywords-v2/scripts/v2/data.py',
]
GUIDE='''# 安装与使用

将压缩包内两个 Skill 文件夹并列放入 Codex Skills 目录，或放在同一工作目录中。关键词 Skill 需要前置的功能卖点界定 Skill。

Python 需要 openpyxl 3.1+。Excel 优先用工作环境的 Node `@oai/artifact-tool`；若当前环境确实没有它，使用包含的 Python openpyxl 后备导出。输入为 .xlsx、.csv 或 .tsv；旧 .xls 请先另存 .xlsx，核对字段口径。

先调用 `define-product-boundary` 生成《产品边界.md》，再调用 `research-amazon-keywords-v2`，按各自 SKILL.md 运行。批次日期未核实时仅做探索训练，不把数值写成同期验证。成果和审计记录由用户选择本地输出目录，输入数据不在安装包内。
'''

def build(output):
    blobs={}
    for rel in FILES:
        path=PROJECT/rel
        if not path.is_file():raise FileNotFoundError(path)
        blobs[rel]=path.read_bytes()
    blobs['安装说明.md']=GUIDE.encode('utf-8')
    manifest={'version':'2.0.0','files':{name:hashlib.sha256(data).hexdigest() for name,data in sorted(blobs.items())}}
    blobs['包清单.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(blobs.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,20,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)
    with zipfile.ZipFile(output) as z:
        names=set(z.namelist());expected=set(blobs)
        if names!=expected:raise ValueError('包内文件与白名单不一致')
        if any(hashlib.sha256(z.read(n)).hexdigest()!=sha for n,sha in manifest['files'].items()):raise ValueError('包内容摘要不一致')
    print(json.dumps({'package':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'files':len(blobs)},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output');args=p.parse_args();build(args.output)

