"""Cinematic LabRepair edit: motivated shots, real UI, labeled illustration.

Readonly sources are the existing browser capture and user-supplied animations.
No browser automation, provider call, candidate execution or paid API is used.
"""
from __future__ import annotations
import argparse,hashlib,json,math,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent/'nebius-labrepair';OLD=ROOT.parent/'nebius-demo-20261029'
sys.path[:0]=[str(REPO/'.test-tmp/media-tools'),str(ROOT.parent/'nebius-demo-20261027/tools')]
import numpy as np
import soundfile as sf
from PIL import Image,ImageDraw,ImageFont,ImageOps
import imageio_ffmpeg
FF=imageio_ffmpeg.get_ffmpeg_exe();W,H=1920,1080
SPEC=json.loads((ROOT/'narration.json').read_text(encoding='utf-8-sig'))
DURATION=sum(scene['duration'] for scene in SPEC['scenes'])
SESSION=json.loads((OLD/'recording/session.json').read_text(encoding='utf-8-sig'))
INK='#0B151A';PANEL='#16272C';WHITE='#F1F5F0';TEAL='#72D6BD';MUTED='#9BAFAE';RED='#EF9B87';AMBER='#E9C476';PAPER='#F4F5EF'
for n in ['frames','clips','temp','qa']:(ROOT/n).mkdir(exist_ok=True)
FONTROOT=Path('C:/Windows/Fonts');FC={};UI_CACHE={}
def font(size=42,bold=False,mono=False):
 k=(size,bold,mono)
 if k not in FC:FC[k]=ImageFont.truetype(str(FONTROOT/('consola.ttf' if mono else 'seguisb.ttf' if bold else 'segoeui.ttf')),size)
 return FC[k]
def txt(d,xy,value,size=42,color=WHITE,bold=False,mono=False):d.text(xy,str(value),font=font(size,bold,mono),fill=color)
def wrap(d,value,width,size=42,bold=False):
 out=[];line=''
 for word in str(value).split():
  v=(line+' '+word).strip()
  if line and d.textlength(v,font=font(size,bold))>width:out.append(line);line=word
  else:line=v
 if line:out.append(line)
 return out

def para(d,xy,value,width,size=42,color=WHITE,bold=False,gap=1.25):
 x,y=xy
 for line in wrap(d,value,width,size,bold):txt(d,(x,y),line,size,color,bold);y+=round(size*gap)
 return y

def chip(im,label,dark=True):
 d=ImageDraw.Draw(im,'RGBA');boxw=round(d.textlength(label,font=font(18,True)))+34
 d.rounded_rectangle((34,26,34+boxw,62),radius=15,fill=(11,26,29,218) if dark else (236,245,238,238))
 txt(d,(51,31),label,18,TEAL if dark else '#226C60',True)
 return im

def subtitle_band(im):
 layer=Image.new('RGBA',(W,H));a=np.zeros((H,W,4),dtype=np.uint8)
 for y in range(890,H):a[y,:,3]=round(205*min(1,(y-890)/95))
 layer=Image.fromarray(a,'RGBA');return Image.alpha_composite(im.convert('RGBA'),layer).convert('RGB')

def save(im,name):p=ROOT/'frames'/name;im.convert('RGB').save(p);return p

def protagonist_nameplate():
 im=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(im)
 label='Nora · Quantum research software engineer'
 width=round(d.textlength(label,font=font(28,True)))+38
 d.rounded_rectangle((94,100,94+width,153),radius=9,fill=(11,21,26,222))
 txt(d,(113,108),label,28,WHITE,True)
 path=ROOT/'frames/protagonist-nameplate.png';im.save(path);return path

