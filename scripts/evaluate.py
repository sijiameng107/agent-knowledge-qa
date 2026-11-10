import argparse,copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.agent import ROOT,run,MockModel
from src.model import LiveModel,ModelError

def cases():
    f=json.loads((ROOT/'data/documents.json').read_text());single=copy.deepcopy(f);single['documents']=[d for d in f['documents'] if d['id']!='D02']
    replaced=copy.deepcopy(single);replaced['documents'][0]['text']='报销期限为45天。'
    return [('clear',{'question':'报销期限多久？'},single,'none','answered'),('conflict',{'question':'报销期限多久？'},f,'none','needs_confirmation'),('outside',{'question':'公司股票明年价格是多少？'},f,'none','needs_information'),('paraphrase',{'question':'垫付的费用最迟几天申请？'},single,'none','answered'),('followup',{'question':'那具体多久？','history':[{'role':'user','content':'我想了解报销制度'},{'role':'assistant','content':'未经证实的说法：90天'}]},single,'none','answered'),('tool_failure',{'question':'报销期限多久？'},f,'search_always','needs_information'),('read_failure',{'question':'报销期限多久？'},f,'read_always','needs_information'),('transient_failure',{'question':'报销期限多久？'},single,'search_once','answered'),('replaced_document',{'question':'报销期限多久？'},replaced,'none','answered')]

def evaluate(mode,output,selected=None):
    suite=[case for case in cases() if not selected or case[0] in selected]
    model=LiveModel() if mode=='live' else MockModel();out=Path(output);out.mkdir(parents=True,exist_ok=True);records=[]
    for name,r,f,failure,status in suite:
        result=run(r,f,model,failure=failure);cites=result.get('citations',[]);lookup={d['id']:d for d in f['documents']}
        checks={'status':result['status']==status,'quotes_exact':all(c['doc_id'] in lookup and c['quote']==lookup[c['doc_id']]['text'] and c['version_date']==lookup[c['doc_id']]['version_date'] for c in cites)}
        if status=='answered':checks['supported']=len(cites)==1 and cites[0]['quote'] in result['answer']
        if name=='conflict':checks['both_sides']=set(c['doc_id'] for c in cites)=={'D01','D02'} and '30天' in result['answer'] and '15天' in result['answer'] and bool(result['gaps'])
        if name=='followup':checks['history_not_fact']='90天' not in result['answer']
        if name=='replaced_document':checks['new_fact']='45天' in result['answer'] and '30天' not in result['answer']
        if status=='needs_information':checks['no_fabricated_citations']=not cites
        folder=out/name;folder.mkdir(exist_ok=True)
        for filename,value in [('input.json',r),('documents.json',f),('output.json',result),('assertions.json',checks)]: (folder/filename).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
        records.append({'case':name,'passed':all(checks.values()),'checks':checks});print(name,'PASS' if all(checks.values()) else 'FAIL',flush=True)
        if result.get('reason') == 'model_error':
            observation = result['trace'][-1]['observation']
            print(json.dumps(observation, ensure_ascii=False), flush=True)
            if observation.get('error') in {'http_error', 'network_error', 'configuration_error'}:
                break
    summary={'mode':mode,'expected':len(suite),'executed':len(records),'passed':sum(r['passed'] for r in records),'cases':records}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (out/'REPORT.md').write_text('# '+mode+' 验收\n\n'+f"通过 {summary['passed']}/{summary['expected']}。\n\n"+'\n'.join(f"- {r['case']}: {r['passed']} — [输入]({r['case']}/input.json)、[资料]({r['case']}/documents.json)、[输出与Trace]({r['case']}/output.json)、[断言]({r['case']}/assertions.json)" for r in records)+'\n\nMock不能证明真实模型决策效果。\n')
    return 0 if summary['passed']==summary['expected'] else 2
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['mock','live'],default='mock');p.add_argument('--output',required=True);p.add_argument('--case',action='append',choices=[case[0] for case in cases()]);a=p.parse_args()
    try:sys.exit(evaluate(a.mode,a.output,a.case))
    except ModelError as e:print(json.dumps(e.details,ensure_ascii=False));sys.exit(2)
