import base64
import hashlib
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from installer import Installer, NAME, OPTIONS, matches
from main import Plugin
from test_installer import binary, entry


class MultiGameTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.config = self.home / '.local/share/Steam/userdata/123/config'
        self.config.mkdir(parents=True)
        self.pb = Installer(self.home)
        self.az = Installer(self.home, game='azeroth')
        self.pb.ensure_brave = AsyncMock()
        self.az.ensure_brave = AsyncMock()

    def tearDown(self):
        self.temp.cleanup()

    def test_native_webgpu_launch_is_isolated(self):
        options = shlex.split(self.az.launch_options())
        self.assertIn('--enable-unsafe-webgpu', options)
        self.assertIn('--filesystem=/run/udev:ro', options)
        self.assertEqual(options[-1], 'https://wow.aethus.pl/')
        self.assertTrue(any(x.startswith('--user-data-dir=') for x in options))
        self.assertEqual(self.pb.launch_options(), OPTIONS)
        self.assertNotIn('--enable-unsafe-webgpu', OPTIONS)
        self.assertNotIn('utm_', self.az.launch_options())

    def test_dedicated_browser_path_keeps_spaces_in_one_argument(self):
        backend = Installer(self.home / 'with spaces', game='azeroth')
        profile = [x for x in shlex.split(backend.launch_options()) if x.startswith('--user-data-dir=')]
        self.assertEqual(len(profile), 1)
        self.assertIn('with spaces', profile[0])

    def test_identity_requires_exact_game_url(self):
        az = entry(AppName='Azeroth Survivors', LaunchOptions=self.az.launch_options())
        self.assertTrue(matches(az, 'azeroth'))
        self.assertFalse(matches(az))
        az['LaunchOptions'] = az['LaunchOptions'].replace('https://wow.aethus.pl/', 'https://wow.aethus.pl/evil')
        self.assertFalse(matches(az, 'azeroth'))
        with self.assertRaises(ValueError): Installer(self.home, game='../azeroth')

    def test_game_browser_disables_first_run_analytics_notice_only_in_its_own_profile(self):
        normal = self.home / '.var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser/Local State'
        normal.parent.mkdir(parents=True)
        normal.write_text('{"unrelated":"keep"}')
        local = self.home / '.var/app/com.brave.Browser/config/azeroth-survivors/Local State'
        local.parent.mkdir(parents=True)
        local.write_text('{"unrelated":"preserve","brave":{"p3a":{"enabled":true}}}')
        self.az.configure_browser_profile()
        data = json.loads(local.read_text())
        self.assertEqual(data['unrelated'], 'preserve')
        self.assertFalse(data['brave']['p3a']['enabled'])
        self.assertTrue(data['brave']['p3a']['notice_acknowledged'])
        self.assertEqual(json.loads(normal.read_text()), {'unrelated':'keep'})
        backup = self.az.state / 'browser-local-state-backup.json'
        self.assertTrue(json.loads(backup.read_text())['brave']['p3a']['enabled'])
        self.az.configure_browser_profile()
        self.assertTrue(json.loads(backup.read_text())['brave']['p3a']['enabled'])

    async def test_install_and_remove_are_independent(self):
        pb = await self.pb.prepare_install('123')
        az = await self.az.prepare_install('123')
        self.assertEqual(pb['name'], NAME)
        self.assertEqual(az['name'], 'Azeroth Survivors')
        self.assertNotEqual(pb['icon'], az['icon'])
        await self.pb.finish_install('123', 0x80000001)
        await self.az.finish_install('123', 0x80000002)
        entries = [entry(appid=0x80000001), entry(appid=0x80000002, AppName=az['name'], LaunchOptions=az['options'])]
        (self.config / 'shortcuts.vdf').write_bytes(binary(entries))
        save = self.home / '.var/app/com.brave.Browser/config/azeroth-survivors/save'
        save.parent.mkdir(parents=True, exist_ok=True)
        save.write_text('keep my progress')
        pb_manifest = self.pb.manifest('123').read_bytes()
        pb_profile = self.pb.profile('123').read_bytes()
        self.assertEqual((await self.az.prepare_remove('123'))['appid'], 0x80000002)
        await self.az.finish_remove('123', 0x80000002)
        self.assertEqual(self.pb.manifest('123').read_bytes(), pb_manifest)
        self.assertEqual(self.pb.profile('123').read_bytes(), pb_profile)
        self.assertFalse(self.az.manifest('123').exists())
        self.assertEqual(save.read_text(), 'keep my progress')

    async def test_azeroth_artwork_cannot_accept_pokebonk_files(self):
        appid = 0x80000002
        grid = self.config / 'grid'
        grid.mkdir()
        roles = {'capsule':'p','wide':'','hero':'_hero','logo':'_logo'}
        for role,suffix in roles.items():
            (grid / f'{appid}{suffix}.png').write_bytes((self.az.assets / f'{role}.png').read_bytes())
        self.assertTrue((await self.az.verify_artwork('123', appid))['ok'])
        (grid / f'{appid}.png').write_bytes((self.pb.assets / 'wide.png').read_bytes())
        with patch('installer.asyncio.sleep', new=AsyncMock()):
            with self.assertRaises(RuntimeError): await self.az.verify_artwork('123', appid)

    async def test_changed_manifest_target_is_not_adopted(self):
        await self.az.prepare_install('123')
        await self.az.finish_install('123', 0x80000002)
        (self.config / 'shortcuts.vdf').write_bytes(binary([entry(appid=0x80000002)]))
        with self.assertRaises(RuntimeError): await self.az.prepare_install('123')

    async def test_backend_routes_artwork_and_rejects_traversal(self):
        plugin = Plugin()
        plugin.installers = {'pokebonk':self.pb,'azeroth':self.az}
        az = await plugin.get_artwork('icon', 'azeroth')
        self.assertEqual(base64.b64decode(az['assets'][0]['data']), (self.az.assets / 'icon.png').read_bytes())
        self.assertFalse((await plugin.get_artwork('../icon', 'azeroth'))['ok'])
        self.assertFalse((await plugin.get_artwork('icon', '../azeroth'))['ok'])
