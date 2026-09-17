import json, os, subprocess, hashlib
from pathlib import Path
from registry_loader import load_registry

ROLE=os.getenv('ROLE','UNKNOWN_ROLE')
MODEL=os.getenv('MODEL','huggingface-projects/llama-3.2-3B-Instruct')
mission=Path('MISSION.md').read_text(encoding='utf-8')
registry_context, registry_state = load_registry(['constitution','macrograins','disciplines','keys','banks'])
prompt=f'''You are {ROLE} in CEREBRON Omega Farm 38 Contradiction Resolution.\n\n{mission}\n\nShared CEREBRON registry context (guidance only; not self-certifying evidence):\n{registry_context}\n\nAnalyze rigorously. Do not erase disagreements by averaging. Distinguish genuine contradiction from differences in definition, scale, time, state, evidence, or model assumptions.'''
PREFERRED=['/generate','/chat','/predict','/respond','/infer','/run']

def run(cmd,timeout=240): return subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
def payload_for(spec):
 p={}; set_prompt=False
 for x in spec.get('parameters',[]):
  n=x.get('name',''); l=n.lower(); req=bool(x.get('required',False)); default=x.get('default'); typ=(x.get('type') or {}).get('type')
  if l in {'message','prompt','text','query','input','instruction','user_message'}: p[n]=prompt; set_prompt=True
  elif l in {'chat_history','history','messages'}: p[n]=[]
  elif l in {'max_new_tokens','max_tokens','maximum_new_tokens'}: p[n]=800
  elif l=='temperature': p[n]=0.1
  elif l=='top_p': p[n]=0.9
  elif l=='top_k': p[n]=40
  elif req and default is None:
   if typ=='string' and not set_prompt: p[n]=prompt; set_prompt=True
   else: return None
 return p if set_prompt else None

def extract(raw):
 raw=raw.strip()
 try:
  o=json.loads(raw)
  if isinstance(o,dict):
   for k in ('Response','response','text','output','message'):
    if isinstance(o.get(k),str): return o[k].strip()
 except: pass
 return raw

out={'farm':38,'role':ROLE,'model':MODEL,'inference_success':False,'status':'EXTERNAL_INFERENCE_FAILED','registry_runtime':registry_state}
try:
 info=run(['hf-gradio','info',MODEL],120)
 if info.returncode!=0: raise RuntimeError(info.stderr or info.stdout)
 api=json.loads(info.stdout); eps=list(api.items()); eps.sort(key=lambda kv:(PREFERRED.index(kv[0]) if kv[0] in PREFERRED else 99,kv[0]))
 errors=[]
 for ep,spec in eps:
  payload=payload_for(spec)
  if payload is None: continue
  pred=run(['hf-gradio','predict',MODEL,ep,json.dumps(payload,ensure_ascii=False)],240)
  if pred.returncode==0 and pred.stdout.strip():
   text=extract(pred.stdout)
   if text:
    out.update({'inference_success':True,'status':'UNREVIEWED_EXTERNAL_AGENT_OUTPUT','endpoint':ep,'output':text,'sha256':hashlib.sha256(text.encode()).hexdigest()}); break
  errors.append((ep,pred.stderr or pred.stdout))
 if not out['inference_success']: out['error']=repr(errors[-3:])
except Exception as e: out['error']=repr(e)
Path('results').mkdir(exist_ok=True)
Path(f'results/{ROLE}.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'role':ROLE,'status':out['status'],'inference_success':out['inference_success'],'registry_runtime':registry_state},ensure_ascii=False))