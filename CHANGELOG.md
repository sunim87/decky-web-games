# Changelog

## 1.1.0

- Add Azeroth Survivors alongside Pokebonk, with separate Install/Uninstall buttons.
- Keep each game's manifests, controller profiles and artwork separate.
- Launch Azeroth with a dedicated Brave profile, read-only gamepad identification access and Linux WebGPU/Vulkan options.
- Disable Brave P3A and its first-run infobar in the dedicated Azeroth profile.
- Add generated capsule, wide capsule, hero, transparent logo and icon for Azeroth.
- Preserve both games' browser data when uninstalling either shortcut.
- Add multi-game isolation and frontend rollback tests. Physical Steam Deck launch, gamepad and uninstall/reinstall validated; long-session testing pending.

## 1.0.4

- Expose `/run/udev` read-only when launching Brave so Chromium can identify Steam Input's virtual gamepad.
- Existing installations need Install again to refresh launch options, followed by a full game restart.

- Use Steam's native gamepad template instead of WASD/mouse conversion.
- Select the built-in Steam Deck controller by its actual controller index.
- Pass Steam's configuration selection type and verify gamepad-only input.
- Preserve an existing profile backup.

## 1.0.2

- Korean and English status messages on separate lines.

## 1.0.1

- Prevent the shortcut icon from overwriting the wide capsule.
- Verify artwork against bundled SHA-256 hashes before reporting success.

## 1.0.0

- Brave installation, official web-game shortcut, Steam artwork and controller setup.
- Managed shortcut removal with browser and save preservation.
- Block unsafe removal of legacy shortcuts containing Flatpak uninstall metadata.
