"""Decode the final film and inspect measurable media properties locally."""
from pathlib import Path
import subprocess,json,hashlib,re,sys
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'nebius-labrepair/.test-tmp/media-tools'))
import imageio_ffmpeg
FF=imageio_ffmpeg.get_ffmpeg_exe()
MOVIE=ROOT/'LabRepair_DEMO_20261029.mp4'
QA=ROOT/'qa';QA.mkdir(exist_ok=True)
run=subprocess.run([FF,'-hide_banner','-i',str(MOVIE),'-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace')
(QA/'full_decode.txt').write_text(run.stderr,encoding='utf-8');assert run.returncode==0,run.stderr
reader=imageio_ffmpeg.read_frames(str(MOVIE));meta=next(reader);reader.close()
assert meta['size']==(1920,1080) and meta['fps']==25 and abs(meta['duration']-142)<.05,meta
loud=subprocess.run([FF,'-hide_banner','-i',str(MOVIE),'-vn','-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
level=json.JSONDecoder().raw_decode(loud.stderr[loud.stderr.rfind('{'):])[0];assert float(level['input_tp'])<0
points=[4,12,27,46,65,86,101,114,125,136]
sheet=Image.new('RGB',(1920,1584),'#e7eee5');d=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
for i,sec in enumerate(points):
    p=QA/f'actual-{sec:03d}.jpg'
    subprocess.run([FF,'-v','error','-ss',str(sec),'-i',str(MOVIE),'-frames:v','1','-y',str(p)],check=True)
    x=(i%3)*640;y=(i//3)*396;sheet.paste(Image.open(p).resize((640,360)),(x,y));d.text((x+10,y+362),f'{sec}s / decoded final MP4',font=font,fill='#173438')
sheet.save(QA/'actual_movie_contact_sheet.jpg',quality=93)
sub=(ROOT/'LabRepair_DEMO_20261029.en.srt').read_text(encoding='utf-8')
def seconds(x):
    h,m,s=x.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(s)
intervals=[tuple(map(seconds,line.split(' --> '))) for line in sub.splitlines() if ' --> ' in line]
assert all(0<=a<b<=142 for a,b in intervals)
assert all(a2>=b1-.001 for (a1,b1),(a2,b2) in zip(intervals,intervals[1:]))
assert 'Nebius Token Factory' in sub and 'NVIDIA Nemotron' in sub
tts=json.loads((ROOT/'tts_receipt.json').read_text());assert all(x['fits'] for x in tts)
result={'schema':'LABREPAIR_MEDIA_VERIFICATION_V3','ui_source_commit':'a7cf2f5629975a00511beadd9e2a90eac3349a52',
 'stream':meta,'full_decode_exit_code':run.returncode,'measured_audio':level,'subtitle_intervals':len(intervals),
 'subtitle_timing_valid':True,'subtitle_method':'Phrase timing proportional to actual clip lengths; not forced word alignment',
 'tts_clips_fit':True,'generic_neural_voice':'Local Kokoro af_heart','windows_system_speech':False,
 'new_paid_calls':0,'new_provider_or_sandbox_calls':0,'sampled_final_frame_seconds':points,
 'recording_method':'Actual browser screenshot frames sampled during interaction, edited holds and focused crops; not a performance benchmark',
 'animation_audio_used':False,'cloud_original_byte_hash_matching':'NOT_VERIFIED',
 'files':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [MOVIE,ROOT/'LabRepair_DEMO_20261029.en.srt',ROOT/'LabRepair_natural_narration_20261029.wav',ROOT/'LabRepair_Judge_TestBuild_20261029.zip']}}
(ROOT/'media_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