def apply_nameplate_only():
 final=ROOT/'LabRepair_DEMO_Release_20261030.mp4'
 output=ROOT/'temp/nameplate-final.mp4';plate=protagonist_nameplate()
 subprocess.run([FF,'-hide_banner','-loglevel','error','-y','-i',str(final),'-loop','1','-i',str(plate),'-filter_complex',"[0:v]fps=25[v];[v][1:v]overlay=0:0:enable='lt(t,5)'[out]",'-map','[out]','-map','0:a:0','-c:v','libx264','-threads','4','-preset','veryfast','-crf','18','-c:a','copy','-t',str(DURATION),'-movflags','+faststart',str(output)],cwd=ROOT,check=True)
 output.replace(final)
 receipt_path=ROOT/'render_receipt.json';receipt=json.loads(receipt_path.read_text())
 receipt['movie']={'name':final.name,'bytes':final.stat().st_size,'sha256':hashlib.sha256(final.read_bytes()).hexdigest()}
 receipt['protagonist_nameplate']={'text':'Nora · Quantum research software engineer','start_seconds':0,'end_seconds':5,'character':'Illustrative protagonist'}
 receipt_path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(receipt),flush=True)

def getframes(label):
 out=[x for x in SESSION['frames'] if x['label']==label]
 if not out:raise ValueError('Missing source label '+label)
 return out

def ui_image(label,focus='context',entry=None):
 if entry is None:entry=getframes(label)[-1]
 k=(entry['file'],focus)
 if k in UI_CACHE:return UI_CACHE[k].copy()
 shot=Image.open(OLD/'recording'/entry['file']).convert('RGB')
 bounds={'context':(38,45,1224,688),'result':(47,6,1219,690),'pairs':(592,251,1208,616),
  'hold':(70,195,560,470),'tool':(600,275,1210,618),'cloud':(0,0,shot.width,shot.height),
  'model':(65,150,1210,525),'hero':(45,15,1220,650)}[focus]
 if focus=='hold' and label=='tool-record':bounds=(70,309,560,584)
 crop=shot.crop(bounds);im=ImageOps.fit(crop,(W,H),Image.Resampling.LANCZOS)
 chip(im,'Recorded run' if focus in ('cloud','model') else 'Local review',True)
 im=subtitle_band(im);UI_CACHE[k]=im;return im.copy()

def dark_canvas(label='Evidence comparison'):
 im=Image.new('RGB',(W,H),INK);d=ImageDraw.Draw(im)
 # Quiet depth, rather than a repeated bordered slide template.
 for x in range(0,W,3):
  f=x/W;col=(round(11+6*f),round(21+12*f),round(26+12*f));d.rectangle((x,0,x+2,H),fill=col)
 chip(im,label);return im

