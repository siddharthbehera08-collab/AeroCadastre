import os
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
ignore_dirs = {'.git', 'node_modules', '.next', '.venv', '.venv-gpu', '__pycache__', 'dist', 'build', '.cache', 'data'}

secret_regexes = [
    ('Google API Key', re.compile(r'AIza[0-9A-Za-z-_]{35}')),
    ('Private Key', re.compile(r'-----BEGIN (?:RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----')),
    ('AWS Access Key ID', re.compile(r'AKIA[0-9A-Z]{16}')),
    ('Hardcoded Secret Token Assignment', re.compile(r'(?:api_key|access_token|secret_key|private_key)\s*=\s*[\'"][0-9a-zA-Z\-_]{20,}[\'"]', re.IGNORECASE)),
]

findings = []
files_scanned = 0

for p in root.rglob('*'):
    if not p.is_file():
        continue
    if any(part in ignore_dirs for part in p.parts):
        continue
    if p.suffix in ['.py', '.ts', '.tsx', '.js', '.json', '.env', '.example', '.ini', '.sql', '.sh', '.ps1', '.yml', '.yaml', '.toml']:
        files_scanned += 1
        try:
            lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
            rel_p = str(p.relative_to(root)).replace('\\', '/')
            for idx, line in enumerate(lines, 1):
                # skip comments or doc templates
                if line.strip().startswith('#') or line.strip().startswith('//'):
                    continue
                for stype, pat in secret_regexes:
                    if pat.search(line):
                        findings.append((rel_p, idx, stype))
        except Exception:
            pass

print(f"Scanned {files_scanned} files for secrets.")
print(f"Total potential secret findings: {len(findings)}")
for f in findings:
    print(f"FILE: {f[0]}, LINE: {f[1]}, TYPE: {f[2]}")
