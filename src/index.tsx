import { ButtonItem, PanelSection, PanelSectionRow, staticClasses } from "@decky/ui";
import { callable, definePlugin, toaster } from "@decky/api";
import { useState } from "react";

declare const SteamClient: any;
declare const App: any;
declare const appStore: any;
declare const ControllerStore: any;

type Reply = {ok: boolean; error?: string; message?: string; appid?: number; existing?: number; icon?: string; config?: string; home?: string; options?: string; assets?: {type: number; data: string}[]};
const prepare = callable<[account: string], Reply>("prepare_install");
const finish = callable<[account: string, appid: number], Reply>("finish_install");
const removal = callable<[account: string], Reply>("prepare_remove");
const clean = callable<[account: string, appid: number], Reply>("finish_remove");
const artwork = callable<[name: string], Reply>("get_artwork");
const verifyArtwork = callable<[account: string, appid: number], Reply>("verify_artwork");
const translations: Record<string, string> = {
  "작업에 실패했습니다.": "The operation failed.",
  "Steam 라이브러리 갱신을 확인하지 못했습니다. 잠시 후 다시 시도하세요.": "Could not confirm the Steam library update. Please try again shortly.",
  "포켓봉크를 종료한 뒤 다시 시도하세요.": "Close Pokebonk and try again.",
  "Steam 바로가기를 만들지 못했습니다.": "Could not create the Steam shortcut.",
  "제거할 항목이 없습니다.": "There is nothing to uninstall.",
  "설치 기록이 없습니다. 설치 버튼으로 기존 항목을 등록할 수 있습니다.": "No installation record. Use Install to register an existing shortcut.",
  "Steam 사용자 정보를 확인하지 못했습니다.": "Could not identify the current Steam user.",
  "현재 Steam 사용자 폴더를 찾지 못했습니다.": "Could not find the current Steam user folder.",
  "같은 이름의 다른 바로가기가 있습니다. 이름을 변경한 뒤 설치하세요.": "An unrelated shortcut has the same name. Rename it before installing.",
  "동일한 포켓봉크 바로가기가 여러 개 있습니다. 중복을 정리한 뒤 시도하세요.": "Multiple Pokebonk shortcuts were found. Remove duplicates and try again.",
  "기존 설치 기록과 바로가기가 다릅니다.": "The shortcut does not match the installation record.",
  "Flatpak이 필요합니다. SteamOS에서 실행하세요.": "Flatpak is required. Run this plugin on SteamOS.",
  "Brave 설치를 확인하지 못했습니다.": "Could not verify the Brave installation.",
  "설치 시간이 초과됐습니다. 네트워크를 확인하고 다시 시도하세요.": "Installation timed out. Check your connection and try again.",
  "바로가기 내용이 변경되어 자동 제거를 중단했습니다.": "The shortcut was modified. Automatic removal was stopped.",
  "기존 바로가기에 Brave 자동 제거 연결 정보가 있습니다. 브라우저 보호를 위해 자동 제거를 중단했습니다.": "This shortcut may uninstall Brave with it. Removal was stopped to protect your browser.",
  "올바르지 않은 바로가기 ID입니다.": "The shortcut ID is invalid.",
  "조작 설정 파일이 없습니다. 설치를 다시 시도하세요.": "The controller configuration is missing. Try installing again.",
  "Steam Deck 내장 컨트롤러를 찾지 못했습니다.": "Could not find the built-in Steam Deck controller.",
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
    throw new Error("포켓봉크를 종료한 뒤 다시 시도하세요.");
}

