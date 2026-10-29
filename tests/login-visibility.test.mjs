import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const template=readFileSync(new URL('../templates/login.html',import.meta.url),'utf8');
const script=template.match(/<script>([\s\S]*?)<\/script>/)[1];
function page(){
  const click={},form={},navigation={},visibility={};
  const field={type:'password',value:'テスト専用の入力abc',form:{addEventListener:(name,fn)=>{form[name]=fn;}}};
  const button={hidden:true,attributes:{},setAttribute(name,value){this.attributes[name]=value;},addEventListener:(name,fn)=>{click[name]=fn;}};
  const help={hidden:true};
  const elements={passphrase:field,'toggle-passphrase':button,'visibility-help':help};
  const document={hidden:false,getElementById:id=>elements[id],addEventListener:(name,fn)=>{visibility[name]=fn;}};
  vm.runInNewContext(script,{document,window:{addEventListener:(name,fn)=>{navigation[name]=fn;}}});
  return {field,button,help,click,form,navigation,visibility,document};
}

test('revealing and hiding preserves the typed phrase and does not submit the form',()=>{
  assert.match(template,/<input id="passphrase" type="password"/);
  assert.match(template,/<button id="toggle-passphrase"[^>]+type="button"/);
  const p=page(),original=p.field.value;
  assert.equal(p.field.type,'password');assert.equal(p.help.hidden,true);
  p.click.click();
  assert.equal(p.field.type,'text');assert.equal(p.field.value,original);
  assert.equal(p.button.textContent,'合言葉を隠す');assert.equal(p.button.attributes['aria-pressed'],'true');
  p.click.click();
  assert.equal(p.field.type,'password');assert.equal(p.field.value,original);
  assert.equal(p.button.attributes['aria-pressed'],'false');
});

test('submission, restoring the page and leaving the tab conceal the phrase again',()=>{
  const p=page(),original=p.field.value;
  for(const hide of [()=>p.form.submit(),()=>p.navigation.pageshow(),()=>{p.document.hidden=true;p.visibility.visibilitychange();}]){
    p.click.click();assert.equal(p.field.type,'text');
    hide();assert.equal(p.field.type,'password');assert.equal(p.field.value,original);assert.equal(p.help.hidden,true);
  }
});
