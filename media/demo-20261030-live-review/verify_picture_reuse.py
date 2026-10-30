"""Verify the narration-only picture cache and preserved previous movie."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent;PREV=ROOT.parent/'nebius-demo-20261030-release'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
shots=json.loads((ROOT/'cinematic_timeline.json').read_text(encoding='utf-8'))['shots']
checks={s['id']:sha(ROOT/'clips'/(s['id']+'.mp4'))==sha(PREV/'clips'/(s['id']+'.mp4')) for s in shots}
assert len(checks)==28 and all(checks.values())
movie=PREV/'LabRepair_DEMO_Release_20261030.mp4'
expected=json.loads((ROOT/'source_reference.json').read_text(encoding='utf-8'))['previous_release_movie']['sha256']
assert sha(movie)==expected
out={'schema':'LABREPAIR_LIVE_REVIEW_PICTURE_REUSE_V1','picture_clips_identical':checks,'verified_count':28,'previous_movie_unchanged':True,'previous_movie_sha256':expected,'note':'Final subtitle pixels and voice differ; base picture clips and source UI do not.'}
(ROOT/'picture_reuse_verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('28/28 base picture clips match; previous movie preserved.')