def graphic(preset,p=1.0):
 im=dark_canvas('Recorded run' if preset in ('model','parameters','protected','sandbox','runtime') else 'Evidence comparison');d=ImageDraw.Draw(im)
 if preset in ('total_one','total_two'):
  txt(d,(120,195),'Two patches.',64,WHITE,True)
  txt(d,(110,350),'2.60',188,WHITE,True,True)
  if preset=='total_two':
   alpha=min(1,max(0,p));c=tuple(round(v*alpha+INKV*(1-alpha)) for v,INKV in zip((241,245,240),(11,21,26)))
   txt(d,(1060,350),'2.60',188,c,True,True);txt(d,(825,415),'=',93,MUTED)
   txt(d,(121,705),'One is wrong. Which evidence holds?',57,WHITE,True)
  else:txt(d,(126,705),'The expected total.',53,MUTED)
 elif preset in ('pairs','pair_lines'):
  txt(d,(100,110),'The headline matches.',61,WHITE,True);txt(d,(101,194),'Every pair is different.',61,RED,True)
  refs=[.70,.65,.75,-.50];wrong=[.80,.75,.65,-.40];labels=['A0B0','A0B1','A1B0','A1B1']
  txt(d,(100,310),'REGISTERED',24,TEAL,True);txt(d,(1410,310),'WRONG REPAIR',24,RED,True)
  for i,(a,b,l) in enumerate(zip(refs,wrong,labels)):
   y=398+i*108;reveal=min(1,max(0,p*4-i));txt(d,(105,y-26),l,32,MUTED,mono=True)
   txt(d,(385,y-31),f'{a:.2f}',44,TEAL,mono=True)
   x1=630+220*(a+.5);x2=630+220*(b+.5)
   d.line((620,y+5,1285,y+5),fill='#284048',width=3)
   end=x1+(x2-x1)*reveal;d.line((x1,y+5,end,y+5),fill=RED,width=9)
   d.ellipse((x1-8,y-3,x1+8,y+13),fill=TEAL);d.ellipse((end-8,y-3,end+8,y+13),fill=RED)
   if reveal>.2:txt(d,(1450,y-31),f'{b:.2f}',44,RED,mono=True)
  txt(d,(103,875),'0 / 4 pair values match',35,RED,True)
 elif preset=='repair_verdict':
  txt(d,(112,170),'Code repair',58,MUTED);txt(d,(102,285),'2.60',176,WHITE,True,True)
  txt(d,(115,580),'PASSED',65,TEAL,True);txt(d,(117,698),'Protected checks passed.',41,MUTED)
 elif preset=='claim_verdict':
  d.line((965,170,965,835),fill='#2D4548',width=3)
  txt(d,(104,182),'Code repair',44,MUTED);txt(d,(100,303),'2.60',138,WHITE,True,True)
  txt(d,(111,551),'PASSED',55,TEAL,True)
  txt(d,(1070,182),'Original claim',44,MUTED);txt(d,(1061,303),'3.40',138,WHITE,True,True)
  txt(d,(1074,551),'NOT REPRODUCED',50,AMBER,True)
  txt(d,(110,785),'A passing repair is not a reproduced result.',49,WHITE,True)
 elif preset=='model':
  txt(d,(98,135),'NVIDIA Nemotron',77,WHITE,True);txt(d,(102,239),'on Nebius Token Factory',49,TEAL)
  nodes=[('Declared convention',105),('Typed parameters',739),('Bounded patch',1370)]
  for i,(label,x) in enumerate(nodes):
   active=p*3>=i;d.rounded_rectangle((x,424,x+450,624),radius=12,fill='#213D41' if active else PANEL)
   para(d,(x+26,469),label,405,42,WHITE if active else MUTED,True)
   if i<2:d.line((x+470,523,x+590,523),fill=TEAL if active else MUTED,width=5);d.polygon([(x+590,523),(x+573,513),(x+573,533)],fill=TEAL)
  txt(d,(109,778),'Prompt supplies the convention. Discovery is not claimed.',37,MUTED)
 elif preset=='parameters':
  txt(d,(103,146),'A small, typed proposal.',66,WHITE,True)
  txt(d,(105,327),'channel_signs',36,MUTED,mono=True);txt(d,(104,387),'[1, 1, -1, -1]',74,TEAL,mono=True)
  txt(d,(106,566),'offsets',36,MUTED,mono=True);txt(d,(104,625),'[0, 0, 0, 0]',74,TEAL,mono=True)
  txt(d,(1160,330),'121',95,WHITE,True,True);txt(d,(1168,453),'input tokens',32,MUTED)
  txt(d,(1160,582),'38',95,WHITE,True,True);txt(d,(1168,705),'output tokens',32,MUTED)
  txt(d,(110,875),'Parameters from the saved model response',28,MUTED)
 elif preset=='protected':
  txt(d,(104,150),'Change the analysis.',69,WHITE,True);txt(d,(106,250),'Keep the evidence fixed.',69,TEAL,True)
  for i,(name,status,col) in enumerate([('analysis.py','Two parameter arrays',TEAL),('counts.json','PROTECTED',WHITE),('test_analysis.py','PROTECTED',WHITE)]):
   y=435+i*142;d.line((109,y+93,1805,y+93),fill='#2D4548',width=2);txt(d,(114,y),name,44,col,mono=True);txt(d,(1090,y+8),status,31,col,True)
 elif preset=='sandbox':
  txt(d,(105,136),'Saved execution outcomes',64,WHITE,True)
  for i,(name,n,out,col) in enumerate([('Baseline','2 / 4','Expected failure',RED),('Model repair','4 / 4','Passed',TEAL),('Wrong-pair control','3 / 4','Expected rejection',RED)]):
   y=332+i*161;active=p*3>=i;txt(d,(116,y),name,43,WHITE);txt(d,(925,y-7),n,54,col if active else MUTED,True,True)
   txt(d,(1333,y+7),out,32,col if active else MUTED,True);d.line((113,y+98,1805,y+98),fill='#294147',width=2)
  txt(d,(114,886),'Protected test checks — distinct from pair-value match counts',28,MUTED)
 elif preset=='runtime':
  txt(d,(107,152),'One real disposable operation.',64,WHITE,True);txt(d,(97,307),'1.273 s',170,TEAL,True,True)
  txt(d,(115,581),'Guest networking disabled',49,WHITE,True)
  txt(d,(116,707),'Three source variants. Unchanged protected tests.',40,MUTED)
  txt(d,(118,869),'Saved run · 26 October 2026 UTC · no new dispatch',28,MUTED)
 elif preset=='receipt':
  txt(d,(100,143),'Hold for evidence.',78,WHITE,True)
  fields=[('Reviewed source','2394f56595e8a577…'),('Review intent','hold-for-evidence'),('New execution','false'),('Original claim','NOT_REPRODUCED')]
  for i,(label,value) in enumerate(fields):
   y=336+i*126;txt(d,(112,y),label,31,MUTED);txt(d,(712,y-5),value,42,TEAL if i!=3 else AMBER,mono=True)
  txt(d,(112,878),'Excerpt from the saved source-bound local receipt',28,MUTED)
 elif preset=='handover':
  txt(d,(105,143),'Leave a decision',77,WHITE,True);txt(d,(108,248),'someone else can inspect.',77,TEAL,True)
  for i,(word,detail) in enumerate([('What changed','Source and proposed parameters'),('What failed','Rejected control and check results'),('What remains','Missing evidence and human intent')]):
   x=110+i*605;d.line((x,476,x+510,476),fill=TEAL,width=4);para(d,(x,530),word,520,49,WHITE,True);para(d,(x,635),detail,520,34,MUTED)
 elif preset=='saved_response':
  response_path=REPO/'evidence/nebius-nano-repair-20261026-1/response.json'
  transport_path=response_path.parent/'cloud-transport-receipt.json'
  response=json.loads(response_path.read_text());transport=json.loads(transport_path.read_text())
  content=json.loads(response['choices'][0]['message']['content'])
  chip(im,'Saved real response · 26 Oct 2026 UTC')
  txt(d,(101,130),'NVIDIA Nemotron',68,WHITE,True);txt(d,(104,220),'Nebius Token Factory',43,TEAL)
  d.rounded_rectangle((96,318,1824,858),radius=12,fill='#102126',outline='#345451',width=2)
  lines=[('http_status',transport['http_status']),('model',response['model']),('usage.prompt_tokens',response['usage']['prompt_tokens']),('usage.completion_tokens',response['usage']['completion_tokens']),('channel_signs',content['channel_signs']),('offsets',content['offsets'])]
  for i,(key,value) in enumerate(lines):
   y=353+i*76;txt(d,(129,y),key,31,MUTED,mono=True);txt(d,(795,y),str(value),32,TEAL if i!=1 else WHITE,mono=True)
  txt(d,(108,892),'Exact fields from response.json + cloud-transport-receipt.json',25,MUTED)
 elif preset=='saved_sandbox':
  path=REPO/'evidence/nebius-sandbox-validation-20261026-1/nebius-sandbox-validation-20261026-1.operation.safe.json'
  operation=json.loads(path.read_text())
  chip(im,'Saved real receipt · 26 Oct 2026 UTC')
  txt(d,(100,135),'Nebius Sandbox',72,WHITE,True);txt(d,(105,235),'Historical operation receipt',42,TEAL)
  lines=[('status',operation['status']),('duration',str(operation['duration'])+' seconds'),('disposable',str(operation['disposable']).lower()),('networking.enabled',str(operation['networking']['enabled']).lower()),('process.exit_code',operation['process']['exit_code'])]
  for i,(key,value) in enumerate(lines):
   y=363+i*94;d.line((105,y+76,1810,y+76),fill='#294147',width=2);txt(d,(111,y),key,35,MUTED,mono=True);txt(d,(1060,y),value,42,TEAL,True,True)
  txt(d,(109,889),'operation.safe.json · uuid '+operation['uuid'][:8]+'… · no new dispatch',27,MUTED)
 elif preset in ('limits_real','limits_not'):
  real=preset=='limits_real';txt(d,(108,139),'What is real' if real else 'What this does not establish',71,TEAL if real else AMBER,True)
  lines=['Saved Nemotron response on Token Factory','Recorded isolated Sandbox execution','Inspectable pair checks and human intent'] if real else ['No physical quantum experiment','No autonomous discovery of the convention','No approval of the original 3.40 claim']
  for i,line in enumerate(lines):txt(d,(116,360+i*148),line,49,WHITE,True)
  txt(d,(116,869),'One synthetic case · curated local controls · historical cloud evidence',29,MUTED)
 elif preset=='action_close':
  txt(d,(104,195),'Try the wrong-pair case.',91,WHITE,True);txt(d,(109,326),'Inspect the evidence. Then decide.',60,TEAL,True)
  txt(d,(113,540),'github.com/mangroveuniversemu-bot/nebius-labrepair',40,WHITE,True,True)
  txt(d,(113,632),'Private review build',34,MUTED)
  txt(d,(113,831),'LabRepair · Repair the analysis. Preserve the evidence.',37,MUTED)
 elif preset=='close_brand':
  txt(d,(106,268),'LabRepair',133,WHITE,True);txt(d,(117,493),'Evidence before acceptance.',58,TEAL)
 elif preset=='close_line':
  txt(d,(108,240),'Repair the analysis.',95,WHITE,True);txt(d,(108,383),'Preserve the evidence.',95,TEAL,True)
  txt(d,(114,663),'A passing repair is not a reproduced result.',43,MUTED)
 return subtitle_band(im)


