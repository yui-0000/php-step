import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {runInNewContext} from 'node:vm';
const content=JSON.parse(await readFile(new URL('../data/questions.json',import.meta.url),'utf8'));
const source=await readFile(new URL('../static/app.js',import.meta.url),'utf8');
const helper=source.slice(source.indexOf('const difficultyNames='),source.indexOf('const labels='));
const pages=source.slice(source.indexOf('function topicList(){'),source.indexOf('function review(){'));
function context(difficulty){return {questions:content.questions,topics:content.topics,state:{settings:{difficulty},records:{}},document:{addEventListener(){}},save(){},render(){},toast(){}};}
test('selector shows all three levels and preserves the selected level',()=>{
 const html=runInNewContext(helper+'difficultyPicker();',context('practice'));
 assert.match(html,/<option value="practice" selected>実践（101問）/);
 assert.match(html,/すべて（300問）/);assert.match(html,/基礎（30問）/);assert.match(html,/標準（169問）/);
});
test('an empty topic and difficulty combination offers a level change',()=>{
 const html=runInNewContext(helper+pages+"topicPage('intro');",context('practice'));
 assert.match(html,/この難易度には問題がありません/);assert.doesNotMatch(html,/data-topic="intro"/);
 const available=runInNewContext(helper+pages+"topicPage('control');",context('practice'));
 assert.match(available,/data-topic="control"/);
});
test('changing the level preserves active session and unrelated settings',()=>{
 const c=context('all');let handler,saves=0;
 c.state.settings.examDate='2026-11-16';c.state.session={ids:['q01'],index:0,responses:{}};
 c.document.addEventListener=(name,fn)=>{handler=fn;};c.save=()=>{saves++;};
 runInNewContext(helper,c);handler({target:{id:'learning-difficulty',value:'practice'}});
 assert.equal(c.state.settings.difficulty,'practice');assert.equal(c.state.settings.examDate,'2026-11-16');
 assert.deepEqual(c.state.session.ids,['q01']);assert.equal(saves,1);
 handler({target:{id:'learning-difficulty',value:'invalid'}});assert.equal(saves,1);
});
