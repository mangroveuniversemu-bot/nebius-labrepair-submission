"""Bind edited receipt excerpts to exact saved source bytes, without fresh calls."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent/'nebius-labrepair'
gen=REPO/'evidence/nebius-nano-repair-20261026-1'
sbox=REPO/'evidence/nebius-sandbox-validation-20261026-1'
response=json.loads((gen/'response.json').read_text());transport=json.loads((gen/'cloud-transport-receipt.json').read_text())
operation=json.loads((sbox/'nebius-sandbox-validation-20261026-1.operation.safe.json').read_text())
guest=json.loads((sbox/'nebius-sandbox-validation-20261026-1.stdout.json').read_text())
cloud=json.loads((sbox/'nebius-sandbox-validation-20261026-1.transport.safe.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(gen/'response.json')==transport['response_sha256']
assert sha(sbox/'nebius-sandbox-validation-20261026-1.stdout.json')==cloud['guest_stdout_sha256']
assert cloud['model_response_sha256']==transport['response_sha256']
counts={r['case']:r['tests_run']-r['failures']-r['errors'] for r in guest['results']}
assert counts=={'baseline':2,'model_fix':4,'same_total_wrong_pairs':3}
assert response['usage']['prompt_tokens']==121 and response['usage']['completion_tokens']==38
assert transport['http_status']==200 and operation['duration']==1.273 and operation['networking']['enabled'] is False
files=[gen/'response.json',gen/'cloud-transport-receipt.json',sbox/'nebius-sandbox-validation-20261026-1.operation.safe.json',sbox/'nebius-sandbox-validation-20261026-1.stdout.json',sbox/'nebius-sandbox-validation-20261026-1.transport.safe.json']
record={'schema':'LABREPAIR_RELEASE_SAVED_EVIDENCE_V1','source_date_utc':'2026-10-26','new_model_or_sandbox_calls':0,'excerpts_are':'Editorial views of literal saved JSON fields, not new browser or provider capture','response_to_guest_hash_chain_verified':True,'http_status':transport['http_status'],'usage':response['usage'],'operation_duration_seconds':operation['duration'],'guest_networking_enabled':False,'protected_checks_passed':counts,'local_wrong_pair_values_matched':'0/4; distinct from protected check count','files':{p.relative_to(REPO).as_posix():sha(p) for p in files}}
(ROOT/'saved_evidence_reference.json').write_text(json.dumps(record,indent=2)+'\n')
print('Verified saved response → guest hash chain and all displayed evidence fields.')
