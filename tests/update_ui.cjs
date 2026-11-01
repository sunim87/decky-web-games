const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const ts=require('typescript');

function view(check,download){
 const state=[];let index=0;
 const hook=initial=>{const n=index++;if(!(n in state))state[n]=initial;return [state[n],value=>{state[n]=typeof value==='function'?value(state[n]):value;}];};
 const node=(type,props)=>({type,props:props||{}});
 const react={Fragment:'Fragment',useState:hook,useRef:value=>hook({current:value})[0]};
 const api={check_update:check,download_update:download};
 const code=ts.transpileModule(fs.readFileSync('src/index.tsx','utf8')+'\nexport const testView=Content;',
  {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,jsx:ts.JsxEmit.ReactJSX}}).outputText;
 const context={exports:{},require:name=>{
  if(name==='react')return react;
  if(name==='react/jsx-runtime')return {jsx:node,jsxs:node,Fragment:'Fragment'};
  if(name==='@decky/ui')return {PanelSection:'PanelSection',PanelSectionRow:'PanelSectionRow',ButtonItem:'ButtonItem',staticClasses:{}};
  if(name==='@decky/api')return {callable:key=>api[key],definePlugin:fn=>fn,toaster:{toast(){}}};
  throw Error(name);
 }};
 vm.runInNewContext(code,context);
 const text=value=>Array.isArray(value)?value.map(text).join(''):value?.props?text(value.props.children):value==null?'':String(value);
 const walk=value=>Array.isArray(value)?value.flatMap(walk):value?.props?[value,...walk(value.props.children)]:[];
 let tree;
 const render=()=>{index=0;tree=context.exports.testView();};
 const buttons=()=>walk(tree).filter(n=>n.type==='ButtonItem');
 const button=label=>buttons().find(n=>text(n.props.children)===label);
 render();
 return {render,button,buttons,text:()=>text(tree)};
}

(async()=>{
 const release={ok:true,installed_version:'1.2.0',latest_version:'1.3.0',update_available:true};
 let resolve;const pending=new Promise(r=>resolve=r);let downloads=0;
 const page=view(()=>pending,async()=>{downloads++;return {...release,downloaded:true,path:'/home/deck/Downloads/decky-web-games-v1.3.0.zip'};});
 const checking=page.button('Check for Updates').props.onClick();page.render();
 assert.ok(page.text().includes('Checking GitHub'));
 assert.ok(page.buttons().every(b=>b.props.disabled));
 resolve(release);await checking;page.render();
 assert.ok(page.text().includes('새 버전이 있습니다: v1.3.0'));
 assert.ok(page.button('Download v1.3.0'));
 await page.button('Download v1.3.0').props.onClick();page.render();
 assert.equal(downloads,1);assert.ok(page.text().includes('/home/deck/Downloads/decky-web-games-v1.3.0.zip'));
 assert.ok(!page.button('Download v1.3.0'));
 console.log('PASS: check progress, new version/download button and completed file path');
 for(const installed of ['1.3.0','1.4.0-test.5']){
  const latest=view(async()=>({...release,installed_version:installed,update_available:false}),async()=>{throw Error('Must not download');});
  await latest.button('Check for Updates').props.onClick();latest.render();
  assert.ok(latest.text().includes('최신 버전입니다.'));
  assert.ok(!latest.button('Download v1.3.0'));
 }
 const failed=view(async()=>{throw Error('offline');});
 await failed.button('Check for Updates').props.onClick();failed.render();
 assert.ok(failed.text().includes('offline'));
 assert.equal(failed.button('Check for Updates').props.disabled,false);
 console.log('PASS: current/newer builds hide downloads; errors allow retry');
})();
