"""Directory uploads use opaque identifiers, never client paths as storage roots."""
import re
from pathlib import Path

from fastapi import HTTPException

ALLOWED_EXTENSIONS = {'.py', '.md', '.js', '.html', '.css', '.ts', '.sh',
                      '.go', '.java', '.svelte'}
EXCLUDED_DIRECTORIES = {'.git', '.venv', 'venv', 'node_modules', '__pycache__',
                        'VectorStore', 'cache_embeddings', '.runtime'}
MAX_FILES = 2000
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 50 * 1024 * 1024


def upload_storage_key(source):
    if not source.startswith('upload://'):
        return None
    identifier = source[len('upload://'):]
    if not re.fullmatch(r'[0-9a-f]{32}', identifier):
        raise ValueError('Invalid uploaded repository identifier')
    return str(Path('uploads') / identifier)


async def save_directory(files, destination):
    """Validate relative paths and save supported UTF-8 source files."""
    if not files or len(files) > MAX_FILES:
        raise HTTPException(400, f'Select a directory with 1–{MAX_FILES} source files.')
    root_name = None
    entries = []
    seen = set()
    for file in files:
        filename = file.filename or ''
        parts = filename.split('/')
        if (len(parts) < 2 or any(p in ('', '.', '..') for p in parts)
                or '\\' in filename or ':' in filename
                or any(ord(c) < 32 for c in filename)):
            raise HTTPException(400, 'Invalid directory-relative file path.')
        if root_name is None:
            root_name = parts[0]
        if parts[0] != root_name:
            raise HTTPException(400, 'Select one directory at a time.')
        if any(p in EXCLUDED_DIRECTORIES for p in parts[:-1]):
            continue
        relative = Path(*parts[1:])
        if relative.suffix not in ALLOWED_EXTENSIONS:
            continue
        if relative in seen:
            raise HTTPException(400, 'Duplicate file path in directory upload.')
        seen.add(relative)
        entries.append((file, relative))

    total = 0
    saved = 0
    for file, relative in entries:
        data = bytearray()
        while chunk := await file.read(1024 * 1024):
            data.extend(chunk)
            total += len(chunk)
            if len(data) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                raise HTTPException(413, 'Upload exceeds 10 MiB per file or 50 MiB total.')
        if not data.strip():
            continue
        try:
            data.decode('utf-8')
        except UnicodeDecodeError:
            continue
        if b'\x00' in data:
            continue
        target = Path(destination) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        saved += 1
    if not saved:
        raise HTTPException(400, 'No supported, non-empty UTF-8 source files in this directory.')
    return root_name, saved
