#!/usr/bin/env python3
from pathlib import Path
import argparse, json

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--secrets', nargs='*', default=[])
    args = ap.parse_args()
    root = Path(args.root)
    findings = []
    for p in root.rglob('*'):
        if not p.is_file():
            continue
        data = p.read_bytes()
        for i, s in enumerate(args.secrets):
            if s and s.encode('utf-8') in data:
                findings.append({'path': str(p), 'secret_index': i})
    report = {'passed': not findings, 'findings': findings, 'root': str(root), 'secret_count': len([s for s in args.secrets if s])}
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 2
if __name__ == '__main__':
    raise SystemExit(main())
