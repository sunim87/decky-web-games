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
