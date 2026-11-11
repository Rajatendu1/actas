"""Check untouched recovery bytes and hash-pinned documented maintenance edits."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
original=json.loads((root/'ORIGINAL-MANIFEST.json').read_text())
curation=json.loads((root/'REPOSITORY-CURATION.json').read_text())
changes={entry['path']:entry for entry in curation['changed']}
assert len(changes)==len(curation['changed']), 'duplicate curation paths'
assert set(changes)<={"source/"+f['path'] for f in original}, 'unknown curation path'
unchanged=0
for f in original:
 path='source/'+f['path'];data=(root/path).read_bytes()
 if path in changes:
  assert hashlib.sha256(data).hexdigest()==changes[path]['sha256'],path
 else:
  assert len(data)==f['bytes'] and hashlib.sha256(data).hexdigest()==f['sha256'] and hashlib.sha1(data).hexdigest()==f['source_sha1'],path
  unchanged+=1
assert unchanged==curation['unchanged_original_files']
print(f'{unchanged}/{len(original)} recovered inputs byte-identical; {len(changes)} documented maintenance edits hash-verified')
