# Verification / 검증 범위

Verified on a physical Steam Deck in SteamOS Gaming Mode with Decky Loader on 2026-10-29.

- Python regression tests: 15 passed.
- TypeScript typecheck and Rollup production build passed.
- Decky frontend and Python backend loaded successfully.
- Install, uninstall and reinstall were exercised using the actual panel buttons.
- Final shortcut removal preserved Brave and its existing browser profile.
- Launching the official web game from a newly installed shortcut was verified.
- Portrait capsule, wide capsule, hero and logo files were compared with their original SHA-256 hashes and visually checked in Steam.
- The shortcut icon uses SetShortcutIcon; the artwork icon slot is avoided because it overwrote the wide capsule on the tested Steam version.
- Native gamepad selection was confirmed through Steam's API and activation log: bUsesGamepad=true, bUsesKeyboard=false, bUsesMouse=false, bSelected=true.

## Limits

Long-session movement stability, every physical button, external controllers, multiple Steam accounts and other devices have not been fully play-tested. Selecting a native gamepad profile is verified; this is not a claim that every input bug is fixed.

Steam/Decky internal APIs and the online game may change independently of this plugin.

## 한국어 요약

실제 스팀덱에서 설치·제거·재설치, Brave 및 브라우저 프로필 보존, 공식 웹게임 실행, 이미지 적용, 네이티브 게임패드 프로필 선택을 확인했습니다. 테스트 15개와 타입 검사·빌드를 통과했습니다. 장시간 이동 고정 재발 여부, 모든 물리 버튼, 외부 패드 및 다른 기기는 완전 검증하지 않았습니다.

## v1.0.4 device visibility

On the affected Steam Deck, Steam Input reported a selected gamepad-only profile and created a virtual Xbox controller. Brave could read its event device but could not read `/run/udev/data`. Adding read-only udev access made `ID_INPUT_JOYSTICK=1` visible inside the Flatpak sandbox. After a full browser restart, the user confirmed that in-game gamepad input works normally.
## v1.1.0

- 23 Python regression tests passed, including independent game records, profile preservation, cross-game artwork rejection and exact URL identity.
- Frontend simulated Steam/Decky tests passed for installing both games, separate artwork routes, native controller selection, isolated uninstall and rollback after controller setup failure.
- TypeScript typecheck and production build passed.
- Official Azeroth v0.127.0 menu and native gamepad settings were observed in a desktop browser.
- Physical Steam Deck Gaming Mode: test plugin installed, Azeroth shortcut created (separate from Pokebonk), all four library artwork hashes verified, native gamepad-only template selected, and AMD RDNA 2 WebGPU adapter initialized. Official game menu rendered. Installation/removal is blocked while the game runs. The user confirmed physical gamepad controls working; world rendering, uninstall/reinstall, preserved browser data and unchanged local storage hashes across reinstall were verified. A first-run Brave analytics infobar was reproduced and fixed by disabling P3A and acknowledging its notice in the dedicated game profile. Long-session performance and stability remain untested.
## D2 Survivors — v1.1.1

- 25 Python tests passed, plus frontend three-game install/artwork/uninstall isolation and rollback checks; typecheck and build passed.
- Installed the local test build on Steam Deck and created a separate D2 shortcut, retaining both existing games.
- Four Steam library artwork files passed hash verification; the icon uses its own copied file.
- Selected gamepad-only native Steam Deck controls and verified the browser sees a standard Xbox controller after physical input.
- Official hosted-files selection loaded the title and Rogue Encampment without a local Diablo installation. This was the site's own setup action; no game files or hosted assets are bundled in the plugin.
- D2 uses its own browser profile and does not require Azeroth's WebGPU flags. P3A is disabled and its notice acknowledged in that dedicated profile.
- Long-session behavior and D2 physical uninstall/reinstall have not been tested. The automated isolation/preservation tests passed; the user confirmed gamepad controls during play.

D2 Korean follow-up: the game initially used en-US from the new browser profile. D2 now launches with Korean UI/accept-language defaults; ko-KR and the Korean game document were verified after relaunch, and the official game language preference was saved as ko. Other games keep their language settings.

Game menu UI: physical Steam Deck DOM checks passed for all-collapsed initial state, opening each of the three games, switching the open game, and collapsing it again. Exactly one Install/Uninstall pair is shown for the selected game. Final screenshot confirms both status lines fit on screen.

Updater: 36 Python tests passed, plus simulated update UI checks for new/current/newer installed versions, busy state, download completion and retry. On Steam Deck, the installed plugin queried the public GitHub latest release and its real UI showed up-to-date without a downgrade button. A separate process simulating v1.0.4 downloaded the real public v1.1.0 install ZIP, verified the SHA-256 and ZIP metadata, and saved it directly in `/home/deck/Downloads/`. That test did not change the installed version. The newer-release UI branch was tested with fixtures, not by publishing a test release.
