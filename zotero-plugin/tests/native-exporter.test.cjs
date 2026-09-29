const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const {
  ExportError,
  exportSnapshot,
  noteHtmlToMarkdown,
} = require("../native-exporter.js");

class NodeFileSystem {
  join(...parts) {
    return path.join(...parts);
  }

  async exists(target) {
    try {
      await fs.access(target);
      return true;
    } catch (_error) {
      return false;
    }
  }

  async stat(target) {
    const value = await fs.stat(target);
    return { size: value.size, mtimeMs: value.mtimeMs, type: value.isFile() ? "regular" : "directory" };
  }

  async isFile(target) {
    try {
      return (await fs.stat(target)).isFile();
    } catch (_error) {
      return false;
    }
  }

  async makeDir(target) {
    await fs.mkdir(target, { recursive: true });
  }

  async readText(target) {
    return fs.readFile(target, "utf8");
  }

  async writeTextAtomic(target, content) {
    await fs.mkdir(path.dirname(target), { recursive: true });
    const temporary = `${target}.${process.pid}.tmp`;
    await fs.writeFile(temporary, content, "utf8");
    await fs.rename(temporary, target);
  }

  async copyAtomic(source, destination) {
    await fs.mkdir(path.dirname(destination), { recursive: true });
    const temporary = `${destination}.${process.pid}.tmp`;
    await fs.copyFile(source, temporary);
    await fs.rename(temporary, destination);
  }

  async hash(target) {
    return crypto.createHash("sha256").update(await fs.readFile(target)).digest("hex");
  }

  async listFiles(root) {
    const files = [];
    const walk = async (directory, relative) => {
      for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
        const childRelative = relative ? `${relative}/${entry.name}` : entry.name;
        if (entry.isDirectory()) await walk(path.join(directory, entry.name), childRelative);
        else if (entry.isFile()) files.push(childRelative);
      }
    };
    if (await this.exists(root)) await walk(root, "");
    return files;
  }

  async listDirectories(root) {
    const directories = [];
    const walk = async (directory, relative) => {
      for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
        if (!entry.isDirectory()) continue;
        const childRelative = relative ? `${relative}/${entry.name}` : entry.name;
        directories.push(childRelative);
        await walk(path.join(directory, entry.name), childRelative);
      }
    };
    if (await this.exists(root)) await walk(root, "");
    return directories;
  }

  async removeFile(target) {
    await fs.rm(target, { force: true });
  }

  async realPath(target) {
    return fs.realpath(target);
  }

  async isWithin(target, parent) {
    const relative = path.relative(parent, target);
    return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
  }
}

function snapshot(pdf, markdown) {
  return {
    schema_version: 1,
    zotero_version: "9.0.6",
    data_dir: path.dirname(pdf),
    collections: [
      { id: 1, key: "ROOTKEY1", name: "My Project", parent_id: null, library_id: 1 },
      { id: 2, key: "CHILD001", name: "References", parent_id: 1, library_id: 1 },
    ],
    attachments: {
      "1": [
        {
          attachment_id: 10,
          attachment_key: "PDF00001",
          item_id: 100,
          item_key: "ITEM0001",
          title: "Attention Is All You Need",
          date: "2017",
          creators: ["Vaswani"],
          content_type: "application/pdf",
          source_path: pdf,
          original_path: "storage:paper.pdf",
          doi: "10.5555/attention",
          tags: ["AI"],
        },
        {
          attachment_id: 11,
          attachment_key: "README01",
          item_id: 101,
          item_key: "ITEM0002",
          title: "README",
          date: null,
          creators: [],
          content_type: "text/markdown",
          source_path: markdown,
          original_path: "storage:README.md",
          doi: null,
          tags: [],
        },
      ],
      "2": [],
    },
    annotations: {
      "10": [{
        annotation_id: 20,
        annotation_key: "ANNOT001",
        attachment_id: 10,
        annotation_type: "highlight",
        text: "Important result",
        comment: "Use this later.",
        color: "#ffd400",
        page_label: "4",
        sort_index: "0001",
        position: "{}",
        author_name: "Researcher",
        date_added: "2026-01-01",
        date_modified: "2026-01-02",
        tags: ["Key"],
        image_path: null,
      }],
    },
    notes: {
      "100": [{
        note_id: 30,
        note_key: "NOTE0001",
        parent_item_id: 100,
        title: "Reading note",
        content: "<p>Compare <strong>models</strong>.</p>",
        date_added: "2026-01-01",
        date_modified: "2026-01-02",
        tags: [],
      }],
    },
  };
}

