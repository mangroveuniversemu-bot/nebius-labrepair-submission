"""Prepare one bounded guest script from pinned synthetic inputs, never execute it.

The real model contributes only two validated literal arrays. All test logic,
source bindings, negative controls and execution policy belong to the operator.
"""
import base64
import hashlib
import json
import uuid

from labrepair.model_parameters import review_chat_response
from labrepair.paths import ROOT
from labrepair.scientific_workflow import SOURCE_PINS, _parameters, load_fixture, make_proposal

RESPONSE_SHA256 = "ed0c2272968d84c4844a1305ca0ad68560451615d147c7eaa9f4f41231419920"
CASE_CHECKER = r'''
import hashlib, importlib.util, io, json, pathlib, sys, unittest
root = pathlib.Path(sys.argv[1])
expected = json.loads(sys.argv[2])
def load(name):
    spec = importlib.util.spec_from_file_location(name, root/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
analysis, specification = load('analysis'), load('test_analysis')
counts = json.loads((root/'counts.json').read_text())
pairs = analysis.correlations(counts['rows'])
total = sum(x*y for x,y in zip(pairs,counts['chsh_terms']))
def hashes():
    return {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in expected}
class ProtectedSpecification(unittest.TestCase):
    def test_each_registered_pair(self):
        self.assertTrue(specification.check_correlations(pairs))
    def test_registered_total(self):
        self.assertAlmostEqual(total,specification.EXPECTED_S,places=12)
    def test_source_and_protected_files_unchanged(self):
        self.assertEqual(hashes(),expected)
    def test_original_claim_preserved(self):
        self.assertEqual(counts['original_claim'],{'claimed_s':'3.4','claim_state':'NOT_REPRODUCED','physical_interpretation':'NOT_ESTABLISHED'})
log = io.StringIO()
result = unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ProtectedSpecification))
print(json.dumps({'case':root.name,'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful(),'pairs':pairs,'total_s':total,'source_sha256':hashes(),'protected_files_unchanged':all(hashes()[n]==expected[n] for n in ['counts.json','test_analysis.py']),'original_claim':counts['original_claim'],'test_log':log.getvalue()},sort_keys=True,separators=(',',':')))
sys.exit(0 if result.wasSuccessful() else 1)
'''

GUEST_RUNNER = r'''
import base64, hashlib, json, os, pathlib, platform, resource, subprocess, sys, tempfile, time
pack = json.loads(base64.b64decode(PACK_B64,validate=True))
assert pack['schema']=='LABREPAIR_PINNED_SANDBOX_EXPERIMENT_V1'
assert len(pack['cases'])==3
resource.setrlimit(resource.RLIMIT_CPU,(20,20))
resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456))
interfaces = sorted(p.name for p in pathlib.Path('/sys/class/net').iterdir())
assert set(interfaces)<={'lo'},'GUEST_NETWORK_NOT_DISABLED'
assert not any(k in os.environ for k in ['NEBIUS_API_KEY','NVIDIA_API_KEY','AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY'])
results = []
started = time.monotonic()
with tempfile.TemporaryDirectory(prefix='labrepair-') as temporary:
    root = pathlib.Path(temporary)
    checker = root/'protected_checker.py'
    checker.write_text(pack['checker'],encoding='utf-8')
    assert hashlib.sha256(checker.read_bytes()).hexdigest()==pack['checker_sha256']
    for case in pack['cases']:
        case_root = root/case['name']; case_root.mkdir()
        assert set(case['files'])=={'analysis.py','counts.json','test_analysis.py'}
        for name,text in case['files'].items():
            raw = text.encode('utf-8')
            assert hashlib.sha256(raw).hexdigest()==case['sha256'][name]
            (case_root/name).write_bytes(raw)
        completed = subprocess.run([sys.executable,'-I','-S',str(checker),str(case_root),json.dumps(case['sha256'])],capture_output=True,text=True,timeout=5,env={'PATH':'/usr/local/bin:/usr/bin:/bin'})
        assert not completed.stderr,'UNEXPECTED_PROCESS_STDERR'
        assert len(completed.stdout.encode())<10000,'CASE_OUTPUT_LIMIT'
        result = json.loads(completed.stdout)
        result['process_exit_code']=completed.returncode
        result['expected_exit_code']=case['expected_exit_code']
        result['expected_outcome_observed']=completed.returncode==case['expected_exit_code']
        results.append(result)
success = all(r['expected_outcome_observed'] and r['protected_files_unchanged'] and r['tests_run']==4 and r['errors']==0 and r['skipped']==0 for r in results)
report={'schema':'LABREPAIR_ACTUAL_GUEST_RESULT_V1','run_id':pack['run_id'],'success':success,'mode':'ACTUAL_CODE_EXECUTION_INSIDE_NEBIUS_SANDBOX','python':platform.python_version(),'system':platform.system(),'machine':platform.machine(),'network_interfaces':interfaces,'guest_network_disabled_observed':True,'credentials_present':False,'checker_sha256':pack['checker_sha256'],'model_response_sha256':pack['model_response_sha256'],'input_sha256':hashlib.sha256(base64.b64decode(PACK_B64)).hexdigest(),'case_count':3,'tests_run':sum(r['tests_run'] for r in results),'elapsed_seconds':round(time.monotonic()-started,6),'results':results,'claim_promotion':'FORBIDDEN_FROM_REPAIR_RESULT'}
print(json.dumps(report,sort_keys=True,separators=(',',':')))
sys.exit(0 if success else 1)
'''


