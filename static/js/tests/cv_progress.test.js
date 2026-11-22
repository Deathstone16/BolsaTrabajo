const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname,'../ui/cv-progress.js'),'utf8');
function setup(storage=new Map()) {
  let close;
  const banner={dataset:{userId:'7',analysisId:'31'},hidden:false,querySelector(){return{addEventListener(event,fn){close=fn;}};}};
  const context={document:{getElementById(){return banner;}},window:{},sessionStorage:{getItem:key=>storage.get(key),setItem:(key,value)=>storage.set(key,value)}};
  vm.runInNewContext(source,context);
  return {banner,close:()=>close(),api:context.window.IenCVProgress,storage};
}
test('closing the notice hides it without clearing the pending analysis',()=>{
  const state=setup();
  state.close();
  assert.equal(state.banner.hidden,true);
  state.api.setPending(31);
  assert.equal(state.banner.hidden,true);
  assert.equal(state.storage.get('ien-cv-progress-dismissed-7'),'31');
});
test('the same analysis stays dismissed after navigation',()=>{
  const state=setup();state.close();
  const next=setup(state.storage);
  assert.equal(next.banner.hidden,true);
});
test('a new analysis is shown even after an earlier notice was dismissed',()=>{
  const state=setup();state.close();state.api.setPending(32);
  assert.equal(state.banner.hidden,false);
});
test('completion removes the pending notice',()=>{
  const state=setup();state.api.setPending(null);
  assert.equal(state.banner.hidden,true);
});
