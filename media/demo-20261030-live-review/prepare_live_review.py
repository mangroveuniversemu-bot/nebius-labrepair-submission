"""Prepare a private narration-only revision; previous movies stay unchanged."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parent;PREV=ROOT.parent/'nebius-demo-20261030-release'
for name in ['audio','clips','frames','temp','qa']:(ROOT/name).mkdir(exist_ok=True)
spec=json.loads((PREV/'narration.json').read_text(encoding='utf-8'))
oldtext={s['id']:s['narration'] for s in spec['scenes']}
changes={
'01_question':'Two patches. Same total. One is wrong. LabRepair.',
'02_hook':'AI agents now patch research code.',
'03_wrong':'Check only the final number, and a wrong repair can look right. LabRepair checks the evidence.',
'07_model':'NVIDIA Nemotron on Nebius Token Factory proposed this repair. We told it which channels to flip. It returned two arrays; counts and tests stayed protected.',
'11_person':'This synthetic case does not prove a quantum result. It shows how to make a repair, and its limits, inspectable.',
'12_close':'Try the wrong-pair case. Leave a decision the next reviewer can inspect.'}
for s in spec['scenes']:
 if s['id'] in changes:s['narration']=changes[s['id']]
spec['schema']='LABREPAIR_LIVE_REVIEW_NARRATION_V1'
spec['timing_reason']='Keep the verified 123-second picture timing. Measure every new voice clip locally before rendering.'
(ROOT/'narration.json').write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8')
for s in spec['scenes']:
 if s['narration']==oldtext[s['id']]:shutil.copyfile(PREV/'audio'/(s['id']+'.wav'),ROOT/'audio'/(s['id']+'.wav'))
for name in ['source_reference.json','saved_evidence_reference.json','tts_provenance.json','cinematic_timeline.json']:
 shutil.copyfile(PREV/name,ROOT/name)
for clip in (PREV/'clips').glob('*.mp4'):shutil.copyfile(clip,ROOT/'clips'/clip.name)
for name in ['synthesize_narration.py','verify_cached_tts.py','bind_saved_evidence.py']:
 source=(PREV/name).read_text(encoding='utf-8')
 source=source.replace("PREV=ROOT.parent/'nebius-demo-20261030'","PREV=ROOT.parent/'nebius-demo-20261030-release'")
 (ROOT/name).write_text(source,encoding='utf-8')
for source_name,target_name in [('render_release.py','render_live_review.py'),('verify_release.py','verify_live_review.py')]:
 source=(PREV/source_name).read_text(encoding='utf-8')
 source=source.replace('LabRepair_DEMO_Release_20261030','LabRepair_DEMO_LiveReview_20261030').replace('LabRepair_release_narration_20261030','LabRepair_live_review_narration_20261030')
 (ROOT/target_name).write_text(source,encoding='utf-8')
previous=PREV/'LabRepair_DEMO_Release_20261030.mp4'
reference=json.loads((ROOT/'source_reference.json').read_text(encoding='utf-8'))
reference['previous_release_movie']={'name':previous.name,'bytes':previous.stat().st_size,'sha256':hashlib.sha256(previous.read_bytes()).hexdigest()}
reference['current_revision']='Narration-only refinement; all 28 picture clips unchanged; no deployed URL implied.'
(ROOT/'source_reference.json').write_text(json.dumps(reference,indent=2)+'\n',encoding='utf-8')
print('Prepared 123-second private narration refinement; 28 picture clips preserved.')
