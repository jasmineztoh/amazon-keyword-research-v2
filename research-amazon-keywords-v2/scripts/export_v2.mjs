import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';
const [input,output]=process.argv.slice(2);
if(!input||!output) throw Error('Usage: node export_v2.mjs excel.json output-dir');
const p=JSON.parse(await fs.readFile(input,'utf8'));
if(!p.headers?.length||!p.rows?.length||p.rows.some(r=>r.length!==p.headers.length)) throw Error('Invalid Excel payload');
const wb=Workbook.create(),s=wb.worksheets.add('关键词库');
const n=p.rows.length+1,cols=p.headers.length;
const safe=v=>typeof v==='string'&&/^[=+@-]/.test(v)?"'"+v:v;
s.showGridLines=false;
s.getRangeByIndexes(0,0,n,cols).values=[p.headers,...p.rows].map(r=>r.map(safe));
s.getRangeByIndexes(0,0,n,cols).format={font:{name:'Microsoft YaHei',size:11},verticalAlignment:'center',rowHeight:54};
const widths={priority:9,keyword:35,translation:22,level:9,tags:22,search_volume:14,aba_rank:14,verified_competitors:18,observed_asins:24,related_count:20,purchase_rate:15,ppc:18,ad_competitors:14,match:17,reason:58,evidence:48};
p.keys.forEach((key,i)=>{
 const r=s.getRangeByIndexes(0,i,n,1);r.format.columnWidth=widths[key]||18;
 if(['keyword','translation','tags','reason','evidence','match'].includes(key))r.format.wrapText=true;
 const body=s.getRangeByIndexes(1,i,n-1,1);
 if(key==='purchase_rate')body.format.numberFormat='0.00%';
 else if(key==='ppc')body.format.numberFormat='0.00';
 else if(['search_volume','aba_rank','verified_competitors','observed_asins','related_count','ad_competitors'].includes(key))body.format.numberFormat='#,##0';
});
const lastCol=String.fromCharCode(64+cols);
const table=s.tables.add(`A1:${lastCol}${n}`,true,'Keywords');
table.style='TableStyleLight1';table.showBandedRows=false;table.showBandedColumns=false;table.showFilterButton=true;
s.getRangeByIndexes(1,0,n-1,cols).format.fill='#FFFFFF';
s.getRangeByIndexes(0,0,1,cols).format={fill:'#233E47',font:{bold:true,color:'#FFFFFF'},rowHeight:54,wrapText:true};
for(let i=0;i<p.rows.length;i++){
 s.getRangeByIndexes(i+1,0,1,1).format={fill:{P1:'#DDEBDD',P2:'#F7EDD5',P3:'#EAE4F0'}[p.rows[i][0]]||'#FFFFFF',font:{bold:true}};
 const reason=p.rows[i][p.keys.indexOf('reason')]||'',evidence=p.rows[i][p.keys.indexOf('evidence')]||'';
 s.getRangeByIndexes(i+1,0,1,cols).format.rowHeight=Math.max(54,Math.ceil(Math.max(String(reason).length/30,String(evidence).length/24))*17);
}
s.freezePanes.freezeRows(1);
if(p.notes?.length){
 const note=wb.worksheets.add('说明');note.showGridLines=false;
 note.getRangeByIndexes(0,0,p.notes.length+1,1).values=[['本次数据说明'],...p.notes.map(x=>[safe(x)])];
 note.getRangeByIndexes(0,0,p.notes.length+1,1).format={columnWidth:110,rowHeight:60,wrapText:true,font:{name:'Microsoft YaHei',size:11}};
 note.getRange('A1').format={fill:'#233E47',font:{bold:true,color:'#FFFFFF'},rowHeight:30};
}
wb.recalculate();await fs.mkdir(output,{recursive:true});
const check=await wb.inspect({kind:'table',range:`关键词库!A1:${lastCol}${Math.min(n,4)}`,include:'values,formulas',tableMaxRows:4,tableMaxCols:cols});
await fs.writeFile(path.join(output,'excel-check.json'),JSON.stringify(check));
const result=await SpreadsheetFile.exportXlsx(wb);await result.save(path.join(output,'关键词库.xlsx'));
for(const [sheetName,range,name] of [['关键词库',`A1:I${Math.min(n,9)}`,'预览-关键词.png'],['关键词库',`${String.fromCharCode(65+Math.max(0,cols-5))}1:${lastCol}${Math.min(n,9)}`,'预览-依据.png'],...(p.notes?.length?[['说明',`A1:A${p.notes.length+1}`,'预览-说明.png']]:[])]){
 const preview=await wb.render({sheetName,range,scale:1,format:'png'});
 await fs.writeFile(path.join(output,name),new Uint8Array(await preview.arrayBuffer()));
}
console.log(JSON.stringify({rows:p.rows.length,sheets:p.notes?.length?2:1,output:path.join(output,'关键词库.xlsx')}));

