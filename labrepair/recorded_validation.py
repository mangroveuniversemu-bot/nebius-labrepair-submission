"""Verify and summarize fixed, client-observed provider receipts for playback.

No provider request, code execution, source write or payment action is available
here. Hashes verify archived content; they are not a provider signature.
"""
import hashlib
import json

from labrepair.candidate_review import canonical_digest, unique_object
from labrepair.paths import ROOT
from labrepair.sandbox_experiment import prepare_experiment

BASE = 'evidence/nebius-sandbox-validation-20261026-1/'
PINS = {
    BASE+'nebius-sandbox-validation-20261026-1.stdout.json':'31c9900c3e55c6d2f059cf00f836f7cae836e781921d91de739da7be8f723b36',
    BASE+'nebius-sandbox-validation-20261026-1.operation.safe.json':'0a91a78904e3cb59ef33c9b0233e2bbb568c9e172d82acfef440e3f57b7ad3da',
    BASE+'nebius-sandbox-validation-20261026-1.transport.safe.json':'2065a5678f168d9844ec38060904b98c5eb8023cac7330ee355249dc28a6e6b6',
    'evidence/nebius-nano-repair-20261026-1/cloud-transport-receipt.json':'c3df4390f4990087a1ea72d78dab3cc24e1385e807b127e736c605cf30e91be7',
}


def _read(name):
    with (ROOT/name).open('rb') as stream:
        raw=stream.read(65537)
    if len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=PINS[name]:
        raise ValueError('RECORDED_PROVIDER_EVIDENCE_CHANGED')
    return json.loads(raw.decode('utf-8'),object_pairs_hook=unique_object)


def load_recorded_validation():
    guest=_read(BASE+'nebius-sandbox-validation-20261026-1.stdout.json')
    operation=_read(BASE+'nebius-sandbox-validation-20261026-1.operation.safe.json')
    transport=_read(BASE+'nebius-sandbox-validation-20261026-1.transport.safe.json')
    generation=_read('evidence/nebius-nano-repair-20261026-1/cloud-transport-receipt.json')
    pack,raw,_=prepare_experiment()  # Data and syntax preparation only.
    if not (
        operation['status']=='SUCCESS' and operation['process']['exit_code']==0
        and operation['process']['timed_out'] is False
        and operation['disposable'] is True and operation['result_image_uuid'] is None
        and operation['networking']['enabled'] is False and operation['timeout']==30
        and guest['schema']=='LABREPAIR_ACTUAL_GUEST_RESULT_V1' and guest['success'] is True
        and guest['network_interfaces']==['lo'] and guest['credentials_present'] is False
        and guest['guest_network_disabled_observed'] is True
        and guest['input_sha256']==hashlib.sha256(raw).hexdigest()
        and guest['model_response_sha256']==pack['model_response_sha256']
        and guest['checker_sha256']==pack['checker_sha256']
        and transport['guest_stdout_sha256']==PINS[BASE+'nebius-sandbox-validation-20261026-1.stdout.json']
        and transport['operation_uuid']==operation['uuid']
        and transport['post_count']==1 and transport['retries']==0
        and transport['generated_model_calls_this_stage']==0
        and generation['http_status']==200 and generation['attempted_count']==1
    ):
        raise ValueError('RECORDED_RUN_BINDING_INVALID')
    expected={c['name']:c for c in pack['cases']}
    cases=guest['results']
    if len(cases)!=3 or {c['case'] for c in cases}!=set(expected) or guest['tests_run']!=12:
        raise ValueError('RECORDED_CASE_SET_INVALID')
    labels={'baseline':'Before repair','model_fix':'NVIDIA-proposed repair','same_total_wrong_pairs':'Same total, wrong pairs'}
    display=[]
    original_claim=json.loads(pack['cases'][0]['files']['counts.json'])['original_claim']
    for c in cases:
        e=expected[c['case']]
        if not (
            c['source_sha256']==e['sha256'] and c['process_exit_code']==e['expected_exit_code']
            and c['tests_run']==4 and c['errors']==0 and c['skipped']==0
            and c['protected_files_unchanged'] is True and c['original_claim']==original_claim
            and c['expected_outcome_observed'] is True
            and c['passed']==(e['expected_exit_code']==0)
        ):
            raise ValueError('RECORDED_CASE_BINDING_INVALID')
        display.append({'case':c['case'],'label':labels[c['case']],'total_s':c['total_s'],'pairs':c['pairs'],'tests_run':4,'checks_passed':4-c['failures'],'failures':c['failures'],'process_exit_code':c['process_exit_code'],'outcome':'Repair passed' if c['case']=='model_fix' else 'Expected failure observed'})
    by_case={c['case']:c for c in display}
    if by_case['model_fix']['checks_passed']!=4 or by_case['baseline']['failures']<1 or by_case['same_total_wrong_pairs']['failures']<1:
        raise ValueError('RECORDED_CONTROL_OUTCOMES_INVALID')
    data={
        'schema':'LABREPAIR_RECORDED_LIVE_VALIDATION_V1','status':'VERIFIED_RECORDED_END_TO_END_RUN',
        'run_id':guest['run_id'],'observed_utc':transport['created_utc'],
        'description':'A real NVIDIA model suggestion generated on Nebius was independently checked, then the approved synthetic source variants ran against unchanged tests in a disposable Nebius Sandbox.',
        'generation':{'model':generation['provider_model'],**generation['usage'],'latency_ms':generation['latency_ms'],'http_status':200},
        'sandbox':{'operation_count':1,'operation_id':operation['uuid'],'image_uuid':operation['image_uuid'],'status':'SUCCESS','exit_code':0,'duration_seconds':operation['duration'],'guest_elapsed_seconds':guest['elapsed_seconds'],'python':guest['python'],'system':guest['system'],'architecture':guest['machine'],'network_interfaces':guest['network_interfaces'],'disposable':True,'result_image_uuid':None},
        'cases':display,'expected_case_outcomes_observed':3,'executed_checks':12,
        'original_claim':original_claim,'protected_files_unchanged':True,
        'candidate_execution':'ACTUAL_NEBIUS_SANDBOX_ONLY','provider_calls_by_replay':0,
        'automatic_cloud_dispatch':'DISABLED','actual_billed_currency':'unknown',
        'boundary':'Synthetic inputs only. Protected tests and counts are unchanged. The original claim remains NOT_REPRODUCED. Saved evidence playback keeps automatic cloud dispatch disabled.',
        'provenance':'Client-observed provider receipts: HTTP 201 accepted, terminal SUCCESS, Linux / '+guest['machine']+'. Hashes establish content integrity, not a provider signature. Actual billed money remains unknown.',
        'source_receipt_sha256':PINS,
    }
    data['receipt_sha256']=canonical_digest(data)
    return data
