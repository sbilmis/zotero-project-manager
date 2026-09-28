const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
function harness() {
  const paper = (key, title) => ({ key, libraryID: 1, isRegularItem: () => true,
    loadDataType: async type => { assert.ok(['itemData', 'creators'].includes(type)); },
    getField: field => field === 'title' ? title : '2020-01-01',
    getCreatorsJSON: () => [{ lastName: 'Author' }] });
  const items = [paper('ABCD2345', 'Paper [one]\nsecond line'), { isRegularItem: () => false },
    { ...paper('EFGH6789', 'Deleted'), deleted: true }];
  const collection = { key: '6RIU3F76', name: 'scientometry', libraryID: 1,
    loadDataType: async () => {}, getChildItems: (...args) => {
      assert.deepEqual(args, [false, false]); return items;
    } };
  const zotero = { Server: { Endpoints: {} }, Libraries: { userLibraryID: 1 },
    Prefs: { get: () => true }, getMainWindow: () => ({ ZoteroPane: { getSelectedCollection: () => collection } }),
    Collections: { getByLibraryAndKeyAsync: async (library, key) => { assert.equal(library, 1); return key === collection.key ? collection : null; } },
    logError() {} };
  const sandbox = vm.createContext({ Zotero: zotero, module: { exports: {} } });
  for (const file of ['links.js', 'picker.js']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', file), 'utf8'), sandbox);
  const picker = sandbox.module.exports.ZPMPicker;
  const request = (query = '', extra = {}) => picker.handle({ method: 'GET', headers: { 'x-zpm-client': 'emacs' }, searchParams: new URLSearchParams(query), ...extra });
  return { picker, request, zotero, collection, items, paper };
}

test('selected collection returns direct regular records, safe labels, authors/year and exact keys', async () => {
  const h = harness(); const result = await h.request(); const data = JSON.parse(result[2]);
  assert.equal(result[0], 200); assert.equal(data.collection.key, '6RIU3F76');
  assert.deepEqual(data.papers, [{ key: 'ABCD2345', title: 'Paper ［one］ second line', authors: 'Author', year: '2020' }]);
});

test('Zotero 10 picker uses all selected rows and never calls removed singular getters', async () => {
  const h = harness();
  const row = { isCollection: () => true, ref: h.collection };
  let rows = [row];
  h.zotero.getMainWindow = () => ({ ZoteroPane: {
    getCollectionTreeRows: () => rows,
    getSelectedCollection: () => assert.fail('Removed in Zotero 10'),
  } });
  assert.equal((await h.request())[0], 200);
  for (const selection of [[], [row, row], [row, { isCollection: () => false }],
    [{ isCollection: () => false }]]) {
    rows = selection;
    const result = await h.request();
    assert.equal(result[0], 409);
    assert.match(JSON.parse(result[2]).error, /exactly one collection/);
    assert.equal((await h.request('collection=6RIU3F76'))[0], 200);
  }
});

test('remembered collection is independent of current selection; missing and invalid keys fail', async () => {
  const h = harness(); h.zotero.getMainWindow = () => null;
  assert.equal((await h.request('collection=6RIU3F76'))[0], 200);
  assert.equal((await h.request())[0], 409);
  assert.equal((await h.request('collection=EFGH6789'))[0], 404);
  for (const query of ['collection=nil', 'collection=', 'collection=6RIU3F76&collection=6RIU3F76', 'other=1']) {
    assert.equal((await h.request(query))[0], 400);
  }
});

test('groups, invalid record keys and disabled local API fail without exposing records', async () => {
  const h = harness(); h.collection.libraryID = 7;
  assert.equal((await h.request())[0], 400);
  h.collection.libraryID = 1; h.items[0].key = 'nil';
  assert.equal((await h.request())[0], 400);
  h.zotero.Prefs.get = () => false;
  const response = await h.request(); assert.equal(response[0], 403);
  assert.match(response[2], /Allow other applications/);
});

test('GET-only local client guard rejects browser requests and missing headers', async () => {
  const h = harness();
  for (const headers of [{}, { 'x-zpm-client': 'other' }, { 'x-zpm-client': 'emacs', Origin: 'https://example.org' },
    { 'x-zpm-client': 'emacs', 'Sec-Fetch-Site': 'cross-site' }]) {
    assert.equal((await h.request('', { headers }))[0], 403);
  }
  assert.equal((await h.request('', { method: 'POST' }))[0], 405);
});

test('empty and large collections are complete, never silently truncated', async () => {
  const h = harness(); h.items.length = 0;
  assert.deepEqual(JSON.parse((await h.request())[2]).papers, []);
  h.items.push(...Array.from({ length: 150 }, (_, i) => h.paper('ABCD2345', `Paper ${i}`)));
  assert.equal(JSON.parse((await h.request())[2]).papers.length, 150);
});

test('endpoint lifecycle registers once and leaves replacement endpoints alone on stop', async () => {
  const h = harness(); h.picker.start();
  const endpoint = new h.zotero.Server.Endpoints['/zpm/papers']();
  assert.deepEqual(Array.from(endpoint.supportedMethods), ['GET']);
  assert.equal(endpoint.allowRequestsFromUnsafeWebContent, false);
  assert.equal((await endpoint.init({ method: 'GET', headers: { 'x-zpm-client': 'emacs' }, searchParams: new URLSearchParams() }))[0], 200);
  h.picker.stop(); assert.equal(h.zotero.Server.Endpoints['/zpm/papers'], undefined);
  h.picker.start(); const replacement = function () {}; h.zotero.Server.Endpoints['/zpm/papers'] = replacement;
  h.picker.stop(); assert.equal(h.zotero.Server.Endpoints['/zpm/papers'], replacement);
});
