import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const project = path.resolve(process.argv[2]);
const output = path.join(project, 'generated');
const input = JSON.parse(await fs.readFile(path.join(output, 'dashboard_inputs.json'), 'utf8'));
const wb = Workbook.create();
const dash = wb.worksheets.add('Dashboard');
const calc = wb.worksheets.add('Analysis');
const raw = wb.worksheets.add('Inputs');
const navy = '#16324F', teal = '#157F78', gray = '#526273', pale = '#EDF3F7', amber = '#FFF1CC';
const num = '#,##0;(#,##0);"–"';
const pct = '0.0%;(0.0%);"–"';
for (const sh of [dash, calc, raw]) {
  sh.showGridLines = false;
  sh.getRange('A1:P65').format.font = {name:'Arial',size:10,color:navy};
  sh.getRange('A1:P65').format.rowHeight = 22;
  sh.getRange('A1:A65').format.columnWidth = 3;
  sh.getRange('B1:P65').format.columnWidth = 12;
  sh.getRange('B1:B65').format.columnWidth = 33;
}
dash.tabColor = navy;
calc.tabColor = teal;
raw.tabColor = '#DFD1B5';
function v(sh,cell,value) {sh.getRange(cell).values=[[value]];}
function f(sh,cell,value) {sh.getRange(cell).formulas=[[value]];sh.getRange(cell).format.font.color=sh===dash?navy:'#008040';}
function header(sh,range) {sh.getRange(range).format={fill:navy,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:30,horizontalAlignment:'center',verticalAlignment:'center',wrapText:true};}
function title(sh,cell,text) {v(sh,cell,text);sh.getRange(cell).format.font={name:'Arial',size:16,bold:true,color:navy};}
title(raw,'B2','Walmart public financial inputs');
v(raw,'B3','USD millions. Fiscal years end January 31. Blue values are source inputs.');
const cols = ['fiscal_year','net_sales','cost_of_sales','operating_income','operating_cash_flow','capex','receivables','inventory','accounts_payable','total_revenue','net_income','cash'];
raw.getRange('B5:M5').values=[['Fiscal year','Net sales','Cost of sales','Operating income','Operating cash','Capex','Receivables','Inventory','Payables','Total revenue','Net income','Cash']];
header(raw,'B5:M5');
raw.getRange('B5:M5').format.rowHeight=46;
raw.getRange('B6:M9').values=input.financials.map(r=>cols.map(c=>r[c]));
raw.getRange('C6:M9').format.numberFormat=num;
raw.getRange('C6:M9').format.font.color='#0000FF';
raw.getRange('B12:G12').values=[['FY25 public guidance','Low','High','Actual','Basis','Unit']];header(raw,'B12:G12');
const metricLabels=['Net sales growth (cc)','Adjusted OI growth (cc)','Adjusted EPS','Capex / net sales'];
raw.getRange('B13:G16').values=input.guidance.map((r,i)=>[metricLabels[i],r.guidance_low,r.guidance_high,r.actual,r.basis,r.unit]);
raw.getRange('C13:E16').format.font.color='#0000FF';
raw.getRange('C13:E14').format.numberFormat=pct;
raw.getRange('C15:E15').format.numberFormat='0.00';
raw.getRange('C16:E16').format.numberFormat='0.00%';
raw.getRange('F12:F16').format.columnWidth=34;
raw.getRange('G12:G16').format.columnWidth=20;
raw.getRange('B19:C19').values=[['Control from rules.yaml','Value']];header(raw,'B19:C19');
raw.getRange('B20:C24').values=[['Day basis',input.rules.calendar.days_per_year],['USD millions per billion',input.rules.publication.unit_scale_millions_per_billion],['Materiality versus midpoint',input.rules.guidance.midpoint_materiality_pct],['Near-zero denominator',input.rules.guidance.zero_denominator_tolerance],['Basis-point scale',input.rules.publication.basis_point_scale]];
raw.getRange('C20:C24').format.font.color='#0000FF';
raw.getRange('C22').format.numberFormat=pct;
v(raw,'B27','Public-source register');raw.getRange('B27').format.font.bold=true;
const sources=[
 ['FY2026 10-K','https://www.sec.gov/Archives/edgar/data/104169/000010416926000055/wmt-20260131.htm','Income statement p52. Balance sheet p54. Cash flow p56.'],
 ['FY2024 10-K','https://www.sec.gov/Archives/edgar/data/104169/000010416924000056/wmt-20240131.htm','FY2023 opening balances for average working capital.'],
 ['FY2025 initial guidance','https://www.sec.gov/Archives/edgar/data/104169/000010416924000019/earningsreleasefy24q4.htm','Guidance p5. FY24 adjusted operating income baseline p13.'],
 ['FY2025 results','https://www.sec.gov/Archives/edgar/data/104169/000010416925000010/earningsreleasefy25q4.htm','Constant currency p13. Adjusted operating income p14. EPS p16.']
];
for(let i=0;i<sources.length;i++){v(raw,`B${29+i*3}`,sources[i][0]);v(raw,`C${29+i*3}`,sources[i][1]);v(raw,`C${30+i*3}`,sources[i][2]);}
v(raw,'B43','Comparison calculations');
v(raw,'B44','FY25 net sales growth (cc)');v(raw,'C44',677736);v(raw,'D44',642637);f(raw,'E44','=C44/D44-1');
v(raw,'B45','FY25 adjusted OI growth (cc)');v(raw,'C45',29746);v(raw,'D45',27105);f(raw,'E45','=C45/D45-1');
v(raw,'B46','FY25 capex / net sales');f(raw,'E46','=Inputs!H8/Inputs!C8');
// Capex is column G, not H: preserve source schema and use direct owning cells.
f(raw,'E46','=G8/C8');
raw.getRange('E44:E46').format.numberFormat='0.00%';
v(raw,'B49','Growth guidance and actuals use matching currency and adjustment bases.');
v(raw,'B50','Capex above guidance requires capital-allocation review.');
v(raw,'B51','Source data is an offline snapshot. No automatic refresh or synthetic fallback.');
raw.freezePanes.freezeRows(5);

