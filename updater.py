"""Public GitHub release checks and verified ZIP downloads; never installs code."""
import hashlib
import json
from pathlib import Path
import re
import ssl
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

REPO = "sunim87/decky-web-games"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
MAX_ZIP = 128 * 1024 * 1024
VERSION = re.compile(r"v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?")


def parse_version(value):
    match = VERSION.fullmatch(value) if isinstance(value, str) and len(value) <= 128 else None
    if not match:
        raise ValueError("버전 정보를 읽을 수 없습니다.\nCould not read the version information.")
    pre = match[4].split(".") if match[4] else None
    if pre and any(p.isdigit() and len(p) > 1 and p[0] == "0" for p in pre):
        raise ValueError("Invalid prerelease version")
    return tuple(int(match[n]) for n in (1, 2, 3)), pre


def compare_versions(left, right):
    a, ap = parse_version(left)
    b, bp = parse_version(right)
    if a != b: return (a > b) - (a < b)
    if ap is None or bp is None:
        return (ap is None) - (bp is None)
    ak = tuple((0, int(p)) if p.isdigit() else (1, p) for p in ap)
    bk = tuple((0, int(p)) if p.isdigit() else (1, p) for p in bp)
    return (ak > bk) - (ak < bk)


def ssl_context():
    try:
        from helpers import get_ssl_context
        return get_ssl_context()
    except ImportError:
        return ssl.create_default_context()


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        host = parsed.hostname or ""
        if parsed.scheme != "https" or not (host == "github.com" or host.endswith(".githubusercontent.com")):
            raise ValueError("다운로드 주소를 확인하지 못했습니다.\nCould not verify the download destination.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Updater:
    def __init__(self, home, current_version):
        parse_version(current_version)
        self.home = Path(home)
        self.current = current_version
        self.opener = urllib.request.build_opener(SafeRedirect(), urllib.request.HTTPSHandler(context=ssl_context()))

    def _open(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": "Decky-Web-Games-Updater", "Accept": "application/vnd.github+json" if url == API else "application/octet-stream"})
        return self.opener.open(req, timeout=30)

    def latest(self):
        with self._open(API) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024: raise ValueError("Release response too large")
        release = json.loads(raw)
        tag = release.get("tag_name", "")
        parse_version(tag)
        version = tag.removeprefix("v")
        if release.get("draft") or release.get("prerelease"):
            raise ValueError("공개 정식 버전을 확인하지 못했습니다.\nCould not find a public stable release.")
        name = f"decky-web-games-v{version}.zip"
        asset = next((a for a in release.get("assets", []) if a.get("name") == name), None)
        available = compare_versions(version, self.current) > 0
        info = {"ok": True, "installed_version": self.current, "latest_version": version, "update_available": available}
        if available:
            if not asset:
                raise ValueError("최신 버전의 설치 ZIP이 없습니다.\nThe latest release has no install ZIP.")
            expected = f"https://github.com/{REPO}/releases/download/{urllib.parse.quote(tag, safe='')}/{urllib.parse.quote(name, safe='')}"
            url = urllib.parse.urlsplit(asset.get("browser_download_url", ""))
            if (url.scheme != "https" or url.netloc != "github.com" or url.query or url.fragment
                    or urllib.parse.unquote(url.path) != urllib.parse.unquote(urllib.parse.urlsplit(expected).path)):
                raise ValueError("다운로드 주소를 확인하지 못했습니다.\nCould not verify the download destination.")
            if type(asset.get("size")) is not int or not 0 < asset["size"] <= MAX_ZIP:
                raise ValueError("설치 ZIP 크기가 올바르지 않습니다.\nThe install ZIP size is invalid.")
            digest = asset.get("digest", "") or ""
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
                raise ValueError("파일 검증 정보를 확인하지 못했습니다.\nCould not verify the file checksum information.")
            info.update(asset_name=name, size=asset["size"])
        return info, asset

    def check(self):
        return self.latest()[0]

    def _verify_zip(self, path, version):
        with zipfile.ZipFile(path) as archive:
            expected = {"decky-pokebonk/plugin.json", "decky-pokebonk/package.json", "decky-pokebonk/main.py", "decky-pokebonk/dist/index.js"}
            if not expected.issubset(archive.namelist()): raise ValueError("Invalid plugin ZIP")
            for name in ("plugin.json", "package.json"):
                entry = "decky-pokebonk/" + name
                if archive.getinfo(entry).file_size > 128 * 1024: raise ValueError("Invalid plugin metadata size")
            metadata = json.loads(archive.read("decky-pokebonk/plugin.json"))
            package = json.loads(archive.read("decky-pokebonk/package.json"))
            if metadata.get("name") != "Decky Web Games" or compare_versions(package.get("version", ""), version) != 0:
                raise ValueError("ZIP version or plugin mismatch")

    def download(self):
        # Refresh at click time so a stale button cannot download an old release.
        info, asset = self.latest()
        if not info["update_available"]: return info
        destination = self.home / "Downloads"
        destination.mkdir(parents=True, exist_ok=True)
        path = destination / info["asset_name"]
        digest = asset["digest"].split(":", 1)[1]
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=destination, prefix=".decky-web-games-", suffix=".part", delete=False) as output:
                temp = Path(output.name)
                actual = hashlib.sha256()
                total = 0
                with self._open(asset["browser_download_url"]) as response:
                    while chunk := response.read(65536):
                        total += len(chunk)
                        if total > asset["size"] or total > MAX_ZIP: raise ValueError("Download size limit exceeded")
                        actual.update(chunk)
                        output.write(chunk)
            if total != asset["size"] or actual.hexdigest() != digest:
                raise ValueError("다운로드 파일 검증에 실패했습니다. 다시 시도하세요.\nDownload verification failed. Please try again.")
            self._verify_zip(temp, info["latest_version"])
            temp.replace(path)
            return {**info, "downloaded": True, "path": str(path)}
        finally:
            if temp and temp.exists(): temp.unlink()


def error_reply(exc):
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 404:
            return {"ok": False, "error": "공개된 릴리스를 찾지 못했습니다.\nNo published release was found."}
        if exc.code in (403, 429):
            return {"ok": False, "error": "GitHub 요청이 제한됐습니다. 잠시 후 다시 시도하세요.\nGitHub rate limit reached. Please try again later."}
    if isinstance(exc, ValueError) and "\n" in str(exc):
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "error": "업데이트 확인 또는 다운로드에 실패했습니다. 인터넷 연결을 확인하세요.\nUpdate check or download failed. Check your connection and try again."}
