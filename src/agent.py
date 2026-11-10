"""Extractive knowledge QA with bounded model-driven retrieval and citation guards."""
import argparse,copy,json,re,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def topic_for(text,catalog):
    for topic,terms in catalog['aliases'].items():
        if any(term.lower() in text.lower() for term in terms):return topic
    return None

def resolve_topic(request,catalog):
    question=request['question'];topic=topic_for(question,catalog)
    if topic:return topic
    # Only explicit short follow-ups inherit topic; never inherit asserted facts.
    if any(x in question for x in ('那','多久','具体','这个','天呢','how long','what about')):
        for msg in reversed(request.get('history',[])):
            if isinstance(msg,dict) and msg.get('role')=='user':
                topic=topic_for(str(msg.get('content','')),catalog)
                if topic:return topic
    return None

class Tools:
    def __init__(self,request,catalog,failure='none'):
        self.request,self.catalog,self.failure=request,catalog,failure
        self.topic=resolve_topic(request,catalog)
        self.state={'topic':self.topic,'searches':[],'candidates':{},'read':{},'tool_errors':[]}
        self.failed_once=False
    def call(self,action,args):
        schemas={'search_documents':{'query'},'read_excerpt':{'doc_id'},'respond':{'disposition','doc_ids'}}
        if action not in schemas or set(args)!=schemas[action]:return {'error':'invalid_tool_or_arguments'}
        if action=='respond':
            if args['disposition'] not in ('answer','conflict','insufficient') or not isinstance(args['doc_ids'],list) or any(not isinstance(x,str) for x in args['doc_ids']):return {'error':'invalid_response_arguments'}
            return self.respond(**args)
        if any(not isinstance(v,str) for v in args.values()):return {'error':'invalid_arguments'}
        fail=self.failure=='search_always' and action=='search_documents' or self.failure=='read_always' and action=='read_excerpt' or self.failure=='search_once' and action=='search_documents' and not self.failed_once
        if fail:
            self.failed_once=True;result={'error':'tool_unavailable','tool':action,'retryable':self.failure=='search_once'};self.state['tool_errors'].append(result);return result
        return getattr(self,action)(**args)
    def search_documents(self,query):
        topic=topic_for(query,self.catalog)
        docs=[d for d in self.catalog['documents'] if d['topic']==topic] if topic else []
        results=[{k:d[k] for k in ('id','version_date','title','topic')} for d in docs]
        self.state['searches'].append({'query':query,'results':results})
        self.state['candidates'].update({d['id']:d for d in results})
        return {'results':results,'truncated':False,'query_topic':topic}
    def read_excerpt(self,doc_id):
        if doc_id not in self.state['candidates']:return {'error':'search_before_read'}
        doc=next(d for d in self.catalog['documents'] if d['id']==doc_id)
        evidence={k:doc[k] for k in ('id','version_date','title','topic','text')}
        self.state['read'][doc_id]=evidence
        return evidence
    def respond(self,disposition,doc_ids):
        if len(doc_ids)!=len(set(doc_ids)):return {'error':'duplicate_citations'}
        if disposition=='insufficient':
            if not self.state['searches'] and not self.state['tool_errors']:return {'error':'search_required'}
            return {'finished':True,'status':'needs_information','answer':'现有资料不足，无法可靠回答。请补充适用制度、产品资料或明确问题；工具故障时可稍后重试。','citations':[],'gaps':['tool_failure' if self.state['tool_errors'] else 'no_reliable_evidence']}
        if not self.topic:return {'error':'unresolved_question_topic','message':'Clarify the question; do not answer a different topic.'}
        relevant=[d['id'] for d in self.catalog['documents'] if d['topic']==self.topic]
        if not relevant:return {'error':'no_evidence'}
        unread=[d for d in relevant if d not in self.state['read']]
        if unread:return {'error':'incomplete_evidence','message':'Search the question topic and read every matching candidate before answering.'}
        if set(doc_ids)!=set(relevant):return {'error':'citation_coverage','message':'Cite all relevant read documents; do not hide conflicts.'}
        evidence=[self.state['read'][d] for d in doc_ids]
        # Strict conservative conflict check: no assumed scope/priority; date alone never resolves it.
        values={re.sub(r'\s+','',d['text']) for d in evidence}
        conflict=len(values)>1
        if conflict and disposition!='conflict':return {'error':'conflicting_evidence','message':'State the conflict and request the applicable policy; never choose by date.'}
        if not conflict and disposition!='answer':return {'error':'no_conflict_found'}
        citations=[{'doc_id':d['id'],'version_date':d['version_date'],'quote':d['text']} for d in evidence]
        quoted='；'.join(f"{c['doc_id']}（{c['version_date']}）：{c['quote']}" for c in citations)
        return {'finished':True,'status':'needs_confirmation' if conflict else 'answered','answer':('资料存在冲突：'+quoted+'。未提供适用范围或优先级，请确认应适用哪份制度；不能擅自选择。') if conflict else '依据已读取资料：'+quoted,'citations':citations,'gaps':['applicable_scope','policy_priority'] if conflict else []}

