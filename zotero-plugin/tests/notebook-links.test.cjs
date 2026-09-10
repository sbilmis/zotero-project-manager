const assert = require("node:assert/strict");
const test = require("node:test");
const destinations = require("../destinations.js");
const { ZPMPlugin } = require("../zpm.js");

const collection = { libraryID: 1, key: "ABCDEFGH", name: "Agentic_AI" };
const url = "https://notebook.google.com/notebook/11111111-2222-3333-4444-555555555555?authuser=1";
const otherURL = "https://notebooklm.google.com/notebook/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
const contextFor = (value) => ({ collectionTreeRow: { isCollection: () => true, ref: value } });

function harness(context, initial = []) {
  const prefs = new Map(initial);
  const answers = [];
  const prompts = [];
  const alerts = [];
  const opened = [];
  const revealed = [];
  const desktopCalls = [];
  const previous = Object.fromEntries(
    ["Zotero", "Services", "ZPMDestinations"].map((key) => [key, Object.getOwnPropertyDescriptor(global, key)]),
  );
  context.after(() => {
    for (const [key, descriptor] of Object.entries(previous)) {
      if (descriptor) Object.defineProperty(global, key, descriptor);
      else delete global[key];
    }
  });
  global.Zotero = {
    Prefs: {
      get: (key) => prefs.get(key),
      set: (key, value) => prefs.set(key, value),
      clear: (key) => prefs.delete(key),
    },
    getMainWindow: () => null,
    logError() {},
    launchURL: (value) => opened.push(value),
    File: { reveal: (value) => revealed.push(value) },
    isMac: false,
  };
  global.Services = {
    prompt: {
      prompt(_parent, title, message, input) {
        prompts.push({ title, message, initial: input.value });
        assert.ok(answers.length, "Unexpected notebook prompt");
        const answer = answers.shift();
        if (answer === null) return false;
        input.value = answer;
        return true;
      },
    },
  };
  global.ZPMDestinations = {
    ...destinations,
    deliveryPlan: async () => ({
      workspace: "/exports/Agentic_AI - NotebookLM",
      files: [{ path: "/exports/Agentic_AI - NotebookLM/paper.pdf" }],
    }),
  };
  const plugin = {
    ...ZPMPlugin, exportInProgress: false,
    alert: (...args) => alerts.push(args),
    runDesktopScript: async (...args) => {
      desktopCalls.push(args);
      return "Linked 1 files to DEVONthink 4";
    },
  };
  return { plugin, prefs, answers, prompts, alerts, opened, revealed, desktopCalls };
}

test("saved URLs require an actual Google notebook and retain only account routing", () => {
  assert.equal(destinations.rememberedNotebookURL("  " + url + "&utm_source=zpm#source=abc  "), url);
  assert.equal(destinations.rememberedNotebookURL(otherURL), otherURL);
  assert.equal(
    destinations.rememberedNotebookURL("https://notebook.google.com/u/2/notebook/abcdefgh"),
    "https://notebook.google.com/u/2/notebook/abcdefgh",
  );
  for (const input of [
    "", "https://notebook.google.com/", "https://notebook.google.com/notebook/",
    "https://notebook.google.com/notebook/new", "https://notebook.google.com/notebook/create",
    "https://notebook.google.com/notebook/one/sources", "https://gemini.google.com/app/abc",
    "https://notebook.google.com.evil.test/notebook/abcdefgh",
    "https://user:password@notebook.google.com/notebook/abcdefgh",
    "http://notebook.google.com/notebook/abcdefgh", "javascript:alert(1)",
    "file:///tmp/private", "https://notebook.google.com:8443/notebook/abcdefgh",
    "https://notebook.google.com/notebook/abcdefgh?" + "x".repeat(2100),
  ]) assert.throws(() => destinations.rememberedNotebookURL(input), undefined, input);
});

test("preference identity survives renaming and separates libraries and collection keys", () => {
  const key = destinations.notebookLinkPreference(collection);
  assert.equal(key, destinations.notebookLinkPreference({ ...collection, name: "Renamed" }));
  assert.notEqual(key, destinations.notebookLinkPreference({ ...collection, libraryID: 2 }));
  assert.notEqual(key, destinations.notebookLinkPreference({ ...collection, key: "IJKLMNOP" }));
  for (const value of [
    null, {}, { ...collection, libraryID: 0 }, { ...collection, libraryID: 1.5 },
    { ...collection, key: "../evil" }, { ...collection, key: "" },
  ]) assert.throws(() => destinations.notebookLinkPreference(value));
});

test("first send saves the pasted link; a new plugin instance reuses it without prompting", async (context) => {
  const h = harness(context);
  h.answers.push(url);
  await h.plugin.sendExport({ workspace: "/exports/Agentic_AI - NotebookLM" }, "gemini-notebook", collection);
  assert.deepEqual(h.opened, [url]);
  assert.equal(h.prefs.get(destinations.notebookLinkPreference(collection)), url);
  assert.equal(h.prompts.length, 1);
  const restartedPlugin = { ...h.plugin };
  await restartedPlugin.sendExport({ workspace: "/exports/Agentic_AI - NotebookLM" }, "gemini-notebook", {
    ...collection, name: "Renamed collection",
  });
  assert.deepEqual(h.opened, [url, url]);
  assert.equal(h.prompts.length, 1);
  assert.ok(h.alerts.every((entry) => entry[1].includes("Nothing has been uploaded")));
});

