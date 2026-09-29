const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function harness() {
  const alerts = [], notices = [], exports = [], settings = [];
  const collection = { id: 1, libraryID: 1, key: "ABCDEFGH", name: "Agentic_AI" };
  const collections = [collection];
  const prefs = new Map([
    ["extensions.zpm.annotationLayout", "sidecar"],
    ["extensions.zpm.filenameTemplate", "year_title"],
    ["extensions.zpm.includeNonPdf", true],
  ]);
  const sandbox = vm.createContext({
    module: { exports: {} },
    Zotero: {
      Libraries: { userLibraryID: 1 },
      Collections: { getByParent(id) {
        const children = collections.filter((value) => value.parentID === id);
        return children.flatMap((child) => [child, ...this.getByParent(child.id)]);
      } },
      Prefs: { get: (key) => prefs.get(key) },
      PreferencePanes: { register: async (options) => settings.push(options) },
      MenuManager: { registerMenu: (options) => { if (options.target === "main/library/collection") sandbox.menu = options; return options.menuID; } },
      Reader: { registerEventListener() {} },
      getMainWindows: () => [],
      debug() {}, logError() {},
      launchURL() { assert.fail("A standard export must not launch external apps"); },
    },
    ZPMPicker: { start() {}, stop() {} },
    ZPMNativeExporter: {
      async exportSnapshot(snapshot, _fileSystem, key, options) {
        exports.push({ snapshot, key, options });
        return {
          collectionName: snapshot.collection.name, workspace: `/exports/${snapshot.collection.name}`,
          copied: 1, updated: 0, unchanged: 0, missing: 0, retainedSettings: [],
        };
      },
    },
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../links.js"), "utf8"), sandbox);
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../zpm.js"), "utf8"), sandbox);
  const plugin = sandbox.module.exports.ZPMPlugin;
  plugin.alert = (...args) => alerts.push(args);
  plugin.notify = (...args) => notices.push(args);
  plugin.chooseOutputDirectory = async () => "/exports";
  plugin.buildSnapshot = async (collection, annotations) => ({ collection, annotations });
  const selection = { collectionTreeRow: { isCollection: () => true, ref: collection } };
  return { sandbox, plugin, selection, alerts, notices, exports, settings, collections, prefs };
}

test("unified collection menu retains export actions and Settings", async () => {
  const h = harness();
  await h.plugin.startup({ id: "zpm@zotero-project-manager", rootURI: "plugin/" });
  assert.equal(h.settings[0].id, "zpm-preferences");
  const root = h.sandbox.menu.menus[0];
  assert.equal(root.l10nID, "zpm-menu-root");
  assert.deepEqual(Array.from(root.menus, x => x.l10nID || x.menuType), ["zpm-copy-root", "zpm-export-root", "separator", "zpm-menu-settings"]);
  const menu = root.menus[1].menus;
  assert.deepEqual(Array.from(menu, (entry) => entry.l10nID || entry.menuType), [
    "zpm-menu-export-pdfs", "zpm-menu-export-annotations",
  ]);
  const commands = [];
  h.plugin.exportSelected = (...args) => commands.push(args);
  menu[0].onCommand(null, h.selection);
  menu[1].onCommand(null, h.selection);
  assert.deepEqual(commands, [[h.selection, false], [h.selection, true]]);
  for (const removed of ["sendExport", "setNotebookLink", "runDesktopScript"]) {
    assert.equal(removed in h.plugin, false);
  }
});

test("standard menu export retains folder, annotations, and filename settings", async () => {
  const h = harness();
  await h.plugin.exportSelected(h.selection, true);
  assert.equal(h.exports.length, 1);
  const { snapshot, key, options } = h.exports[0];
  assert.equal(snapshot.annotations, true);
  assert.equal(key, "ABCDEFGH");
  assert.equal(options.outputDir, "/exports");
  assert.equal(options.exportAnnotations, true);
  assert.equal(options.includeNonPdf, true);
  assert.equal(options.annotationLayout, "sidecar");
  assert.equal(options.filenameTemplate, "year_title");
  assert.equal("notebooklm" in options, false);
  assert.equal(h.alerts.length, 0);
  assert.equal(h.notices[0][0], "Export complete");
  assert.match(h.notices[0][1], /\/exports\/Agentic_AI/);
  assert.equal(h.plugin.exportInProgress, false);
});

test("Zotero 10 export menu supports multiple collections but not mixed rows", async () => {
  const h = harness();
  await h.plugin.startup({ id: "zpm@zotero-project-manager", rootURI: "plugin/" });
  const menu = h.sandbox.menu.menus[0].menus[1];
  const row = h.selection.collectionTreeRow;
  let enabled;
  const context = {
    collectionTreeRows: [row],
    get collectionTreeRow() { assert.fail("Removed in Zotero 10"); },
    setEnabled(value) { enabled = value; },
  };
  menu.onShowing(null, context);
  assert.equal(enabled, true);
  await h.plugin.exportSelected(context, true);
  assert.equal(h.exports.length, 1);
  assert.equal(h.exports[0].key, row.ref.key);
  const second = { id: 2, libraryID: 1, key: "JKLM2345", name: "Motivation" };
  h.collections.push(second);
  context.collectionTreeRows = [row, { isCollection: () => true, ref: second }];
  menu.onShowing(null, context);
  assert.equal(enabled, true);
  let prompts = 0;
  h.plugin.chooseOutputDirectory = async () => { prompts++; return "/exports"; };
  await h.plugin.exportSelected(context, false);
  assert.equal(prompts, 1);
  assert.deepEqual(h.exports.slice(1).map((entry) => entry.key), ["ABCDEFGH", "JKLM2345"]);
  assert.ok(h.exports.slice(1).every((entry) => entry.options.outputDir === "/exports"
    && entry.options.exportAnnotations === false));
  assert.equal(h.alerts.length, 0);
  assert.match(h.notices.at(-1)[1], /Exported 2 of 2 collections/);
  assert.match(h.notices.at(-1)[1], /\/exports\/Motivation/);
  // Copy Link remains deliberately singular even when Export is enabled.
  context.setVisible = () => {};
  h.sandbox.menu.menus[0].menus[0].onShowing(null, context);
  assert.equal(enabled, false);
  h.plugin.chooseOutputDirectory = () => assert.fail("Invalid selection must not choose a folder");
  for (const rows of [[], [row, { isCollection: () => false }],
    [{ isCollection: () => false }], [{ isCollection: () => true }]]) {
    context.collectionTreeRows = rows;
    menu.onShowing(null, context);
    assert.equal(enabled, false);
    await h.plugin.exportSelected(context, false);
    assert.equal(h.exports.length, 3);
    assert.match(h.alerts.at(-1)[1], /one or more Zotero collections/);
    assert.equal(h.plugin.exportInProgress, false);
  }
});

function multiSelection(collections) {
  return { collectionTreeRows: collections.map((ref) => ({ ref, isCollection: () => true })),
    get collectionTreeRow() { assert.fail("Removed in Zotero 10"); } };
}

test("subcollection export uses that subtree, and overlapping selections are exported once", async () => {
  const h = harness();
  const child = { id: 2, parentID: 1, libraryID: 1, key: "JKLM2345", name: "Child" };
  const grandchild = { id: 3, parentID: 2, libraryID: 1, key: "NPQR5678", name: "Grandchild" };
  h.collections.push(child, grandchild);
  await h.plugin.exportSelected(multiSelection([child]), true);
  assert.deepEqual(h.exports.map((entry) => entry.key), [child.key]);
  h.exports.length = 0;
  await h.plugin.exportSelected(multiSelection([grandchild, child, h.collections[0], child]), true);
  assert.deepEqual(h.exports.map((entry) => entry.key), [h.collections[0].key]);
  assert.match(h.notices.at(-1)[1], /Included within a selected parent collection: Grandchild, Child/);
});

test("invalid and cross-library selections are rejected before any export", async () => {
  const h = harness();
  h.plugin.chooseOutputDirectory = () => assert.fail("Validation must precede the folder prompt");
  for (const invalid of [
    { ...h.collections[0], id: 0 },
    { ...h.collections[0], key: "nil" },
    { ...h.collections[0], deleted: true },
    { ...h.collections[0], id: 2, libraryID: 2 },
  ]) {
    await h.plugin.exportSelected(multiSelection([h.collections[0], invalid]), true);
    assert.equal(h.exports.length, 0);
    assert.equal(h.alerts.at(-1)[0], "zpm export failed");
    assert.equal(h.plugin.exportInProgress, false);
  }
  assert.match(h.alerts.at(-1)[1], /one Zotero library/);
});

test("a failed collection is reported and later collections still export", async () => {
  const h = harness();
  h.collections.push({ id: 2, libraryID: 1, key: "JKLM2345", name: "Broken" },
    { id: 3, libraryID: 1, key: "NPQR5678", name: "Last" });
  h.sandbox.ZPMNativeExporter.exportSnapshot = async (snapshot, _fs, key, options) => {
    if (key === "JKLM2345") throw new Error("Disk fixture failure");
    h.exports.push({ snapshot, key, options });
    return { collectionName: snapshot.collection.name, workspace: `/exports/${snapshot.collection.name}`,
      copied: 1, updated: 0, unchanged: 0, missing: 0, retainedSettings: [] };
  };
  await h.plugin.exportSelected(multiSelection(h.collections), true);
  assert.deepEqual(h.exports.map((entry) => entry.key), ["ABCDEFGH", "NPQR5678"]);
  assert.equal(h.alerts.length, 1);
  assert.equal(h.alerts[0][0], "Export finished with errors");
  assert.equal(h.notices.length, 0);
  assert.match(h.alerts[0][1], /Exported 2 of 3 collections/);
  assert.match(h.alerts[0][1], /Broken \[JKLM2345\]: Disk fixture failure/);
  assert.match(h.alerts[0][1], /may have written some files/);
  assert.match(h.alerts[0][1], /\/exports\/Last/);
  assert.equal(h.plugin.exportInProgress, false);
});

test("missing attachments retain a warning instead of a success notification", async () => {
  const h = harness();
  h.sandbox.ZPMNativeExporter.exportSnapshot = async () => ({
    collectionName: "Agentic_AI", workspace: "/exports/Agentic_AI",
    copied: 1, updated: 0, unchanged: 0, missing: 2, retainedSettings: [],
  });
  await h.plugin.exportSelected(h.selection, false);
  assert.equal(h.notices.length, 0);
  assert.equal(h.alerts[0][0], "Export finished with missing files");
  assert.match(h.alerts[0][1], /2 missing/);
  assert.equal(h.plugin.exportInProgress, false);
});

test("the batch keeps one guard, captures the selection, and reuses settings across async exports", async () => {
  const h = harness();
  h.collections.push({ id: 2, libraryID: 1, key: "JKLM2345", name: "Second" });
  const context = multiSelection(h.collections);
  let release;
  const pending = new Promise((resolve) => { release = resolve; });
  let started;
  const firstStarted = new Promise((resolve) => { started = resolve; });
  h.plugin.buildSnapshot = async (collection, annotations) => {
    if (collection.id === 1) { started(); await pending; }
    return { collection, annotations };
  };
  const batch = h.plugin.exportSelected(context, true);
  await firstStarted;
  context.collectionTreeRows = [];
  h.prefs.set("extensions.zpm.annotationLayout", "bundle");
  await h.plugin.exportSelected(h.selection, false);
  assert.equal(h.alerts[0][0], "Export in progress");
  assert.equal(h.plugin.exportInProgress, true);
  release();
  await batch;
  assert.equal(h.exports.length, 2);
  assert.ok(h.exports.every((entry) => entry.options.annotationLayout === "sidecar"));
  assert.equal(h.plugin.exportInProgress, false);
});

test("the standard exporter still rejects concurrent exports", async () => {
  const h = harness();
  h.plugin.exportInProgress = true;
  await h.plugin.exportSelected(h.selection, false);
  assert.equal(h.exports.length, 0);
  assert.equal(h.alerts[0][0], "Export in progress");
  assert.equal(h.plugin.exportInProgress, true);
});

test("folder cancellation releases the export guard without exporting", async () => {
  const h = harness();
  h.collections.push({ id: 2, libraryID: 1, key: "JKLM2345", name: "Second" });
  h.plugin.chooseOutputDirectory = async () => null;
  await h.plugin.exportSelected(multiSelection(h.collections), true);
  assert.equal(h.exports.length, 0);
  assert.equal(h.alerts.length, 0);
  assert.equal(h.plugin.exportInProgress, false);
});

test("export failures release the guard and show the error", async () => {
  const h = harness();
  h.plugin.buildSnapshot = async () => { throw new Error("Fixture read failure"); };
  await h.plugin.exportSelected(h.selection, true);
  assert.equal(h.exports.length, 0);
  assert.equal(h.alerts[0][0], "zpm export failed");
  assert.match(h.alerts[0][1], /Fixture read failure/);
  assert.equal(h.plugin.exportInProgress, false);
});
