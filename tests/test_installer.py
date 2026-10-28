import asyncio
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installer import Installer, OPTIONS, NAME, matches, read_shortcuts


def binary(entries):
    def emit(obj):
        data = b""
        for key, value in obj.items():
            kind = 0 if isinstance(value, dict) else 2 if isinstance(value, int) else 1
            data += bytes([kind]) + key.encode() + b"\0"
            data += emit(value) if kind == 0 else struct.pack("<I", value) if kind == 2 else value.encode() + b"\0"
        return data + b"\x08"
    return emit({"shortcuts": {str(i): e for i, e in enumerate(entries)}})


def entry(appid=4183725916, **changes):
    result = {"appid": appid, "AppName": NAME, "Exe": '"/usr/bin/flatpak"', "LaunchOptions": OPTIONS}
    result.update(changes)
    return result


class InstallerTests(unittest.IsolatedAsyncioTestCase):
    def test_native_gamepad_profile_does_not_emit_keyboard_or_mouse(self):
        from installer import ROOT
        text = (ROOT / "assets/controller_neptune.vdf").read_text()
        self.assertIn("Pokebonk Online - Gamepad", text)
        self.assertNotIn("key_press", text)
        self.assertNotIn("mouse_button", text)
        self.assertIn('"xinput_button A"', text)
        self.assertIn('"joystick active"', text)
        self.assertIn('"right_joystick active"', text)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.backend = Installer(self.home)
        self.config = self.home / ".local/share/Steam/userdata/123/config"
        self.config.mkdir(parents=True)
        self.backend.ensure_brave = AsyncMock()

    def tearDown(self): self.temp.cleanup()

    def shortcuts(self, *entries):
        (self.config / "shortcuts.vdf").write_bytes(binary(entries))

    async def test_roundtrip_and_existing_adoption(self):
        self.shortcuts(entry())
        r = await self.backend.prepare_install("123")
        self.assertEqual(r["existing"], 4183725916)
        self.assertEqual(read_shortcuts(binary([entry()])), [entry()])

    async def test_fresh_prepare_and_idempotent_finish(self):
        r = await self.backend.prepare_install("123")
        self.assertIsNone(r["existing"])
        self.assertEqual(r["config"], "template://controller_neptune_gamepad_joystick.vdf")
        await self.backend.finish_install("123", 0x80000001)
        await self.backend.finish_install("123", 0x80000001)
        r = await self.backend.prepare_install("123")
        self.assertEqual(r["existing"], 0x80000001)
        profile = self.backend.profile("123").read_text()
        self.assertNotIn("__PROFILE_URL__", profile)
        self.assertNotIn("__STEAMID__", profile)
        self.assertIn("76561197960265851", profile)

    async def test_reject_same_name_unrelated_app(self):
        self.shortcuts(entry(Exe="/tmp/other"))
        with self.assertRaises(ValueError): await self.backend.prepare_install("123")
        self.backend.ensure_brave.assert_not_awaited()

    async def test_reject_duplicate_matching_entries(self):
        self.shortcuts(entry(), entry(4183725917))
        with self.assertRaises(ValueError): self.backend.find_existing("123")

    async def test_reject_path_traversal_and_bad_ids(self):
        for bad in ["../123", "123/../../", "0", "4294967296", "123x"]:
            with self.assertRaises(ValueError): self.backend.account_dir(bad)
        await self.backend.prepare_install("123")
        for bad in [0, 42, True, 0x100000000]:
            with self.assertRaises(ValueError): await self.backend.finish_install("123", bad)

    async def test_restore_preexisting_profile_preserve_browser(self):
        p = self.backend.profile("123"); p.parent.mkdir(parents=True); p.write_text("original")
        browser = self.home / ".var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser/Default/Local Storage/save"
        browser.parent.mkdir(parents=True); browser.write_text("progress")
        await self.backend.prepare_install("123"); await self.backend.finish_install("123", 0x80000001)
        self.assertTrue((await self.backend.prepare_remove("123"))["ok"])
        await self.backend.finish_remove("123", 0x80000001)
        self.assertEqual(p.read_text(), "original")
        self.assertEqual(browser.read_text(), "progress")
        self.assertNotIn("appid", await self.backend.prepare_remove("123"))

    async def test_preserve_user_edited_profile(self):
        await self.backend.prepare_install("123"); await self.backend.finish_install("123", 0x80000001)
        p = self.backend.profile("123"); p.write_text("user edit")
        await self.backend.finish_remove("123", 0x80000001)
        self.assertEqual(p.read_text(), "user edit")

    async def test_reject_changed_shortcut_before_remove(self):
        await self.backend.prepare_install("123"); await self.backend.finish_install("123", 0x80000001)
        self.shortcuts(entry(0x80000001, LaunchOptions="https://another.example/"))
        with self.assertRaises(RuntimeError): await self.backend.prepare_remove("123")

    async def test_reject_steam_flatpak_uninstall_metadata(self):
        await self.backend.prepare_install("123"); await self.backend.finish_install("123", 0x80000001)
        self.shortcuts(entry(0x80000001, FlatpakAppID="com.brave.Browser"))
        with self.assertRaisesRegex(RuntimeError, "Brave"):
            await self.backend.prepare_remove("123")
        self.assertTrue(self.backend.manifest("123").exists())

    async def test_removal_id_mismatch_does_not_delete(self):
        await self.backend.prepare_install("123"); await self.backend.finish_install("123", 0x80000001)
        with self.assertRaises(ValueError): await self.backend.finish_remove("123", 0x80000002)
        self.assertTrue(self.backend.manifest("123").exists())

    async def test_missing_brave_installs_user_scope_only(self):
        self.backend.ensure_brave = Installer.ensure_brave.__get__(self.backend)
        self.backend.command = AsyncMock(side_effect=[(1,""),(1,""),(0,""),(0,""),(0,"")])
        with patch("installer.Path.is_file", return_value=True): await self.backend.ensure_brave()
        calls = [c.args for c in self.backend.command.await_args_list]
        self.assertIn(("/usr/bin/flatpak", "install", "--user", "-y", "flathub", "com.brave.Browser"), calls)
        self.assertFalse(any("sudo" in c for c in calls))

    async def test_brave_reuse_does_not_install(self):
        self.backend.ensure_brave = Installer.ensure_brave.__get__(self.backend)
        self.backend.command = AsyncMock(return_value=(0,""))
        with patch("installer.Path.is_file", return_value=True): await self.backend.ensure_brave()
        self.assertEqual(self.backend.command.await_count, 1)

    async def test_install_failure_leaves_other_game_untouched(self):
        self.shortcuts(entry(42, AppName="Other game"))
        original = (self.config / "shortcuts.vdf").read_bytes()
        self.backend.ensure_brave.side_effect = RuntimeError("offline")
        with self.assertRaises(RuntimeError): await self.backend.prepare_install("123")
        self.assertEqual((self.config / "shortcuts.vdf").read_bytes(), original)
        self.assertFalse(self.backend.manifest("123").exists())

    async def test_artwork_verification_detects_icon_overwriting_wide(self):
        from installer import ROOT
        import shutil
        grid = self.config / "grid"; grid.mkdir()
        for name, suffix in {"capsule":"p", "wide":"", "hero":"_hero", "logo":"_logo"}.items():
            shutil.copy2(ROOT / "assets" / (name + ".png"), grid / (str(0x80000001) + suffix + ".png"))
        self.assertTrue((await self.backend.verify_artwork("123", 0x80000001))["ok"])
        shutil.copy2(ROOT / "assets/icon.png", grid / (str(0x80000001) + ".png"))
        with patch("installer.asyncio.sleep", new=AsyncMock()):
            with self.assertRaisesRegex(RuntimeError, "wide"):
                await self.backend.verify_artwork("123", 0x80000001)
