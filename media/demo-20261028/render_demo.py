"""Build an edited, narrated demo from actual UI captures and labeled evidence cards."""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1] if (ROOT.parents[1] / "labrepair").is_dir() else ROOT.parent / "nebius-labrepair"
if not REPO.is_dir():
    REPO = ROOT
sys.path.insert(0, str(REPO / ".test-tmp/media-tools"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT.parent / "nebius-demo-20261027/tools"))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import imageio_ffmpeg
import soundfile as sf

SPEC = json.loads((REPO / "docs/demo_narration_20261028.json").read_text(encoding="utf-8"))
FRAMES = ROOT / "frames"
CLIPS = ROOT / "clips"
FRAMES.mkdir(exist_ok=True)
CLIPS.mkdir(exist_ok=True)
W,H = 1920,1080
BG="#F4F5EF"; INK="#173438"; TEAL="#216F68"; MUTED="#566B69"; LINE="#CBD5CF"
RED="#A34935"; PALE="#E6EEE8"; WHITE="#FEFFFC"
FFMPEG=imageio_ffmpeg.get_ffmpeg_exe()
FONTROOT=Path("C:/Windows/Fonts")

def font(size=32,kind="regular"):
    name={"regular":"segoeui.ttf","bold":"seguisb.ttf","mono":"consola.ttf"}[kind]
    return ImageFont.truetype(str(FONTROOT/name),size)

def text(draw, xy, value, size=32, fill=INK, kind="regular"):
    draw.text(xy,str(value),font=font(size,kind),fill=fill)

def wrap(draw, value, width, size=32, kind="regular"):
    lines=[]; line=""
    for word in str(value).split():
        trial=(line+" "+word).strip()
        if draw.textlength(trial,font=font(size,kind))>width and line:
            lines.append(line);line=word
        else:line=trial
    if line:lines.append(line)
    return lines

def paragraph(draw,xy,value,width,size=32,fill=MUTED,kind="regular",gap=1.36):
    x,y=xy
    for line in wrap(draw,value,width,size,kind):
        text(draw,(x,y),line,size,fill,kind);y+=int(size*gap)
    return y

def base(scene, index):
    im=Image.new("RGB",(W,H),BG);d=ImageDraw.Draw(im)
    d.rectangle((76,48,114,86),fill=TEAL)
    text(d,(83,45),"L",28,WHITE,"bold")
    text(d,(133,48),"LABREPAIR",29,INK,"bold")
    text(d,(1130,52),"EDITED DEMO  /  SYNTHETIC STUDY",22,TEAL,"mono")
    d.line((80,111,1840,111),fill=LINE,width=2)
    text(d,(85,136),scene["title"],49,INK,"bold")
    text(d,(87,205),scene["subtitle"],26,MUTED)
    d.line((80,923,1840,923),fill=LINE,width=2)
    text(d,(84,1034),"LOCAL NEURAL VOICE / RECORDED UI INTERACTIONS / SAVED CLOUD RESULTS",17,MUTED,"mono")
    text(d,(1730,1030),f"{index:02d} / 09",21,TEAL,"mono")
    return im

def card(draw,box,label,value,detail,color=TEAL):
    x,y,x2,y2=box
    draw.rectangle(box,fill=WHITE,outline=LINE,width=2)
    draw.rectangle((x,y,x+7,y2),fill=color)
    text(draw,(x+30,y+24),label,24,color,"bold")
    value_size=99
    while draw.textlength(str(value),font=font(value_size,"mono"))>x2-x-65:
        value_size-=1
    text(draw,(x+30,y+82),value,value_size,color,"mono")
    paragraph(draw,(x+30,y+220),detail,x2-x-60,29,color)

SESSION=json.loads((ROOT/'recording/session.json').read_text(encoding='utf-8'))
frame_cache={}

def save(im,name):
    path=FRAMES/name
    if not path.exists(): im.save(path)
    return path

