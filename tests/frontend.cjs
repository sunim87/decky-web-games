const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

function setup({gamepad=true, existing=false}={}) {
  const calls = [];
  const apps = new Map();
  let nextId = 0x80000001;
  const ids = {pokebonk:0x80000001,azeroth:0x80000002};
  if(existing) apps.set(ids.azeroth, {is_running:false});
  const api = {
    prepare_install: async (account,game) => ({ok:true,name:game==='azeroth'?'Azeroth Survivors':'Pokebonk Online',existing:existing?ids[game]:undefined,home:'"/home/deck"',options:game,icon:`/${game}/icon.png`,config:'template://gamepad'}),
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
      GetConfigForAppAndController: async ()=>({bUsesGamepad:gamepad,bUsesKeyboard:!gamepad,bUsesMouse:false}),
    },
  };
  const source=fs.readFileSync('src/index.tsx','utf8')+'\nexport const testAPI = {installGame,removeGame};';
  const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020}}).outputText;
  const context={exports:{},SteamClient,App:{m_CurrentUser:{strSteamID:'76561197960265851'}},
    appStore:{GetAppOverviewByAppID:id=>apps.get(id)},ControllerStore:{GetControllers:()=>[{eControllerType:4,nControllerIndex:15}]},
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
})();
