"""Create a bounded production handover with per-entry byte hashes."""
from pathlib import Path
import zipfile,json,hashlib
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent/'nebius-labrepair'
def sha(b):return hashlib.sha256(b).hexdigest()
items={}
for name in ['LabRepair_DEMO_20261029.mp4','LabRepair_DEMO_20261029.en.srt','LabRepair_natural_narration_20261029.wav',
 'LabRepair_Judge_TestBuild_20261029.zip','test_build_receipt.json','asset_manifest.json','asset_contact_sheet.jpg','tts_receipt.json','tts_provenance.json',
 'render_receipt.json','media_verification.json','render_demo.py','synthesize_narration.py','verify_media.py','package_production.py','PRODUCTION_README.txt']:
    items[name]=(ROOT/name).read_bytes()
for name in ['docs/demo_narration_20261029.json','docs/DESIGN_REVIEW_20261029.md','evidence/judge_browser_acceptance_20261029.json','evidence/poc_validation_20261029.json']:
    items['source/'+name]=(REPO/name).read_bytes()
session=json.loads((ROOT/'recording/session.json').read_text())
items['recording/session.json']=(ROOT/'recording/session.json').read_bytes()
for f in session['frames']:items['recording/'+f['file']]=(ROOT/'recording'/f['file']).read_bytes()
for folder in ['inputs','audio']:
    for p in sorted((ROOT/folder).iterdir()):
        if p.is_file():items[folder+'/'+p.name]=p.read_bytes()
for name in ['judge-desktop.png','actual_movie_contact_sheet.jpg','full_decode.txt']:
    items['qa/'+name]=(ROOT/'qa'/name).read_bytes()
manifest={'schema':'LABREPAIR_PRODUCTION_MANIFEST_V3','ui_source_commit':'a7cf2f5629975a00511beadd9e2a90eac3349a52',
 'files':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in sorted(items.items())},
 'limits':['No model weights, installed packages or credentials included.','UI code test build is the exact named Git commit.','Future cloud delivery records are separate from this frozen source bundle.','Recorded execution is historical, not new provider calls.']}
items['MANIFEST.json']=(json.dumps(manifest,indent=2)+'\n').encode()
out=ROOT/'LabRepair_DEMO_Production_20261029.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,6) as z:
    for name,b in items.items():z.writestr(name,b)
with zipfile.ZipFile(out) as z:
    assert len(z.namelist())==len(items) and z.testzip() is None
    for name,meta in manifest['files'].items():
        raw=z.read(name);assert len(raw)==meta['bytes'] and sha(raw)==meta['sha256'],name
record={'name':out.name,'bytes':out.stat().st_size,'sha256':sha(out.read_bytes()),'entries':len(items),'payload_hashes_verified':len(manifest['files'])}
(ROOT/'package_verification.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record))
