import { ButtonItem, PanelSection, PanelSectionRow, staticClasses } from "@decky/ui";
import { callable, definePlugin, toaster } from "@decky/api";
import { Fragment, useRef, useState } from "react";

declare const SteamClient: any;
declare const App: any;
declare const appStore: any;
declare const ControllerStore: any;
declare const controllerConfiguratorStore: any;

type Game = "pokebonk" | "azeroth" | "d2";
const games: {id: Game; name: string}[] = [{id:"pokebonk",name:"Pokebonk Online"},{id:"azeroth",name:"Azeroth Survivors"},{id:"d2",name:"D2 Survivors"}];
type Reply = {name?: string; ok: boolean; error?: string; message?: string; appid?: number; existing?: number; icon?: string; config?: string; home?: string; options?: string; assets?: {type: number; data: string}[]};
const prepare = callable<[account: string, game: Game], Reply>("prepare_install");
const finish = callable<[account: string, appid: number, game: Game], Reply>("finish_install");
const removal = callable<[account: string, game: Game], Reply>("prepare_remove");
const clean = callable<[account: string, appid: number, game: Game], Reply>("finish_remove");
const artwork = callable<[name: string, game: Game], Reply>("get_artwork");
const verifyArtwork = callable<[account: string, appid: number, game: Game], Reply>("verify_artwork");
type UpdateReply = {ok: boolean; error?: string; installed_version?: string; latest_version?: string; update_available?: boolean; downloaded?: boolean; path?: string};
const checkUpdate = callable<[], UpdateReply>("check_update");
const downloadUpdate = callable<[], UpdateReply>("download_update");
const translations: Record<string, string> = {
  "작업에 실패했습니다.": "The operation failed.",
  "알 수 없는 게임입니다.": "Unknown game.",
  "이미지 파일을 읽을 수 없습니다.": "Could not read the artwork files.",
  "Steam 라이브러리 갱신을 확인하지 못했습니다. 잠시 후 다시 시도하세요.": "Could not confirm the Steam library update. Please try again shortly.",
  "게임을 종료한 뒤 다시 시도하세요.": "Close the game and try again.",
  "Steam 바로가기를 만들지 못했습니다.": "Could not create the Steam shortcut.",
  "제거할 항목이 없습니다.": "There is nothing to uninstall.",
  "설치 기록이 없습니다. 설치 버튼으로 기존 항목을 등록할 수 있습니다.": "No installation record. Use Install to register an existing shortcut.",
  "Steam 사용자 정보를 확인하지 못했습니다.": "Could not identify the current Steam user.",
  "현재 Steam 사용자 폴더를 찾지 못했습니다.": "Could not find the current Steam user folder.",
  "같은 이름의 다른 바로가기가 있습니다. 이름을 변경한 뒤 설치하세요.": "An unrelated shortcut has the same name. Rename it before installing.",
  "동일한 게임 바로가기가 여러 개 있습니다. 중복을 정리한 뒤 시도하세요.": "Multiple game shortcuts were found. Remove duplicates and try again.",
  "기존 설치 기록과 바로가기가 다릅니다.": "The shortcut does not match the installation record.",
  "Flatpak이 필요합니다. SteamOS에서 실행하세요.": "Flatpak is required. Run this plugin on SteamOS.",
  "Brave 설치를 확인하지 못했습니다.": "Could not verify the Brave installation.",
  "설치 시간이 초과됐습니다. 네트워크를 확인하고 다시 시도하세요.": "Installation timed out. Check your connection and try again.",
  "바로가기 내용이 변경되어 자동 제거를 중단했습니다.": "The shortcut was modified. Automatic removal was stopped.",
  "기존 바로가기에 Brave 자동 제거 연결 정보가 있습니다. 브라우저 보호를 위해 자동 제거를 중단했습니다.": "This shortcut may uninstall Brave with it. Removal was stopped to protect your browser.",
  "올바르지 않은 바로가기 ID입니다.": "The shortcut ID is invalid.",
  "조작 설정 파일이 없습니다. 설치를 다시 시도하세요.": "The controller configuration is missing. Try installing again.",
  "지원되는 게임패드를 찾지 못했습니다. 내장 컨트롤러를 게임패드 모드로 켠 뒤 다시 시도하세요.": "No supported gamepad found. Enable gamepad mode on the built-in controller and try again.",
  "게임패드 설정 적용을 확인하지 못했습니다.": "Could not verify the gamepad configuration.",
  "설치 기록과 제거 대상이 다릅니다.": "The removal target does not match the installation record.",
};
function bilingual(message: string): string {
  if (message.includes("\n")) return message;
  if (message.startsWith("Steam 이미지 적용을 확인하지 못했습니다:"))
    return message + "\nCould not verify the Steam artwork: " + message.split(":").slice(1).join(":").trim();
  return message + "\n" + (translations[message] || "Please check the message above and try again.");
}
const check = (r: Reply) => { if (!r.ok) throw new Error(r.error || "작업에 실패했습니다."); return r; };
const account = () => String(BigInt(App.m_CurrentUser.strSteamID) & BigInt(0xffffffff));
const delay = (ms: number) => new Promise(r => setTimeout(r, ms));
async function waitFor(id: number, present: boolean) {
  for (let i = 0; i < 80; i++) {
    if (Boolean(appStore.GetAppOverviewByAppID(id)) === present) return;
    await delay(100);
  }
  throw new Error("Steam 라이브러리 갱신을 확인하지 못했습니다. 잠시 후 다시 시도하세요.");
}
function assertStopped(id: number) {
  const overview = appStore.GetAppOverviewByAppID(id);
  if (overview?.is_running || overview?.per_client_data?.some((p: any) => p.display_status === 0))
    throw new Error("게임을 종료한 뒤 다시 시도하세요.");
}

