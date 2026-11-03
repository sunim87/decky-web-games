"""Fit Brave's startup window to the active Steam/Gamescope display at launch."""
import os
import json
from pathlib import Path
import re
import subprocess
import sys


def display_size():
    for command, pattern in [
        (["/usr/bin/xrandr", "--current"], r"current\s+(\d+)\s+x\s+(\d+)"),
        (["/usr/bin/xdpyinfo"], r"dimensions:\s+(\d+)x(\d+)"),
    ]:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=3, check=True)
            match = re.search(pattern, result.stdout)
            if match:
                width, height = map(int, match.groups())
                if 320 <= width <= 16384 and 240 <= height <= 16384:
                    return width, height
        except (OSError, subprocess.SubprocessError):
            pass
    return 1280, 800


def launch_arguments(arguments, size):
    width, height = size
    # The site's fit runs before kiosk transition on some Chromium builds.
    # Leave room for startup browser decorations so its 16:9 stage is not
    # initially shrunk. Kiosk still uses the actual display's dimensions.
    startup_height = max(height, (width * 9 + 15) // 16) + 128
    return [arg for arg in arguments if not arg.startswith(("--window-size=", "--force-device-scale-factor="))] + [
        "--force-device-scale-factor=1", f"--window-size={width},{startup_height}",
    ]


def main():
    size = display_size()
    arguments = launch_arguments(sys.argv[1:], size)
    try:
        Path(__file__).with_name("display-launch.json").write_text(
            json.dumps({"display": list(size), "window_size": arguments[-1].split("=")[1]}), encoding="utf-8")
    except OSError:
        pass
    os.execv("/usr/bin/flatpak", ["/usr/bin/flatpak", *arguments])


if __name__ == "__main__":
    main()