def illustration_overlay(preset):
 im=Image.new('RGBA',(W,H));arr=np.zeros((H,W,4),np.uint8)
 for x in range(W):arr[:,x,3]=round(218*max(0,1-x/1600))
 im=Image.fromarray(arr,'RGBA');d=ImageDraw.Draw(im)
 if preset=='question':
  txt(d,(95,305),'Two patches.',84,WHITE,True)
  txt(d,(95,415),'Same total.',84,WHITE,True)
  txt(d,(95,525),'One is wrong.',84,WHITE,True)
 elif preset=='question_close':
  txt(d,(101,440),'A repair is ready.',66,WHITE,True);txt(d,(104,543),'The decision is not.',66,TEAL,True)
 elif preset=='person_return':
  txt(d,(93,319),'What changed.',74,WHITE,True);txt(d,(93,424),'What failed.',74,WHITE,True);txt(d,(93,529),'What needs evidence.',74,TEAL,True)
 chip(im,'Illustration',True)
 # Permanent caption region is dark enough for a single consistent subtitle style.
 band=Image.new('RGBA',(W,H));bd=ImageDraw.Draw(band);bd.rectangle((0,974,W,H),fill=(0,0,0,150));im=Image.alpha_composite(im,band)
 return im


def plan():
 # Each tuple is a motivated shot, not an arbitrary duplicate slide.
 groups=[
 ('01_question',[(5,'illustration','question','clip-01.mp4',0)]),
 ('02_hook',[(4,'kinetic','total_two',None,None)]),
 ('03_wrong',[(2,'ui','wrong-select','context','last'),(3,'ui','wrong-run','context','record'),(5,'ui','wrong-result','result','record')]),
 ('04_difference',[(5,'kinetic','pairs',None,None),(6,'ui','wrong-evidence','pairs','last')]),
 ('05_repair',[(2,'ui','valid-select','context','last'),(3,'ui','valid-run','context','record'),(4,'ui','valid-result','result','record')]),
 ('07_model',[(8,'graphic','saved_response',None,None),(4,'kinetic','model',None,None),(4,'graphic','protected',None,None)]),
 ('08_sandbox',[(4,'ui','saved-detail','cloud','last'),(4,'graphic','saved_sandbox',None,None),(5,'kinetic','sandbox',None,None)]),
 ('06_claim',[(3,'graphic','repair_verdict',None,None),(6,'graphic','claim_verdict',None,None)]),
 ('09_unknown',[(3,'ui','unknown-select','context','last'),(3,'ui','unknown-run','context','record'),(6,'ui','unknown-result','result','record')]),
 ('10_handover',[(3,'ui','hold','hold','record'),(3,'ui','tool-record','tool','record'),(4,'graphic','receipt',None,None),(4,'graphic','handover',None,None)]),
 ('11_person',[(6,'graphic','limits_real',None,None),(7,'graphic','limits_not',None,None)]),
 ('12_close',[(7,'graphic','action_close',None,None)])]
 scenes={s['id']:s for s in SPEC['scenes']};shots=[];time=0
 for sid,items in groups:
  assert sum(x[0] for x in items)==scenes[sid]['duration'],sid
  for dur,kind,preset,source,mode in items:
   shots.append({'id':f'shot-{len(shots)+1:02d}','scene':sid,'start_seconds':time,'duration_seconds':dur,'end_seconds':time+dur,'kind':kind,'preset':preset,'source':source,'mode':mode})
   time+=dur
 assert time==DURATION==123
 return shots