title(calc,'B2','Performance and cash calculations');
v(calc,'B3','USD millions unless stated. Ratios use net sales and cost of sales consistently.');
calc.getRange('B5:M5').values=[['Fiscal year','Net sales ($bn)','Operating margin','Operating cash ($bn)','Capex ($bn)','Free cash ($bn)','Net sales growth','DSO days','DIO days','DPO days','Cash cycle days','Capex / net sales']];header(calc,'B5:M5');
calc.getRange('B5:M5').format.rowHeight=46;
for(let r=6;r<=9;r++){
 const rr=r;
 const values=[`='Inputs'!B${rr}`,`='Inputs'!C${rr}/'Inputs'!$C$21`,`='Inputs'!E${rr}/'Inputs'!C${rr}`,r===6?'="n.a."':`='Inputs'!F${rr}/'Inputs'!$C$21`,r===6?'="n.a."':`='Inputs'!G${rr}/'Inputs'!$C$21`,r===6?'="n.a."':`=E${r}-F${r}`,r===6?'="n.a."':`='Inputs'!C${rr}/'Inputs'!C${rr-1}-1`,r===6?'="n.a."':`=AVERAGE('Inputs'!H${rr-1}:H${rr})/'Inputs'!C${rr}*'Inputs'!$C$20`,r===6?'="n.a."':`=AVERAGE('Inputs'!I${rr-1}:I${rr})/'Inputs'!D${rr}*'Inputs'!$C$20`,r===6?'="n.a."':`=AVERAGE('Inputs'!J${rr-1}:J${rr})/'Inputs'!D${rr}*'Inputs'!$C$20`,r===6?'="n.a."':`=I${r}+J${r}-K${r}`,r===6?'="n.a."':`='Inputs'!G${rr}/'Inputs'!C${rr}`];
 calc.getRange(`B${r}:M${r}`).formulas=[values];
}
calc.getRange('C6:G9').format.numberFormat='0.00';
calc.getRange('D6:D9').format.numberFormat=pct;calc.getRange('H6:H9').format.numberFormat=pct;calc.getRange('I6:L9').format.numberFormat='0.000';calc.getRange('M6:M9').format.numberFormat='0.00%';
calc.getRange('B13:H13').values=[['FY25 initial guidance','Low','High','Midpoint','Actual','Variance','Position']];header(calc,'B13:H13');
for(let i=0;i<4;i++){
 const r=14+i,s=13+i;
 calc.getRange(`B${r}:H${r}`).formulas=[[`='Inputs'!B${s}`,`='Inputs'!C${s}`,`='Inputs'!D${s}`,`=AVERAGE(C${r}:D${r})`,`='Inputs'!E${s}`,`=F${r}-E${r}`,`=IF(F${r}>D${r},"ABOVE",IF(F${r}<C${r},"BELOW","WITHIN"))`]];
 calc.getRange(`C${r}:G${r}`).format.numberFormat=i===2?'0.00':'0.00%';
}
v(calc,'B20','Working-capital definitions');
v(calc,'B21','DSO = average net receivables / net sales × day basis.');
v(calc,'B22','DIO = average inventory / cost of sales × day basis.');
v(calc,'B23','DPO = average payables / cost of sales × day basis.');
v(calc,'B24','Cash cycle = DSO + DIO − DPO. This is a derived measure.');
v(calc,'B27','FY25 net sales growth uses $677,736m constant-currency sales / $642,637m reported baseline.');
v(calc,'B28','FY25 adjusted OI growth uses $29,746m / $27,105m adjusted baseline.');
v(calc,'B29','Percentage-metric variances are percentage-point differences. EPS variance is USD per share.');
v(calc,'B31','Independent reconciliation');
v(calc,'B32','FY26 free cash flow difference');f(calc,'C32',`=G9-14923/'Inputs'!$C$21`);
v(calc,'B33','FY25 net sales growth difference');f(calc,'C33',"=F14-'Inputs'!E44");
v(calc,'B34','FY25 adjusted OI growth difference');f(calc,'C34',"=F15-'Inputs'!E45");
v(calc,'B35','FY25 capex ratio difference');f(calc,'C35',"=F17-'Inputs'!E46");
calc.getRange('C32:C35').format.numberFormat='0.000000';
calc.getRange('C32:C35').format.font.color=navy;
calc.getRange('B39:F39').values=[['Fiscal year','Operating cash','Capex','Free cash','Cash cycle days']];header(calc,'B39:F39');
for(let i=0;i<3;i++){let r=40+i,s=7+i;calc.getRange(`B${r}:F${r}`).formulas=[[`="FY"&B${s}`,`=E${s}`,`=F${s}`,`=G${s}`,`=L${s}`]];}
calc.getRange('C40:F42').format.numberFormat='0.000';
calc.freezePanes.freezeRows(5);

