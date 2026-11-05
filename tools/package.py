"""Package only original mod files, source tools and review evidence."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib,json
root=Path(__file__).resolve().parents[1]
out=root/'dist';out.mkdir(exist_ok=True)
files=list((root/'ViewpointFinishers').rglob('*'))
files += [root/'README.md',root/'Install.ps1',root/'CHANGELOG.md']
files += [root/'validation'/name for name in ['STATUS.md','static.json','polish-tests.log','choreography.json','runtime-0.4.0.log','runtime-0.4.1.log','knife-reverse-0.4.1.gif','new-finishers-0.4.0.gif','gameplay-preview-0.3.1.gif']]
files=[p for p in files if p.is_file()]
assert all(p.suffix.lower() not in {'.jar','.dll','.exe','.class'} for p in files)
archive=out/'ViewpointFinishers-0.4.1.zip'
with ZipFile(archive,'w',ZIP_DEFLATED,compresslevel=9) as z:
    for file in sorted(files):z.write(file,file.relative_to(root).as_posix())
with ZipFile(archive) as z:
    assert z.testzip() is None
    for file in files:
        assert z.read(file.relative_to(root).as_posix())==file.read_bytes()
manifest={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(out/'SHA256.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(f'Verified {archive.name}: {len(files)} files; {archive.stat().st_size} bytes')
