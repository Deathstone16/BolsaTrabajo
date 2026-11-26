const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

test('auth forms keep the first native submit, reject duplicates and reset on back navigation', () => {
  const events = {};const windowEvents={};
  const button={innerHTML:'Ingresar <span>→</span>',disabled:false};
  const form={dataset:{submitLabel:'Ingresando…'},querySelectorAll:()=>[button],
    addEventListener:(name,fn)=>events[name]=fn,setAttribute(){},removeAttribute(){}};
  vm.runInNewContext(fs.readFileSync('static/js/auth-submit.js','utf8'),{
    document:{querySelectorAll:()=>[form]},window:{addEventListener:(name,fn)=>windowEvents[name]=fn}
  });
  let prevented=0;
  const event={defaultPrevented:false,preventDefault(){prevented++;}};
  events.submit(event);assert.equal(prevented,0);assert.equal(button.disabled,true);
  events.submit(event);assert.equal(prevented,1);
  windowEvents.pageshow();assert.equal(button.disabled,false);assert.equal(button.innerHTML,'Ingresar <span>→</span>');
  events.submit(event);assert.equal(prevented,1);
});