title(dash,'B2','Walmart performance and cash dashboard');
v(dash,'B3','FY2024–FY2026 actuals and FY2025 initial public guidance. Independent portfolio by Muhammad Jawad, ACA/ACCA.');
dash.getRange('B4:O4').format.borders={bottom:{style:'thin',color:teal}};
for(const [cell,label,formula,format] of [
 ['B6','FY26 net sales ($bn)',"='Analysis'!C9",'0.0'],
 ['E6','Operating margin',"='Analysis'!D9",pct],
 ['I6','Operating cash ($bn)',"='Analysis'!E9",'0.0'],
 ['M6','Free cash flow ($bn)',"='Analysis'!G9",'0.0']
]){v(dash,cell,label);const target=cell.replace('6','8');f(dash,target,formula);dash.getRange(target).format.font={name:'Arial',size:22,bold:true,color:navy};dash.getRange(target).format.numberFormat=format;}
v(dash,'B10','Net sales growth');f(dash,'D10',"='Analysis'!H9");dash.getRange('D10').format.numberFormat=pct;
v(dash,'I10','Cash cycle (days)');f(dash,'L10',"='Analysis'!L9");dash.getRange('L10').format.numberFormat='0.000';
function chart(type,ranges,title,start,end,format,colors){
 const c=dash.charts.add(type,ranges);c.title=title;c.titleTextStyle.typeface='Arial';c.titleTextStyle.fontSize=14;
 c.setPosition(start,end);c.xAxis={axisType:'textAxis',textStyle:{typeface:'Arial',fontSize:11}};
 c.yAxis={numberFormatCode:format,numberFormatSourceLinked:false,textStyle:{typeface:'Arial',fontSize:11}};
 c.hasLegend=ranges.length>2;c.legend={position:'bottom',textStyle:{typeface:'Arial',fontSize:11}};
 c.series.items.forEach((s,i)=>{s.fill=colors[i%colors.length];if(type==='line')s.line={fill:colors[i%colors.length],style:'solid',width:2};});
 return c;
}
chart('line',[calc.getRange('B5:B9'),calc.getRange('C5:C9')],'Net sales ($bn)','B12','H26','0',[teal]);
chart('bar',[calc.getRange('B39:B42'),calc.getRange('C39:C42'),calc.getRange('D39:D42'),calc.getRange('E39:E42')],'Operating cash, capex and free cash ($bn)','I12','P26','0',[navy,'#86B6B0',teal]);
v(dash,'B28','FY25 initial public guidance comparison');dash.getRange('B28').format.font.bold=true;
dash.getRange('B30:F30').values=[['Metric','Low','High','Actual','Position']];header(dash,'B30:F30');
for(let i=0;i<4;i++){
 const r=31+i,s=14+i;
 dash.getRange(`B${r}:F${r}`).formulas=[[`='Analysis'!B${s}`,`='Analysis'!C${s}`,`='Analysis'!D${s}`,`='Analysis'!F${s}`,`='Analysis'!H${s}`]];
 dash.getRange(`C${r}:E${r}`).format.numberFormat=i===2?'0.00':'0.00%';
}
dash.getRange('F34').conditionalFormats.add('containsText',{text:'ABOVE',format:{fill:amber,font:{bold:true,color:'#805C00'}}});
v(dash,'B37','Capex above guidance requires a capital-allocation review.');
v(dash,'B38','Growth rows use constant currency. Operating income is adjusted.');
v(dash,'B40','Review focus');dash.getRange('B40').format.font.bold=true;
v(dash,'B41','Compare margin growth with sales growth.');
v(dash,'B42','Review cash generation alongside reinvestment.');
v(dash,'B43','Investigate the drivers of the cash-conversion cycle.');
chart('line',[calc.getRange('B39:B42'),calc.getRange('F39:F42')],'Cash-conversion cycle (days)','I29','P44','0.0',[teal]);
v(dash,'B46','Public-data demonstration. No internal Walmart budget or employer/client data.');
v(dash,'B47','Historical scope. Forecast and valuation modules remain separate modelling demonstrations.');
dash.getRange('B46:P47').format.font={name:'Arial',size:10,italic:true,color:gray};
wb.recalculate();
const baseline=calc.getRange('L9').values[0][0];
raw.getRange('C20').values=[[input.rules.calendar.days_per_year*2]];wb.recalculate();
const changed=calc.getRange('L9').values[0][0];
if(Math.abs(changed-2*baseline)>1e-8)throw Error('Day-basis recalculation failed');
raw.getRange('C20').values=[[input.rules.calendar.days_per_year]];wb.recalculate();
const actualGrowth=calc.getRange('F14').values[0][0];
if(Math.abs(actualGrowth-input.guidance[0].actual)>1e-8)throw Error('Guidance formula differs from Python');
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'Final formula scan'});
await fs.writeFile(path.join(output,'workbook_inspection.txt'),errors.ndjson);
for(const [sh,range] of [[dash,'A1:P48'],[calc,'A1:N44'],[raw,'A1:N51']]){
 const preview=await wb.render({sheetName:sh.name,range,scale:1.5,format:'png'});
 await fs.writeFile(path.join(output,`${sh.name.toLowerCase()}_preview.png`),new Uint8Array(await preview.arrayBuffer()));
}
const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(path.join(output,'Walmart_FPA_Decision_Dashboard.xlsx'));
await fs.writeFile(path.join(output,'workbook_validation.json'),JSON.stringify({day_basis_original:baseline,day_basis_doubled:changed,python_guidance_growth:input.guidance[0].actual,excel_guidance_growth:actualGrowth,chart_count:dash.charts.items.length},null,2));
console.log(JSON.stringify({workbook:'Walmart_FPA_Decision_Dashboard.xlsx',cash_cycle_days:baseline,guidance_growth:actualGrowth,charts:dash.charts.items.length}));
