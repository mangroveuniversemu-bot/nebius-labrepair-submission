"""Decode and measure the exported movie; no browser/provider requests."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'nebius-labrepair/.test-tmp/media-tools'))
sys.path.insert(0,str(ROOT.parent/'nebius-demo-20261027/tools'))
import imageio_ffmpeg
from PIL import Image,ImageDraw
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
movie=ROOT/'LabRepair_DEMO_NeuralVoice_20261028.mp4'
run=subprocess.run([ffmpeg,'-hide_banner','-i',str(movie),'-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace')
assert run.returncode==0,run.stderr
(ROOT/'qa/full_decode.txt').write_text(run.stderr,encoding='utf-8')
reader=imageio_ffmpeg.read_frames(str(movie));metadata=next(reader);reader.close()
assert metadata['size']==(1920,1080) and abs(metadata['fps']-25)<.001
assert abs(metadata['duration']-160)<.05
loud=subprocess.run([ffmpeg,'-hide_banner','-i',str(movie),'-vn','-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
level=json.JSONDecoder().raw_decode(loud.stderr[loud.stderr.rfind('{'):])[0]
assert float(level['input_tp'])<0
points=[5,12,29,55,80,105,123,139,154]
for second in points:
    subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-ss',str(second),'-i',str(movie),'-frames:v','1',str(ROOT/'qa'/f'actual-{second:03d}.png')],check=True)
sheet=Image.new('RGB',(1920,1194),'#dfe8df');d=ImageDraw.Draw(sheet)
for index,second in enumerate(points):
    x=(index%3)*640;y=(index//3)*398
    sheet.paste(Image.open(ROOT/'qa'/f'actual-{second:03d}.png').resize((640,360)),(x,y))
    d.text((x+8,y+367),str(second)+' seconds / decoded MP4',fill='#173438')
sheet.save(ROOT/'qa/actual_movie_contact_sheet.png')
srt=(ROOT/'LabRepair_DEMO_20261028.en.srt').read_text(encoding='utf-8')
def sec(value):
    h,m,s=value.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(s)
times=[tuple(map(sec,line.split(' --> '))) for line in srt.splitlines() if ' --> ' in line]
assert all(0<=a<b<=160 for a,b in times)
assert all(a2>=b1-.001 for (a1,b1),(a2,b2) in zip(times,times[1:]))
assert 'Nebius Token Factory' in srt and 'NVIDIA Nemotron' in srt
clips=json.loads((ROOT/'tts_receipt.json').read_text())
assert all(c['fits'] for c in clips)
result={'schema':'LABREPAIR_MEDIA_VERIFICATION_V2','source_ui_commit':'4c1cc58bf244db9b3a63704a12c62068136bbd72',
 'movie':{'name':movie.name,'size_bytes':movie.stat().st_size,'sha256':hashlib.sha256(movie.read_bytes()).hexdigest()},
 'stream':metadata,'full_decode_exit_code':run.returncode,'measured_audio':level,
 'decoded_frames_inspected_at_seconds':points,'subtitle_intervals':len(times),'subtitle_timing_valid':True,
 'tts_clips_fit':True,'spoken_product_names_in_script':['Nebius Token Factory','NVIDIA Nemotron'],
 'generic_neural_voice':'Kokoro af_heart','windows_system_speech':False,'new_paid_tts_calls':0,
 'provider_calls_during_recording':0,'continuous_real_time_desktop_video':False,
 'recording_method':'Timestamped actual browser screenshot frames during real interactions; edited holds, crop focus and omitted waits.',
 'raw_download_wait_preserved_in_provenance':True,'submission_ready':False}
(ROOT/'media_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))