// Steam controller types (not device indices). Handhelds may expose Xbox or
// DualSense devices, including through InputPlumber/HHD. Steam converts the
// base Xbox/DualSense templates for Elite/Edge devices; verify the result below.
const gamepadTemplates: Record<number, string> = {
  4: "controller_neptune",
  30: "controller_generic",
  31: "controller_xbox360",
  32: "controller_xboxone",
  45: "controller_ps5",
  46: "controller_xboxone",
  48: "controller_ps5",
};
function controllerRows(value: any): any[] {
  if (Array.isArray(value)) return value;
  if (typeof value === "string") {
    try { return controllerRows(JSON.parse(value)); } catch { return []; }
  }
  if (value && typeof value.values === "function" && typeof value.get === "function") return [...value.values()];
  if (value && typeof value === "object") {
    if ("nControllerIndex" in value || "unControllerIndex" in value || "controller_index" in value) return [value];
    for (const key of ["controllers", "rgControllers", "controller_list"])
      if (value[key]) return controllerRows(value[key]);
    return Object.values(value);
  }
  return [];
}
function gamepadPlans(rows: any[]): {index: number; template: string}[] {
  const plans: {index: number; template: string}[] = [];
  for (const controller of rows) {
    if (!controller || typeof controller !== "object") continue;
    const rawIndex = controller.nControllerIndex ?? controller.unControllerIndex ?? controller.controller_index;
    const rawType = controller.eControllerType ?? controller.nControllerType ?? controller.controller_type;
    if (rawIndex == null || rawIndex === "" || rawType == null || rawType === "") continue;
    const index = Number(rawIndex), type = Number(rawType);
    // 16 is Steam's invalid device index. Keyboard, mouse and front-panel
    // devices are not gamepads. Do not reject new gamepad types by allowlist.
    if (!Number.isInteger(index) || index < 0 || index >= 16 || !Number.isInteger(type) || type < 0 || type >= 400 || type === 20) continue;
    const template = gamepadTemplates[type] || "controller_xboxone";
    if (!plans.some(p => p.index === index))
      plans.push({index, template: `template://${template}_gamepad_joystick.vdf`});
  }
  return plans;
}
async function connectedGamepads(): Promise<{index: number; template: string}[]> {
  const rows: any[] = [];
  try { rows.push(...controllerRows(ControllerStore.GetControllers())); } catch { /* Store varies between Steam versions. */ }
  try { rows.push(...controllerRows(controllerConfiguratorStore.m_controllerList)); } catch { /* Optional Steam store. */ }
  let plans = gamepadPlans(rows);
  if (plans.length || typeof SteamClient.Input.RegisterForControllerListChanges !== "function") return plans;
  let subscription: any;
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const observed = await new Promise<any[]>(resolve => {
      subscription = SteamClient.Input.RegisterForControllerListChanges((value: any) => {
        const found = controllerRows(value);
        if (gamepadPlans(found).length) resolve(found);
      });
      timer = setTimeout(() => resolve([]), 1500);
    });
    plans = gamepadPlans(observed);
  } catch { /* Installation can still use the device's existing native input. */ }
  finally {
    if (timer !== undefined) clearTimeout(timer);
    subscription?.unregister?.();
  }
  return plans;
}

