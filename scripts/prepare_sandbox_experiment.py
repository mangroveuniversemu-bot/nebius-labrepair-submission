"""Emit one reviewable Sandbox request; does not submit it or execute the code."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from labrepair.sandbox_experiment import prepare_request


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    request,manifest=prepare_request(args.image)
    raw=json.dumps(request,separators=(',',':')).encode()
    with args.output.open('xb') as f:f.write(raw)
    manifest.update(request_sha256=hashlib.sha256(raw).hexdigest(),request_bytes=len(raw))
    with args.output.with_suffix('.manifest.json').open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
