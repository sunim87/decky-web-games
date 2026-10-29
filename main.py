"""Unprivileged Decky backend. Steam library writes go through the frontend API."""
import asyncio
import base64
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from installer import Installer, game_info


class Plugin:
    async def _main(self):
        self.installer = Installer()
        self.installers = {"pokebonk": self.installer, "azeroth": Installer(game="azeroth")}
        self.lock = asyncio.Lock()

    async def _unload(self):
        pass

    async def _call(self, method, *args, game="pokebonk"):
        try:
            async with self.lock:
                game_info(game)
                return await getattr(self.installers[game], method)(*args)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def prepare_install(self, account: str, game: str = "pokebonk"):
        return await self._call("prepare_install", account, game=game)

    async def finish_install(self, account: str, appid: int, game: str = "pokebonk"):
        return await self._call("finish_install", account, appid, game=game)

    async def prepare_remove(self, account: str, game: str = "pokebonk"):
        return await self._call("prepare_remove", account, game=game)

    async def finish_remove(self, account: str, appid: int, game: str = "pokebonk"):
        return await self._call("finish_remove", account, appid, game=game)

    async def verify_artwork(self, account: str, appid: int, game: str = "pokebonk"):
        return await self._call("verify_artwork", account, appid, game=game)

    async def get_artwork(self, name: str, game: str = "pokebonk"):
        types = {"capsule": 0, "hero": 1, "logo": 2, "wide": 3, "icon": 4}
        if game not in self.installers or name not in types:
            return {"ok": False, "error": "알 수 없는 이미지입니다."}
        try:
            path = self.installers[game].assets / (name + ".png")
            return {"ok": True, "assets": [{"type": types[name], "data": base64.b64encode(path.read_bytes()).decode()}]}
        except OSError:
            return {"ok": False, "error": "이미지 파일을 읽을 수 없습니다."}
