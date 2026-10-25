import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const content=JSON.parse(await readFile(new URL('../data/questions.json',import.meta.url),'utf8'));
globalThis.fetch=async()=>({ok:true,json:async()=>content});
const {questions}=await import('../static/questions.js');
const {initialState,isCorrect,recordAnswer,needsReview,selectQuestions,validateState}=await import('../static/core.js');
const {todayReviewIds,saveQuestionNote,questionsText}=await import('../static/core.js');
test('today review excludes older mistakes and removes corrected confident answers',()=>{
 const s=initialState(),now=new Date(2026,9,25,12).getTime();
 recordAnswer(s,'q01',[1],'unknown',now-86400000);
 recordAnswer(s,'q02',[0],'unsure',now);
 recordAnswer(s,'q03',questions[2].answer,'unsure',now);
 assert.deepEqual(todayReviewIds(s,now),['q02','q03']);
 recordAnswer(s,'q02',questions[1].answer,'sure',now+1000);
 assert.deepEqual(todayReviewIds(s,now+1000),['q03']);
 assert.equal(selectQuestions(s,{now:now+86400000})[0],'q01');
});
test('saved questions preserve the original answer, survive export, and include useful copy context',()=>{
 const s=initialState(),response={selected:[0],confidence:'unsure'};
 saveQuestionNote(s,'q02','2行目が不安です',response,123);
 response.selected[0]=2;
 const restored=validateState(JSON.parse(JSON.stringify(s)));
 assert.deepEqual(restored.questionNotes.q02.selected,[0]);
 assert.match(questionsText(restored.questionNotes),/自分の回答：2/);
 assert.match(questionsText(restored.questionNotes),/正解：5/);
 assert.match(questionsText(restored.questionNotes),/2行目が不安です/);
 for(const bad of [null,[],{unknown:restored.questionNotes.q02},{q02:{...restored.questionNotes.q02,selected:[99]}}]){
  assert.throws(()=>validateState({...restored,questionNotes:bad}));
 }
 const legacy=initialState();delete legacy.questionNotes;assert.doesNotThrow(()=>validateState(legacy));
});
test('every question has explanations for all code lines and options, and each topic has a mini lesson',()=>{
 for(const q of questions){assert.equal(q.optionReasons.length,q.options.length);assert.ok(q.optionReasons.every(Boolean));if(q.code)assert.equal(q.lines.length,q.code.split('\n').length);}
 for(const t of content.topics)assert.ok(t.example&&t.exampleExplanation);
});
test('multiple-choice grading requires exactly the correct choices',()=>{
 const q=questions.find(q=>q.answer.length>1);
 assert.equal(isCorrect(q,[...q.answer].reverse()),true);
 assert.equal(isCorrect(q,[q.answer[0]]),false);
 assert.equal(isCorrect(q,[...q.answer,0]),false);
});
test('an uncertain correct answer stays in review; confident repetitions space reviews',()=>{
 const s=initialState(),q=questions[0],now=1000000000000;
 recordAnswer(s,q.id,q.answer,'unsure',now);
 assert.equal(needsReview(s.records[q.id]),true);
 recordAnswer(s,q.id,q.answer,'sure',now+86400000);
 assert.equal(s.records[q.id].streak,1);
 recordAnswer(s,q.id,q.answer,'sure',now+2*86400000);
 assert.equal(s.records[q.id].dueAt,now+5*86400000);
 assert.equal(needsReview(s.records[q.id]),false);
 s.records[q.id].bookmark=true;
 assert.equal(needsReview(s.records[q.id]),true);
});
test('weak questions get priority without excluding every new question',()=>{
 const s=initialState();
 questions.slice(0,8).forEach(q=>recordAnswer(s,q.id,[], 'unknown',0));
 const selected=selectQuestions(s,{now:1000000000000});
 assert.equal(selected.length,5);
 assert.ok(selected.slice(0,4).every(id=>s.records[id]));
 assert.ok(selected.some(id=>!s.records[id]));
 assert.equal(new Set(selected).size,5);
});
test('topic and review modes only use relevant questions',()=>{
 const s=initialState();assert.deepEqual(selectQuestions(s,{mode:'review'}),[]);
 const selected=selectQuestions(s,{topic:'basics'});
 assert.ok(selected.every(id=>questions.find(q=>q.id===id).topic==='basics'));
});
test('backup roundtrip preserves progress and rejects invalid or foreign IDs',()=>{
 const s=initialState(),q=questions[0];recordAnswer(s,q.id,q.answer,'sure');
 s.session={mode:'learn',ids:[q.id],index:0,responses:{[q.id]:{selected:q.answer,confidence:'sure',correct:true}}};
 assert.deepEqual(validateState(JSON.parse(JSON.stringify(s))),s);
 const bad=structuredClone(s);bad.session.responses[q.id].selected=[99];
 assert.throws(()=>validateState(bad));
 const foreign=structuredClone(s);foreign.records.unknown=foreign.records[q.id];
 assert.throws(()=>validateState(foreign));
});
test('question bank has unique stable IDs, answers, explanations, and HTTPS references',()=>{
 assert.equal(questions.length,100);assert.equal(new Set(questions.map(q=>q.id)).size,100);
 for(const q of questions){assert.ok(content.topics.some(t=>t.id===q.topic));assert.ok(q.answer.every(i=>Number.isInteger(i)&&i>=0&&i<q.options.length));assert.ok(q.easy&&q.trace&&q.explanation);assert.match(q.reference,/^https:\/\/www\.php\.net\/manual\/ja\//);}
});
test('100-question edition covers every planned topic and preserves new question progress',()=>{
 const distribution={intro:3,basics:12,operators:10,control:14,builtin:9,functions:8,classes:7,request:10,database:5,oop:17,advanced:5};
 for(const [topic,count] of Object.entries(distribution))assert.equal(questions.filter(q=>q.topic===topic).length,count,topic);
 assert.ok(questions.filter(q=>q.answer.length>1).length>=10);
 assert.equal(new Set(questions.map(q=>q.title+'\n'+q.code)).size,100);
 for(const q of questions){assert.equal(new Set(q.answer).size,q.answer.length);assert.ok(q.answer.length>0&&q.answer.length<q.options.length);assert.equal(new Set(q.options).size,q.options.length);}
 const s=initialState(),q=questions.find(q=>q.id==='q100');
 recordAnswer(s,q.id,q.answer,'unsure');
 saveQuestionNote(s,q.id,'追記を復習する',{selected:q.answer,confidence:'unsure'});
 const restored=validateState(JSON.parse(JSON.stringify(s)));
 assert.deepEqual(selectQuestions(restored,{mode:'review'}),['q100']);
 assert.match(questionsText(restored.questionNotes),/追記を復習する/);
});
