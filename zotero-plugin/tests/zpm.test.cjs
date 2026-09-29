const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const {
  zpmCreatorName,
  zpmTrimOutput,
} = require("../zpm.js");

test("creator names prefer the family name and degrade safely", () => {
  assert.equal(zpmCreatorName({ firstName: "Ada", lastName: "Lovelace" }), "Lovelace");
  assert.equal(zpmCreatorName({ name: "CERN" }), "CERN");
  assert.equal(zpmCreatorName({ firstName: "Plato" }), "Plato");
});

test("process output is bounded before display", () => {
  assert.equal(zpmTrimOutput("  ready  "), "ready");
  assert.match(zpmTrimOutput("x".repeat(13000)), /output truncated/);
});

test("success dialog is parented, keeps multiline details, and displays collection names as text", () => {
  let opened;
  const mainWindow = { openDialog: (...args) => { opened = args; } };
  const sandbox = vm.createContext({ module: { exports: {} }, Zotero: { getMainWindow: () => mainWindow } });
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../zpm.js"), "utf8"), sandbox);
  const plugin = sandbox.module.exports.ZPMPlugin;
  plugin.rootURI = "jar:file:///zpm.xpi!/";
  const message = '<a href="https://example.org">Research & notes</a>\n1 copied\n/exports/Research';
  plugin.notify("Export complete", message);
  assert.equal(opened[0], "jar:file:///zpm.xpi!/export-result.xhtml");
  assert.match(opened[2], /modal/);
  assert.equal(opened[3].message, message);

  // Run the packaged dialog's load handler. Values must remain plain text.
  const elements = { "result-title": {}, "result-message": {} };
  let resized = false;
  const dialog = vm.createContext({
    window: { arguments: [opened[3]], addEventListener: (_type, callback) => callback(),
      sizeToContent: () => { resized = true; } },
    document: { getElementById: id => elements[id] },
  });
  const xhtml = fs.readFileSync(path.join(__dirname, "../export-result.xhtml"), "utf8");
  vm.runInContext(xhtml.match(/<!\[CDATA\[([\s\S]*?)\]\]>/)[1], dialog);
  assert.equal(elements["result-title"].textContent, "Export complete");
  assert.equal(elements["result-message"].textContent, message);
  assert.equal(resized, true);
});
