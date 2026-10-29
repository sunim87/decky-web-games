import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import shlex

ROOT = Path(__file__).resolve().parent
NAME = "Pokebonk Online"
BRAVE = "com.brave.Browser"
OPTIONS = "run --branch=stable --arch=x86_64 --filesystem=/run/udev:ro --command=brave com.brave.Browser --no-first-run --no-default-browser-check --ozone-platform=x11 --kiosk --force-device-scale-factor=1.25 --enable-features=OverlayScrollbar https://pokebonk.com/"
GAMES = {
    "pokebonk": {"name": NAME, "url": "https://pokebonk.com/"},
    "azeroth": {"name": "Azeroth Survivors", "url": "https://wow.aethus.pl/"},
}


def game_info(game):
    if game not in GAMES:
        raise ValueError("알 수 없는 게임입니다.")
    return GAMES[game]


def read_shortcuts(data):
    pos = 0
    def string():
        nonlocal pos
        end = data.index(0, pos)
        result = data[pos:end].decode("utf-8")
        pos = end + 1
        return result
    def obj():
        nonlocal pos
        result = {}
        while True:
            kind = data[pos]
            pos += 1
            if kind == 8:
                return result
            key = string()
            if kind == 0:
                value = obj()
            elif kind == 1:
                value = string()
            elif kind == 2:
                value = struct.unpack_from("<I", data, pos)[0]
                pos += 4
            elif kind == 7:
                value = struct.unpack_from("<Q", data, pos)[0]
                pos += 8
            else:
                raise ValueError("Steam 바로가기 형식을 읽을 수 없습니다.")
            result[key] = value
    return list(obj().get("shortcuts", {}).values())


def matches(entry, game="pokebonk"):
    info = game_info(game)
    return (entry.get("AppName") == info["name"]
            and entry.get("Exe", "").strip('"') == "/usr/bin/flatpak"
            and BRAVE in entry.get("LaunchOptions", "")
            and info["url"] in shlex.split(entry.get("LaunchOptions", "")))


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temp.replace(path)


