// Run with: node scripts/test_match_cancel_ui.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('templates/nueva_ui/detalle_oferta.html','utf8');
const code = [...source.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).find(s=>s.includes('match-card'))
  .replace(/\{% url 'matching:(\w+)' '([^']+)' %\}/g,(_,name,id)=>`/matching/${name}/${id}/`);
const nodes = new Map(), sockets = [], calls = [];
const el = id => {
  if (!nodes.has(id)) nodes.set(id,{dataset:{},hidden:id==='match-cancel-button'||id==='match-details-action',handlers:{},style:{},classList:{add(){},remove(){},toggle(){}},querySelector(){return {value:'csrf'}},addEventListener(name,fn){this.handlers[name]=fn;},action:'/calculate/'});
  return nodes.get(id);
};
let requestNumber=0;
function Socket(){this.close=()=>{};sockets.push(this);}
vm.runInNewContext(code, {document:{getElementById:el},window:{addEventListener(){}},location:{protocol:'http:',host:'localhost'},WebSocket:Socket,
  setInterval(){return 1},clearInterval(){},fetch:async(url,options)=>{
    calls.push({url,options});
    let data;
    if(url==='/calculate/') {requestNumber++;data=requestNumber===1?{success:true,status:'processing',request_id:'old'}:{success:true,status:'completed',request_id:'new',match_percentage:0};}
    else if(url.includes('/cancelar/')) data={success:true,status:'cancelled',request_id:'old'};
    else data={status:'processing',request_id:'old'};
    return {ok:true,json:async()=>data};
  }});
const flush=()=>new Promise(setImmediate);
(async()=>{
  assert.equal(calls.length,0);
  el('match-form').handlers.submit({preventDefault(){}});await flush();
  assert.equal(el('match-cancel-button').hidden,false);
  assert.equal(el('match-button').disabled,true);
  await el('match-cancel-button').handlers.click();await flush();
  assert.equal(el('match-card').dataset.status,'cancelled');
  assert.equal(el('match-button').disabled,false);
  assert.equal(el('match-cancel-button').hidden,true);
  sockets[0].onmessage({data:JSON.stringify({status:'completed',request_id:'old',match_percentage:99})});
  assert.equal(el('match-percentage').textContent,'Cancelado');
  el('match-form').handlers.submit({preventDefault(){}});await flush();
  assert.equal(el('match-percentage').textContent,'0%');
  assert.equal(el('match-details-link').href,'/matching/detalle/new/');
  assert.equal(el('match-details-action').hidden,false);
  console.log('OK: inicio manual, cancelar, descartar respuesta tardía y reintentar con 0% válido.');
})().catch(error=>{console.error(error);process.exitCode=1;});
