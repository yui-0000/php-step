import {questions} from './questions.js';
export const STORAGE_KEY='php-step:v1';
export const dayKey=(date=new Date())=>`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
export const initialState=()=>({version:1,settings:{examDate:'2026-11-16',dailyGoal:15,difficulty:'all'},records:{},questionNotes:{},daily:{},session:null,lastResult:null});
export const isCorrect=(question,selection)=>selection.length===question.answer.length && question.answer.every(i=>selection.includes(i));
export const needsReview=r=>!!r&&(r.bookmark||!r.correct||r.confidence!=='sure');
export function recordAnswer(state,id,selection,confidence,now=Date.now()){
 const question=questions.find(q=>q.id===id);if(!question)throw Error('Unknown question');
 const correct=isCorrect(question,selection);const old=state.records[id]||{};
 const streak=correct&&confidence==='sure'?(old.streak||0)+1:0;
 const interval=streak===0?1:streak===1?1:streak===2?3:7;
 state.records[id]={...old,attempts:(old.attempts||0)+1,correct,confidence,streak,lastAt:now,dueAt:now+interval*86400000};
 const key=dayKey(new Date(now));state.daily[key]=(state.daily[key]||0)+1;
 return correct;
}
export function selectQuestions(state,{mode='learn',topic,count=5,difficulty=state.settings?.difficulty??'all',now=Date.now(),random=Math.random}={}){
 let pool=questions.filter(q=>(!topic||q.topic===topic)&&(mode==='review'||difficulty==='all'||q.difficulty===difficulty));
 if(mode==='review')pool=pool.filter(q=>needsReview(state.records[q.id]));
 if(mode==='quiz')return pool.map(q=>({q,n:random()})).sort((a,b)=>a.n-b.n).slice(0,count).map(x=>x.q.id);
 const score=q=>{const r=state.records[q.id];if(!r)return 20;if(needsReview(r))return (r.dueAt<=now?0:10)+(r.correct?3:0);return r.dueAt<=now?30:40;};
 pool.sort((a,b)=>score(a)-score(b)||(state.records[a.id]?.lastAt||0)-(state.records[b.id]?.lastAt||0));
 let picked=pool.slice(0,count);
 // 苦手が多くても、新しい問題を最低1問混ぜて範囲を広げる。
 if(mode==='learn'&&!topic&&picked.length===count&&!picked.some(q=>!state.records[q.id])){const fresh=pool.find(q=>!state.records[q.id]);if(fresh)picked[picked.length-1]=fresh;}
 return picked.map(q=>q.id);
}
const integer=n=>Number.isSafeInteger(n)&&n>=0;
const validDate=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&!Number.isNaN(Date.parse(s))&&new Date(s).toISOString().slice(0,10)===s;
const ids=new Set(questions.map(q=>q.id));
const confidences=['sure','unsure','unknown'];
export function validateState(s){
 if(!s||s.version!==1||!s.settings||!validDate(s.settings.examDate)||!integer(s.settings.dailyGoal)||s.settings.dailyGoal<5||s.settings.dailyGoal>100)throw Error('設定が正しくありません');
 if(s.settings.difficulty!==undefined&&!['all','basic','standard','practice'].includes(s.settings.difficulty))throw Error('難易度の設定が正しくありません');
 if(!s.records||Array.isArray(s.records)||typeof s.records!=='object'||!s.daily||Array.isArray(s.daily)||typeof s.daily!=='object')throw Error('履歴が正しくありません');
 for(const [id,r]of Object.entries(s.records)){if(!ids.has(id)||!r||!integer(r.attempts)||r.attempts<1||typeof r.correct!=='boolean'||!confidences.includes(r.confidence)||!integer(r.streak)||!integer(r.lastAt)||!integer(r.dueAt)||(r.bookmark!==undefined&&typeof r.bookmark!=='boolean'))throw Error('問題の履歴が正しくありません');}
 for(const [key,n]of Object.entries(s.daily))if(!validDate(key)||!integer(n))throw Error('日別履歴が正しくありません');
 for(const current of [s.session,s.lastResult]){if(!current)continue;if(!['learn','review','topic','quiz'].includes(current.mode)||!Array.isArray(current.ids)||current.ids.length<1||current.ids.length>questions.length||new Set(current.ids).size!==current.ids.length||current.ids.some(id=>!ids.has(id))||!integer(current.index)||current.index>=current.ids.length||!current.responses||typeof current.responses!=='object')throw Error('学習途中のデータが正しくありません');
 for(const[id,r]of Object.entries(current.responses)){const q=questions.find(q=>q.id===id);if(!current.ids.includes(id)||!Array.isArray(r.selected)||new Set(r.selected).size!==r.selected.length||r.selected.length<1||r.selected.some(n=>!integer(n)||n>=q.options.length)||!confidences.includes(r.confidence)||r.correct!==isCorrect(q,r.selected))throw Error('回答データが正しくありません');}}
 if(s.session?.pending!==undefined){
  const current=s.session,p=current.pending,q=questions.find(q=>q.id===p?.id);
  if(!p||!q||p.id!==current.ids[current.index]||current.responses[p.id]||!Array.isArray(p.selected)||!p.selected.length||new Set(p.selected).size!==p.selected.length||p.selected.some(i=>!integer(i)||i>=q.options.length))throw Error('自信の記録待ちデータが正しくありません');
 }
 if(s.lastResult?.pending!==undefined)throw Error('結果に未確定の回答があります');
 const notes=s.questionNotes===undefined?{}:s.questionNotes;
 if(typeof notes!=='object'||Array.isArray(notes)||notes===null)throw Error('質問ノートが正しくありません');
 for(const [id,n] of Object.entries(notes)){
  const q=questions.find(q=>q.id===id);
  if(!q||!n||typeof n.note!=='string'||n.note.length>2000||!integer(n.savedAt)||!Array.isArray(n.selected)||new Set(n.selected).size!==n.selected.length||n.selected.some(i=>!integer(i)||i>=q.options.length)||!confidences.includes(n.confidence))throw Error('質問ノートが正しくありません');
 }
 return s;
}

export function todayReviewIds(state,now=Date.now()){
 return questions.filter(q=>needsReview(state.records[q.id])&&dayKey(new Date(state.records[q.id].lastAt))===dayKey(new Date(now))).map(q=>q.id);
}
export function saveQuestionNote(state,id,note,response,now=Date.now()){
 if(!questions.some(q=>q.id===id))throw Error('Unknown question');
 state.questionNotes??={};
 state.questionNotes[id]={note:note.slice(0,2000),selected:[...(response?.selected||[])],confidence:response?.confidence||'unknown',savedAt:now};
}
export function questionText(id,note){
 const q=questions.find(q=>q.id===id);
 return `問題ID：${id}\n問題：${q.title}\n${q.code||''}\n選択肢：\n${q.options.map((v,i)=>`${i+1}. ${v}`).join('\n')}\n自分の回答：${note.selected.length?note.selected.map(i=>q.options[i]).join(' / '):'未回答'}\n自信：${{sure:'自信あり',unsure:'迷った',unknown:'わからない'}[note.confidence]}\n正解：${q.answer.map(i=>q.options[i]).join(' / ')}\n解説：${q.explanation}\n質問：${note.note||'どこから考えればよいか、初心者向けに説明してください。'}\n参考：${q.reference}`;
}
export function questionsText(notes){
 return 'PHP8初級の学習中です。次の問題を初心者向けに、コードの流れと選択肢の違いも含めて説明してください。\n\n'+Object.entries(notes).map(([id,n])=>questionText(id,n)).join('\n\n──────────\n\n');
}

export function stageAnswer(state,selection){
 const s=state.session,id=s?.ids[s.index],q=questions.find(q=>q.id===id);
 if(!q||s.responses[id]||s.pending)throw Error('この回答はすでに受け付けています');
 if(!Array.isArray(selection)||!selection.length||new Set(selection).size!==selection.length||selection.some(i=>!integer(i)||i>=q.options.length))throw Error('答えを選んでください');
 s.pending={id,selected:[...selection]};
 return isCorrect(q,selection);
}
export function confirmConfidence(state,confidence,now=Date.now()){
 const s=state.session,p=s?.pending;
 if(!p||p.id!==s.ids[s.index]||s.responses[p.id])throw Error('記録待ちの回答がありません');
 if(!confidences.includes(confidence))throw Error('自信を選んでください');
 const correct=recordAnswer(state,p.id,p.selected,confidence,now);
 s.responses[p.id]={selected:[...p.selected],confidence,correct};
 delete s.pending;
 return correct;
}
