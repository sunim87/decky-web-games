import hashlib
import json
import os
import re
import shlex
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from updater import SafeRedirect, ssl_context

REPOSITORY = "CharcherGit/pokebonk-app"


def install(root):
    opener = urllib.request.build_opener(
        SafeRedirect(), urllib.request.HTTPSHandler(context=ssl_context())
    )
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/releases/latest",
        headers={"User-Agent": "Decky-Web-Games"},
    )
    with opener.open(request, timeout=30) as response:
        release = json.load(response)
    tag = release["tag_name"]
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        raise ValueError("Unexpected Pokebonk release tag.")
    name = f"PokeBonk-{tag[1:]}-linux-x86_64.AppImage"
    asset = next((asset for asset in release["assets"] if asset["name"] == name), None)
    if asset is None:
        raise ValueError("The Pokebonk release has no Linux x86_64 AppImage.")
    digest = asset.get("digest", "")
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError("The Pokebonk release has no SHA-256 digest.")

    root.mkdir(exist_ok=True)
    payload = root / f"{tag}-{digest[7:19]}"
    if not (payload / "squashfs-root/AppRun").is_file():
        with tempfile.TemporaryDirectory(dir=root) as folder:
            staging = Path(folder)
            image = staging / name
            url = f"https://github.com/{REPOSITORY}/releases/download/{tag}/{name}"
            checksum = hashlib.sha256()
            with opener.open(url, timeout=60) as response, image.open("wb") as output:
                size = 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > asset["size"]:
                        raise ValueError("Unexpected Pokebonk download size.")
                    checksum.update(chunk)
                    output.write(chunk)
            if size != asset["size"] or "sha256:" + checksum.hexdigest() != digest:
                raise ValueError("Pokebonk download checksum mismatch.")
            image.chmod(0o700)
            subprocess.run([str(image), "--appimage-extract"], cwd=staging,
                           stdout=subprocess.DEVNULL, check=True, timeout=180)
            if not (staging / "squashfs-root/AppRun").is_file():
                raise ValueError("The Pokebonk package has no launcher.")
            image.unlink()
            os.replace(staging, payload)

    launcher = root / "launch.sh"
    temporary = root / "launch.tmp"
    working = shlex.quote(str(payload / "squashfs-root"))
    temporary.write_text(
        "#!/bin/sh\nunset LD_PRELOAD LD_LIBRARY_PATH\n"
        f"cd {working} || exit 1\n"
        'exec ./AppRun --ozone-platform=x11 "$@"\n',
        encoding="utf-8", newline="\n",
    )
    temporary.chmod(0o755)
    temporary.replace(launcher)
    return launcher
