const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { ZPMLinks: links } = require('../links.js');
const item = (kind = 'item', extra = {}) => ({
  id: kind === 'pdf' ? 2 : 1, key: kind === 'pdf' ? 'EFGH6789' : 'ABCD2345', libraryID: 1,
  isRegularItem: () => kind === 'item', isFileAttachment: () => kind === 'pdf',
  attachmentContentType: kind === 'pdf' ? 'application/pdf' : undefined,
  getCollections: () => [10],
  getField: () => kind === 'pdf' ? 'Full Text PDF' : 'Paper title', ...extra,
});
const annotation = (extra = {}) => ({
  id: 3, key: 'JKLM2345', libraryID: 1, parentID: 2, isAnnotation: () => true,
  annotationPosition: '{"pageIndex":4}', annotationText: 'A [highlight]\nwith text', ...extra,
});

test('collection, item and PDF formats retain exact destinations and own keys', () => {
  assert.equal(links.format(links.collection({ key: '6RIU3F76', libraryID: 1, name: 'scientometry' }, 1), 'org'),
    '[[zotero-collection:6RIU3F76][scientometry]]');
  assert.equal(links.format(links.item(item(), 1), 'org'), '[[zotero-item:ABCD2345][Paper title]]');
  assert.equal(links.format(links.item(item('pdf', { parentID: 1 }), 1), 'org'), '[[zotero-pdf:EFGH6789][Full Text PDF]]');
  assert.equal(links.format(links.item(item(), 1), 'markdown'), '[Paper title](zotero://select/library/items/ABCD2345)');
  assert.equal(links.format(links.item(item('pdf'), 1), 'uri'), 'zotero://open-pdf/library/items/EFGH6789');
  assert.equal(links.format(links.collection({ key: '6RIU3F76', libraryID: 1, name: 'c' }, 1), 'uri'), 'zotero://select/library/collections/6RIU3F76');
});

test('labels normalize brackets, CR/LF, blank lines and Unicode whitespace', () => {
  const target = links.item(item('item', { getField: () => '  A [test]]\r\n\n New\tline\u2028文献\0 ' }), 1);
  assert.equal(links.format(target, 'org'), '[[zotero-item:ABCD2345][A ［test］］ New line 文献]]');
  assert.equal(links.label('\n\t', 'fallback'), 'fallback');
  assert.match(links.format({ ...target, label: null }, 'org'), /item ABCD2345/);
  assert.equal(links.format({ ...target, label: '*x* _y_ `z` <i> &amp; \\ [q]' }, 'markdown'),
    '[\\*x\\* \\_y\\_ \\`z\\` \\<i\\> \\&amp; \\\\ ［q］](zotero://select/library/items/ABCD2345)');
});

test('keys are strict strings: no nil, missing, lowercase, controls, URL syntax or excluded characters', () => {
  for (const key of [undefined, null, '', 'nil', 23456789, 'abcd2345', 'ABCD1234', 'ABCD0EFG', 'ABCDOEFG', 'ABCD2345\n', ' ABCD2345', 'ABCD2345?page=2', '../ABCD2', 'ABCDEFGHI']) {
    assert.throws(() => links.key(key), /key/i);
  }
  assert.equal(links.key('23456789'), '23456789');
  assert.equal(links.key('6RIU3F76'), '6RIU3F76');
});

test('all unsupported selections fail explicitly', () => {
  for (const candidate of [item('note'), item('annotation'), item('pdf', { attachmentContentType: 'image/png' }),
    item('pdf', { isFileAttachment: () => false }), item('item', { libraryID: 7 }),
    item('item', { libraryID: undefined }), item('item', { deleted: true }), item('item', { key: '' })]) {
    assert.throws(() => links.selection([candidate], 1));
    assert.throws(() => links.selection([item(), candidate], 1, true));
  }
  for (const selection of [undefined, [], [item(), item()]]) assert.throws(() => links.selection(selection, 1));
  assert.throws(() => links.selection([item()], 1, true));
  assert.throws(() => links.item(item(), undefined));
  assert.throws(() => links.collection({ key: '6RIU3F76', libraryID: 7 }, 1));
});

