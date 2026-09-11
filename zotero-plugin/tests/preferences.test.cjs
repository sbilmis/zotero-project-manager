const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../preferences.js"), "utf8");
const markup = fs.readFileSync(path.join(__dirname, "../preferences.xhtml"), "utf8");
const onload = markup.match(/onload="([^"]+)"/)[1];
const prefix = "extensions.zpm.";

function harness(prefs = new Map()) {
  const nodes = new Map([...markup.matchAll(/\bid="([^"]+)"/g)].map(([, id]) => [id, {
    value: "", checked: false, disabled: false, textContent: "", dataset: {},
    listeners: new Map(),
    addEventListener(type, listener) {
      const listeners = this.listeners.get(type) || [];
      listeners.push(listener);
      this.listeners.set(type, listeners);
    },
    async dispatch(type) {
      await Promise.all((this.listeners.get(type) || []).map((listener) => listener()));
    },
  }]));
  const document = { getElementById: (id) => nodes.get(id) || null };
  const state = { pickers: [], logs: [], writes: [], result: 0, file: "/exports/chosen", stats: [] };
  const Zotero = {
    Prefs: {
      get(key) { if (state.readError) throw state.readError; return prefs.get(key); },
      set(key, value) { state.writes.push([key, value]); prefs.set(key, value); },
    },
    getMainWindow() { throw new Error("The picker must belong to Settings, not the library window"); },
    logError: (error) => state.logs.push(error),
  };
  class FilePicker {
    modeGetFolder = 2;
    returnOK = 0;
    constructor() { state.pickers.push(this); }
    init(parent, title, mode) { Object.assign(this, {parent, title, mode}); }
    async show() {
      if (state.showError) throw state.showError;
      if (state.waitForPicker) await state.waitForPicker;
      this.file = state.file;
      return state.result;
    }
  }
  // Zotero loads scripts into a pane sandbox, but inline markup handlers run
  // in the Settings window. Do not expose pane globals on that window here.
  let paneScope;
  const settingsWindow = vm.createContext({
    document, Zotero,
    Zotero_Preferences: {
      getScope(id) { assert.equal(id, "zpm-preferences"); return paneScope; },
    },
  });
  document.defaultView = settingsWindow;
  paneScope = vm.createContext({
    document, window: settingsWindow, Zotero,
    ChromeUtils: {
      importESModule(uri) {
        assert.equal(uri, "chrome://zotero/content/modules/filePicker.mjs");
        if (state.importError) throw state.importError;
        return { FilePicker };
      },
    },
    IOUtils: {
      async stat(value) {
        state.stats.push(value);
        if (state.statError) throw state.statError;
        return { type: state.pathType || "directory" };
      },
    },
  });
  vm.runInContext(source, paneScope);
  return {
    prefs, state, settingsWindow,
    node: (name) => document.getElementById("zpm-preferences-" + name),
    load: () => vm.runInContext(onload, settingsWindow),
  };
}

test("Settings onload resolves the isolated pane scope and initializes only once", () => {
  const h = harness(new Map([
    [prefix + "outputDir", "/exports/saved"], [prefix + "includeNonPdf", true],
    [prefix + "annotationLayout", "sidecar"], [prefix + "filenameTemplate", "title_year"],
  ]));
  assert.equal(h.settingsWindow.ZPMPreferences, undefined);
  h.load();
  h.load();
  assert.equal(h.node("output").value, "/exports/saved");
  assert.equal(h.node("include-non-pdf").checked, true);
  assert.equal(h.node("layout-select").value, "sidecar");
  assert.equal(h.node("filename-select").value, "title_year");
  assert.match(h.node("layout-description").textContent, /beside/);
  assert.equal(h.node("output-button").listeners.get("click").length, 1);
  assert.equal(h.state.writes.length, 0);
});

test("missing preferences initialize defaults; invalid layouts fall back safely", () => {
  const h = harness(new Map([[prefix + "annotationLayout", "invalid"]]));
  h.load();
  assert.equal(h.node("output").value, "");
  assert.equal(h.node("include-non-pdf").checked, false);
  assert.equal(h.node("layout-select").value, "separate");
  assert.equal(h.node("filename-select").value, "author_year_title");
});

test("an initialization failure can be retried without a stuck initialized flag", () => {
  const h = harness();
  h.state.readError = new Error("Temporary preference read failure");
  assert.throws(h.load, /Temporary preference read failure/);
  h.state.readError = null;
  h.load();
  assert.equal(h.node("output-button").listeners.get("click").length, 1);
});

