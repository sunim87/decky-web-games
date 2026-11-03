import subprocess
import unittest
from unittest.mock import patch
from display_launcher import display_size, launch_arguments


class DisplayLauncherTests(unittest.TestCase):
    def test_handheld_resolutions_and_relaunch_changes(self):
        for width, height in [(1280,800),(1920,1080),(1920,1200),(2560,1600),(800,1280)]:
            with self.subTest(size=(width,height)):
                with patch('display_launcher.subprocess.run', return_value=subprocess.CompletedProcess([],0,f'Screen 0: minimum 16 x 16, current {width} x {height}, maximum 32767 x 32767')):
                    size=display_size()
                self.assertEqual(size,(width,height))
                args=launch_arguments(['run','--window-size=1280,900','--force-device-scale-factor=2','--user-data-dir=/path with spaces','https://brave-league.github.io/'],size)
                self.assertEqual(args[-1],f'--window-size={width},{max(height,(width*9+15)//16)+128}')
                self.assertEqual(args.count('--force-device-scale-factor=1'),1)
                self.assertIn('--user-data-dir=/path with spaces',args)
                self.assertEqual(sum(a.startswith('--window-size=') for a in args),1)

    def test_fallback_and_timeout(self):
        responses=[FileNotFoundError(),subprocess.CompletedProcess([],0,'dimensions:  1920x1200 pixels')]
        with patch('display_launcher.subprocess.run',side_effect=responses):
            self.assertEqual(display_size(),(1920,1200))
        with patch('display_launcher.subprocess.run',side_effect=subprocess.TimeoutExpired('xrandr',3)):
            self.assertEqual(display_size(),(1280,800))
        with patch('display_launcher.subprocess.run',return_value=subprocess.CompletedProcess([],0,'current 0 x 0')):
            self.assertEqual(display_size(),(1280,800))
