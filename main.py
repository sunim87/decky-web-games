"""Unprivileged Decky backend. Steam library writes go through the frontend API."""
import asyncio
import base64
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from installer import Installer


class Plugin:
    async def _main(self):
        self.installer = Installer()
        self.lock = asyncio.Lock()

    async def _unload(self):
        pass

    async def _call(self, method, *args):
        try:
            async with self.lock:
                return await getattr(self.installer, method)(*args)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def prepare_install(self, account: str):
        return await self._call("prepare_install", account)

    async def finish_install(self, account: str, appid: int):
        return await self._call("finish_install", account, appid)

    async def prepare_remove(self, account: str):
        return await self._call("prepare_remove", account)

    async def finish_remove(self, account: str, appid: int):
        return await self._call("finish_remove", account, appid)

    async def verify_artwork(self, account: str, appid: int):
        return await self._call("verify_artwork", account, appid)

    async def get_artwork(self, name: str):
        types = {"capsule": 0, "hero": 1, "logo": 2, "wide": 3, "icon": 4}
        if name not in types:
            return {"ok": False, "error": "알 수 없는 이미지입니다."}
        return {"ok": True, "assets": [{"type": types[name], "data": base64.b64encode((ROOT / "assets" / (name + ".png")).read_bytes()).decode()}]}
