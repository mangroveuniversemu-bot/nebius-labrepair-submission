"""Package only the new edit; unchanged source material stays in its prior package."""
from pathlib import Path
import json,hashlib,zipfile
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent/'nebius-labrepair'
items={}
names=['LabRepair_DEMO_Cinematic_20261030.mp4','LabRepair_DEMO_Cinematic_20261030.en.srt','LabRepair_cinematic_narration_20261030.wav',
 'render_cinematic.py','synthesize_narration.py','verify_cinematic.py','package_cinematic.py','cinematic_timeline.json',
 'render_receipt.json','media_verification.json','tts_receipt.json','tts_provenance.json','source_reference.json','chapters-en.txt','EDIT_README.txt']
for name in names:items[name]=(ROOT/name).read_bytes()
for p in sorted((ROOT/'audio').glob('*.wav')):items['audio/'+p.name]=p.read_bytes()
for name in ['docs/demo_narration_20261030.json','docs/CINEMATIC_REDESIGN_20261030.md']:items['source/'+name]=(REPO/name).read_bytes()
for name in ['actual_movie_contact_sheet.jpg','draft_contact_sheet.jpg','full_decode.txt']:items['qa/'+name]=(ROOT/'qa'/name).read_bytes()
manifest={'schema':'LABREPAIR_CINEMATIC_EDIT_MANIFEST_V1','kind':'DIFFERENTIAL_EDIT_PACKAGE',
 'files':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in sorted(items.items())},
 'unchanged_sources':'See source_reference.json for the prior full production archive and source hashes. Raw clips, original UI PNGs, model weights and installed dependencies are not duplicated.'}
items['MANIFEST.json']=(json.dumps(manifest,indent=2)+'\n').encode()
out=ROOT/'LabRepair_Cinematic_Edit_Package_20261030.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,6) as z:
    for n,b in items.items():z.writestr(n,b)
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    for n,m in manifest['files'].items():
        b=z.read(n);assert len(b)==m['bytes'] and hashlib.sha256(b).hexdigest()==m['sha256'],n
receipt={'name':out.name,'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'entries':len(items),'payload_hashes_verified':len(manifest['files']),'kind':'DIFFERENTIAL_EDIT_PACKAGE'}
(ROOT/'package_verification.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt))