def media_frame(asset,t,out,overlay_preset):
 # Read the same plainly labeled illustrative footage used in the animated shot.
 vf=illustration_filter(asset,overlay_preset)
 subprocess.run([FF,'-hide_banner','-loglevel','error','-y','-ss',str(t),'-i',str(OLD/'inputs'/asset),'-filter_complex',vf+'[masked]','-map','[masked]','-frames:v','1',str(out)],check=True)
 im=Image.open(out).convert('RGBA');return Image.alpha_composite(im,illustration_overlay(overlay_preset)).convert('RGB')

def illustration_filter(asset,preset=None):
 # Fictional workstation context is visibly labeled Illustration, never evidence.
 return '[0:v]scale=1920:1080'


def preview(shot):
 if shot['kind']=='illustration':
  im=media_frame(shot['source'],shot['mode']+shot['duration_seconds']/2,ROOT/'temp'/(shot['id']+'-raw.jpg'),shot['preset'])
  if shot['start_seconds']<5:im=Image.alpha_composite(im.convert('RGBA'),Image.open(protagonist_nameplate())).convert('RGB')
  return im
 if shot['kind']=='ui':return ui_image(shot['preset'],shot['source'])
 return graphic(shot['preset'],.8)


def write_timeline(shots):
 data={'schema':'LABREPAIR_CINEMATIC_TIMELINE_V1','duration_seconds':DURATION,'source_ui_commit':'a7cf2f5629975a00511beadd9e2a90eac3349a52','source_repo_head_observed':'103d3ca','source_session':'../nebius-demo-20261029/recording/session.json','shot_count':len(shots),'shots':shots,'boundaries':['Illustrations are not customers, physical measurements or application evidence.','Actual UI is edited replay from timestamped captured frames; no new provider call.','Wrong-first story order is an edit; source capture order is preserved in raw session.','Local pair values and recorded protected-test check counts are separate.','The prompt supplies the convention; no autonomous discovery is claimed.']}
 (ROOT/'cinematic_timeline.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')

