import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from updater import API, Updater, compare_versions


def package(version='1.3.0', name='Decky Web Games'):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        z.writestr('decky-pokebonk/plugin.json',json.dumps({'name':name}))
        z.writestr('decky-pokebonk/package.json',json.dumps({'version':version}))
        z.writestr('decky-pokebonk/main.py','')
        z.writestr('decky-pokebonk/dist/index.js','')
    return stream.getvalue()


def release(data, version='1.3.0'):
    name=f'decky-web-games-v{version}.zip'
    return {'tag_name':'v'+version,'draft':False,'prerelease':False,'assets':[
        {'name':name,'size':len(data),'digest':'sha256:'+hashlib.sha256(data).hexdigest(),
         'browser_download_url':f'https://github.com/sunim87/decky-web-games/releases/download/v{version}/{name}'}]}


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.home=Path(self.temp.name)
        self.client=Updater(self.home,'1.2.0')
        self.data=package()
        self.latest=release(self.data)
        self.calls=[]

    def tearDown(self): self.temp.cleanup()

    def open(self,url):
        self.calls.append(url)
        return io.BytesIO(json.dumps(self.latest).encode() if url==API else self.data)

    def test_semver_release_and_prerelease_order(self):
        order=['1.2.0-alpha','1.2.0-alpha.2','1.2.0-alpha.10','1.2.0-beta','1.2.0-rc.1','1.2.0','1.2.1','1.10.0','2.0.0']
        for a,b in zip(order,order[1:]): self.assertLess(compare_versions(a,b),0)
        self.assertEqual(compare_versions('v1.2.0+build.2','1.2.0'),0)

    def test_invalid_versions_are_rejected(self):
        for value in ['../1.2.3','1.2','01.2.3','1.2.3-test.01','1.2.3/other']:
            with self.assertRaises(ValueError): compare_versions(value,'1.2.0')

    def test_new_release_shows_version_and_exact_install_asset(self):
        self.latest['assets'].insert(0,{'name':'decky-web-games-v1.3.0-source.zip'})
        with patch.object(self.client,'_open',side_effect=self.open): info=self.client.check()
        self.assertTrue(info['update_available'])
        self.assertEqual(info['latest_version'],'1.3.0')
        self.assertEqual(info['asset_name'],'decky-web-games-v1.3.0.zip')

    def test_equal_or_newer_installed_build_does_not_offer_downgrade(self):
        for installed in ['1.3.0','1.4.0-test.4']:
            self.client.current=installed
            with patch.object(self.client,'_open',side_effect=self.open): result=self.client.download()
            self.assertFalse(result['update_available'])
        self.assertEqual(self.calls,[API,API])
        self.assertFalse((self.home/'Downloads').exists())

    def test_same_core_stable_release_updates_test_build(self):
        self.client.current='1.3.0-test.5'
        with patch.object(self.client,'_open',side_effect=self.open): self.assertTrue(self.client.check()['update_available'])

    def test_download_saves_verified_zip_without_extracting_or_installing(self):
        with patch.object(self.client,'_open',side_effect=self.open): info=self.client.download()
        self.assertTrue(info['downloaded'])
        path=Path(info['path'])
        self.assertEqual(path.parent,self.home/'Downloads')
        self.assertEqual(path.read_bytes(),self.data)
        self.assertEqual(list(path.parent.iterdir()),[path])
        self.assertFalse((self.home/'homebrew').exists())

    def test_wrong_checksum_removes_partial_and_preserves_existing_file(self):
        self.latest['assets'][0]['digest']='sha256:'+'0'*64
        target=self.home/'Downloads/decky-web-games-v1.3.0.zip'
        target.parent.mkdir(parents=True)
        target.write_bytes(b'keep existing file')
        with patch.object(self.client,'_open',side_effect=self.open):
            with self.assertRaises(ValueError): self.client.download()
        self.assertEqual(target.read_bytes(),b'keep existing file')
        self.assertEqual(list(target.parent.iterdir()),[target])

    def test_bad_asset_origin_and_missing_digest_are_rejected(self):
        for url in ['https://example.com/file.zip','https://github.com/other/repo/file.zip','http://github.com/sunim87/decky-web-games/releases/download/v1.3.0/decky-web-games-v1.3.0.zip']:
            self.latest=release(self.data)
            self.latest['assets'][0]['browser_download_url']=url
            with patch.object(self.client,'_open',side_effect=self.open):
                with self.assertRaises(ValueError): self.client.check()
        self.latest=release(self.data)
        self.latest['assets'][0].pop('digest')
        with patch.object(self.client,'_open',side_effect=self.open):
            with self.assertRaises(ValueError): self.client.download()

    def test_version_mismatch_does_not_leave_zip(self):
        self.data=package(version='1.2.0')
        self.latest=release(self.data)
        with patch.object(self.client,'_open',side_effect=self.open):
            with self.assertRaises(ValueError): self.client.download()
        self.assertEqual(list((self.home/'Downloads').iterdir()),[])

    def test_size_limit_and_interrupted_download_clean_up(self):
        self.latest['assets'][0]['size']-=1
        with patch.object(self.client,'_open',side_effect=self.open):
            with self.assertRaises(ValueError): self.client.download()
        self.assertEqual(list((self.home/'Downloads').iterdir()),[])

    def test_missing_asset_is_an_error_for_new_release(self):
        self.latest['assets']=[]
        with patch.object(self.client,'_open',side_effect=self.open):
            with self.assertRaises(ValueError): self.client.check()