async function fixture() {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "zpm-native-"));
  const source = path.join(root, "source");
  const output = path.join(root, "output");
  await fs.mkdir(source);
  const pdf = path.join(source, "paper.pdf");
  const markdown = path.join(source, "README.md");
  await fs.writeFile(pdf, "pdf-content");
  await fs.writeFile(markdown, "# Personal project\n");
  return { root, output, pdf, markdown };
}

test("selected subcollections export to independent incremental workspaces with safe name collisions", async (context) => {
  const value = await fixture();
  context.after(() => fs.rm(value.root, { recursive: true, force: true }));
  const fileSystem = new NodeFileSystem();
  const collections = [
    { id: 1, key: "ABCDEFGH", name: "References", parentID: 90, libraryID: 1 },
    { id: 2, key: "EFGH2345", name: "Nested", parentID: 1, libraryID: 1 },
    { id: 3, key: "JKLM5678", name: "References", parentID: 91, libraryID: 1 },
    { id: 4, key: "NPQR6789", name: "Unselected", parentID: 90, libraryID: 1 },
  ];
  const results = [], alerts = [];
  const sandbox = vm.createContext({ module: { exports: {} }, Zotero: {
    Prefs: { get: (key) => key === "extensions.zpm.includeNonPdf" ? true : undefined },
    Collections: { getByParent(id) {
      return collections.filter((collection) => collection.parentID === id)
        .flatMap((child) => [child, ...this.getByParent(child.id)]);
    } },
    logError(error) { throw error; },
  }, ZPMNativeExporter: { async exportSnapshot(data, _adapter, key, options) {
    const result = await exportSnapshot(data, fileSystem, key, options);
    results.push(result);
    return result;
  } } });
  vm.runInContext(await fs.readFile(path.join(__dirname, "../links.js"), "utf8"), sandbox);
  vm.runInContext(await fs.readFile(path.join(__dirname, "../zpm.js"), "utf8"), sandbox);
  const plugin = sandbox.module.exports.ZPMPlugin;
  plugin.alert = (...args) => alerts.push(args);
  plugin.notify = (...args) => alerts.push(args);
  let prompts = 0;
  plugin.chooseOutputDirectory = async () => { prompts++; return value.output; };
  plugin.buildSnapshot = async (root) => {
    const data = snapshot(value.pdf, value.markdown);
    data.collections = [root, ...sandbox.Zotero.Collections.getByParent(root.id)].map((c) => ({
      id: c.id, key: c.key, name: c.name, parent_id: c.parentID, library_id: c.libraryID,
    }));
    const [pdf, markdown] = data.attachments["1"];
    data.attachments = { "1": [pdf], "2": [markdown], "3": [pdf], "4": [pdf] };
    return data;
  };
  const selection = { collectionTreeRows: [collections[1], collections[0], collections[2]]
    .map((ref) => ({ isCollection: () => true, ref })) };
  await plugin.exportSelected(selection, true);
  assert.equal(prompts, 1);
  assert.equal(results.length, 2);
  assert.deepEqual((await fs.readdir(value.output)).sort(), ["References", "References [JKLM5678]"]);
  const first = results[0].workspace;
  const second = results[1].workspace;
  assert.equal(await fs.readFile(path.join(first, "Nested", "README.md"), "utf8"), "# Personal project\n");
  assert.match(await fs.readFile(path.join(first, "Annotations", "Vaswani - 2017 - Attention Is All You Need.md"), "utf8"), /Important result/);
  for (const [workspace, key] of [[first, "ABCDEFGH"], [second, "JKLM5678"]]) {
    const manifest = JSON.parse(await fs.readFile(path.join(workspace, ".zpm", "manifest.json")));
    assert.equal(manifest.collection_key, key);
  }
  assert.match(alerts[0][1], /Included within a selected parent collection: Nested/);

  results.length = 0;
  await plugin.exportSelected(selection, true);
  assert.ok(results.every((result) => result.copied === 0 && result.updated === 0));
  assert.deepEqual(results.map((result) => result.unchanged), [2, 1]);
  await fs.writeFile(value.pdf, "changed PDF from Zotero");
  results.length = 0;
  await plugin.exportSelected(selection, true);
  assert.deepEqual(results.map((result) => result.updated), [1, 1]);

  // Selecting only a child starts its workspace at that child, without siblings or parents.
  const childOutput = path.join(value.root, "child-output");
  plugin.chooseOutputDirectory = async () => childOutput;
  await plugin.exportSelected({ collectionTreeRows: [selection.collectionTreeRows[0]] }, false);
  assert.deepEqual(await fs.readdir(childOutput), ["Nested"]);
  assert.equal(await fs.readFile(path.join(childOutput, "Nested", "README.md"), "utf8"), "# Personal project\n");
});

