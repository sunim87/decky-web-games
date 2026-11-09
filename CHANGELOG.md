# Changelog

## 1.1.4

- Add the official Pokebonk Linux app with verified download, Steam registration and its own library artwork.
- Rename the web entry in the plugin to Pokebonk Online Web.
- Preserve saves when uninstalling the managed app.

## 1.1.3

- Compress library artwork using 256-color PNG palettes; retain pixel dimensions and transparency.
- Add Pokemon Brave League with touch controls, an isolated Brave profile and five library artwork assets based on the official site.
- Detect the active Steam/Gamescope display at every Brave League launch and calculate fullscreen startup bounds dynamically. Confirmed on Steam Deck; other handheld resolutions are covered by automated calculations, not physical-device tests.
- Skip controller detection and template changes for the touch-only game. Preserve browser saves and existing controller profiles on uninstall.

## 1.1.2

- ROG Ally·Legion Go에서 Xbox·DualSense 계열로 인식되는 컨트롤러에도 게임패드 설정을 적용하도록 수정했습니다.
- Steam의 여러 컨트롤러 정보 형식을 처리하고, 알 수 없는 게임패드 유형에도 기본 게임패드 템플릿 적용을 시도합니다.
- 컨트롤러를 감지하지 못하거나 자동 설정을 확인하지 못해도 바로가기·이미지를 설치하고 미확인 상태를 안내합니다.
- 기존 사용자는 ZIP 업데이트 후 게임을 종료하고 각 게임의 Install을 다시 눌러 주세요.
- 자동 테스트를 통과했으며 ROG Ally·Legion Go 실기기 검증은 아직 진행하지 않았습니다.

## 1.1.1

- 디아블로 서바이버 추가

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