class MockModel:
    mode='mock';model='scripted-test-double'
    def decide(self,context,history):
        state=context['state'];topic=state['topic'];action,args='search_documents',{'query':context['request']['question']}
        if history and history[-1]['observation'].get('error')=='tool_unavailable':
            if history[-1]['observation']['retryable']:return {'action':history[-1]['action'],'arguments':history[-1]['arguments'],'decision_summary':'Offline: retry transient tool error.'}
            action,args='respond',{'disposition':'insufficient','doc_ids':[]}
        elif state['searches']:
            ids=[d for d,e in state['candidates'].items() if e['topic']==topic]
            if not ids and topic and len(state['searches'])<2:action,args='search_documents',{'query':context['aliases'][topic][0]}
            elif not ids:action,args='respond',{'disposition':'insufficient','doc_ids':[]}
            else:
                unread=[d for d in ids if d not in state['read']]
                if unread:action,args='read_excerpt',{'doc_id':unread[0]}
                else:action,args='respond',{'disposition':'conflict' if len({state['read'][d]['text'] for d in ids})>1 else 'answer','doc_ids':ids}
        return {'action':action,'arguments':args,'decision_summary':'Offline scripted policy; not real model evidence.'}

def run(request,catalog,model,max_steps=12,failure='none'):
    if not isinstance(request.get('question'),str) or not request['question'].strip():return {'status':'needs_information','answer':'请提供问题。','citations':[],'gaps':['question'],'trace':[],'model_mode':model.mode}
    if not isinstance(request.get('history',[]),list):raise ValueError('history must be a list')
    if max_steps<1:raise ValueError('max_steps must be positive')
    tools=Tools(request,catalog,failure);trace=[];final={'status':'incomplete','reason':'limit_reached','answer':'执行达到上限，尚未形成可验证回答。','citations':[],'gaps':['execution_limit']}
    for step in range(1,max_steps+1):
        context={'request':request,'state':copy.deepcopy(tools.state),'aliases':catalog['aliases']}
        try:
            d=model.decide(context,trace)
            if not isinstance(d,dict) or not isinstance(d.get('action'),str) or not isinstance(d.get('arguments'),dict) or not isinstance(d.get('decision_summary'),str) or not d['decision_summary'].strip():raise ValueError('invalid_decision')
        except Exception as e:
            observation=getattr(e,'details',{'error':type(e).__name__});trace.append({'step':step,'action':'model_error','arguments':{},'observation':observation,'decision_summary':'No valid decision.'});final.update(reason='model_error',gaps=['model_error']);break
        observation=tools.call(d['action'],d['arguments'])
        trace.append({'step':step,'action':d['action'],'arguments':d['arguments'],'observation':observation,'decision_summary':d['decision_summary'][:500],'model_response':getattr(model,'last_meta',{})})
        if observation.get('finished'):final={k:v for k,v in observation.items() if k!='finished'};break
    for i,e in enumerate(trace):e['next_action']=trace[i+1]['action'] if i+1<len(trace) else 'stop:'+final['status']
    return {**final,'timestamp':datetime.now(timezone.utc).isoformat(),'model_mode':model.mode,'model':model.model,'tool_mode':'local_synthetic','max_steps':max_steps,'steps_used':len(trace),'state':tools.state,'trace':trace}

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--data',default=str(ROOT/'data/documents.json'));p.add_argument('--mode',choices=['mock','live'],default='mock');p.add_argument('--output',default='answer.json');p.add_argument('--max-steps',type=int,default=12);p.add_argument('--failure',choices=['none','search_once','search_always','read_always'],default='none');a=p.parse_args()
    try:
        from src.model import LiveModel
        result=run(json.loads(Path(a.input).read_text()),json.loads(Path(a.data).read_text()),LiveModel() if a.mode=='live' else MockModel(),a.max_steps,a.failure)
    except Exception as e:print(json.dumps(getattr(e,'details',{'error':type(e).__name__}),ensure_ascii=False));return 2
    Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('status','answer','citations','gaps')},ensure_ascii=False,indent=2))
    return 2 if result['status']=='incomplete' else 0
if __name__=='__main__':sys.exit(main())
