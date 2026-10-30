"""Check the bounded judge release manifest without executing candidates/providers."""
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'evidence/judge_release_20261028.json'


def file_digest(name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name:
        raise ValueError('UNSAFE_MANIFEST_PATH')
    target = ROOT.joinpath(*relative.parts)
    if not target.resolve().is_relative_to(ROOT) or any(p.is_symlink() for p in (target, *target.parents)):
        raise ValueError('UNSAFE_MANIFEST_PATH')
    with target.open('rb') as stream:
        raw = stream.read(1048577)
    if len(raw) > 1048576:
        raise ValueError('MANIFEST_FILE_TOO_LARGE')
    # Portable across Git's Windows CRLF checkout conversion. Not a byte signature.
    canonical = raw.decode('utf-8-sig').replace('\r\n', '\n').encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()


def check(data):
    if data['schema'] != 'LABREPAIR_JUDGE_RELEASE_V1' or not 5 <= len(data['files']) <= 200:
        raise ValueError('INVALID_MANIFEST')
    for name, expected in data['files'].items():
        if file_digest(name) != expected:
            raise ValueError('RELEASE_FILE_DRIFT: ' + name)
    combined = json.dumps(data['files'], sort_keys=True, separators=(',', ':')).encode()
    if hashlib.sha256(combined).hexdigest() != data['source_tree_sha256']:
        raise ValueError('RELEASE_TREE_DRIFT')
    return {'status': 'PASS', 'checked_files': len(data['files']),
            'source_tree_sha256': data['source_tree_sha256'],
            'scope': 'UTF-8 LF content integrity, not provider signature or deployment',
            'provider_calls': 0}


if __name__ == '__main__':
    try:
        result = check(json.loads(MANIFEST.read_text(encoding='utf-8-sig')))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)}))
        raise SystemExit(1)
    print(json.dumps(result, indent=2))
