const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

function setup({gamepad=true, existing=false, controllers=[{eControllerType:4,nControllerIndex:15}], failedIndex}={}) {
  const calls = [];
  const apps = new Map();
  let nextId = 0x80000001;
  const ids = {pokebonk:0x80000001,azeroth:0x80000002,d2:0x80000003};
  const names = {pokebonk:'Pokebonk Online',azeroth:'Azeroth Survivors',d2:'D2 Survivors'};
  if(existing) apps.set(ids.azeroth, {is_running:false});
  const api = {
    prepare_install: async (account,game) => {calls.push(['prepare',game]);return {ok:true,name:names[game],existing:existing?ids[game]:undefined,home:'"/home/deck"',options:game,icon:`/${game}/icon.png`,config:'template://gamepad'};},
    finish_install: async (...args) => {calls.push(['finish',...args]);return {ok:true};},
    prepare_remove: async (account,game) => ({ok:true,appid:ids[game]}),
    finish_remove: async (...args) => {calls.push(['clean',...args]);return {ok:true};},
    get_artwork: async (role,game) => {calls.push(['art',role,game]);return {ok:true,assets:[{type:{capsule:0,hero:1,logo:2,wide:3}[role],data:game+role}]};},
    verify_artwork: async (...args) => {calls.push(['verify',...args]);return {ok:true};},
  };
  const SteamClient = {
    Apps: new Proxy({}, {get:(_,method) => (...args) => {
      calls.push([method,...args]);
      if(method==='AddShortcut'){const id=nextId++;apps.set(id,{is_running:false});return Promise.resolve(id);}
      if(method==='RemoveShortcut')apps.delete(args[0]);
      return Promise.resolve();
    }}),
    Input: {
      SetSelectedConfigForApp: async (...args)=>calls.push(['config',...args]),
      GetConfigForAppAndController: async (id,index)=>{calls.push(['verifyConfig',id,index]);return {bUsesGamepad:gamepad&&index!==failedIndex,bUsesKeyboard:!gamepad||index===failedIndex,bUsesMouse:false};},
    },
  };
  const source=fs.readFileSync('src/index.tsx','utf8')+'\nexport const testAPI = {installGame,removeGame};';
  const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020}}).outputText;
  const context={exports:{},SteamClient,App:{m_CurrentUser:{strSteamID:'76561197960265851'}},
    appStore:{GetAppOverviewByAppID:id=>apps.get(id)},ControllerStore:{GetControllers:()=>controllers},
    setTimeout:fn=>{fn();return 0;},
    require:name=>name==='@decky/api'?{callable:key=>api[key],definePlugin:fn=>fn,toaster:{toast(){}}}:{}
  };
  vm.runInNewContext(code,context);
  return {...context.exports.testAPI,calls,apps};
}

(async()=>{
  const both=setup();
  await both.installGame('pokebonk',()=>{});
  await both.installGame('azeroth',()=>{});
  assert.deepEqual(both.calls.filter(c=>c[0]==='AddShortcut').map(c=>c[1]),['Pokebonk Online','Azeroth Survivors']);
  assert.deepEqual(both.calls.filter(c=>c[0]==='art').map(c=>c[2]),['pokebonk','pokebonk','pokebonk','pokebonk','azeroth','azeroth','azeroth','azeroth']);
  assert.ok(both.calls.filter(c=>c[0]==='SetCustomArtworkForApp').every(c=>c[4]!==4));
  assert.ok(both.calls.filter(c=>c[0]==='config').every(c=>c.length===6&&c[2]===15&&c[5]===0));
  await both.removeGame('azeroth',()=>{});
  assert.ok(both.apps.has(0x80000001));
  assert.ok(!both.apps.has(0x80000002));
  assert.equal(both.calls.filter(c=>c[0]==='clean').at(-1)[3],'azeroth');
  console.log('PASS: two installs, game-specific artwork, native template, isolated uninstall');

  const three=setup();
  for(const game of ['pokebonk','azeroth','d2']) await three.installGame(game,()=>{});
  assert.deepEqual(three.calls.filter(c=>c[0]==='AddShortcut').map(c=>c[1]),['Pokebonk Online','Azeroth Survivors','D2 Survivors']);
  assert.deepEqual(three.calls.filter(c=>c[0]==='art'&&c[2]==='d2').map(c=>c[1]),['capsule','hero','logo','wide']);
  await three.removeGame('d2',()=>{});
  assert.ok(three.apps.has(0x80000001)&&three.apps.has(0x80000002));
  assert.ok(!three.apps.has(0x80000003));
  console.log('PASS: D2 install/artwork/uninstall preserves both existing games');

  const failure=setup({gamepad:false});
  await assert.rejects(()=>failure.installGame('azeroth',()=>{}));
  assert.equal(failure.apps.size,0);
  assert.equal(failure.calls.filter(c=>c[0]==='clean').at(-1)[3],'azeroth');
  console.log('PASS: failed new install rolls back its shortcut and manifest');

  const repair=setup({gamepad:false,existing:true});
  await assert.rejects(()=>repair.installGame('azeroth',()=>{}));
  assert.ok(repair.apps.has(0x80000002));
  assert.equal(repair.calls.filter(c=>c[0]==='RemoveShortcut').length,0);
  console.log('PASS: failed repair preserves the existing game');

  for(const [type,template] of [[4,'neptune'],[30,'generic'],[31,'xbox360'],[32,'xboxone'],[45,'ps5'],[46,'xboxone'],[48,'ps5']]) {
    const handheld=setup({controllers:[{eControllerType:type,nControllerIndex:7}]});
    for(const game of ['pokebonk','azeroth','d2']) await handheld.installGame(game,()=>{});
    const configs=handheld.calls.filter(c=>c[0]==='config');
    assert.equal(configs.length,3);
    assert.ok(configs.every(c=>c[2]===7&&c[3]===`template://controller_${template}_gamepad_joystick.vdf`&&c[4]===false&&c[5]===0));
    assert.ok(handheld.calls.filter(c=>c[0]==='verifyConfig').every(c=>c[2]===7));
  }
  console.log('PASS: Steam Deck, Xbox, generic, DualSense and Edge/Elite handheld modes for all three games');

  const multiple=setup({controllers:[{eControllerType:400,nControllerIndex:1},{eControllerType:800,nControllerIndex:2},{eControllerType:32,nControllerIndex:3},{eControllerType:45,nControllerIndex:8},{eControllerType:32,nControllerIndex:3}]});
  await multiple.installGame('d2',()=>{});
  assert.deepEqual(multiple.calls.filter(c=>c[0]==='config').map(c=>c[2]),[3,8]);
  console.log('PASS: configures each connected gamepad, excluding keyboard/mouse and duplicate indices');

  for(const controllers of [[],[{eControllerType:400,nControllerIndex:1}],[{eControllerType:999,nControllerIndex:0}],[{eControllerType:32,nControllerIndex:undefined}],[{eControllerType:32,nControllerIndex:-1}]]) {
    const missing=setup({controllers});
    await assert.rejects(()=>missing.installGame('d2',()=>{}),/지원되는 게임패드/);
    assert.equal(missing.calls.length,0);
  }
  const mixedFailure=setup({controllers:[{eControllerType:32,nControllerIndex:3},{eControllerType:45,nControllerIndex:8}],failedIndex:8});
  await assert.rejects(()=>mixedFailure.installGame('d2',()=>{}),/게임패드 설정 적용/);
  assert.equal(mixedFailure.apps.size,0);
  console.log('PASS: missing/invalid controllers fail before mutation; failed secondary gamepad rolls back installation');
})();
