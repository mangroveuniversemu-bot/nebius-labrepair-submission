"""Render generic neural narration with already verified local Kokoro weights."""
import hashlib,json,os,sys,time,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CACHED=ROOT.parent/'nebius-demo-20261027'
REPO=ROOT.parents[1] if (ROOT.parents[1]/'labrepair').is_dir() else ROOT.parent/'nebius-labrepair'
if not REPO.is_dir(): REPO=ROOT
MODEL_ROOT=ROOT/'models' if (ROOT/'models/kokoro-v1.0.onnx').is_file() else CACHED/'models'
sys.path.insert(0,str(CACHED/'tools'))
os.environ.setdefault('OMP_NUM_THREADS','4')
import soundfile as sf
import numpy as np
from kokoro_onnx import Kokoro
spec=json.loads((REPO/'docs/demo_narration_20261030.json').read_text(encoding='utf-8-sig'))
old_path=REPO/'docs/demo_narration_20261028.json'
old=json.loads(old_path.read_text(encoding='utf-8-sig')) if old_path.is_file() else {'scenes':[]}
oldtext={s['id']:s['narration'] for s in old['scenes']}
engine=Kokoro(str(MODEL_ROOT/'kokoro-v1.0.onnx'),str(MODEL_ROOT/'voices-v1.0.bin'))
receipts=[]
force_ids=set(sys.argv[1:])
for scene in spec['scenes']:
    path=ROOT/'audio'/(scene['id']+'.wav')
    started=time.perf_counter()
    reused=False
    if not path.exists() or scene['id'] in force_ids:
        if reused and (CACHED/'audio'/path.name).is_file():
            shutil.copyfile(CACHED/'audio'/path.name,path)
        else:
            audio,sr=engine.create(scene['narration'],voice='am_michael',speed=.97,lang='en-us',sentence_pause=.24,clause_pause=.1)
            sf.write(path,audio,sr,subtype='PCM_16')
    audio,sr=sf.read(path)
    duration=len(audio)/sr
    record={'scene':scene['id'],'voice':'am_michael','sample_rate':sr,'duration_seconds':duration,'text_sha256':hashlib.sha256(scene['narration'].encode()).hexdigest(),
    'scene_seconds':scene['duration'],'fits':duration+.32<scene['duration'],'reused_identical_text_clip':reused,
    'peak':float(np.max(np.abs(audio))),'rms':float(np.sqrt(np.mean(audio*audio))),
    'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
    'elapsed_seconds':round(time.perf_counter()-started,3),'cloud_tts_requests':0,'windows_system_speech':False}
    receipts.append(record)
    print(json.dumps(record),flush=True)
(ROOT/'tts_receipt.json').write_text(json.dumps(receipts,indent=2)+'\n',encoding='utf-8')
assert all(r['fits'] for r in receipts),'A scene is too short for natural narration; extend that scene before rendering.'
