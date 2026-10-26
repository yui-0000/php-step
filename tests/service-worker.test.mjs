import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

function worker(fetchResponse) {
  const events = {}, puts = [];
  const cache = {match: async () => new Response('offline-study'), put: async (key, response) => puts.push([key, await response.text()])};
  vm.runInNewContext(readFileSync(new URL('../static/sw.js', import.meta.url), 'utf8'), {
    self: {addEventListener: (type, handler) => { events[type] = handler; }},
    location: {origin: 'https://study.example'}, URL, Response,
    caches: {open: async () => cache}, fetch: fetchResponse,
  });
  return {puts, request: (path) => new Promise(resolve => events.fetch({request: {url: 'https://study.example' + path, method: 'GET'}, respondWith: resolve}))};
}

test('online denial never falls back to cached questions', async () => {
  const w = worker(async () => new Response('entrance_required', {status: 401}));
  assert.equal((await w.request('/api/questions')).status, 401);
  assert.equal(w.puts.length, 0);
});

test('login redirect does not replace offline study shell', async () => {
  const response = new Response('login-form');
  Object.defineProperty(response, 'redirected', {value: true});
  const w = worker(async () => response);
  assert.equal(await (await w.request('/')).text(), 'login-form');
  assert.equal(w.puts.length, 0);
});

test('connection failure permits already downloaded offline study', async () => {
  const w = worker(async () => {throw new TypeError('offline');});
  assert.equal(await (await w.request('/')).text(), 'offline-study');
  assert.equal(await (await w.request('/api/questions')).text(), 'offline-study');
});

test('authenticated online responses refresh cached content', async () => {
  const w = worker(async () => new Response('updated-study'));
  assert.equal(await (await w.request('/api/questions')).text(), 'updated-study');
  assert.equal(w.puts[0][1], 'updated-study');
});

test('new worker activates only after all shell assets are cached', async () => {
  const events={}, calls=[];
  let finish;
  const ready=new Promise(resolve=>{finish=resolve;});
  vm.runInNewContext(readFileSync(new URL('../static/sw.js', import.meta.url), 'utf8'), {
    self:{addEventListener:(name,handler)=>{events[name]=handler;},skipWaiting:()=>{calls.push('activate');}},
    caches:{open:async()=>({addAll:async()=>{calls.push('cache');await ready;}})},
  });
  let installed;
  events.install({waitUntil:promise=>{installed=promise;}});
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(calls,['cache']);
  finish();await installed;
  assert.deepEqual(calls,['cache','activate']);
});
