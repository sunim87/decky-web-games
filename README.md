# Pokebonk Online for Decky Loader

[한국어](#한국어) · [English](#english) · [Download / 다운로드](https://github.com/sunim87/decky-pokebonk/releases/latest)

![Pokebonk Online artwork](assets/wide.png)

## 한국어

Steam Deck에서 공식 웹게임 [PokéBonk](https://pokebonk.com/)을 설치·제거하는 비공식 Decky Loader 플러그인입니다. **Install / Uninstall** 두 버튼과 한국어·영어 상태 안내를 제공합니다.

### 설치

1. [최신 릴리스](https://github.com/sunim87/decky-pokebonk/releases/latest)에서 `decky-pokebonk-v1.0.4.zip`을 다운로드합니다.
2. Decky Loader 설정의 개발자 메뉴에서 ZIP 설치 기능으로 파일을 선택합니다. 필요하면 Decky 개발자 모드를 켭니다.
3. Decky에서 **Pokebonk Installer**를 열고 **Install**을 누릅니다.
4. Steam 라이브러리의 **Pokebonk Online**을 실행합니다.

Brave가 없으면 공식 Flathub에서 사용자 권한으로 설치하며 기존 설치가 있으면 재사용합니다. 전체화면·X11·배율 1.25, Steam 바로가기, 게임패드 설정, 캡슐·넓은 캡슐·히어로·로고·아이콘을 함께 등록합니다. 로그인이나 게스트 시작은 게임에서 직접 선택합니다.

인터넷 연결, Decky Loader가 설치된 SteamOS 게이밍 모드와 Steam Deck 내장 컨트롤러가 필요합니다.

### 조작

| 입력 | 전달되는 동작 |
| --- | --- |
| 왼쪽 스틱 | 왼쪽 아날로그 축 / 이동 |
| 오른쪽 스틱 | 오른쪽 아날로그 축 / 카메라 |
| A/B/X/Y, LT/RT, LB/RB, 방향 패드 | 해당 게임패드 버튼 |
| 메뉴 / 보기 버튼 | Start / Select |

Steam 표준 게임패드 템플릿을 사용하며 WASD나 마우스로 변환하지 않습니다. 세부 버튼 기능은 게임 내 게임패드 설정을 따릅니다. 이동 고정 증상의 장시간 재발 여부와 모든 버튼의 실제 플레이 검증은 아직 완료하지 않았습니다.

### 제거 및 데이터 보존

**Uninstall**은 설치 기록에 있는 바로가기와 라이브러리 이미지를 제거합니다. **Brave, 브라우저 프로필, 로그인, 게임 저장 데이터, 기존 오프라인판과 다른 게임은 보존**합니다. 설치 전 조작 설정이 있으면 복원하며, 사용자가 변경한 프로필은 보존합니다. 실행 중인 게임은 먼저 종료해야 합니다.

다른 내용의 동명 바로가기는 변경하지 않습니다. 기존 수동 바로가기에 `FlatpakAppID` 정보가 있으면 Steam이 Brave까지 제거할 수 있어 자동 제거를 중단합니다. 이 플러그인이 새로 생성하는 바로가기에는 해당 정보를 넣지 않습니다.

Decky에서 플러그인 자체를 삭제하는 것과 게임 바로가기 제거는 별개입니다. 게임도 제거하려면 먼저 **Uninstall**을 누르세요. 설치 기록과 복구용 프로필은 `~/.local/share/decky-pokebonk/`에 보관됩니다.

## English

An unofficial Decky Loader plugin that installs the official [PokéBonk web game](https://pokebonk.com/) as a non-Steam shortcut. The panel has **Install / Uninstall** buttons and Korean/English status messages.

### Install

1. Download `decky-pokebonk-v1.0.4.zip` from the [latest release](https://github.com/sunim87/decky-pokebonk/releases/latest).
2. Install the ZIP through Decky Loader's developer settings. Enable developer mode if needed.
3. Open **Pokebonk Installer** in Decky and select **Install**.
4. Launch **Pokebonk Online** from your Steam library.

The installer reuses Brave or installs it from the official Flathub repository in user scope. It sets up kiosk mode, X11, scale factor 1.25, native Steam Deck gamepad controls, and all five Steam artwork roles. Choose guest play or sign in yourself inside the game.

Requires an internet connection, SteamOS Gaming Mode, Decky Loader and the built-in Steam Deck controller. Native gamepad controls follow the game's bindings; movement is not converted to WASD or mouse input. Long-session input stability and every physical button have not been fully play-tested.

### Uninstall

**Uninstall** removes the managed shortcut and its library artwork. **Brave, browser profiles, login sessions, game saves, offline builds and other games are kept.** Pre-existing controller profiles are restored when unchanged; user-edited profiles are preserved. Close the game first.

Unrelated shortcuts are not modified. Removal is blocked if a manually created shortcut contains `FlatpakAppID` metadata that could cause Steam to uninstall Brave. New shortcuts created by this plugin do not contain that metadata.

Removing the plugin from Decky does not remove the game shortcut. Use **Uninstall** first if you also want to remove it. Persistent installation records and profile backups are stored in `~/.local/share/decky-pokebonk/`.

## Development

Node.js 20+, pnpm 11.25.0, Python 3.11+:

```sh
pnpm install --frozen-lockfile
pnpm typecheck
pnpm build
python -m unittest discover -s tests -v
python scripts/package_plugin.py
```

The package script writes the install ZIP next to the repository directory. See [CHANGELOG.md](CHANGELOG.md) and [VERIFICATION.md](VERIFICATION.md) for changes and testing limits. Steam/Decky internal APIs and the online game may change independently of this plugin.

## Credits and license

This is an unofficial community installer, not an official game distribution. PokéBonk is by Charcher and is loaded from its official website. No game code or unlocked offline edition is included. The PB icon originates from the game's bundled icon; capsule, hero and wordmark artwork was generated with ImageGen. The controller profile is based on Steam's standard gamepad template.

Installer code is [MIT licensed](LICENSE). This does not grant rights to Pokémon characters, trademarks, game artwork or third-party assets. Not affiliated with Charcher, Valve, Nintendo, GAME FREAK, Creatures or The Pokémon Company.