def draft(shots):
 ims=[]
 for s in shots:
  im=preview(s);p=save(im,s['id']+'-preview.png');s['preview']=p.name;ims.append(im)
 cols=4;tw,th=480,270;header=30;rows=math.ceil(len(ims)/cols);sheet=Image.new('RGB',(cols*tw,rows*(th+header)),INK);d=ImageDraw.Draw(sheet)
 for i,(s,im) in enumerate(zip(shots,ims)):
  x=i%cols*tw;y=i//cols*(th+header);txt(d,(x+7,y+2),f"{s['start_seconds']:03d}s {s['id']} {s['kind']}",18,WHITE,True)
  sheet.paste(im.resize((tw,th),Image.Resampling.LANCZOS),(x,y+header))
 p=ROOT/'qa/draft_contact_sheet.jpg';sheet.save(p,quality=92);write_timeline(shots);print(json.dumps({'draft':str(p),'shots':len(shots)}),flush=True)


def encode_shot(shot):
 out=ROOT/'clips'/(shot['id']+'.mp4');dur=shot['duration_seconds'];preset=shot['preset']
 common=['-an','-t',str(dur),'-r','25','-c:v','libx264','-threads','4','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',str(out)]
 if shot['kind']=='illustration':
  overlay=ROOT/'frames'/(shot['id']+'-overlay.png');illustration_overlay(preset).save(overlay)
  vf=illustration_filter(shot['source'],preset)+f'[masked];[masked][1:v]overlay=0:0,fps=25,tpad=stop_mode=clone:stop_duration={dur}[out]'
  cmd=[FF,'-hide_banner','-loglevel','error','-y','-ss',str(shot['mode']),'-i',str(OLD/'inputs'/shot['source']),'-loop','1','-i',str(overlay),'-filter_complex',vf,'-map','[out]']+common
 elif shot['kind']=='kinetic':
  frames=[];count=max(2,round(dur*10))
  for n in range(count):
   im=graphic(preset,min(1,n/max(1,count-1)));p=save(im,f"{shot['id']}-motion-{n:03d}.png");frames.append(p)
  concat=ROOT/'temp'/(shot['id']+'.concat');concat.write_text('\n'.join(v for p in frames for v in [f"file '../frames/{p.name}'",f'duration {dur/count}'])+f"\nfile '../frames/{frames[-1].name}'\n",encoding='utf-8')
  cmd=[FF,'-hide_banner','-loglevel','error','-y','-safe','0','-f','concat','-i',str(concat),'-vf','fps=25']+common
 elif shot['kind']=='ui' and shot['mode']=='record':
  entries=getframes(preset)
  spans=[max(.04,(b['observed_at_ms']-a['observed_at_ms'])/1000) for a,b in zip(entries,entries[1:])];spans.append(.12)
  scale=dur/sum(spans);lines=[]
  for e,t in zip(entries,spans):
   im=ui_image(preset,shot['source'],e);p=save(im,shot['id']+'-'+e['file']);lines.extend([f"file '../frames/{p.name}'",f'duration {t*scale}'])
  lines.append(f"file '../frames/{p.name}'");concat=ROOT/'temp'/(shot['id']+'.concat');concat.write_text('\n'.join(lines)+'\n',encoding='utf-8')
  cmd=[FF,'-hide_banner','-loglevel','error','-y','-safe','0','-f','concat','-i',str(concat),'-vf','fps=25']+common
 else:
  p=save(preview(shot),shot['id']+'-still.png')
  vf="zoompan=z='min(1.04,1+0.00030*on)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1920x1080:fps=25"
  cmd=[FF,'-hide_banner','-loglevel','error','-y','-loop','1','-framerate','25','-i',str(p),'-vf',vf]+common
 subprocess.run(cmd,cwd=ROOT,check=True);print(json.dumps({'shot':shot['id'],'seconds':dur,'kind':shot['kind'],'bytes':out.stat().st_size}),flush=True)
 return out