test("same-named collections get independent remembered links", async (context) => {
  const h = harness(context);
  const secondCollection = { ...collection, key: "IJKLMNOP" };
  h.answers.push(url, otherURL);
  h.plugin.setNotebookLink(contextFor(collection));
  h.plugin.setNotebookLink(contextFor(secondCollection));
  assert.equal(h.plugin.notebookURLForCollection(collection), url);
  assert.equal(h.plugin.notebookURLForCollection(secondCollection), otherURL);
  assert.equal(h.prefs.size, 2);
  assert.deepEqual(h.opened, []); // Saving a link does not open apps.
});

test("editing replaces a link; cancel preserves it; clearing affects only that collection", (context) => {
  const key = destinations.notebookLinkPreference(collection);
  const unrelated = destinations.notebookLinkPreference({ ...collection, libraryID: 2 });
  const h = harness(context, [[key, url], [unrelated, url]]);
  h.answers.push(otherURL, null, "");
  h.plugin.setNotebookLink(contextFor(collection));
  assert.equal(h.prefs.get(key), otherURL);
  h.plugin.setNotebookLink(contextFor(collection));
  assert.equal(h.prefs.get(key), otherURL);
  h.plugin.setNotebookLink(contextFor(collection));
  assert.equal(h.prefs.has(key), false);
  assert.equal(h.prefs.get(unrelated), url);
  assert.match(h.alerts.at(-1)[1], /No notebook or sources were deleted/);
});

test("invalid edits never overwrite a saved link", (context) => {
  const key = destinations.notebookLinkPreference(collection);
  const h = harness(context, [[key, url]]);
  h.answers.push("https://example.com/notebook/private", null);
  h.plugin.setNotebookLink(contextFor(collection));
  assert.equal(h.prefs.get(key), url);
  assert.equal(h.alerts[0][0], "Invalid notebook link");
});

test("an invalid stored link is not opened and can be repaired", (context) => {
  const key = destinations.notebookLinkPreference(collection);
  const h = harness(context, [[key, "https://example.com/notebook/private"]]);
  h.answers.push(otherURL);
  assert.equal(h.plugin.notebookURLForCollection(collection), otherURL);
  assert.equal(h.prefs.get(key), otherURL);
  assert.equal(h.alerts[0][0], "Invalid saved notebook link");
});

test("blank first-use input opens the home page without remembering it", async (context) => {
  const h = harness(context);
  h.answers.push("");
  await h.plugin.sendExport({ workspace: "/exports/test" }, "gemini-notebook", collection);
  assert.deepEqual(h.opened, [destinations.NOTEBOOK_URL]);
  assert.equal(h.prefs.size, 0);
});

test("cancelling first use opens neither browser nor Finder", async (context) => {
  const h = harness(context);
  h.answers.push(null);
  await h.plugin.sendExport({ workspace: "/exports/test" }, "gemini-notebook", collection);
  assert.deepEqual(h.opened, []);
  assert.deepEqual(h.revealed, []);
  assert.equal(h.prefs.size, 0);
});

test("DEVONthink handoff remains independent of notebook prompts", async (context) => {
  const h = harness(context);
  await h.plugin.sendExport({ workspace: "/exports/test" }, "devonthink", collection);
  assert.equal(h.desktopCalls[0][0], "devonthink.applescript");
  assert.deepEqual(h.prompts, []);
  assert.deepEqual(h.opened, []);
});

test("link editing is blocked during a running export", (context) => {
  const h = harness(context);
  h.plugin.exportInProgress = true;
  h.plugin.setNotebookLink(contextFor(collection));
  assert.equal(h.alerts[0][0], "Export in progress");
  assert.deepEqual(h.prompts, []);
});

test("exportSelected passes the selected collection identity into the handoff", async (context) => {
  const h = harness(context);
  const previous = Object.getOwnPropertyDescriptor(global, "ZPMNativeExporter");
  context.after(() => {
    if (previous) Object.defineProperty(global, "ZPMNativeExporter", previous);
    else delete global.ZPMNativeExporter;
  });
  const stats = { workspace: "/exports/test" };
  global.ZPMNativeExporter = { exportSnapshot: async () => stats };
  let actual;
  h.plugin.chooseOutputDirectory = async () => "/exports";
  h.plugin.buildSnapshot = async () => ({});
  h.plugin.sendExport = async (...args) => { actual = args; };
  await h.plugin.exportSelected(contextFor(collection), true, true, "gemini-notebook");
  assert.deepEqual(actual, [stats, "gemini-notebook", collection]);
  assert.equal(h.plugin.exportInProgress, false);
});