async function installGame(progress: (s: string) => void) {
  const user = account();
  progress("Brave와 설치 파일 준비 중…\nPreparing Brave and installation files…");
  const r = check(await prepare(user));
  let id = r.existing || 0;
  if (id && !appStore.GetAppOverviewByAppID(id)) id = 0;
  let created = false;
  try {
    if (id) assertStopped(id);
    if (!id) {
      id = (await SteamClient.Apps.AddShortcut("Pokebonk Online", "/usr/bin/flatpak", "", "")) >>> 0;
      if (!id) throw new Error("Steam 바로가기를 만들지 못했습니다.");
      created = true;
    }
    await waitFor(id, true);
    progress("Steam 바로가기·이미지 등록 중…\nAdding the Steam shortcut and artwork…");
    SteamClient.Apps.SetShortcutName(id, "Pokebonk Online");
    SteamClient.Apps.SetShortcutExe(id, "/usr/bin/flatpak");
    SteamClient.Apps.SetShortcutStartDir(id, r.home);
    SteamClient.Apps.SetShortcutLaunchOptions(id, r.options);
    SteamClient.Apps.SetShortcutIcon(id, r.icon);
    // Steam's icon artwork slot can overwrite the wide capsule on shortcuts.
    // Icons use SetShortcutIcon above; only library image slots go through this API.
    for (const name of ["capsule", "hero", "logo", "wide"]) {
      const a = check(await artwork(name));
      await SteamClient.Apps.ClearCustomArtworkForApp(id, a.assets![0].type);
      await delay(500);
      await SteamClient.Apps.SetCustomArtworkForApp(id, a.assets![0].data, "png", a.assets![0].type);
    }
    await SteamClient.Apps.SetCustomLogoPositionForApp(id, JSON.stringify({pinnedPosition:"BottomLeft",nWidthPct:45,nHeightPct:60}));
    check(await verifyArtwork(user, id));
    progress("조작 설정을 적용하는 중…\nApplying controller settings…");
    // Save ownership before selecting the config, so a retry can repair partial installs.
    check(await finish(user, id));
    const controllers = ControllerStore.GetControllers();
    const deck = controllers.find((c: any) => c.eControllerType === 4);
    if (!deck) throw new Error("Steam Deck 내장 컨트롤러를 찾지 못했습니다.");
    await SteamClient.Input.SetSelectedConfigForApp(id, deck.nControllerIndex, r.config, false, 0);
    let verified = false;
    for (let attempt = 0; attempt < 40; attempt++) {
      const config = await SteamClient.Input.GetConfigForAppAndController(id, deck.nControllerIndex);
      if (config?.bUsesGamepad && !config.bUsesKeyboard && !config.bUsesMouse) { verified = true; break; }
      await delay(100);
    }
    if (!verified) throw new Error("게임패드 설정 적용을 확인하지 못했습니다.");
    check(await finish(user, id));
    return "설치 완료 · 라이브러리에서 실행하세요.\nInstalled · Launch from your library.";
  } catch (error) {
    if (created && id) {
      try {
        SteamClient.Apps.RemoveShortcut(id);
        await waitFor(id, false);
        await clean(user, id);
      } catch { /* Keep manifest if rollback fails; removal can be retried. */ }
    }
    throw error;
  }
}
async function removeGame(progress: (s: string) => void) {
  const user = account();
  const r = check(await removal(user));
  if (!r.appid) return bilingual(r.message || "제거할 항목이 없습니다.");
  const id = r.appid;
  assertStopped(id);
  progress("포켓봉크 바로가기·이미지 제거 중…\nRemoving shortcut and artwork…");
  for (const type of [0, 1, 2, 3]) await SteamClient.Apps.ClearCustomArtworkForApp(id, type);
  await SteamClient.Apps.ClearCustomLogoPositionForApp(id);
  SteamClient.Apps.RemoveShortcut(id);
  await waitFor(id, false);
  check(await clean(user, id));
  return "제거 완료 · Brave와 저장 데이터 보존\nUninstalled · Brave and saves kept.";
}
function Content() {
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("공식 웹게임 · 인터넷 연결 필요\nOfficial web game · Internet required");
  const run = async (action: typeof installGame) => {
    if (busy) return;
    setBusy(true);
    try { const message = await action(setStatus); setStatus(message); toaster.toast({title:"Pokebonk Online",body:message}); }
    catch (e) { const message = bilingual(e instanceof Error ? e.message : String(e)); setStatus(message); toaster.toast({title:"Pokebonk Online",body:message}); }
    finally { setBusy(false); }
  };
  return <PanelSection>
    <div className={staticClasses.PanelSectionTitle} style={{textTransform:"none"}}>Pokebonk Online</div>
    <PanelSectionRow><ButtonItem layout="below" disabled={busy} onClick={() => run(installGame)}>Install</ButtonItem></PanelSectionRow>
    <PanelSectionRow><ButtonItem layout="below" disabled={busy} onClick={() => run(removeGame)}>Uninstall</ButtonItem></PanelSectionRow>
    <PanelSectionRow><div style={{fontSize:13,lineHeight:1.6,color:"#b8bcbf",whiteSpace:"pre-line"}} role="status">{status}</div></PanelSectionRow>
  </PanelSection>;
}
export default definePlugin(() => ({name:"Pokebonk Installer", titleView:<div className={staticClasses.Title}>Pokebonk Online</div>, content:<Content/>, icon:<span style={{fontWeight:900}}>PB</span>, onDismount() {}}));
