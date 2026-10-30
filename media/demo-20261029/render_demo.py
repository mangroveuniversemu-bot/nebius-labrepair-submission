"""Render a labeled, edited LabRepair demo from real UI frames and safe illustrative crops.

No provider, browser control, candidate execution or paid API. Animation audio is
always discarded. Generated screens/documents are cropped away or fully masked.
"""
from __future__ import annotations
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent/'nebius-labrepair'
sys.path[:0]=[str(ROOT.parent/'nebius-demo-20261027/tools'),str(REPO/'.test-tmp/media-tools')]
import numpy as np
import soundfile as sf
from PIL import Image,ImageDraw,ImageFont,ImageOps
import imageio_ffmpeg
FFMPEG=imageio_ffmpeg.get_ffmpeg_exe()
SPEC=json.loads((REPO/'docs/demo_narration_20261029.json').read_text(encoding='utf-8-sig'))
SESSION=json.loads((ROOT/'recording/session.json').read_text(encoding='utf-8-sig'))
UI_COMMIT='a7cf2f5629975a00511beadd9e2a90eac3349a52'
W,H=1920,1080
BG='#F5F4EF';WHITE='#FFFefa';INK='#173438';TEAL='#17685F';MUTED='#5B6E6B';LINE='#CDD5CC';RED='#A34835';AMBER='#8A681C';PALE='#E7EEE5'
FRAMES=ROOT/'frames';CLIPS=ROOT/'clips';TEMP=ROOT/'temp'
for p in [FRAMES,CLIPS,TEMP,ROOT/'qa']:p.mkdir(parents=True,exist_ok=True)
FONT=Path('C:/Windows/Fonts')

def font(size=36,bold=False,mono=False):return ImageFont.truetype(str(FONT/('consola.ttf' if mono else 'seguisb.ttf' if bold else 'segoeui.ttf')),size)
def tx(d,xy,value,size=36,color=INK,bold=False,mono=False):d.text(xy,str(value),font=font(size,bold,mono),fill=color)
def wrap(d,value,width,size=36,bold=False,mono=False):
 out=[];line=''
 for word in str(value).split():
  candidate=(line+' '+word).strip()
  if line and d.textlength(candidate,font=font(size,bold,mono))>width:out.append(line);line=word
  else:line=candidate
 if line:out.append(line)
 return out

def para(d,xy,value,width,size=36,color=MUTED,bold=False,gap=1.35):
 x,y=xy
 for line in wrap(d,value,width,size,bold):tx(d,(x,y),line,size,color,bold);y+=round(size*gap)
 return y

def base(scene,index,mode='ACTUAL LOCAL UI / SYNTHETIC INPUTS',alpha=False):
 im=Image.new('RGBA' if alpha else 'RGB',(W,H),BG);d=ImageDraw.Draw(im)
 tx(d,(66,27),'LABREPAIR',28,TEAL,True)
 fs=20
 while d.textlength(mode,font=font(fs,mono=True))>1420:fs-=1
 tx(d,(430,34),mode,fs,MUTED,mono=True)
 d.line((65,80,1855,80),fill=LINE,width=2)
 size=53
 while d.textlength(scene['title'],font=font(size,True))>1790:size-=1
 tx(d,(65,98),scene['title'],size,INK,True)
 d.rectangle((0,963,W,H),fill=BG)
 d.line((65,961,1855,961),fill=LINE,width=2)
 tx(d,(70,1056),'EDITED INTERACTIONS / NO NEW MODEL CALL',15,MUTED,mono=True)
 tx(d,(1740,1052),f'{index:02d} / 10',19,TEAL,mono=True)
 return im

def save(im,name):
 p=FRAMES/name;im.save(p);return p

def card(d,box,label,value,detail,color=TEAL):
 x,y,x2,y2=box;d.rectangle(box,fill=WHITE,outline=LINE,width=2);d.rectangle((x,y,x+6,y2),fill=color)
 tx(d,(x+30,y+23),label,27,color,True)
 size=114
 while d.textlength(value,font=font(size,True,True))>x2-x-60:size-=1
 tx(d,(x+30,y+94),value,size,color,mono=True)
 para(d,(x+32,y+255),detail,x2-x-64,32,color)

def source(label):
 out=[f for f in SESSION['frames'] if f['label']==label]
 if not out:raise ValueError('Missing captured UI label: '+label)
 return out