class Installer:
    def __init__(self, home=None, state=None, game="pokebonk"):
        info = game_info(game)
        self.game = game
        self.name = info["name"]
        self.assets = ROOT / "assets" if game == "pokebonk" else ROOT / "assets" / game
        self.home = Path(home or os.environ.get("DECKY_USER_HOME", str(Path.home()))).resolve()
        self.steam = self.home / ".local/share/Steam"
        if not self.steam.is_dir():
            candidate = self.home / ".steam/steam"
            if candidate.is_dir(): self.steam = candidate.resolve()
        # User-owned persistent location survives plugin updates/uninstallation.
        self.state = Path(state or self.home / ".local/share/decky-pokebonk")
        if game != "pokebonk": self.state = self.state / game
        self.state.mkdir(parents=True, exist_ok=True)

    def account_dir(self, account):
        if not isinstance(account, str) or not re.fullmatch(r"[1-9][0-9]{0,9}", account) or int(account) > 0xffffffff:
            raise ValueError("Steam 사용자 정보를 확인하지 못했습니다.")
        p = self.steam / "userdata" / account / "config"
        if not p.is_dir(): raise ValueError("현재 Steam 사용자 폴더를 찾지 못했습니다.")
        return p

    def manifest(self, account):
        self.account_dir(account)
        return self.state / (account + ".json")

    def entries(self, account):
        p = self.account_dir(account) / "shortcuts.vdf"
        return read_shortcuts(p.read_bytes()) if p.exists() else []

    def find_existing(self, account):
        named = [e for e in self.entries(account) if e.get("AppName") == self.name]
        if any(not matches(e, self.game) for e in named):
            raise ValueError("같은 이름의 다른 바로가기가 있습니다. 이름을 변경한 뒤 설치하세요.")
        if len(named) > 1: raise ValueError("동일한 게임 바로가기가 여러 개 있습니다. 중복을 정리한 뒤 시도하세요.")
        return named[0].get("appid") if named else None

    def assert_stopped(self, appid):
        marker = ("AppId=" + str(appid)).encode()
        for proc in Path("/proc").glob("[0-9]*/cmdline"):
            try:
                args = proc.read_bytes().split(b"\0")
                if marker in args and any(b"reaper" in arg for arg in args[:1]):
                    raise RuntimeError("게임을 종료한 뒤 다시 시도하세요.")
            except (OSError, PermissionError):
                continue

    async def command(self, *args, timeout=900, allow_fail=False):
        env = os.environ.copy()
        for key in list(env):
            if key in {"LD_PRELOAD", "LD_LIBRARY_PATH", "PYTHONHOME", "PYTHONPATH"} or key.startswith("STEAM_RUNTIME"):
                env.pop(key, None)
        env["HOME"] = str(self.home)
        env["XDG_DATA_HOME"] = str(self.home / ".local/share")
        env["XDG_CONFIG_HOME"] = str(self.home / ".config")
        env["PATH"] = "/usr/local/bin:/usr/bin:/bin"
        proc = await asyncio.create_subprocess_exec(*args, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        try:
            output, _ = await asyncio.wait_for(proc.communicate(), timeout)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            proc.kill()
            await proc.wait()
            raise RuntimeError("설치 시간이 초과됐습니다. 네트워크를 확인하고 다시 시도하세요.")
        text = output.decode(errors="replace")
        if proc.returncode and not allow_fail:
            raise RuntimeError("명령 실행 실패: " + text[-1400:])
        return proc.returncode, text

    async def ensure_brave(self):
        if not Path("/usr/bin/flatpak").is_file(): raise RuntimeError("Flatpak이 필요합니다. SteamOS에서 실행하세요.")
        for scope in ("--user", "--system"):
            code, _ = await self.command("/usr/bin/flatpak", "info", scope, BRAVE, allow_fail=True)
            if code == 0: return
        await self.command("/usr/bin/flatpak", "remote-add", "--user", "--if-not-exists", "flathub", "https://flathub.org/repo/flathub.flatpakrepo")
        await self.command("/usr/bin/flatpak", "install", "--user", "-y", "flathub", BRAVE)
        code, _ = await self.command("/usr/bin/flatpak", "info", "--user", BRAVE, allow_fail=True)
        if code: raise RuntimeError("Brave 설치를 확인하지 못했습니다.")

    def profile(self, account):
        return self.steam / "steamapps/common/Steam Controller Configs" / account / "config" / self.name.lower() / "controller_neptune.vdf"

    def launch_options(self):
        if self.game == "pokebonk": return OPTIONS
        # A separate browser process is required: an existing Brave process ignores new GPU flags.
        profile = self.home / ".var/app" / BRAVE / "config/azeroth-survivors"
        return ("run --branch=stable --arch=x86_64 --filesystem=/run/udev:ro --command=brave "
                + BRAVE + " --no-first-run --no-default-browser-check --ozone-platform=x11 --kiosk "
                "--enable-unsafe-webgpu --enable-features=Vulkan --use-angle=vulkan "
                "--user-data-dir=" + shlex.quote(str(profile)) + " " + GAMES[self.game]["url"])

    def configure_browser_profile(self):
        if self.game != "azeroth": return
        profile = self.home / ".var/app" / BRAVE / "config/azeroth-survivors"
        marker = ("--user-data-dir=" + str(profile)).encode()
        for proc in Path("/proc").glob("[0-9]*/cmdline"):
            try:
                if marker in proc.read_bytes().split(b"\0"):
                    raise RuntimeError("게임을 종료한 뒤 다시 시도하세요.")
            except OSError:
                continue
        local_state = profile / "Local State"
        data = json.loads(local_state.read_text(encoding="utf-8")) if local_state.exists() else {}
        # This profile belongs only to this game. Do not alter the user's normal Brave profile.
        if local_state.exists() and not (self.state / "browser-local-state-backup.json").exists():
            shutil.copy2(local_state, self.state / "browser-local-state-backup.json")
        prefs = data.setdefault("brave", {}).setdefault("p3a", {})
        prefs["enabled"] = False
        prefs["notice_acknowledged"] = True
        atomic_json(local_state, data)

    def backup_profile(self, account):
        marker = self.state / (account + ".profile-backup.json")
        if marker.exists(): return
        target = self.profile(account)
        backup = self.state / (account + ".controller-backup.vdf")
        if target.exists(): shutil.copy2(target, backup)
        atomic_json(marker, {"existed": target.exists()})

    async def prepare_install(self, account):
        self.account_dir(account)
        old = self.manifest(account)
        existing = self.find_existing(account)
        if old.exists():
            managed = json.loads(old.read_text())
            if existing and existing != managed["appid"]: raise RuntimeError("기존 설치 기록과 바로가기가 다릅니다.")
            if any(e.get("appid") == managed["appid"] and not matches(e, self.game) for e in self.entries(account)):
                raise RuntimeError("기존 설치 기록과 바로가기가 다릅니다.")
            existing = existing or managed["appid"]
        if existing: self.assert_stopped(existing)
        if any(not (self.assets / (role + ".png")).is_file() for role in ("capsule", "wide", "hero", "logo", "icon")):
            raise RuntimeError("이미지 파일을 읽을 수 없습니다.")
        await self.ensure_brave()
        self.configure_browser_profile()
        assets = self.state / "assets"
        assets.mkdir(exist_ok=True)
        for source in self.assets.glob("*.png"):
            shutil.copy2(source, assets / source.name)
        self.backup_profile(account)
        target = self.profile(account)
        target.parent.mkdir(parents=True, exist_ok=True)
        text = (ROOT / "assets/controller_neptune.vdf").read_text(encoding="utf-8")
        text = text.replace("Pokebonk Online - Gamepad", self.name + " - Gamepad")
        text = text.replace("__PROFILE_URL__", "autosave://" + str(target))
        text = text.replace("__STEAMID__", str(76561197960265728 + int(account)))
        target.write_text(text, encoding="utf-8")
        return {"ok": True, "name": self.name, "existing": existing, "icon": str(assets / "icon.png"), "config": "template://controller_neptune_gamepad_joystick.vdf", "home": '"' + str(self.home) + '"', "options": self.launch_options()}

    async def finish_install(self, account, appid):
        self.account_dir(account)
        if type(appid) is not int or not 0x80000000 <= appid <= 0xffffffff: raise ValueError("올바르지 않은 바로가기 ID입니다.")
        profile = self.profile(account)
        if not profile.is_file(): raise ValueError("조작 설정 파일이 없습니다. 설치를 다시 시도하세요.")
        atomic_json(self.manifest(account), {"version": 1, "appid": appid, "profile_sha256": hashlib.sha256(profile.read_bytes()).hexdigest()})
        return {"ok": True}

    async def verify_artwork(self, account, appid):
        config = self.account_dir(account)
        if type(appid) is not int or not 0x80000000 <= appid <= 0xffffffff:
            raise ValueError("올바르지 않은 바로가기 ID입니다.")
        roles = {"capsule": "p", "wide": "", "hero": "_hero", "logo": "_logo"}
        expected = {name: hashlib.sha256((self.assets / (name + ".png")).read_bytes()).digest() for name in roles}
        for attempt in range(30):
            bad = []
            for name, suffix in roles.items():
                target = config / "grid" / (str(appid) + suffix + ".png")
                if not target.is_file() or hashlib.sha256(target.read_bytes()).digest() != expected[name]:
                    bad.append(name)
            if not bad: return {"ok": True}
            await asyncio.sleep(0.2)
        raise RuntimeError("Steam 이미지 적용을 확인하지 못했습니다: " + ", ".join(bad))

    async def prepare_remove(self, account):
        p = self.manifest(account)
        if not p.exists(): return {"ok": True, "message": "설치 기록이 없습니다. 설치 버튼으로 기존 항목을 등록할 수 있습니다."}
        manifest = json.loads(p.read_text())
        self.assert_stopped(manifest["appid"])
        for entry in self.entries(account):
            if entry.get("appid") == manifest["appid"] and not matches(entry, self.game):
                raise RuntimeError("바로가기 내용이 변경되어 자동 제거를 중단했습니다.")
            if entry.get("appid") == manifest["appid"] and entry.get("FlatpakAppID"):
                raise RuntimeError("기존 바로가기에 Brave 자동 제거 연결 정보가 있습니다. 브라우저 보호를 위해 자동 제거를 중단했습니다.")
        return {"ok": True, "appid": manifest["appid"]}

    async def finish_remove(self, account, appid):
        p = self.manifest(account)
        if not p.exists(): return {"ok": True}
        manifest = json.loads(p.read_text())
        if type(appid) is not int or manifest["appid"] != appid: raise ValueError("설치 기록과 제거 대상이 다릅니다.")
        target = self.profile(account)
        marker = self.state / (account + ".profile-backup.json")
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == manifest["profile_sha256"]:
            if marker.exists() and json.loads(marker.read_text()).get("existed"):
                shutil.copy2(self.state / (account + ".controller-backup.vdf"), target)
            else: target.unlink()
        # Retain changed profiles and all browser data. Never recursively delete user directories.
        p.unlink()
        if marker.exists(): marker.unlink()
        return {"ok": True}
