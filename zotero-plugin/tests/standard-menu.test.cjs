const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function harness() {
  const alerts = [], exports = [], settings = [];
  const prefs = new Map([
    ["extensions.zpm.annotationLayout", "sidecar"],
    ["extensions.zpm.filenameTemplate", "year_title"],
    ["extensions.zpm.includeNonPdf", true],
  ]);
  const sandbox = vm.createContext({
    module: { exports: {} },
    Zotero: {
      Prefs: { get: (key) => prefs.get(key) },
      PreferencePanes: { register: async (options) => settings.push(options) },
      MenuManager: { registerMenu: (options) => { sandbox.menu = options; return "menu-id"; } },
      getMainWindows: () => [],
      debug() {}, logError() {},
      launchURL() { assert.fail("A standard export must not launch external apps"); },
    },
    ZPMNativeExporter: {
      async exportSnapshot(snapshot, _fileSystem, key, options) {
        exports.push({ snapshot, key, options });
        return {
          collectionName: "Agentic_AI", workspace: "/exports/Agentic_AI",
          copied: 1, updated: 0, unchanged: 0, missing: 0, retainedSettings: [],
        };
      },
    },
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../zpm.js"), "utf8"), sandbox);
  const plugin = sandbox.module.exports.ZPMPlugin;
  plugin.alert = (...args) => alerts.push(args);
  plugin.chooseOutputDirectory = async () => "/exports";
  plugin.buildSnapshot = async (collection, annotations) => ({ collection, annotations });
  const collection = { key: "ABCDEFGH", name: "Agentic_AI" };
  const selection = { collectionTreeRow: { isCollection: () => true, ref: collection } };
  return { sandbox, plugin, selection, alerts, exports, settings };
}

test("collection menu offers only standard export actions and Settings", async () => {
  const h = harness();
  await h.plugin.startup({ id: "zpm@zotero-project-manager", rootURI: "plugin/" });
  assert.equal(h.settings[0].id, "zpm-preferences");
  const menu = h.sandbox.menu.menus[0].menus;
  assert.deepEqual(Array.from(menu, (entry) => entry.l10nID || entry.menuType), [
    "zpm-menu-export-pdfs", "zpm-menu-export-annotations", "separator", "zpm-menu-settings",
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
  assert.equal(h.alerts[0][0], "Export complete");
  assert.match(h.alerts[0][1], /\/exports\/Agentic_AI/);
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
  h.plugin.chooseOutputDirectory = async () => null;
  await h.plugin.exportSelected(h.selection, true);
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