CACHE={}
def ui_frame(scene,index,entry,focus='whole'):
 key=(scene['id'],entry['file'],focus)
 if key in CACHE:return CACHE[key]
 im=base(scene,index);d=ImageDraw.Draw(im);shot=Image.open(ROOT/'recording'/entry['file']).convert('RGB')
 if focus=='whole':
  crop=shot.crop((45,15,min(1210,shot.width-10),min(695,shot.height)))
  fit=ImageOps.contain(crop,(1788,780),Image.Resampling.LANCZOS);im.paste(fit,(66+(1788-fit.width)//2,174+(780-fit.height)//2))
 elif focus=='score':
  crop=shot.crop((48,15,min(1200,shot.width-20),240));fit=ImageOps.contain(crop,(1788,405),Image.Resampling.LANCZOS)
  im.paste(fit,(66+(1788-fit.width)//2,180))
  wrong='wrong' in entry['label'];color=RED if wrong else TEAL
  tx(d,(91,660),'0 / 4 pair values match' if wrong else '4 / 4 pair values match',62,color,True)
  tx(d,(94,763),'The total is 2.60 in both cases.',41,INK,True)
  tx(d,(94,842),'Local pair-value comparison — not the cloud test count.',28,MUTED)
 elif focus=='difference':
  crop=shot.crop((598,270,min(1205,shot.width),min(680,shot.height)))
  fit=ImageOps.contain(crop,(1050,760),Image.Resampling.LANCZOS);im.paste(fit,(805+(1050-fit.width)//2,183))
  tx(d,(83,248),'2.60',112,INK,True,True);tx(d,(87,402),'The same total.',43,INK,True)
  para(d,(87,515),'Four conflicting pair values change the decision.',630,51,RED,True)
  tx(d,(90,798),'ACTUAL UI / FOCUSED CROP',23,MUTED,mono=True)
 elif focus=='handover':
  crop=shot.crop((48,190,min(1205,shot.width),min(670,shot.height)))
  fit=ImageOps.contain(crop,(1788,780),Image.Resampling.LANCZOS);im.paste(fit,(66+(1788-fit.width)//2,176+(780-fit.height)//2))
 elif focus=='unknown':
  crop=shot.crop((48,15,min(1200,shot.width-20),240));fit=ImageOps.contain(crop,(1788,400),Image.Resampling.LANCZOS)
  im.paste(fit,(66+(1788-fit.width)//2,180));tx(d,(90,670),'Unknown stays unknown.',68,AMBER,True)
  tx(d,(93,786),'Curated local control — not a fourth cloud execution.',32,MUTED)
 CACHE[key]=save(im,scene['id']+'-'+entry['file'].replace('.png','')+'-'+focus+'.png');return CACHE[key]

def record(seq,scene,index,label,seconds,focus='whole'):
 entries=source(label)
 spans=[max(.03,(b['observed_at_ms']-a['observed_at_ms'])/1000) for a,b in zip(entries,entries[1:])]
 spans.append(max(.04,(entries[-1]['completed_at_ms']-entries[-1]['observed_at_ms'])/1000))
 scale=seconds/sum(spans)
 seq.extend((ui_frame(scene,index,f,focus),t*scale) for f,t in zip(entries,spans))
def hold(seq,scene,index,label,seconds,focus='whole'):seq.append((ui_frame(scene,index,source(label)[-1],focus),seconds))

def editorial(scene,index,kind):
 mode='EDITORIAL SUMMARY / SAVED REAL EXECUTION / 26 OCT 2026 UTC' if kind in ('model','execution') else 'EDITORIAL VERDICT / ONE SYNTHETIC CASE'
 im=base(scene,index,mode);d=ImageDraw.Draw(im)
 if kind=='model':
  tx(d,(88,225),'Nebius Token Factory',58,INK,True);tx(d,(90,318),'NVIDIA Nemotron',50,TEAL,True)
  tx(d,(93,414),'121 input / 38 output tokens',37,TEAL,True)
  para(d,(92,535),'Prompt supplies the convention. The model translates it into parameters.',825,41,INK)
  tx(d,(94,773),'Counts and protected tests stay fixed.',31,MUTED)
  d.rectangle((1030,223,1835,808),fill=INK)
  tx(d,(1060,256),'PARAMETERS FROM SAVED RESPONSE',22,'#BEDDD3',mono=True)
  tx(d,(1070,369),'channel_signs',32,'#D8E8DD',True,True);tx(d,(1070,425),'[1, 1, -1, -1]',44,'#D8E8DD',mono=True)
  tx(d,(1070,541),'offsets',32,'#D8E8DD',True,True);tx(d,(1070,597),'[0, 0, 0, 0]',44,'#D8E8DD',mono=True)
  tx(d,(92,885),'Model: nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B',26,MUTED,mono=True)
 elif kind=='execution':
  for box,label,value,detail,color in [((70,240,625,704),'BASELINE','2 / 4','Expected failure.',RED),((682,240,1237,704),'MODEL REPAIR','4 / 4','Repair passed.',TEAL),((1294,240,1849,704),'WRONG-PAIR CONTROL','3 / 4','Expected rejection.',RED)]:card(d,box,label,value,detail,color)
  tx(d,(87,755),'1.273 seconds · one disposable operation',47,INK,True)
  tx(d,(91,846),'Protected test checks — distinct from the local pair-value match count.',28,MUTED)
  tx(d,(91,904),'Guest networking disabled. 12 checks include 3 expected control failures.',25,MUTED)
 elif kind=='close':
  tx(d,(90,252),'Repair the analysis.',93,INK,True);tx(d,(90,383),'Preserve the evidence.',93,TEAL,True)
  d.line((94,564,1810,564),fill=LINE,width=3)
  tx(d,(95,624),'A passing repair',49,INK,True);tx(d,(95,698),'is not a reproduced result.',61,RED,True)
  tx(d,(98,856),'TRY THE ZERO-KEY REVIEW · CHECK THE EVIDENCE RECEIPT',23,MUTED,mono=True)
 return save(im,scene['id']+'-'+kind+'.png')

def animation_overlay(scene,index,kind):
 mode='AI-GENERATED ILLUSTRATION / FICTIONAL CHARACTER / SYNTHETIC CASE'
 im=base(scene,index,mode,alpha=True);d=ImageDraw.Draw(im)
 if kind in ('hook','person'):
  d.rectangle((1280,172,1840,947),fill=(0,0,0,0))
  if kind=='hook':
   card(d,(75,230,650,676),'REPAIR A','2.60','Evidence matches.')
   card(d,(690,230,1240,676),'REPAIR B','2.60','Pair evidence conflicts.',RED)
   tx(d,(90,769),'One number is not enough.',48,INK,True)
   tx(d,(94,862),'ILLUSTRATIVE PORTRAIT / EDITORIAL COMPARISON',21,MUTED,mono=True)
  else:
   tx(d,(90,237),'Nora',98,INK,True)
   para(d,(94,395),'Quantum research software engineer.',1065,57,TEAL,True)
   para(d,(96,627),'Accept a repair without changing what the evidence supports.',1030,43,INK)
   tx(d,(97,875),'Fictional role. Not a customer testimonial.',25,MUTED)
 elif kind=='claim':
  # Show only blurred ambient outer margins; generated papers stay fully covered.
  d.rectangle((0,173,64,962),fill=(0,0,0,0))
  d.rectangle((1856,173,W-1,962),fill=(0,0,0,0))
  # These opaque masks cover every generated document, signature and fake text.
  # Only blurred outer background margins can remain visible.
  d.rectangle((0,0,W,173),fill=BG)
  # Restore the standard header after covering the animation's entire top area.
  header=base(scene,index,mode,alpha=True);im.alpha_composite(header.crop((0,0,W,173)),(0,0));d=ImageDraw.Draw(im)
  d.rectangle((65,165,1855,962),fill=BG)
  card(d,(92,230,929,792),'CODE REPAIR','2.60','PASSED against protected checks.',TEAL)
  card(d,(991,230,1828,792),'ORIGINAL CLAIM','3.40','NOT REPRODUCED.',RED)
  tx(d,(101,855),'Two decisions. Neither can silently approve the other.',40,INK,True)
  tx(d,(104,917),'OPAQUE EDITORIAL PANELS / ALL GENERATED DOCUMENT CONTENT MASKED',19,MUTED,mono=True)
 return save(im,scene['id']+'-animation-overlay.png')

def build_sequences():
 out={}
 for i,s in enumerate(SPEC['scenes'],1):
  seq=[];sid=s['id'];dur=s['duration']
  if sid in ('01_hook','02_person','07_claim'):out[sid]=None;continue
  if sid=='03_action':
   for label,t in [('valid-select',2.5),('valid-run',2),('valid-result',2.5),('wrong-select',2.5),('wrong-run',2),('wrong-result',2.5)]:record(seq,s,i,label,t)
   hold(seq,s,i,'wrong-result',dur-14,'score')
  elif sid=='04_difference':hold(seq,s,i,'wrong-evidence',dur,'difference')
  elif sid=='05_model':
   record(seq,s,i,'saved-detail',3.0);hold(seq,s,i,'saved-detail',3.0)
   seq.append((editorial(s,i,'model'),dur-6))
  elif sid=='06_execution':
   hold(seq,s,i,'saved-detail',4.0);seq.append((editorial(s,i,'execution'),dur-4))
  elif sid=='08_unknown':
   record(seq,s,i,'unknown-select',2.5);record(seq,s,i,'unknown-run',2.5);record(seq,s,i,'unknown-result',2.0)
   hold(seq,s,i,'unknown-result',dur-7,'unknown')
  elif sid=='09_handover':
   record(seq,s,i,'hold',2.5,'handover');record(seq,s,i,'tool-record',2.5,'handover');hold(seq,s,i,'tool-record',dur-5,'handover')
  elif sid=='10_close':seq=[(editorial(s,i,'close'),dur)]
  else:raise ValueError(sid)
  assert abs(sum(t for _,t in seq)-dur)<1e-6,(sid,seq)
  out[sid]=seq
 return out

def stamp(seconds):
 ms=round(seconds*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
 return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
def captions(scene,seconds,start=0):
 chunks=[]
 for sentence in re.split(r'(?<=[.!?])\s+',scene['narration']):
  words=sentence.split()
  while len(words)>11:chunks.append(' '.join(words[:9]));words=words[9:]
  if words:chunks.append(' '.join(words))
 total=sum(len(c.split()) for c in chunks);pos=.20;out=[]
 for chunk in chunks:
  end=pos+seconds*len(chunk.split())/total;out.append((start+pos,start+end,chunk));pos=end
 return out

def write_srt(path,items):path.write_text('\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{t}\n' for i,(a,b,t) in enumerate(items)),encoding='utf-8')
def ass_stamp(x):
 cs=round(x*100);h,cs=divmod(cs,360000);m,cs=divmod(cs,6000);s,cs=divmod(cs,100);return f'{h}:{m:02d}:{s:02d}.{cs:02d}'
def write_ass(path,items):
 header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Segoe UI,41,&H00383417,&H00383417,&H00EFF4F5,&H00EFF4F5,0,0,0,0,100,100,0,0,3,8,0,2,100,100,37,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
 path.write_text(header+'\n'.join(f'Dialogue: 0,{ass_stamp(a)},{ass_stamp(b)},Default,,0,0,0,,{t.replace(chr(123),chr(32)).replace(chr(125),chr(32))}' for a,b,t in items)+'\n',encoding='utf-8')

def encode_static(scene,seq,ass,output):
 concat=TEMP/(scene['id']+'.concat');lines=[]
 for p,t in seq:lines.extend([f"file '../frames/{p.name}'",f'duration {t}'])
 lines.append(f"file '../frames/{seq[-1][0].name}'");concat.write_text('\n'.join(lines)+'\n',encoding='utf-8')
 vf=f"fps=25,subtitles=temp/{ass.name},fade=t=in:st=0:d=0.15,fade=t=out:st={scene['duration']-.15}:d=0.15,format=yuv420p"
 subprocess.run([FFMPEG,'-hide_banner','-loglevel','error','-y','-safe','0','-f','concat','-i',str(concat),'-vf',vf,'-t',str(scene['duration']),'-an','-c:v','libx264','-threads','4','-preset','veryfast','-crf','20',str(output)],cwd=ROOT,check=True)

def encode_animation(scene,index,ass,output):
 sid=scene['id'];dur=scene['duration'];kind={'01_hook':'hook','02_person':'person','07_claim':'claim'}[sid]
 overlay=animation_overlay(scene,index,kind)
 if kind=='hook':
  asset='clip-05.mp4';start='1.8';transform='crop=300:790:790:0,scale=560:1474,crop=560:775:0:350'
 elif kind=='person':
  asset='clip-01.mp4';start='0.5';transform='crop=370:640:620:25,scale=560:968,crop=560:775:0:0'
 else:asset='clip-04.mp4';start='0';transform='scale=1920:1080,gblur=sigma=23'
 if kind!='claim':transform+=',pad=1920:1080:1280:172:color=0xF5F4EF'
 inputs=[FFMPEG,'-hide_banner','-loglevel','error','-y','-ss',start,'-i',str(ROOT/'inputs'/asset),'-loop','1','-i',str(overlay)]
 composition='[v][1:v]overlay=0:0'
 if kind=='person':
  # The role introduction ends on the actual homepage, without interrupting
  # its nine-second narration or adding any synthetic interface content.
  home=ui_frame(scene,index,source('home')[-1])
  inputs+=['-loop','1','-i',str(home)]
  composition+="[illustrated];[illustrated][2:v]overlay=0:0:enable='gte(t,6)'"
 graph=(f'[0:v]{transform},fps=25,setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={dur}[v];'
        f'{composition},subtitles=temp/{ass.name},fade=t=in:st=0:d=0.15,fade=t=out:st={dur-.15}:d=0.15,format=yuv420p[out]')
 subprocess.run(inputs+['-filter_complex',graph,'-map','[out]','-t',str(dur),'-an','-c:v','libx264','-threads','4','-preset','veryfast','-crf','20',str(output)],cwd=ROOT,check=True)


def main():
 sequences=build_sequences();allsubs=[];stems=[];clip_paths=[];elapsed=0;scene_records=[]
 for i,scene in enumerate(SPEC['scenes'],1):
  sid=scene['id'];audio,sr=sf.read(ROOT/'audio'/(sid+'.wav'));assert sr==24000
  seconds=len(audio)/sr
  if seconds+.20>scene['duration']:raise ValueError(f'Voice does not fit: {sid} {seconds} / {scene["duration"]}')
  pad=np.zeros(round(scene['duration']*sr),dtype=np.float32);offset=round(.20*sr);pad[offset:offset+len(audio)]=audio;stems.append(pad)
  sub=captions(scene,seconds);ass=TEMP/(sid+'.ass');write_ass(ass,sub);write_srt(TEMP/(sid+'.srt'),sub)
  allsubs.extend(captions(scene,seconds,elapsed));elapsed+=scene['duration']
  output=CLIPS/(sid+'.mp4')
  if sequences[sid] is None:encode_animation(scene,i,ass,output)
  else:encode_static(scene,sequences[sid],ass,output)
  scene_records.append({'scene':sid,'seconds':scene['duration'],'voice_seconds':seconds,'bytes':output.stat().st_size})
  print(json.dumps({'rendered':scene_records[-1]}),flush=True);clip_paths.append(output)
 stem=ROOT/'LabRepair_natural_narration_20261029.wav';sf.write(stem,np.concatenate(stems),24000,subtype='PCM_16')
 subs=ROOT/'LabRepair_DEMO_20261029.en.srt';write_srt(subs,allsubs)
 join=TEMP/'video.concat';join.write_text('\n'.join(f"file '../clips/{p.name}'" for p in clip_paths)+'\n',encoding='utf-8')
 final=ROOT/'LabRepair_DEMO_20261029.mp4'
 subprocess.run([FFMPEG,'-hide_banner','-loglevel','error','-y','-safe','0','-f','concat','-i',str(join),'-i',str(stem),'-map','0:v:0','-map','1:a:0','-vf','fps=25','-c:v','libx264','-threads','4','-preset','veryfast','-crf','18','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-c:a','aac','-b:a','160k','-ar','48000','-t',str(elapsed),'-movflags','+faststart',str(final)],cwd=ROOT,check=True)
 receipt={'schema':'LABREPAIR_RENDER_RECEIPT_V3','ui_source_commit':UI_COMMIT,'duration_seconds':elapsed,'width':W,'height':H,'fps':25,'movie':{'name':final.name,'bytes':final.stat().st_size,'sha256':hashlib.sha256(final.read_bytes()).hexdigest()},'subtitle_intervals':len(allsubs),'voice':'Local Kokoro af_heart','animation_audio_used':False,'used_animation_clips':['clip-01','clip-04','clip-05'],'generated_ui_content':'Clip05centralportraitcrop; clip01actorcrop; clip04allpaperareasopaquelymasked; no generated document/signature treated as evidence','provider_calls':0,'scenes':scene_records}
 receipt['actual_homepage_first_visible_seconds']=14
 receipt['scene02_edit']='First 6 seconds: illustrated Nora. Final 3 seconds: actual current homepage; continuous voice and subtitles.'
 (ROOT/'render_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt),flush=True)

if __name__=='__main__':main()

