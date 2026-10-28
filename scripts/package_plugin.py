from pathlib import Path
import hashlib
import json
import zipfile

root = Path(__file__).resolve().parents[1]
version = json.loads((root / "package.json").read_text())["version"]
output = root.parent / ("decky-pokebonk-v" + version + ".zip")
files = [root / name for name in ["main.py", "installer.py", "plugin.json", "package.json", "README.md", "LICENSE", "CHANGELOG.md"]]
files += list((root / "assets").glob("*"))
files += [root / "dist/index.js"]
with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
    for source in files:
        archive.write(source, "decky-pokebonk/" + source.relative_to(root).as_posix())
print(output)
print(hashlib.sha256(output.read_bytes()).hexdigest())