test('batch keeps selection order and one link per logical line, including mixed item/PDF selections', () => {
  assert.equal(links.text(links.selection([item('pdf'), item()], 1, true), 'org'),
    '[[zotero-pdf:EFGH6789][Full Text PDF]]\n[[zotero-item:ABCD2345][Paper title]]');
  assert.throws(() => links.text([], 'org'));
  assert.throws(() => links.format(links.item(item(), 1), 'html'));
});

test('page and saved annotation links use physical pages and the owning attachment', () => {
  assert.equal(links.format(links.page(item('pdf'), 0, 1), 'uri'), 'zotero://open-pdf/library/items/EFGH6789?page=1');
  const target = links.annotation(item('pdf'), annotation(), 1);
  assert.equal(links.format(target, 'uri'), 'zotero://open-pdf/library/items/EFGH6789?page=5&annotation=JKLM2345');
  assert.match(links.format(target, 'org'), /^\[\[zotero-pdf:EFGH6789\?page=5&annotation=JKLM2345\]\[/);
  for (const page of [-1, undefined, null, '4', 1.5, NaN, Infinity, Number.MAX_SAFE_INTEGER]) assert.throws(() => links.page(item('pdf'), page, 1));
  for (const bad of [annotation({ parentID: 99 }), annotation({ libraryID: 7 }), annotation({ key: '' }),
    annotation({ annotationPosition: 'broken' }), annotation({ annotationPosition: 'null' }),
    annotation({ annotationPosition: '{"pageIndex":-1}' }), annotation({ isAnnotation: () => false })]) {
    assert.throws(() => links.annotation(item('pdf'), bad, 1));
  }
  assert.throws(() => links.page(item(), 0, 1));
  assert.throws(() => links.format({ kind: 'item', key: 'ABCD2345', page: 1 }, 'uri'));
});

function harness() {
  const copied = [], errors = [], menus = [], listeners = [], removed = [];
  const pdf = item('pdf');
  const sandbox = vm.createContext({ module: { exports: {} }, Zotero: {
    Libraries: { userLibraryID: 1 },
    MenuManager: { registerMenu: (menu) => { menus.push(menu); return menu.menuID; }, unregisterMenu: (id) => removed.push(id) },
    Reader: { registerEventListener: (type, handler, pluginID) => listeners.push({ type, handler, pluginID }),
      _unregisterEventListenerByPluginID: (id) => removed.push(id),
      unregisterEventListener: () => assert.fail('Do not use the broken Zotero 9.0 public cleanup') },
    Items: { get: (id) => id === 2 ? pdf : null, getByLibraryAndKey: (_lib, key) => key === 'JKLM2345' ? annotation() : null },
    Utilities: { Internal: { copyTextToClipboard: (text) => copied.push(text) } },
    logError() {},
  } });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../links.js'), 'utf8'), sandbox);
  const controller = sandbox.module.exports.ZPMLinkMenus;
  controller.start({ id: 'zpm-test', alert: (...args) => errors.push(args) });
  return { controller, copied, errors, menus, listeners, removed, pdf };
}

test('native menus dispatch exact selection types, revalidate on command, and preserve clipboard on failure', () => {
  const h = harness();
  const menu = h.menus[1].menus[0].menus;
  const orgItem = menu.find(x => x.l10nID === 'zpm-copy-root').menus[0];
  let enabled;
  const context = { items: [item()], setEnabled: value => { enabled = value; } };
  orgItem.onShowing(null, context); assert.equal(enabled, true);
  orgItem.onCommand(null, context); assert.equal(h.copied.length, 1);
  context.items = [item(), item('note')];
  orgItem.onShowing(null, context); assert.equal(enabled, false);
  orgItem.onCommand(null, context); assert.equal(h.copied.length, 1);
  const batch = menu.find(x => x.l10nID === 'zpm-copy-multiple').menus[1];
  batch.onCommand(null, context); assert.equal(h.copied.length, 1);
  assert.match(h.errors.at(-1)[1], /Notes/);
  context.items = [item(), item('pdf')];
  batch.onShowing(null, context); assert.equal(enabled, true);
  batch.onCommand(null, context); assert.equal(h.copied[1].split('\n').length, 2);
  const collection = h.menus[0].menus[0].menus[0].menus[0];
  collection.onCommand(null, { collectionTreeRow: { isCollection: () => false } });
  assert.equal(h.copied.length, 2);
});

test('Zotero 10 collection and scoped item links reject ambiguous selection without reading singular context', () => {
  const h = harness();
  const collection = { id: 10, key: '6RIU3F76', libraryID: 1, name: 'Research' };
  const row = { isCollection: () => true, ref: collection };
  let enabled;
  const context = {
    items: [item()], collectionTreeRows: [row],
    get collectionTreeRow() { assert.fail('Removed in Zotero 10'); },
    setEnabled(value) { enabled = value; }, setVisible() {},
  };
  const collectionMenu = h.menus[0].menus[0].menus[0];
  const scopedMenu = h.menus[1].menus[0].menus.find(x => x.l10nID === 'zpm-copy-in-collection');
  collectionMenu.onShowing(null, context);
  assert.equal(enabled, true);
  collectionMenu.menus[0].onCommand(null, context);
  assert.equal(h.copied[0], '[[zotero-collection:6RIU3F76][Research]]');
  scopedMenu.menus[0].onCommand(null, context);
  assert.match(h.copied[1], /collection=6RIU3F76/);
  for (const rows of [[], [row, row], [row, { isCollection: () => false }],
    [{ isCollection: () => false }]]) {
    context.collectionTreeRows = rows;
    for (const menu of [collectionMenu, scopedMenu]) {
      menu.onShowing(null, context);
      assert.equal(enabled, false);
      menu.menus[0].onCommand(null, context);
      assert.equal(h.copied.length, 2);
    }
  }
  h.menus[1].menus[0].menus[0].menus[0].onCommand(null, context);
  assert.equal(h.copied[2], '[[zotero-item:ABCD2345][Paper title]]');
});

function readerMenu(h, type, params) {
  const groups = [];
  h.listeners.find(x => x.type === type).handler({
    reader: { itemID: 2 }, params, append: (...items) => groups.push(items),
  });
  return groups;
}

test('native reader menus copy pages and disable unavailable or multiple targets', () => {
  const h = harness();
  function event(type, params) {
    const [[menu]] = readerMenu(h, type, params);
    assert.equal(menu.label, 'ZPM');
    assert.equal(menu.groups[0][0].label, 'Copy PDF Page Link');
    return menu.groups[0][0].groups[0];
  }
  let commands = event('createViewContextMenu', { position: { pageIndex: 3 } });
  assert.equal(commands[0].disabled, false); commands[2].onCommand();
  assert.equal(h.copied[0], 'zotero://open-pdf/library/items/EFGH6789?page=4');
  commands = event('createThumbnailContextMenu', { pageIndexes: [0] });
  commands[0].onCommand(); assert.match(h.copied[1], /EFGH6789\?page=1/);
  for (const [type, params] of [['createViewContextMenu', {}], ['createThumbnailContextMenu', { pageIndexes: [0, 1] }]]) {
    const commands = event(type, params);
    assert.equal(commands[0].disabled, true); commands[0].onCommand();
    assert.equal(h.copied.length, 2);
  }
  h.pdf.libraryID = 7;
  assert.equal(event('createViewContextMenu', { position: { pageIndex: 0 } })[0].disabled, true);
});

test('internal annotation menu exposes directly clickable links in every format', () => {
  const h = harness();
  const groups = readerMenu(h, 'createAnnotationContextMenu', { ids: ['JKLM2345'] });
  // Zotero's internal annotation menu renders only top-level rows; it never
  // traverses native-menu `groups`. All actions must be directly reachable.
  const commands = groups.flat().filter(command => !command.disabled || command.persistent);
  assert.equal(groups.length, 1);
  assert.deepEqual(commands.map(command => command.label), [
    'ZPM: Copy Annotation Link (Org)',
    'ZPM: Copy Annotation Link (Markdown)',
    'ZPM: Copy Annotation Link (Zotero URI)',
  ]);
  for (const command of commands) {
    assert.equal(command.groups, undefined);
    assert.equal(command.disabled, false);
    command.onCommand();
  }
  assert.deepEqual(h.copied, [
    '[[zotero-pdf:EFGH6789?page=5&annotation=JKLM2345][Full Text PDF — PDF page 5 — A ［highlight］ with text]]',
    '[Full Text PDF — PDF page 5 — A ［highlight］ with text](zotero://open-pdf/library/items/EFGH6789?page=5&annotation=JKLM2345)',
    'zotero://open-pdf/library/items/EFGH6789?page=5&annotation=JKLM2345',
  ]);
});

test('annotation commands stay disabled for unsupported selections and revalidate when invoked', () => {
  const h = harness();
  const params = { ids: ['JKLM2345'] };
  const commands = readerMenu(h, 'createAnnotationContextMenu', params).flat();
  commands[2].onCommand();
  params.ids = [];
  commands[2].onCommand();
  assert.equal(h.copied.length, 1);
  assert.match(h.errors.at(-1)[1], /exactly one saved PDF annotation/);
  for (const params of [{}, { ids: [] }, { ids: ['JKLM2345', 'ABCD2345'] },
    { ids: ['ABCD2345'] }, { ids: ['invalid'] }]) {
    const commands = readerMenu(h, 'createAnnotationContextMenu', params).flat();
    assert.equal(commands.length, 3);
    for (const command of commands) {
      assert.equal(command.disabled, true);
      assert.equal(command.persistent, true);
      command.onCommand();
    }
    assert.equal(h.copied.length, 1);
  }
  h.pdf.libraryID = 7;
  const groupCommands = readerMenu(h, 'createAnnotationContextMenu', { ids: ['JKLM2345'] }).flat();
  for (const command of groupCommands) {
    assert.equal(command.disabled, true);
    command.onCommand();
  }
  assert.equal(h.copied.length, 1);
  h.controller.stop();
  commands[0].onCommand();
  assert.equal(h.copied.length, 1);
});

test('shutdown removes this plugin menus and reader hooks; queued commands become inert', () => {
  const h = harness();
  h.controller.stop();
  assert.deepEqual(h.removed, ['zpm-collection', 'zpm-item', 'zpm-test']);
  h.listeners[0].handler({ append: () => assert.fail('stopped plugin appended menu') });
  h.controller.copy(() => [links.item(item(), 1)], 'org');
  assert.equal(h.copied.length, 0);
});

test('bootstrap loads the packaged link module and starts/stops all menus alongside exports', async () => {
  const registered = [], removed = [], copied = [];
  const pluginDir = path.join(__dirname, '..');
  const sandbox = vm.createContext({
    APP_SHUTDOWN: 99,
    Zotero: {
      initializationPromise: Promise.resolve(),
      Server: { Endpoints: {} },
      PreferencePanes: { register: async () => {} },
      getMainWindows: () => [], debug() {}, logError() {},
      Libraries: { userLibraryID: 1 },
      Utilities: { Internal: { copyTextToClipboard: value => copied.push(value) } },
      MenuManager: {
        registerMenu: menu => { registered.push(menu); return menu.menuID; },
        unregisterMenu: id => removed.push(id),
      },
      Reader: { registerEventListener() {}, _unregisterEventListenerByPluginID() {} },
    },
    Services: { scriptloader: { loadSubScript: filename => {
      vm.runInContext(fs.readFileSync(filename, 'utf8'), sandbox, { filename });
    } } },
  });
  vm.runInContext(fs.readFileSync(path.join(pluginDir, 'bootstrap.js'), 'utf8'), sandbox);
  await sandbox.startup({ id: 'zpm-test', rootURI: pluginDir + '/' });
  assert.deepEqual(registered.map(x => x.menuID), ['zpm-collection', 'zpm-item']);
  const entry = registered[1].menus[0].menus.find(x => x.l10nID === 'zpm-copy-root').menus[0];
  entry.onCommand(null, { items: [item()] });
  assert.equal(copied[0], '[[zotero-item:ABCD2345][Paper title]]');
  sandbox.shutdown({}, 0);
  assert.deepEqual(removed, ['zpm-collection', 'zpm-item']);
});


test('collection-aware paper links validate both keys and direct membership in all formats', () => {
  const collection = { id: 10, key: '6RIU3F76', libraryID: 1 };
  const target = links.itemInCollection(item(), collection, 1);
  assert.equal(links.format(target, 'org'), '[[zotero-item:ABCD2345?collection=6RIU3F76][Paper title]]');
  assert.equal(links.format(target, 'uri'), 'zotero://select/library/collections/6RIU3F76/items/ABCD2345');
  assert.equal(links.format(target, 'markdown'), '[Paper title](zotero://select/library/collections/6RIU3F76/items/ABCD2345)');
  for (const bad of [{ ...collection, key: '' }, { ...collection, libraryID: 7 }, { ...collection, id: 11 }]) {
    assert.throws(() => links.itemInCollection(item(), bad, 1));
  }
  assert.throws(() => links.itemInCollection(item('pdf'), collection, 1));
  assert.throws(() => links.format({ ...target, collection: 'nil' }, 'org'));
  assert.throws(() => links.format({ ...target, kind: 'pdf' }, 'uri'));
});

test('one parent menu shows single, batch, and collection-context actions only when appropriate', () => {
  const h = harness();
  assert.equal(h.menus.length, 2);
  for (const menu of h.menus) assert.equal(menu.menus[0].l10nID, 'zpm-menu-root');
  const [single, multiple, scoped] = h.menus[1].menus[0].menus;
  let visible, enabled;
  const context = { items: [item()], setVisible: x => { visible = x; }, setEnabled: x => { enabled = x; },
    collectionTreeRow: { isCollection: () => true, ref: { id: 10, key: '6RIU3F76', libraryID: 1 } } };
  single.onShowing(null, context); assert.equal(visible, true); assert.equal(enabled, true);
  multiple.onShowing(null, context); assert.equal(visible, false);
  scoped.onShowing(null, context); assert.equal(visible, true); assert.equal(enabled, true);
  scoped.menus[0].onCommand(null, context); assert.match(h.copied[0], /collection=6RIU3F76/);
  context.items = [item('pdf')];
  single.onShowing(null, context); assert.equal(visible, true); assert.equal(enabled, true);
  scoped.onShowing(null, context); assert.equal(visible, false);
  context.items = [item(), item('pdf')];
  single.onShowing(null, context); assert.equal(visible, false);
  multiple.onShowing(null, context); assert.equal(visible, true); assert.equal(enabled, true);
  scoped.onShowing(null, context); assert.equal(visible, false);
  context.items = [item('note')];
  single.onShowing(null, context); assert.equal(visible, true); assert.equal(enabled, false);
  context.items = [item()];
  context.collectionTreeRow = { isCollection: () => false };
  scoped.onShowing(null, context); assert.equal(visible, false);
  scoped.menus[0].onCommand(null, context); assert.equal(h.copied.length, 1);
  context.collectionTreeRow = { isCollection: () => true, ref: { id: 11, key: '6RIU3F76', libraryID: 1 } };
  scoped.onShowing(null, context); assert.equal(visible, false);
  scoped.menus[0].onCommand(null, context); assert.equal(h.copied.length, 1);
});
