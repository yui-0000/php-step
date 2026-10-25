// 端末の履歴をFlaskへバックアップ。競合したら自動上書きを止める。
export function createSync({getState,replaceState,hasLocal,onStatus,validate,blocked}) {
  const KEY='php-step:server-meta';
  let info=null,ready=false,running=false,pending=false,conflict=false,edited=false;
  const meta=()=>{try{return JSON.parse(localStorage.getItem(KEY)||'null');}catch{return null;}};
  const remember=()=>{try{localStorage.setItem(KEY,JSON.stringify({id:info.browserId,revision:info.revision}));}catch{}};
  async function fetchInfo(){const r=await fetch('/api/state',{cache:'no-store'});if(!r.ok)throw Error('server');return r.json();}
  async function init(){
    if(blocked())return;
    try{
      const remote=await fetchInfo();const prior=meta();info=remote;
      if(remote.state&&!hasLocal()&&!edited){replaceState(validate(remote.state));remember();}
      else if(remote.state&&(!prior||prior.id!==remote.browserId||prior.revision!==remote.revision)){
        conflict=true;onStatus('履歴の競合：設定で確認');return;
      }
      ready=true;remember();onStatus('端末・サーバーに保存');
      if(edited||(!remote.state&&hasLocal())){pending=true;await flush();}
    }catch{onStatus('端末に保存・通信待ち');}
  }
  async function flush(){
    if(!ready||running||conflict||blocked()||!pending)return;
    running=true;
    try{
      while(pending){pending=false;const r=await fetch('/api/state',{method:'PUT',headers:{'Content-Type':'application/json','X-CSRF-Token':info.csrf},body:JSON.stringify({revision:info.revision,state:getState()})});
        if(r.status===409){conflict=true;onStatus('履歴の競合：設定で確認');break;}
        if(!r.ok)throw Error('save');const saved=await r.json();info.revision=saved.revision;remember();onStatus('端末・サーバーに保存');
      }
    }catch{pending=true;onStatus('端末に保存・通信待ち');}
    finally{running=false;}
  }
  window.addEventListener('online',()=>{if(!ready&&!conflict)init();else flush();});
  return {
    init,
    changed(){edited=true;pending=true;flush();},
    async restore(){if(running)throw Error('保存中です。少し待ってからもう一度お試しください。');const remote=await fetchInfo();if(!remote.state)throw Error('サーバーに保存済みの履歴はありません');const restored=validate(remote.state);info=remote;replaceState(restored);remember();ready=true;conflict=false;pending=false;onStatus('サーバーの履歴を復元しました');},
    async overwrite(){if(running)throw Error('保存中です。少し待ってからもう一度お試しください。');info=await fetchInfo();ready=true;conflict=false;pending=true;await flush();if(pending||conflict)throw Error('保存できませんでした。端末の履歴は保持しています。');},
  };
}