async function installGame(game: Game, progress: (s: string) => void): Promise<string> {
  const user = account();
  progress("Brave와 설치 파일 준비 중…\nPreparing Brave and installation files…");
  const r = check(await prepare(user, game));
  let id = r.existing || 0;
  if (id && !appStore.GetAppOverviewByAppID(id)) id = 0;
  let created = false;
  try {
    if (id) assertStopped(id);
    if (!id) {
      id = (await SteamClient.Apps.AddShortcut(r.name, "/usr/bin/flatpak", "", "")) >>> 0;
      if (!id) throw new Error("Steam 바로가기를 만들지 못했습니다.");
      created = true;
    }
    await waitFor(id, true);
    progress("Steam 바로가기·이미지 등록 중…\nAdding the Steam shortcut and artwork…");
    SteamClient.Apps.SetShortcutName(id, r.name);
    SteamClient.Apps.SetShortcutExe(id, "/usr/bin/flatpak");
    SteamClient.Apps.SetShortcutStartDir(id, r.home);
    SteamClient.Apps.SetShortcutLaunchOptions(id, r.options);
    SteamClient.Apps.SetShortcutIcon(id, r.icon);
    // Steam's icon artwork slot can overwrite the wide capsule on shortcuts.
    // Icons use SetShortcutIcon above; only library image slots go through this API.
    for (const name of ["capsule", "hero", "logo", "wide"]) {
      const a = check(await artwork(name, game));
      await SteamClient.Apps.ClearCustomArtworkForApp(id, a.assets![0].type);
      await delay(500);
      await SteamClient.Apps.SetCustomArtworkForApp(id, a.assets![0].data, "png", a.assets![0].type);
    }
    await SteamClient.Apps.SetCustomLogoPositionForApp(id, JSON.stringify({pinnedPosition:"BottomLeft",nWidthPct:45,nHeightPct:60}));
    check(await verifyArtwork(user, id, game));
    progress("조작 설정을 적용하는 중…\nApplying controller settings…");
    // Save ownership before selecting the config, so a retry can repair partial installs.
    check(await finish(user, id, game));
    const controllers = await connectedGamepads();
    let controlsVerified = controllers.length > 0;
    for (const controller of controllers) {
      try {
        await SteamClient.Input.SetSelectedConfigForApp(id, controller.index, controller.template, false, 0);
        let verified = false;
        for (let attempt = 0; attempt < 40; attempt++) {
          const config = await SteamClient.Input.GetConfigForAppAndController(id, controller.index);
          if (config?.bUsesGamepad && !config.bUsesKeyboard && !config.bUsesMouse) { verified = true; break; }
          await delay(100);
        }
        if (!verified) throw new Error("게임패드 설정 적용을 확인하지 못했습니다.");
      } catch { controlsVerified = false; }
    }
    check(await finish(user, id, game));
    if (!controlsVerified)
      return "설치 완료 · 패드 자동 설정 미확인. Steam 조작 설정을 확인하세요.\nInstalled · Controls unverified. Check Steam controller settings.";
    return "설치 완료 · 라이브러리에서 실행하세요.\nInstalled · Launch from your library.";
  } catch (error) {
    if (created && id) {
      try {
        SteamClient.Apps.RemoveShortcut(id);
        await waitFor(id, false);
        await clean(user, id, game);
      } catch { /* Keep manifest if rollback fails; removal can be retried. */ }
    }
    throw error;
  }
}
async function removeGame(game: Game, progress: (s: string) => void) {
  const user = account();
  const r = check(await removal(user, game));
  if (!r.appid) return bilingual(r.message || "제거할 항목이 없습니다.");
  const id = r.appid;
  assertStopped(id);
  progress("게임 바로가기·이미지 제거 중…\nRemoving shortcut and artwork…");
  for (const type of [0, 1, 2, 3]) await SteamClient.Apps.ClearCustomArtworkForApp(id, type);
  await SteamClient.Apps.ClearCustomLogoPositionForApp(id);
  SteamClient.Apps.RemoveShortcut(id);
  await waitFor(id, false);
  check(await clean(user, id, game));
  return "제거 완료 · Brave와 저장 데이터 보존\nUninstalled · Brave and saves kept.";
}
function Content() {
  const [selected, setSelected] = useState<Game | null>(null);
  const [busy, setBusy] = useState(false);
  const [update, setUpdate] = useState<UpdateReply | null>(null);
  const [updateStatus, setUpdateStatus] = useState("");
  const running = useRef(false);
  const [statuses, setStatuses] = useState<Record<Game,string>>({
    pokebonk:"공식 웹게임 · 인터넷 연결 필요\nOfficial web game · Internet required",
    azeroth:"공식 웹게임 · 인터넷 연결 필요\nOfficial web game · Internet required",
    d2:"공식 웹게임 · 인터넷 연결 필요\nOfficial web game · Internet required"
  });
  const run = async (game: Game, action: typeof installGame) => {
    if (running.current) return;
    running.current = true;
    setBusy(true);
    const setStatus = (message: string) => setStatuses(old => ({...old,[game]:message}));
    const title = games.find(g => g.id === game)!.name;
    try { const message = await action(game, setStatus); setStatus(message); toaster.toast({title,body:message}); }
    catch (e) { const message = bilingual(e instanceof Error ? e.message : String(e)); setStatus(message); toaster.toast({title,body:message}); }
    finally { running.current = false; setBusy(false); }
  };
  const runUpdate = async (download: boolean) => {
    if (running.current) return;
    running.current = true;
    setBusy(true);
    setUpdateStatus(download ? "최신 ZIP 다운로드 중…\nDownloading the latest ZIP…" : "GitHub에서 최신 버전 확인 중…\nChecking GitHub for updates…");
    setUpdate(null);
    try {
      const result = await (download ? downloadUpdate() : checkUpdate());
      if (!result.ok) throw new Error(result.error || "작업에 실패했습니다.");
      setUpdate(result);
      const versions = `설치 / Installed: v${result.installed_version}\n최신 공개 / Latest: v${result.latest_version}`;
      if (result.downloaded) setUpdateStatus(`다운로드 완료 · Decky에서 ZIP으로 설치하세요.\nDownloaded · Install the ZIP through Decky.\n${result.path}`);
      else if (result.update_available) setUpdateStatus(`새 버전이 있습니다: v${result.latest_version}\nUpdate available: v${result.latest_version}\n${versions}`);
      else setUpdateStatus(`최신 버전입니다.\nYou’re up to date.\n${versions}`);
    } catch (e) {
      setUpdateStatus(bilingual(e instanceof Error ? e.message : String(e)));
    } finally { running.current = false; setBusy(false); }
  };
  return <><PanelSection>{games.map(game => <Fragment key={game.id}>
    <PanelSectionRow><ButtonItem layout="below" disabled={busy} onClick={() => setSelected(selected === game.id ? null : game.id)}>
      {selected === game.id ? "▾ " : "▸ "}{game.name}
    </ButtonItem></PanelSectionRow>
    {selected === game.id && <>
      <PanelSectionRow><ButtonItem layout="below" disabled={busy} onClick={() => run(game.id, installGame)}>Install</ButtonItem></PanelSectionRow>
      <PanelSectionRow><ButtonItem layout="below" disabled={busy} onClick={() => run(game.id, removeGame)}>Uninstall</ButtonItem></PanelSectionRow>
      <PanelSectionRow><div style={{fontSize:13,lineHeight:1.6,color:"#b8bcbf",whiteSpace:"pre-line"}} role="status">{statuses[game.id]}</div></PanelSectionRow>
    </>}
  </Fragment>)}</PanelSection>
  <PanelSection>
    <PanelSectionRow><ButtonItem layout="below" disabled={busy} onClick={() => runUpdate(false)}>Check for Updates</ButtonItem></PanelSectionRow>
    {update?.update_available && !update.downloaded && <PanelSectionRow><ButtonItem layout="below" disabled={busy} onClick={() => runUpdate(true)}>Download v{update.latest_version}</ButtonItem></PanelSectionRow>}
    {updateStatus && <PanelSectionRow><div style={{fontSize:13,lineHeight:1.6,color:"#b8bcbf",whiteSpace:"pre-line",overflowWrap:"anywhere"}} role="status">{updateStatus}</div></PanelSectionRow>}
  </PanelSection></>;
}
export default definePlugin(() => ({name:"Decky Web Games", titleView:<div className={staticClasses.Title}>Decky Web Games</div>, content:<Content/>, icon:<span style={{fontWeight:900}}>WG</span>, onDismount() {}}));
