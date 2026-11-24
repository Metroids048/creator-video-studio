"""Copy local source files without importing credentials or live process state."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat

EXCLUDED_DIRS = {'.git', 'node_modules', '__pycache__', '.pytest_cache', '.cache', '.next', '.turbo',
                 '.ssh', '.gnupg', '.aws', '.codex', 'BrowserProfile', 'chrome-profile'}
PRIVATE = re.compile(r'(^\.env($|[.-])|(^|[._-])(credentials?|secrets?|cookies?|tokens?|keys?)([._-]|$)|\.(pem|p12|pfx|key|kdbx|sock|pid)$)', re.I)

def exclude(path):
    name = path.name
    if name in EXCLUDED_DIRS or name.startswith('.venv'):
        return 'runtime/rebuildable directory' if name != '.git' else 'Git history stored separately'
    if name in {'.DS_Store', '.loop-state.json', '.npmrc', 'SingletonLock', 'SingletonCookie', 'SingletonSocket'} or name.endswith(('.lock.tmp', '.tmp')):
        return 'temporary state or machine-local config'
    if (PRIVATE.search(name) and not name.endswith(('.example', '.sample', '.template', '.md', '.py', '.js', '.mjs', '.ts'))) or name.startswith(('id_rsa', 'id_ed25519')):
        return 'credential candidate'
    return None

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def snapshot(src, dst, manifest):
    dst.mkdir(parents=True, exist_ok=True)
    tmp = manifest.with_suffix('.tmp')
    with tmp.open('w', encoding='utf-8') as stream:
        def record(path, status, **details):
            stream.write(json.dumps({'path': path.as_posix(), 'status': status, **details}, ensure_ascii=False) + '\n')

        def visit(path):
            rel = path.relative_to(src)
            dest = dst / rel
            reason = exclude(path)
            if reason:
                record(rel, 'excluded', reason=reason)
            elif path.is_symlink():
                target = os.readlink(path)
                resolved = path.resolve()
                if Path(target).is_absolute() or not resolved.is_relative_to(src) or not resolved.exists():
                    record(rel, 'missing' if not resolved.exists() else 'excluded', target=target,
                           reason='external or unresolved link')
                    return
                if any(exclude(src / part) for part in resolved.relative_to(src).parts):
                    record(rel, 'excluded', reason='link to excluded path')
                    return
                if not dest.is_symlink() and not dest.exists():
                    dest.symlink_to(target)
                if not dest.is_symlink() or os.readlink(dest) != target:
                    raise ValueError(f'destination conflicts with source link: {rel}')
                record(rel, 'linked', target=target)
            elif path.is_dir():
                dest.mkdir(exist_ok=True)
                for child in sorted(path.iterdir()):
                    visit(child)
            elif stat.S_ISREG(path.stat().st_mode):
                checksum = sha(path)
                if not dest.exists():
                    shutil.copy2(path, dest)
                if sha(dest) != checksum:
                    raise ValueError(f'checksum mismatch: {rel}')
                record(rel, 'copied', size=dest.stat().st_size, sha256=checksum)
            else:
                record(rel, 'excluded', reason='special file')
        for child in sorted(src.iterdir()):
            visit(child)
    tmp.replace(manifest)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    source, destination = args.source.resolve(), args.destination.resolve()
    if source == destination or destination.is_relative_to(source):
        parser.error('destination must be outside the source')
    snapshot(source, destination, args.manifest)
