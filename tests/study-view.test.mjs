import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {runInNewContext} from 'node:vm';
const content=JSON.parse(await readFile(new URL('../data/questions.json',import.meta.url),'utf8'));
const source=await readFile(new URL('../static/app.js',import.meta.url),'utf8');
const studySource=source.slice(source.indexOf('function study(){'),source.indexOf('function result(){'));
function render(session){return runInNewContext(studySource+';study();',{
 state:{session,records:{}},questions:content.questions,labels:{learn:'学習',quiz:'チェック'},
 escape:s=>String(s),topicName:()=>'',button:(text,action)=>`<button data-action="${action}">${text}</button>`,
 isCorrect:(q,selected)=>selected.length===q.answer.length&&q.answer.every(i=>selected.includes(i)),
 lesson:()=>'<details>基礎の説明</details>',answerDetails:()=>'<details>詳しい解説</details>',questionNote:()=>'<div>質問ノート</div>'
 });}
test('initial view has a question and answer button, without explanation or confidence',()=>{
 const html=render({mode:'learn',ids:['q01'],index:0,responses:{}});
 assert.match(html,/id="answer-form"/);assert.match(html,/回答する/);
 assert.doesNotMatch(html,/id="confidence-form"|id="answer-feedback"|基礎の説明|詳しい解説/);
});
test('after answering, explanation precedes confidence and next is unavailable until recorded',()=>{
 const session={mode:'learn',ids:['q01'],index:0,responses:{},pending:{id:'q01',selected:[0]}};
 const html=render(session);
 assert.ok(html.indexOf('id="answer-feedback"')<html.indexOf('id="confidence-form"'));
 assert.match(html,/詳しい解説/);assert.doesNotMatch(html,/data-action="next"/);
 delete session.pending;session.responses.q01={selected:[0],correct:true,confidence:'unsure'};
 const confirmed=render(session);assert.match(confirmed,/data-action="next"/);assert.doesNotMatch(confirmed,/id="confidence-form"/);
});
test('10-question check still conceals correctness and explanation until completion',()=>{
 const html=render({mode:'quiz',ids:['q01'],index:0,responses:{},pending:{id:'q01',selected:[0]}});
 assert.match(html,/id="confidence-form"/);assert.doesNotMatch(html,/id="answer-feedback"|詳しい解説|基礎の説明|class="option correct/);
 const confirmed=render({mode:'quiz',ids:['q01'],index:0,responses:{q01:{selected:[1],correct:false,confidence:'sure'}}});
 assert.doesNotMatch(confirmed,/復習対象として記録|id="answer-feedback"/);
});

test('q04 explains extra and missing choices before asking for understanding',()=>{
 const session={mode:'learn',ids:['q04'],index:0,responses:{},pending:{id:'q04',selected:[1,2,3]}};
 const html=render(session);
 assert.match(html,/正解：\$b \/ \$d/);
 assert.match(html,/あなたの回答：\$b \/ \$c \/ \$d/);
 assert.match(html,/選びすぎた選択肢：\$c/);
 assert.match(html,/verdict-incorrect/);
 assert.match(html,/id="verdict-heading">不正解です/);
 assert.match(html,/× あなたの誤答/);
 assert.match(html,/trueは真偽値です/);
 assert.match(html,/理解できた/);
 assert.match(html,/理解度を記録する/);
 assert.doesNotMatch(html,/選び忘れた選択肢|>自信あり</);
 assert.ok(html.indexOf('trueは真偽値です')<html.indexOf('id="confidence-form"'));
 session.pending.selected=[1];
 const missing=render(session);
 assert.match(missing,/選び忘れた選択肢：\$d/);
 assert.doesNotMatch(missing,/選びすぎた選択肢/);
 session.pending.selected=[1,3];
 const correct=render(session);
 assert.match(correct,/verdict-correct/);
 assert.match(correct,/id="verdict-heading">正解です！/);
 assert.doesNotMatch(correct,/× あなたの誤答|verdict-incorrect/);
});
