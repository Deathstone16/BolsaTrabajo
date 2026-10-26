// Run with: node scripts/test_cv_background.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync('static/js/cv_notifications.js', 'utf8');
const flush = () => new Promise(setImmediate);
function page(storage, { pending = '', version = '7', user = '1', state = 'pendiente' } = {}) {
  const events = {}, windowEvents = {}, toasts = [], completed = [], calls = [], intervals = new Set();
  const indicator = { hidden: !pending };
  const config = {dataset: {userId:user, analysisId:pending, currentVersionId:version, statusUrl:'/ia/analisis/0/estado/', profileUrl:'/perfil/#cv-analysis', token:'test'}};
  const document = {hidden:false, getElementById(id) { return id === 'cv-notifications-config' ? config : id === 'cv-analysis-global' ? indicator : null; },
    querySelectorAll() {return [];}, addEventListener(name, fn) {events[name]=fn;},
    dispatchEvent(event) {completed.push(event);}, body: {appendChild(el) {toasts.push(el);}},
    createElement() {return {children:[],setAttribute(){},addEventListener(){},appendChild(el){this.children.push(el);},remove(){}};}};
  const localStorage = {getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)};
  const window = {addEventListener(name, fn) {windowEvents[name]=fn;}};
  vm.runInNewContext(code, {window,document,localStorage,location:{protocol:'http:',host:'localhost'},
    CustomEvent:function(type,options){this.type=type;this.detail=options.detail;},
    fetch:async url=>{calls.push(url);return {ok:true,json:async()=>({estado:state,version_cv_id:Number(version),es_version_actual:true})};},
    setInterval(fn){intervals.add(fn);return fn;},clearInterval(fn){intervals.delete(fn);},setTimeout(){},clearTimeout(){}});
  events.DOMContentLoaded();
  return {indicator,toasts,completed,calls,intervals,window,events,windowEvents};
}
(async()=>{
  const storage = new Map();
  const first = page(storage, {pending:'42'});
  await flush();
  assert.equal(first.indicator.hidden,false);
  assert.equal(first.toasts.length,0);
  assert.equal(first.intervals.size,1);
  first.windowEvents.pagehide();
  assert.equal(first.intervals.size,0);
  // The job completes between two page loads; the server no longer reports a pending job.
  const next = page(storage, {state:'completado'});
  await flush();
  assert.equal(next.calls[0],'/ia/analisis/42/estado/');
  assert.equal(next.indicator.hidden,true);
  assert.equal(next.toasts.length,1);
  assert.match(next.toasts[0].textContent,/Tu CV ya está analizado/);
  assert.equal(next.intervals.size,0);
  const reloaded = page(storage,{state:'completado'});
  await flush();assert.equal(reloaded.toasts.length,0);assert.equal(reloaded.calls.length,0);
  const anotherUser = page(storage,{user:'2'});
  await flush();assert.equal(anotherUser.calls.length,0);assert.equal(anotherUser.indicator.hidden,true);
  const changedCV = new Map([['ien-cv-analysis-tracking-1',JSON.stringify({id:42,versionId:7})]]);
  const replaced=page(changedCV,{version:'8'});
  await flush();assert.equal(replaced.calls.length,0);assert.equal(changedCV.has('ien-cv-analysis-tracking-1'),false);
  console.log('OK: progreso global, navegación, finalización entre páginas, aviso único, privacidad y cambio de CV.');
})().catch(error=>{console.error(error);process.exitCode=1;});
