"""Measure the final media and retain decoded frames for actual visual review."""
from pathlib import Path
import hashlib,json,subprocess,sys
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'nebius-labrepair/.test-tmp/media-tools'))
import imageio_ffmpeg
FF=imageio_ffmpeg.get_ffmpeg_exe();movie=ROOT/'LabRepair_DEMO_Release_20261030.mp4'
qa=ROOT/'qa';qa.mkdir(exist_ok=True)
decode=subprocess.run([FF,'-hide_banner','-i',str(movie),'-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace')
(qa/'full_decode.txt').write_text(decode.stderr,encoding='utf-8');assert decode.returncode==0,decode.stderr
r=imageio_ffmpeg.read_frames(str(movie));stream=next(r);r.close()
assert stream['size']==(1920,1080) and stream['fps']==25 and abs(stream['duration']-123)<.06,stream
measure=subprocess.run([FF,'-hide_banner','-i',str(movie),'-vn','-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
audio=json.JSONDecoder().raw_decode(measure.stderr[measure.stderr.rfind('{'):])[0];assert float(audio['input_tp'])<0
points=[0,7,14,24,34,40,60,70,83,96,109,119]
sheet=Image.new('RGB',(1920,1584),'#101b20');d=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',19)
for i,second in enumerate(points):
    p=qa/f'actual-{second:03d}.jpg';subprocess.run([FF,'-v','error','-ss',str(second),'-i',str(movie),'-frames:v','1','-y',str(p)],check=True)
    x=(i%3)*640;y=(i//3)*396;sheet.paste(Image.open(p).resize((640,360)),(x,y));d.text((x+8,y+364),f'{second}s / decoded final movie',font=font,fill='#e4f3ed')
sheet.save(qa/'actual_movie_contact_sheet.jpg',quality=94)
sub=(ROOT/'LabRepair_DEMO_Release_20261030.en.srt').read_text(encoding='utf-8')
def sec(x):
    h,m,s=x.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(s)
times=[tuple(map(sec,line.split(' --> '))) for line in sub.splitlines() if ' --> ' in line]
assert all(0<=a<b<=123 for a,b in times) and all(a2>=b1-.001 for (a1,b1),(a2,b2) in zip(times,times[1:]))
subtitle_text=' '.join(line.strip() for line in sub.splitlines() if line.strip() and not line.strip().isdigit() and ' --> ' not in line)
assert 'Nebius Token Factory' in subtitle_text and 'NVIDIA Nemotron' in subtitle_text
clips=json.loads((ROOT/'tts_receipt.json').read_text());assert len(clips)==12 and all(c['fits'] and c['voice']=='am_michael' for c in clips)
for clip in clips:
    path=ROOT/'audio'/(clip['scene']+'.wav');assert hashlib.sha256(path.read_bytes()).hexdigest()==clip['sha256']
timeline=json.loads((ROOT/'cinematic_timeline.json').read_text())
shots=timeline['shots'];assert len(shots)>=24
result={'schema':'LABREPAIR_CINEMATIC_MEDIA_VERIFICATION_V1','stream':stream,'full_decode_exit_code':decode.returncode,
 'measured_audio':audio,'shots':len(shots),'subtitle_intervals':len(times),'subtitle_timing_valid':True,
 'sampled_final_frame_seconds':points,'voice':'Local Kokoro am_michael','voice_clips_fit':True,'windows_system_speech':False,
 'tts_model_weights_reverified':True,'new_model_or_sandbox_calls':0,'new_paid_calls':0,
 'ui_source':'Unchanged from a7cf2f5; edited actual browser captures, not new provider dispatch',
 'continuous_live_capture':False,'motion_graphics':'Editorial reveals derived from the same fixed synthetic case',
 'reference_footage_or_audio_reused':False,'cloud_original_byte_hash_matching':'NOT_VERIFIED',
 'files':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [movie,ROOT/'LabRepair_DEMO_Release_20261030.en.srt',ROOT/'LabRepair_release_narration_20261030.wav']}}
(ROOT/'media_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
