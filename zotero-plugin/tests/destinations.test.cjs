const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { deliveryPlan, notebookURL } = require("../destinations.js");
const { ZPMPlugin } = require("../zpm.js");

const fileSystem = {
  join: path.join,
  realPath: fs.realpath,
  async isFile(value) { return (await fs.stat(value)).isFile(); },
  async isWithin(value, root) {
    const relative = path.relative(root, value);
    return !relative.startsWith("..") && !path.isAbsolute(relative);
  },
};

test("delivery selects only the explicit current files, preserving Unicode names", async (context) => {
  const workspace = await fs.mkdtemp(path.join(os.tmpdir(), "zpm-destination-"));
  context.after(() => fs.rm(workspace, { recursive: true }));
  await fs.writeFile(path.join(workspace, 'İnanç "paper".pdf'), "pdf");
  await fs.writeFile(path.join(workspace, "personal.md"), "private");
  const plan = await deliveryPlan({
    workspace, deliveryFiles: ['İnanç "paper".pdf', 'İnanç "paper".pdf'],
  }, fileSystem);
  assert.equal(plan.files.length, 1);
  assert.equal(plan.files[0].relative, 'İnanç "paper".pdf');
});

test("delivery rejects traversal, bookkeeping, missing files, and escaped symlinks", async (context) => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "zpm-destination-"));
  context.after(() => fs.rm(root, { recursive: true }));
  const workspace = path.join(root, "workspace");
  await fs.mkdir(workspace);
  await fs.writeFile(path.join(root, "secret"), "private");
  for (const relative of ["../secret", "/secret", ".zpm/manifest.json", "a\\b", "a/./b"]) {
    await assert.rejects(deliveryPlan({ workspace, deliveryFiles: [relative] }, fileSystem), /Unsafe/);
  }
  await assert.rejects(deliveryPlan({ workspace, deliveryFiles: ["absent"] }, fileSystem));
  await fs.symlink(path.join(root, "secret"), path.join(workspace, "escape"));
  await assert.rejects(deliveryPlan({ workspace, deliveryFiles: ["escape"] }, fileSystem), /outside/);
});

test("Notebook URLs must point to the supported Google hosts", () => {
  assert.equal(notebookURL("https://notebooklm.google.com/notebook/test"),
    "https://notebooklm.google.com/notebook/test");
  for (const url of ["file:///tmp/a", "http://notebook.google.com", "https://notebook.google.com.evil.test", "https://user@notebook.google.com"]) {
    assert.throws(() => notebookURL(url));
  }
});

test("the export guard prevents a second app handoff while one is running", async () => {
  const alerts = [];
  const plugin = { ...ZPMPlugin, exportInProgress: true, alert: (...args) => alerts.push(args) };
  await plugin.exportSelected({}, true, true, "gemini-notebook");
  assert.equal(alerts[0][0], "Export in progress");
});

test("an export error releases the guard", async () => {
  global.Zotero = { logError() {} };
  const plugin = { ...ZPMPlugin, exportInProgress: false, alert() {} };
  try {
    await plugin.exportSelected({}, true, true, "gemini-notebook");
    assert.equal(plugin.exportInProgress, false);
  } finally {
    delete global.Zotero;
  }
});