def fit_ui(scene,index,source):
    im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    text(d,(75,26),'LABREPAIR',27,TEAL,'bold')
    title_size=37
    while d.textlength(scene['title'],font=font(title_size,'bold'))>1440:title_size-=1
    text(d,(360,23),scene['title'],title_size,INK,'bold')
    text(d,(78,84),scene['subtitle'],24,MUTED)
    d.line((75,130,1845,130),fill=LINE,width=2)
    shot=Image.open(ROOT/'recording'/source).convert('RGB')
    fit=ImageOps.contain(shot,(1770,785),Image.Resampling.LANCZOS)
    im.paste(fit,(75+(1770-fit.width)//2,144))
    d.line((75,936,1845,936),fill=LINE,width=2)
    text(d,(80,1053),'RECORDED UI INTERACTION / EDITED FOR PACE / NO NEW MODEL CALL',16,MUTED,'mono')
    text(d,(1730,1050),f'{index:02d} / 09',20,TEAL,'mono')
    return im

def ui_frame(scene,index,entry):
    key=(scene['id'],hashlib.sha256((ROOT/'recording'/entry['file']).read_bytes()).hexdigest())
    if key not in frame_cache:
        frame_cache[key]=save(fit_ui(scene,index,entry['file']),scene['id']+'-'+key[1][:16]+'.png')
    return frame_cache[key]

def source_frames(label):
    found=[f for f in SESSION['frames'] if f['label']==label]
    assert found,label
    return found

def add_record(seq,scene,index,label,seconds):
    entries=source_frames(label)
    spans=[max(.02,(b['observed_at_ms']-a['observed_at_ms'])/1000) for a,b in zip(entries,entries[1:])]
    spans.append(max(.04,(entries[-1]['completed_at_ms']-entries[-1]['observed_at_ms'])/1000))
    scale=seconds/sum(spans)
    seq.extend((ui_frame(scene,index,f),duration*scale) for f,duration in zip(entries,spans))

def add_hold(seq,scene,index,label,seconds):
    seq.append((ui_frame(scene,index,source_frames(label)[-1]),seconds))

def editorial(scene,index,kind):
    im=base(scene,index);d=ImageDraw.Draw(im)
    if kind=='hook':
        card(d,(95,295,925,755),'MODEL REPAIR','2.60','All four registered pair values match.')
        card(d,(990,295,1825,755),'WRONG-PAIR OPERATOR CONTROL','2.60','Same total. Contradictory pair evidence.',RED)
        text(d,(105,810),'A matching total can hide a wrong repair.',43,INK,'bold')
        text(d,(105,880),'EDITORIAL COMPARISON / RECORDED REAL RESULTS',20,MUTED,'mono')
    elif kind=='model':
        text(d,(100,285),'NEBIUS TOKEN FACTORY',28,TEAL,'mono')
        text(d,(100,340),'NVIDIA Nemotron 3 Nano',52,INK,'bold')
        text(d,(101,420),'121 input / 38 output tokens',33,TEAL,'bold')
        text(d,(101,484),'Prompt supplies the channel convention.',33,INK,'bold')
        text(d,(101,542),'Model translates it into typed parameters.',30,MUTED)
        text(d,(101,600),'Adapter builds the bounded source patch.',30,MUTED)
        text(d,(101,685),'No autonomous discovery is claimed.',29,RED,'bold')
        response=json.loads((REPO/'evidence/nebius-nano-repair-20261026-1/response.json').read_text(encoding='utf-8'))
        d.rectangle((1030,305,1810,670),fill=INK)
        y=355
        for line in response['choices'][0]['message']['content'].splitlines():
            for sub in wrap(d,line,710,28,'mono'):
                text(d,(1060,y),sub,28,'#D9EEE5','mono');y+=46
        paragraph(d,(1045,730),'Exact saved model response. Counts and protected tests remain unchanged.',735,29,INK)
        text(d,(103,877),'SAVED REAL GENERATION / 26 OCTOBER 2026 UTC / NO NEW CALL',20,MUTED,'mono')
    elif kind=='sandbox':
        card(d,(95,300,635,685),'BASELINE','2 / 4','Expected failure observed.',RED)
        card(d,(690,300,1230,685),'NVIDIA REPAIR','4 / 4','Repair passed.')
        card(d,(1285,300,1825,685),'WRONG-PAIR CONTROL','3 / 4','Expected rejection observed.',RED)
        text(d,(100,739),'1 disposable operation · 1.273 seconds',47,INK,'bold')
        text(d,(102,813),'12 checks include 3 expected failures. Guest network disabled.',29,MUTED)
        text(d,(102,877),'EDITORIAL SUMMARY OF RECORDED REAL EXECUTION / NO NEW CALL',20,MUTED,'mono')
    elif kind=='claim':
        card(d,(95,290,930,738),'REPAIRED ANALYSIS','2.60','Code checks passed in the recorded real run.')
        card(d,(990,290,1825,738),'ORIGINAL SCIENTIFIC CLAIM','3.40','NOT REPRODUCED. Physical interpretation not established.',RED)
        text(d,(102,790),'A code repair cannot approve a scientific conclusion.',43,INK,'bold')
        text(d,(104,878),'SYNTHETIC INPUTS / NO PHYSICAL BELL EXPERIMENT OR QUANTUM ADVANTAGE',19,MUTED,'mono')
    elif kind=='receipt':
        r=json.loads((ROOT/'local-review-downloaded.json').read_text(encoding='utf-8'))
        text(d,(103,285),'ACTUAL DOWNLOADED LOCAL RECEIPT',25,TEAL,'mono')
        text(d,(103,355),'Hold for evidence',62,INK,'bold')
        paragraph(d,(105,465),'The intent binds to the exact reviewed source. No job, payment or claim promotion is authorized.',815,35,INK)
        d.rectangle((1035,302,1810,810),fill=WHITE,outline=LINE,width=2)
        y=342
        fields=[('Scenario',r['review']['scenario']),('Local result',r['review']['local_result']),('Intent',r['review_intent']['choice']),('Authorizes execution',str(r['review_intent']['executes_candidate'])),('Authorizes payment',str(r['review_intent']['authorizes_payment']))]
        for label,value in fields:
            text(d,(1065,y),label,22,MUTED,'mono');text(d,(1065,y+32),value,29,TEAL,'bold');y+=87
        text(d,(105,878),'EDITORIAL EXCERPT / SOURCE-BOUND JSON / DOWNLOAD WAIT OMITTED',20,MUTED,'mono')
    elif kind=='close':
        text(d,(99,320),'Repair the analysis.',82,INK,'bold')
        text(d,(99,425),'Preserve the evidence.',82,TEAL,'bold')
        d.line((103,565,1805,565),fill=LINE,width=3)
        text(d,(105,618),'Recorded model repair: PASSED',43,TEAL,'bold')
        text(d,(105,700),'Original claim: NOT REPRODUCED',43,RED,'bold')
        text(d,(106,853),'VERIFICATION-FIRST DEVELOPER TOOL / ONE BOUNDED SYNTHETIC CASE',20,MUTED,'mono')
    return save(im,scene['id']+'-'+kind+'.png')

def zoom_verifier(scene,index,label):
    im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    text(d,(78,35),'LABREPAIR / INDEPENDENT VERIFIER',24,TEAL,'mono')
    text(d,(78,101),'FOCUSED CROP OF ACTUAL RECORDED UI',20,MUTED,'mono')
    if label=='wrong-pairs':
        paragraph(d,(88,280),'Same total. Different evidence.',730,66,INK,'bold')
        paragraph(d,(90,520),'The wrong repair changes every pair. Protected evidence rejects it.',700,36,RED,'bold')
        paragraph(d,(90,725),'Original claim: NOT REPRODUCED',700,30,INK)
    else:
        paragraph(d,(88,280),'Missing evidence stays REVIEW.',730,66,INK,'bold')
        paragraph(d,(90,530),'Unknown values remain unknown. A plausible story cannot fill the gap.',700,36,TEAL,'bold')
        paragraph(d,(90,740),'Curated local control; not a fourth cloud execution.',700,29,MUTED)
    shot=Image.open(ROOT/'recording'/source_frames(label)[-1]['file']).convert('RGB').crop((600,0,1210,535))
    fit=ImageOps.contain(shot,(965,800),Image.Resampling.LANCZOS)
    im.paste(fit,(865+(965-fit.width)//2,140))
    d.line((75,939,1845,939),fill=LINE,width=2)
    text(d,(80,1053),'ACTUAL LOCAL REVIEW / SYNTHETIC INPUTS / NO MODEL CALL',16,MUTED,'mono')
    text(d,(1730,1050),f'{index:02d} / 09',20,TEAL,'mono')
    return save(im,scene['id']+'-focused-verifier.png')

def build_sequences():
    out={}
    for i,scene in enumerate(SPEC['scenes'],1):
        s=[];sid=scene['id']
        if sid=='01_role':add_record(s,scene,i,'home',1.8);add_hold(s,scene,i,'home',8.2)
        elif sid=='02_hook':s=[(editorial(scene,i,'hook'),7)]
        elif sid=='03_pairs':
            for label,secs in [('select-valid',2.2),('run-valid',2.2),('valid-pairs',1.8)]:add_record(s,scene,i,label,secs)
            add_hold(s,scene,i,'valid-pairs',2.3)
            for label,secs in [('select-wrong',2.2),('run-wrong',2.2),('wrong-pairs',1.8)]:add_record(s,scene,i,label,secs)
            s.append((zoom_verifier(scene,i,'wrong-pairs'),9.3))
        elif sid=='04_model':
            add_record(s,scene,i,'recorded-panel',2.2);add_record(s,scene,i,'provider-details',2.2);add_hold(s,scene,i,'provider-details',7.6)
            s.append((editorial(scene,i,'model'),16))
        elif sid=='05_sandbox':add_hold(s,scene,i,'provider-details',16);s.append((editorial(scene,i,'sandbox'),7))
        elif sid=='06_claim':s=[(editorial(scene,i,'claim'),22)]
        elif sid=='07_review':
            for label,secs in [('select-incomplete',2.2),('run-incomplete',2.2),('incomplete-pairs',1.8)]:add_record(s,scene,i,label,secs)
            s.append((zoom_verifier(scene,i,'incomplete-pairs'),10.8))
        elif sid=='08_handover':
            for label,secs in [('hold',2.2),('download-receipt',2.2),('hold-evidence',1.8)]:add_record(s,scene,i,label,secs)
            add_hold(s,scene,i,'hold-evidence',6.8);s.append((editorial(scene,i,'receipt'),5))
        elif sid=='09_close':s=[(editorial(scene,i,'close'),11)]
        assert abs(sum(duration for _,duration in s)-scene['duration'])<1e-7,(sid,sum(duration for _,duration in s))
        out[sid]=s
    return out

def srt_time(seconds):
    ms=round(seconds*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def subtitles(scene,audio_seconds,start=0):
    chunks=[]
    for sentence in re.split(r"(?<=[.!?])\s+",scene["narration"]):
        words=sentence.split()
        while len(words)>13:
            cut=10
            chunks.append(" ".join(words[:cut]));words=words[cut:]
        if words:chunks.append(" ".join(words))
    counts=[len(c.split()) for c in chunks];total=sum(counts);offset=0.32;out=[]
    for i,(c,n) in enumerate(zip(chunks,counts),1):
        a=offset;b=offset+audio_seconds*n/total
        out.append(f"{i}\n{srt_time(start+a)} --> {srt_time(start+b)}\n{c}\n")
        offset=b
    return out

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def ass_time(seconds):
    cs=round(seconds*100);h,cs=divmod(cs,360000);m,cs=divmod(cs,6000);s,cs=divmod(cs,100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def write_ass(srt_path,ass_path):
    header="""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Segoe UI,39,&H00383417,&H00383417,&H00EFF5F4,&H00EFF5F4,0,0,0,0,100,100,0,0,3,10,0,2,110,110,58,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    blocks=srt_path.read_text(encoding="utf-8").strip().split("\n\n");lines=[]
    def parse(s):
        h,m,s=s.replace(",", ".").split(":");return int(h)*3600+int(m)*60+float(s)
    for block in blocks:
        parts=block.splitlines()
        if len(parts)<3:continue
        a,b=parts[1].split(" --> ")
        value=" ".join(parts[2:]).replace("{", "").replace("}", "")
        lines.append(f"Dialogue: 0,{ass_time(parse(a))},{ass_time(parse(b))},Default,,0,0,0,,{value}")
    ass_path.write_text(header+"\n".join(lines)+"\n",encoding="utf-8")

def render(sequence):
    elapsed=0;all_captions=[];combined=[];clip_paths=[]
    for i,scene in enumerate(SPEC["scenes"],1):
        sid=scene["id"];samples,sr=sf.read(ROOT/"audio"/(sid+".wav"));assert sr==24000
        assert len(samples)/sr+0.32<scene["duration"],sid
        padded=np.zeros(round(scene["duration"]*sr),dtype=np.float32)
        padded[round(.32*sr):round(.32*sr)+len(samples)]=samples
        combined.append(padded)
        local_sub=ROOT/(sid+".srt")
        local_sub.write_text("\n".join(subtitles(scene,len(samples)/sr)),encoding="utf-8")
        local_ass=ROOT/(sid+".ass")
        write_ass(local_sub,local_ass)
        all_captions.extend(subtitles(scene,len(samples)/sr,elapsed))
        elapsed+=scene["duration"]
        concat=ROOT/(sid+".concat")
        parts=[]
        for path,duration in sequence[sid]:parts.extend([f"file 'frames/{path.name}'",f"duration {duration}"])
        parts.append(f"file 'frames/{sequence[sid][-1][0].name}'")
        concat.write_text("\n".join(parts)+"\n",encoding="utf-8")
        output=CLIPS/(sid+".mp4")
        filters=(f"fps=25,fade=t=in:st=0:d=0.25,fade=t=out:st={scene['duration']-.22}:d=0.22,"
                 f"subtitles={local_ass.name},format=yuv420p")
        cmd=[FFMPEG,"-hide_banner","-loglevel","error","-y","-safe","0","-f","concat","-i",concat.name,
             "-vf",filters,"-t",str(scene["duration"]),"-an","-c:v","libx264","-threads","4",
             "-preset","veryfast","-crf","20","-pix_fmt","yuv420p",str(output)]
        subprocess.run(cmd,cwd=ROOT,check=True)
        clip_paths.append(output)
        print(json.dumps({"rendered_scene":sid,"duration_seconds":scene["duration"],"bytes":output.stat().st_size}),flush=True)
    (ROOT/"LabRepair_DEMO_20261028.en.srt").write_text("\n".join(f"{i+1}\n"+c.split("\n",1)[1] for i,c in enumerate(all_captions)),encoding="utf-8")
    sf.write(ROOT/"LabRepair_natural_narration_20261028.wav",np.concatenate(combined),24000,subtype="PCM_16")
    join=ROOT/"video.concat";join.write_text("\n".join(f"file 'clips/{p.name}'" for p in clip_paths)+"\n",encoding="utf-8")
    final=ROOT/"LabRepair_DEMO_NeuralVoice_20261028.mp4"
    subprocess.run([FFMPEG,"-hide_banner","-loglevel","error","-y","-safe","0","-f","concat","-i",join.name,
                    "-i","LabRepair_natural_narration_20261028.wav","-map","0:v:0","-map","1:a:0",
                    "-c:v","copy","-af","loudnorm=I=-16:TP=-1.5:LRA=11","-c:a","aac","-b:a","160k","-ar","48000",
                    "-t","160","-movflags","+faststart",final.name],cwd=ROOT,check=True)
    return final

if __name__=="__main__":
    seq=build_sequences()
    if len(sys.argv)>1 and sys.argv[1]=="frames":
        print("Prepared labeled scene images for visual inspection.")
    else:
        path=render(seq)
        print(json.dumps({"video":str(path),"bytes":path.stat().st_size,"sha256":sha(path)}),flush=True)
