"""Create a verified local-review UI snapshot retaining prior hashed assets.

The clean Vite dist remains untouched. This is for an already-open local review
tab whose lazy route chunks may still refer to the previous build.
"""
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend/src'))
from awesome_stock.runtime.owner_ui import OwnerUI


def merge(source: Path, output: Path, previous: Path | None = None) -> None:
    source, output = source.resolve(), output.absolute()
    if output.exists():
        raise FileExistsError(output)
    current = OwnerUI(source)
    old = OwnerUI(previous.resolve()) if previous else None
    if output == source or output == previous:
        raise ValueError('output must be a new directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.preview-ui-', dir=output.parent) as staging_name:
        staging = Path(staging_name)
        assets = dict(current.assets)
        if old:
            for name, entry in old.assets.items():
                if name == 'index.html':
                    continue
                if name in assets and assets[name][0] != entry[0]:
                    raise ValueError(f'asset path changed without a new name: {name}')
                assets.setdefault(name, entry)
        for name, (data, _) in assets.items():
            path = staging / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        manifest = json.loads((source / 'UI_BUILD_MANIFEST.json').read_text())
        manifest['assets'] = [
            {'path': name, 'sha256': hashlib.sha256(data).hexdigest()}
            for name, (data, _) in sorted(assets.items())
        ]
        (staging / 'UI_BUILD_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
        OwnerUI(staging)
        shutil.move(staging, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Clean frontend/owner-ui/dist')
    parser.add_argument('output', type=Path, help='New local-review snapshot directory')
    parser.add_argument('--previous', type=Path, help='Previous local-review snapshot')
    args = parser.parse_args()
    merge(args.source, args.output, args.previous)