test("native export copies PDFs and Markdown while isolating control files", async (context) => {
  const value = await fixture();
  context.after(() => fs.rm(value.root, { recursive: true, force: true }));
  const fileSystem = new NodeFileSystem();
  const first = await exportSnapshot(snapshot(value.pdf, value.markdown), fileSystem, "ROOTKEY1", {
    outputDir: value.output,
    includeNonPdf: true,
    exportAnnotations: true,
    annotationLayout: "separate",
  });
  const workspace = path.join(value.output, "My Project");
  assert.equal(await fs.readFile(path.join(workspace, "README.md"), "utf8"), "# Personal project\n");
  assert.equal(await fs.readFile(path.join(workspace, "Vaswani - 2017 - Attention Is All You Need.pdf"), "utf8"), "pdf-content");
  assert.equal(JSON.parse(await fs.readFile(path.join(workspace, ".zpm", "manifest.json"))).items.length, 2);
  assert.match(await fs.readFile(path.join(workspace, ".zpm", "INDEX.md"), "utf8"), /\[MD\]/);
  const annotationMarkdown = await fs.readFile(
    path.join(workspace, "Annotations", "Vaswani - 2017 - Attention Is All You Need.md"), "utf8",
  );
  assert.match(annotationMarkdown, /Important result[\s\S]*Compare models/);
  assert.ok(annotationMarkdown.includes(
    "[Open annotation in Zotero](zotero://open-pdf/library/items/PDF00001?annotation=ANNOT001)",
  ));
  assert.equal(first.copied, 2);
  assert.equal(first.annotations, 1);

  const second = await exportSnapshot(snapshot(value.pdf, value.markdown), fileSystem, "ROOTKEY1", {
    outputDir: value.output,
    includeNonPdf: true,
    exportAnnotations: true,
    annotationLayout: "separate",
  });
  assert.equal(second.unchanged, 2);
  assert.equal(second.copied, 0);
});

test("repeat export copies only differing files and restores exported edits from Zotero", async (context) => {
  const value = await fixture();
  context.after(() => fs.rm(value.root, { recursive: true, force: true }));
  const fileSystem = new NodeFileSystem();
  const options = { outputDir: value.output, includeNonPdf: true };
  const run = () => exportSnapshot(snapshot(value.pdf, value.markdown), fileSystem, "ROOTKEY1", options);
  const first = await run();
  const destination = path.join(first.workspace, "Vaswani - 2017 - Attention Is All You Need.pdf");
  const copies = [];
  const copy = fileSystem.copyAtomic.bind(fileSystem);
  fileSystem.copyAtomic = async (source, target) => { copies.push(target); await copy(source, target); };
  const unchanged = await run();
  assert.equal(unchanged.unchanged, 2);
  assert.deepEqual(copies, []);
  await fs.writeFile(value.pdf, "updated Zotero PDF");
  const changed = await run();
  assert.equal(changed.updated, 1);
  assert.equal(changed.unchanged, 1);
  assert.deepEqual(copies, [destination]);
  assert.equal(await fs.readFile(destination, "utf8"), "updated Zotero PDF");
  await fs.writeFile(destination, "external reader highlights and notes");
  const restored = await run();
  assert.equal(restored.updated, 1);
  assert.equal(restored.unchanged, 1);
  assert.equal(await fs.readFile(value.pdf, "utf8"), "updated Zotero PDF");
  assert.equal(await fs.readFile(destination, "utf8"), "updated Zotero PDF");
});

