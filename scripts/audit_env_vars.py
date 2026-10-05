import os
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
ignore_dirs = {'.git', 'node_modules', '.next', '.venv', '.venv-gpu', '__pycache__', 'dist', 'build', '.cache'}

patterns = [
    ('os.getenv / environ.get', re.compile(r'os\.(?:getenv|environ\.get)\s*\(\s*[\'"]([A-Za-z0-9_]+)[\'"](?:,\s*([^\)]+))?')),
    ('os.environ[]', re.compile(r'os\.environ\s*\[\s*[\'"]([A-Za-z0-9_]+)[\'"]\s*\]')),
    ('process.env', re.compile(r'process\.env\.([A-Za-z0-9_]+)')),
    ('$env:', re.compile(r'\$env:([A-Za-z0-9_]+)')),
    ('%VAR%', re.compile(r'%([A-Za-z0-9_]+)%')),
]

# Also search for BaseSettings fields in backend
pydantic_settings_pat = re.compile(r'class\s+([A-Za-z0-9_]*Settings[A-Za-z0-9_]*)\s*\((?:BaseSettings|Settings)')

results = {}
files_scanned = 0

for p in root.rglob('*'):
    if not p.is_file():
        continue
    if any(part in ignore_dirs for part in p.parts):
        continue
    if p.suffix in ['.py', '.ts', '.tsx', '.js', '.jsx', '.ps1', '.sh', '.bat', '.env', '.example', '.ini', '.json', '.yml', '.yaml', '.toml', '.md']:
        files_scanned += 1
        try:
            content = p.read_text(encoding='utf-8', errors='ignore')
            rel_path = str(p.relative_to(root)).replace('\\', '/')
            for kind, pat in patterns:
                for match in pat.finditer(content):
                    var_name = match.group(1)
                    # Ignore common powershell or system variables if purely shell builtins
                    default_val = match.group(2).strip() if (kind == 'os.getenv / environ.get' and match.lastindex >= 2 and match.group(2)) else None
                    results.setdefault(var_name, []).append({
                        'file': rel_path,
                        'kind': kind,
                        'default': default_val
                    })
        except Exception as e:
            pass

print(f"Scanned {files_scanned} files.")
print(f"Found {len(results)} potential environment variable names:\n")
for var in sorted(results.keys()):
    occurrences = results[var]
    unique_files = sorted(list(set(o['file'] for o in occurrences)))
    defaults = list(set(o['default'] for o in occurrences if o['default']))
    print(f"=== {var} ===")
    print(f"  Files ({len(unique_files)}): {unique_files}")
    if defaults:
        print(f"  Defaults found in code: {defaults}")