def prepare_experiment():
    files, _, contract = load_fixture()
    response = (ROOT/'evidence/nebius-nano-repair-20261026-1/response.json').read_bytes()
    if hashlib.sha256(response).hexdigest() != RESPONSE_SHA256:
        raise ValueError("OBSERVED_MODEL_RESPONSE_CHANGED")
    review = review_chat_response(response)
    if review['local_review']['local_result'] != 'LOCAL_SEMANTIC_MATCH':
        raise ValueError("MODEL_PARAMETERS_NOT_LOCALLY_VERIFIED")
    fixed = review['operator_bound_proposal']['replacements'][0]['after_utf8']
    negative = make_proposal('same-total',files,contract)['replacements'][0]['after_utf8']
    originals = {name:raw.decode('utf-8') for name,raw in files.items()}
    cases = []
    for name,source,expected in [('baseline',originals['analysis.py'],1),('model_fix',fixed,0),('same_total_wrong_pairs',negative,1)]:
        _parameters(source,originals['analysis.py'])
        contents = dict(originals,**{'analysis.py':source})
        pins = {n:hashlib.sha256(t.encode()).hexdigest() for n,t in contents.items()}
        assert all(pins[n]==SOURCE_PINS[n] for n in ('counts.json','test_analysis.py'))
        cases.append({'name':name,'origin':'OBSERVED_NVIDIA_PARAMETERS' if name=='model_fix' else 'OPERATOR_SYNTHETIC_CONTROL','files':contents,'sha256':pins,'expected_exit_code':expected})
    pack={'schema':'LABREPAIR_PINNED_SANDBOX_EXPERIMENT_V1','run_id':'nebius-sandbox-validation-20261026-1','model_response_sha256':RESPONSE_SHA256,'checker':CASE_CHECKER,'checker_sha256':hashlib.sha256(CASE_CHECKER.encode()).hexdigest(),'cases':cases}
    raw=json.dumps(pack,sort_keys=True,separators=(',',':')).encode()
    script="PACK_B64 = "+repr(base64.b64encode(raw).decode())+"\n"+GUEST_RUNNER
    compile(script,'operator_guest_script.py','exec')  # Syntax only, never execute on the host.
    return pack,raw,script.encode()


def prepare_request(image_uuid):
    if str(uuid.UUID(image_uuid)) != image_uuid:
        raise ValueError("IMMUTABLE_IMAGE_UUID_REQUIRED")
    pack,raw,script=prepare_experiment()
    request={'command':'/usr/local/bin/python3','image':image_uuid,'args':['-I','-S','-'],'shell':False,'hostname':'labrepair-demo-20261026-1','env':{'PATH':'/usr/local/bin:/usr/bin:/bin'},'preserve_env':False,'cwd':'/tmp','uid':65534,'gid':65534,'resources_limits':{'max_layer_bytes':16777216},'networking':{'enabled':False},'stdin':{'value':base64.b64encode(script).decode(),'encoding':'base64','close':True},'timeout':30,'truncate_output_at':32768,'disposable':True}
    return request,{'input_sha256':hashlib.sha256(raw).hexdigest(),'script_sha256':hashlib.sha256(script).hexdigest(),'script_bytes':len(script),'checker_sha256':pack['checker_sha256'],'model_response_sha256':RESPONSE_SHA256,'cases':[{k:v for k,v in c.items() if k!='files'} for c in pack['cases']],'cpu_and_vm_memory_configuration':'NOT_EXPOSED_BY_REST_SCHEMA; guest process limits are not VM allocation limits','model_calls':0,'host_candidate_execution':'NOT_RUN'}