test("standard export creates one workspace and preserves a legacy Notebook sibling", async (context) => {
  const value = await fixture();
  context.after(() => fs.rm(value.root, { recursive: true, force: true }));
  const legacy = path.join(value.output, "My Project - NotebookLM");
  await fs.mkdir(legacy, { recursive: true });
  const oldFile = path.join(legacy, "collection-overview.md");
  await fs.writeFile(oldFile, "Existing exported sources\n");
  const fileSystem = new NodeFileSystem();
  for (let attempt = 0; attempt < 2; attempt++) {
    const result = await exportSnapshot(snapshot(value.pdf, value.markdown), fileSystem, "ROOTKEY1", {
      outputDir: value.output, exportAnnotations: true,
    });
    assert.equal(result.workspace, path.join(value.output, "My Project"));
    assert.equal("notebooklmSources" in result, false);
  }
  assert.deepEqual((await fs.readdir(value.output)).sort(), ["My Project", "My Project - NotebookLM"]);
  assert.deepEqual(await fs.readdir(legacy), ["collection-overview.md"]);
  assert.equal(await fs.readFile(oldFile, "utf8"), "Existing exported sources\n");
  await assert.rejects(fs.access(path.join(value.output, "My Project", "collection-overview.md")));
});

test("legacy root control files migrate without deleting personal README files", async (context) => {
  const value = await fixture();
  context.after(() => fs.rm(value.root, { recursive: true, force: true }));
  const workspace = path.join(value.output, "My Project");
  await fs.mkdir(workspace, { recursive: true });
  await fs.writeFile(path.join(workspace, "manifest.json"), JSON.stringify({
    version: 4,
    exported_at: "2026-01-01T00:00:00+00:00",
    collection_key: "ROOTKEY1",
    collection_name: "My Project",
    filename_template: "author_year_title",
    annotation_layout: "separate",
    items: [],
  }));
  await fs.writeFile(path.join(workspace, "README.md"), "# Personal README\n");

  await exportSnapshot(snapshot(value.pdf, value.markdown), new NodeFileSystem(), "ROOTKEY1", {
    outputDir: value.output,
    includeNonPdf: false,
    annotationLayout: "separate",
  });
  assert.equal(await fs.readFile(path.join(workspace, "README.md"), "utf8"), "# Personal README\n");
  await assert.rejects(fs.access(path.join(workspace, "manifest.json")));
  assert.ok(await fs.readFile(path.join(workspace, ".zpm", "manifest.json"), "utf8"));
});

test("a legacy generated summary does not rename an attached README", async (context) => {
  const value = await fixture();
  context.after(() => fs.rm(value.root, { recursive: true, force: true }));
  const workspace = path.join(value.output, "My Project");
  await fs.mkdir(workspace, { recursive: true });
  await fs.writeFile(path.join(workspace, "manifest.json"), JSON.stringify({
    version: 4,
    exported_at: "2026-01-01T00:00:00+00:00",
    collection_key: "ROOTKEY1",
    collection_name: "My Project",
    filename_template: "author_year_title",
    annotation_layout: "separate",
    items: [],
  }));
  await fs.writeFile(
    path.join(workspace, "README.md"),
    "# Project exported from Zotero\n\nLegacy summary\n",
  );

  await exportSnapshot(snapshot(value.pdf, value.markdown), new NodeFileSystem(), "ROOTKEY1", {
    outputDir: value.output,
    includeNonPdf: true,
    annotationLayout: "separate",
  });
  assert.equal(await fs.readFile(path.join(workspace, "README.md"), "utf8"), "# Personal project\n");
  await assert.rejects(fs.access(path.join(workspace, "README [README01].md")));
});

test("native exporter refuses unmanaged workspaces", async (context) => {
  const value = await fixture();
  context.after(() => fs.rm(value.root, { recursive: true, force: true }));
  await fs.mkdir(path.join(value.output, "My Project"), { recursive: true });
  await assert.rejects(
    exportSnapshot(snapshot(value.pdf, value.markdown), new NodeFileSystem(), "ROOTKEY1", {
      outputDir: value.output,
      annotationLayout: "separate",
    }),
    ExportError,
  );
});

test("bundle layout preserves an existing empty user directory", async (context) => {
  const value = await fixture();
  context.after(() => fs.rm(value.root, { recursive: true, force: true }));
  const workspace = path.join(value.output, "My Project");
  const control = path.join(workspace, ".zpm");
  const desiredBundle = path.join(workspace, "Vaswani - 2017 - Attention Is All You Need");
  await fs.mkdir(control, { recursive: true });
  await fs.mkdir(desiredBundle);
  await fs.writeFile(path.join(control, "manifest.json"), JSON.stringify({
    version: 4,
    exported_at: "2026-01-01T00:00:00+00:00",
    collection_key: "ROOTKEY1",
    collection_name: "My Project",
    filename_template: "author_year_title",
    annotation_layout: "bundle",
    items: [],
  }));

  await exportSnapshot(snapshot(value.pdf, value.markdown), new NodeFileSystem(), "ROOTKEY1", {
    outputDir: value.output,
    annotationLayout: "bundle",
  });
  assert.deepEqual(await fs.readdir(desiredBundle), []);
  assert.equal(
    await fs.readFile(path.join(
      workspace,
      "Vaswani - 2017 - Attention Is All You Need [PDF00001]",
      "Vaswani - 2017 - Attention Is All You Need [PDF00001].pdf",
    ), "utf8"),
    "pdf-content",
  );
});