test("Choose opens a Settings-owned folder picker and saves the accepted path", async () => {
  const h = harness(new Map([[prefix + "outputDir", "/exports/saved"]]));
  h.load();
  await h.node("output-button").dispatch("click");
  const picker = h.state.pickers[0];
  assert.equal(picker.parent, h.settingsWindow);
  assert.equal(picker.mode, picker.modeGetFolder);
  assert.equal(picker.displayDirectory, "/exports/saved");
  assert.equal(h.node("output").value, h.state.file);
  assert.equal(h.prefs.get(prefix + "outputDir"), h.state.file);
  assert.equal(h.node("status").dataset.kind, "success");
  assert.equal(h.node("output-button").disabled, false);
  const reopened = harness(h.prefs);
  reopened.load();
  assert.equal(reopened.node("output").value, h.state.file);
});

test("cancelling the folder picker preserves the path and preferences", async () => {
  const h = harness(new Map([[prefix + "outputDir", "/exports/saved"]]));
  h.state.result = 1;
  h.load();
  await h.node("output-button").dispatch("click");
  assert.equal(h.node("output").value, "/exports/saved");
  assert.equal(h.prefs.get(prefix + "outputDir"), "/exports/saved");
  assert.equal(h.state.writes.length, 0);
  assert.equal(h.node("output-button").disabled, false);
});

test("manually entered folder paths are trimmed, saved, and restored", async () => {
  const h = harness();
  h.load();
  h.node("output").value = "  /exports/typed  ";
  await h.node("output").dispatch("change");
  assert.equal(h.prefs.get(prefix + "outputDir"), "/exports/typed");
  const reopened = harness(h.prefs);
  reopened.load();
  assert.equal(reopened.node("output").value, "/exports/typed");
});

test("other settings also save after pane initialization", async () => {
  const h = harness();
  h.load();
  h.node("include-non-pdf").checked = true;
  await h.node("include-non-pdf").dispatch("change");
  h.node("filename-select").value = "year_title";
  await h.node("filename-select").dispatch("change");
  h.node("layout-select").value = "bundle";
  await h.node("layout-select").dispatch("change");
  assert.equal(h.prefs.get(prefix + "includeNonPdf"), true);
  assert.equal(h.prefs.get(prefix + "filenameTemplate"), "year_title");
  assert.equal(h.prefs.get(prefix + "annotationLayout"), "bundle");
  assert.match(h.node("layout-description").textContent, /one folder|a folder/);
});

test("blank, missing, or non-directory saved paths do not prevent choosing a folder", async () => {
  for (const value of ["", "missing", "file"]) {
    const h = harness(new Map([[prefix + "outputDir", value]]));
    if (value === "missing") h.state.statError = new Error("Not found");
    if (value === "file") h.state.pathType = "regular";
    h.load();
    await h.node("output-button").dispatch("click");
    assert.equal(h.state.pickers[0].displayDirectory, undefined);
    assert.equal(h.prefs.get(prefix + "outputDir"), h.state.file);
    assert.equal(h.state.logs.length, 0);
  }
});

test("picker/import failures are visible, preserve preferences, and allow retry", async () => {
  for (const phase of ["showError", "importError"]) {
    const h = harness(new Map([[prefix + "outputDir", "/exports/saved"]]));
    h.load();
    h.state[phase] = new Error("Picker unavailable");
    await h.node("output-button").dispatch("click");
    assert.equal(h.node("status").dataset.kind, "error");
    assert.match(h.node("status").textContent, /Picker unavailable/);
    assert.equal(h.state.logs.length, 1);
    assert.equal(h.prefs.get(prefix + "outputDir"), "/exports/saved");
    assert.equal(h.node("output-button").disabled, false);
    h.state[phase] = null;
    await h.node("output-button").dispatch("click");
    assert.equal(h.prefs.get(prefix + "outputDir"), h.state.file);
    assert.equal(h.node("status").dataset.kind, "success");
  }
});

test("repeated clicks while the picker is open do not create extra dialogs", async () => {
  const h = harness();
  h.load();
  let finish;
  h.state.waitForPicker = new Promise((resolve) => { finish = resolve; });
  const firstClick = h.node("output-button").dispatch("click");
  assert.equal(h.node("output-button").disabled, true);
  await h.node("output-button").dispatch("click");
  assert.equal(h.state.pickers.length, 1);
  finish();
  await firstClick;
  assert.equal(h.node("output-button").disabled, false);
  assert.equal(h.state.writes.length, 1);
});
