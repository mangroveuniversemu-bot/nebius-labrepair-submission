"""Verify reused local model weights and identify unchanged narration bytes."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parent;PREV=ROOT.parent/'nebius-demo-20261030-release'
reference=json.loads((PREV/'tts_provenance.json').read_text())
for name,record in reference['models'].items():
 p=ROOT.parent/'nebius-demo-20261027/models'/name
 assert p.stat().st_size==record['bytes']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==record['sha256']
reference['weights_reverified_at_utc']=datetime.now(timezone.utc).isoformat()
reference['new_model_downloads']=0
(ROOT/'tts_provenance.json').write_text(json.dumps(reference,indent=2)+'\n')
receipts=json.loads((ROOT/'tts_receipt.json').read_text())
for r in receipts:
 previous=PREV/'audio'/(r['scene']+'.wav')
 r['reused_identical_text_clip']=previous.exists() and hashlib.sha256(previous.read_bytes()).hexdigest()==r['sha256']
(ROOT/'tts_receipt.json').write_text(json.dumps(receipts,indent=2)+'\n')
print('Verified both cached TTS model digests; speech seconds',sum(r['duration_seconds'] for r in receipts))