def srt_time(x):
 ms=round(x*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000);return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
def ass_time(x):
 cs=round(x*100);h,cs=divmod(cs,360000);m,cs=divmod(cs,6000);s,cs=divmod(cs,100);return f'{h}:{m:02d}:{s:02d}.{cs:02d}'

def audio_subtitles():
 stems=[];subs=[];start=0
 for s in SPEC['scenes']:
  wav,sr=sf.read(ROOT/'audio'/(s['id']+'.wav'));assert sr==24000
  seconds=len(wav)/sr;lead=.18
  if seconds+lead>s['duration']:raise ValueError('Narration does not fit '+s['id'])
  block=np.zeros(round(s['duration']*sr),np.float32);n=round(lead*sr);block[n:n+len(wav)]=wav;stems.append(block)
  chunks=[]
  for sentence in re.split(r'(?<=[.!?])\s+',s['narration']):
   words=sentence.split()
   while len(words)>11:chunks.append(' '.join(words[:9]));words=words[9:]
   if words:chunks.append(' '.join(words))
  total=sum(len(c.split()) for c in chunks);pos=start+lead
  for c in chunks:
   end=pos+seconds*len(c.split())/total;subs.append((pos,end,c));pos=end
  start+=s['duration']
 stem=ROOT/'LabRepair_release_narration_20261030.wav';sf.write(stem,np.concatenate(stems),24000,subtype='PCM_16')
 srt=ROOT/'LabRepair_DEMO_Release_20261030.en.srt';srt.write_text('\n'.join(f'{i+1}\n{srt_time(a)} --> {srt_time(b)}\n{t}\n' for i,(a,b,t) in enumerate(subs)),encoding='utf-8')
 header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Segoe UI,41,&H00F0F5F1,&H00F0F5F1,&H0010150B,&H0010150B,0,0,0,0,100,100,0,0,1,2,1,2,110,110,39,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
 ass=ROOT/'temp/cinematic.ass';ass.write_text(header+'\n'.join(f'Dialogue: 0,{ass_time(a)},{ass_time(b)},Default,,0,0,0,,{t}' for a,b,t in subs)+'\n',encoding='utf-8')
 return stem,ass,len(subs)