test("existing workspaces retain their recorded filename and layout settings", async (context) => {
  const value = await fixture();
  context.after(() => fs.rm(value.root, { recursive: true, force: true }));
  const fileSystem = new NodeFileSystem();
  await exportSnapshot(snapshot(value.pdf, value.markdown), fileSystem, "ROOTKEY1", {
    outputDir: value.output,
    annotationLayout: "separate",
    filenameTemplate: "author_year_title",
  });
  const stats = await exportSnapshot(snapshot(value.pdf, value.markdown), fileSystem, "ROOTKEY1", {
    outputDir: value.output,
    annotationLayout: "bundle",
    filenameTemplate: "title",
  });
  assert.deepEqual(stats.retainedSettings, [
    "filename order: author_year_title",
    "layout: separate",
  ]);
  const manifest = JSON.parse(await fs.readFile(
    path.join(value.output, "My Project", ".zpm", "manifest.json"),
  ));
  assert.equal(manifest.filename_template, "author_year_title");
  assert.equal(manifest.annotation_layout, "separate");
});

test("native exporter refuses symlink escapes and unmanaged control files", async (context) => {
  const value = await fixture();
  context.after(() => fs.rm(value.root, { recursive: true, force: true }));
  const fileSystem = new NodeFileSystem();
  await exportSnapshot(snapshot(value.pdf, value.markdown), fileSystem, "ROOTKEY1", {
    outputDir: value.output,
    annotationLayout: "separate",
  });
  const workspace = path.join(value.output, "My Project");
  const outside = path.join(value.root, "outside");
  await fs.mkdir(outside);
  await fs.symlink(outside, path.join(workspace, "Annotations"));
  await assert.rejects(
    exportSnapshot(snapshot(value.pdf, value.markdown), fileSystem, "ROOTKEY1", {
      outputDir: value.output,
      exportAnnotations: true,
      annotationLayout: "separate",
    }),
    /resolves outside the workspace/,
  );
  await fs.rm(path.join(workspace, "Annotations"));
  await fs.writeFile(path.join(workspace, ".zpm", "metadata.json"), '{"personal":true}\n');
  await assert.rejects(
    exportSnapshot(snapshot(value.pdf, value.markdown), fileSystem, "ROOTKEY1", {
      outputDir: value.output,
      annotationLayout: "separate",
    }),
    /unmanaged metadata/,
  );
});

test("native exporter validates the Zotero snapshot before creating a workspace", async (context) => {
  const value = await fixture();
  context.after(() => fs.rm(value.root, { recursive: true, force: true }));
  const invalid = snapshot(value.pdf, value.markdown);
  invalid.schema_version = 99;
  await assert.rejects(
    exportSnapshot(invalid, new NodeFileSystem(), "ROOTKEY1", {
      outputDir: value.output,
      annotationLayout: "separate",
    }),
    /Unsupported Zotero snapshot schema/,
  );
  await assert.rejects(fs.access(value.output));
});

test("annotation images must resolve inside Zotero's cache", async (context) => {
  const value = await fixture();
  context.after(() => fs.rm(value.root, { recursive: true, force: true }));
  const cache = path.join(path.dirname(value.pdf), "cache");
  const outside = path.join(value.root, "outside.png");
  await fs.mkdir(cache);
  await fs.writeFile(outside, "not-a-cache-image");
  await fs.symlink(outside, path.join(cache, "escaped.png"));
  const captured = snapshot(value.pdf, value.markdown);
  captured.annotations["10"][0].image_path = path.join(cache, "escaped.png");
  await assert.rejects(
    exportSnapshot(captured, new NodeFileSystem(), "ROOTKEY1", {
      outputDir: value.output,
      exportAnnotations: true,
      annotationLayout: "separate",
    }),
    /not a readable Zotero cache PNG/,
  );
});

test("Zotero note HTML is converted conservatively", () => {
  assert.equal(noteHtmlToMarkdown("<p>First &amp; second</p><ul><li>One</li></ul>"), "First & second\n\n- One");
});
