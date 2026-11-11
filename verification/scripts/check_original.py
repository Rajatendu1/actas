"""Fail if any recovered provider input changes."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
for f in json.loads((root/'ORIGINAL-MANIFEST.json').read_text()):
 if f['path']=='README.md':continue # Public/current-guide curation is recorded separately.
 data=(root/'source'/f['path']).read_bytes()
 assert len(data)==f['bytes'] and hashlib.sha256(data).hexdigest()==f['sha256'] and hashlib.sha1(data).hexdigest()==f['source_sha1'],f['path']
curation=json.loads((root/'REPOSITORY-CURATION.json').read_text())
for change in curation['changed']:
 assert hashlib.sha256((root/change['path']).read_bytes()).hexdigest()==change['sha256'],change['path']
print('30/30 retained runtime provider-input files unchanged; README curated, SHA1+SHA256 verified')