def render(shots,reuse=False):
 previous={}
 if reuse and (ROOT/'cinematic_timeline.json').exists():
  previous={s['id']:s for s in json.loads((ROOT/'cinematic_timeline.json').read_text(encoding='utf-8-sig'))['shots']}
 stem,ass,nsubs=audio_subtitles();clip_paths=[]
 for shot in shots:
  path=ROOT/'clips'/(shot['id']+'.mp4');old=previous.get(shot['id'],{})
  if reuse and path.exists() and all(old.get(k)==shot.get(k) for k in ('duration_seconds','kind','preset','source','mode')):
   clip_paths.append(path);print(json.dumps({'reused_shot':shot['id']}),flush=True)
  else:clip_paths.append(encode_shot(shot))
 concat=ROOT/'temp/film.concat';concat.write_text('\n'.join(f"file '../clips/{p.name}'" for p in clip_paths)+'\n',encoding='utf-8')
 final=ROOT/'LabRepair_DEMO_Release_20261030.mp4'
 plate=protagonist_nameplate()
 subprocess.run([FF,'-hide_banner','-loglevel','error','-y','-safe','0','-f','concat','-i',str(concat),'-i',str(stem),'-loop','1','-i',str(plate),'-filter_complex',"[0:v]fps=25,subtitles=temp/cinematic.ass[v];[v][2:v]overlay=0:0:enable='lt(t,5)'[out]",'-map','[out]','-map','1:a:0','-c:v','libx264','-threads','4','-preset','veryfast','-crf','18','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-c:a','aac','-b:a','160k','-ar','48000','-t',str(DURATION),'-movflags','+faststart',str(final)],cwd=ROOT,check=True)
 receipt={'schema':'LABREPAIR_CINEMATIC_RENDER_V1','ui_source_commit':'a7cf2f5629975a00511beadd9e2a90eac3349a52','duration_seconds':DURATION,'fps':25,'width':W,'height':H,'shot_count':len(shots),'subtitle_intervals':nsubs,'voice':'Local generic Kokoro am_michael','movie':{'name':final.name,'bytes':final.stat().st_size,'sha256':hashlib.sha256(final.read_bytes()).hexdigest()},'animation_audio_used':False,'new_provider_calls':0,'visual_grammar':['Full-bleed illustration','Neutral kinetic total reveal','Fullscreen actual UI','Animated pair evidence','Dark scientific verdict separation','Parameter pipeline and recorded execution','Human handover'],'note':'Actual UI capture timing and story ordering are edited, not a speed benchmark or new cloud run.'}
 receipt['protagonist_nameplate']={'text':'Nora · Quantum research software engineer','start_seconds':0,'end_seconds':5,'character':'Illustrative protagonist'}
 (ROOT/'render_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');write_timeline(shots);print(json.dumps(receipt),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--draft',action='store_true');p.add_argument('--reuse-shots',action='store_true');p.add_argument('--nameplate-only',action='store_true');p.add_argument('--refresh-opening',action='store_true');a=p.parse_args();shots=plan()
 if a.nameplate_only:apply_nameplate_only()
 elif a.refresh_opening:
  for shot in shots[:2]:encode_shot(shot)
  render(shots,True)
  opening=preview(shots[0])
  opening.save(ROOT/'qa/nameplate-preview.jpg')
  save(opening,'shot-01-preview.png')
 elif a.draft:draft(shots)
 else:render(shots,a.reuse_shots)
