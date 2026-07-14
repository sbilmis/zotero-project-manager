/* global ChromeUtils, IOUtils, PathUtils, Services, Zotero */

const ZPM_PLUGIN_ID = "zpm@zotero-project-manager";
const ZPM_PREF_OUTPUT = "extensions.zpm.outputDir";
const ZPM_PREF_EXECUTABLE = "extensions.zpm.executablePath";
const ZPM_SNAPSHOT_SCHEMA = 1;
const ZPM_MAX_OUTPUT = 12000;

function zpmCreatorName(creator) {
  return String(creator.lastName || creator.name || creator.firstName || "").trim();
}

function zpmTags(item) {
  return item.getTags().map((value) => String(value.tag)).sort((a, b) => a.localeCompare(b));
}

function zpmCommandArguments(snapshotPath, collectionKey, outputDir, annotations) {
  const args = [
    "plugin-export",
    snapshotPath,
    collectionKey,
    "--output",
    outputDir,
  ];
  if (annotations) {
    args.push("--annotations");
  }
  return args;
}

function zpmTrimOutput(output) {
  const text = String(output || "").trim();
  if (text.length <= ZPM_MAX_OUTPUT) {
    return text;
  }
  return text.slice(0, ZPM_MAX_OUTPUT) + "\n…output truncated…";
}

var ZPMPlugin = {
  id: ZPM_PLUGIN_ID,
  rootURI: "",
  menuID: null,

  async startup({ id, rootURI }) {
    this.id = id;
    this.rootURI = rootURI;
    for (const window of Zotero.getMainWindows()) {
      this.addToWindow(window);
    }
    const plugin = this;
    this.menuID = Zotero.MenuManager.registerMenu({
      menuID: "zpm-export-collection",
      pluginID: this.id,
      target: "main/library/collection",
      menus: [
        {
          menuType: "submenu",
          l10nID: "zpm-menu-root",
          onShowing(_event, context) {
            context.setVisible(Boolean(context.collectionTreeRow?.isCollection()));
          },
          menus: [
            {
              menuType: "menuitem",
              l10nID: "zpm-menu-export-pdfs",
              onCommand(_event, context) {
                void plugin.exportSelected(context, false);
              },
            },
            {
              menuType: "menuitem",
              l10nID: "zpm-menu-export-annotations",
              onCommand(_event, context) {
                void plugin.exportSelected(context, true);
              },
            },
            { menuType: "separator" },
            {
              menuType: "menuitem",
              l10nID: "zpm-menu-choose-output",
              onCommand() {
                void plugin.chooseOutputDirectory(true);
              },
            },
            {
              menuType: "menuitem",
              l10nID: "zpm-menu-choose-executable",
              onCommand() {
                void plugin.chooseExecutable();
              },
            },
            {
              menuType: "menuitem",
              l10nID: "zpm-menu-check-installation",
              onCommand() {
                void plugin.checkInstallation();
              },
            },
          ],
        },
      ],
    });
    Zotero.debug("zpm companion plugin started");
  },

  addToWindow(window) {
    window.MozXULElement.insertFTLIfNeeded("zpm.ftl");
  },

  removeFromWindow(window) {
    window.document.querySelector('link[href="zpm.ftl"]')?.remove();
  },

  shutdown() {
    if (this.menuID) {
      Zotero.MenuManager.unregisterMenu(this.menuID);
      this.menuID = null;
    }
    for (const window of Zotero.getMainWindows()) {
      this.removeFromWindow(window);
    }
    Zotero.debug("zpm companion plugin stopped");
  },

  async exportSelected(context, annotations) {
    try {
      const row = context.collectionTreeRow;
      if (!row?.isCollection() || !row.ref?.key) {
        throw new Error("Select a Zotero collection before exporting.");
      }
      const outputDir = await this.chooseOutputDirectory(false);
      if (!outputDir) {
        return;
      }
      const executable = await this.findExecutable();
      const snapshot = await this.buildSnapshot(row.ref, annotations);
      const snapshotPath = PathUtils.join(
        PathUtils.tempDir,
        `zpm-zotero-${Date.now()}-${Math.random().toString(16).slice(2)}.json`,
      );
      await Zotero.File.putContentsAsync(snapshotPath, JSON.stringify(snapshot));
      try {
        const result = await this.runProcess(
          executable,
          zpmCommandArguments(snapshotPath, row.ref.key, outputDir, annotations),
        );
        if (result.exitCode !== 0) {
          throw new Error(result.output || `zpm exited with status ${result.exitCode}`);
        }
        this.alert("Export complete", result.output || `${row.ref.name} was exported.`);
      } finally {
        await Zotero.File.removeIfExists(snapshotPath);
      }
    } catch (error) {
      Zotero.logError(error);
      this.alert("zpm export failed", error.message || String(error));
    }
  },

  async checkInstallation() {
    try {
      const executable = await this.findExecutable();
      const result = await this.runProcess(executable, ["--version"]);
      if (result.exitCode !== 0) {
        throw new Error(result.output || `zpm exited with status ${result.exitCode}`);
      }
      this.alert("zpm is ready", `${result.output}\n\nExecutable: ${executable}`);
    } catch (error) {
      Zotero.logError(error);
      this.alert("zpm was not found", error.message || String(error));
    }
  },

  async chooseOutputDirectory(forcePicker) {
    const saved = String(Zotero.Prefs.get(ZPM_PREF_OUTPUT) || "");
    if (!forcePicker && saved && await IOUtils.exists(saved)) {
      return saved;
    }
    const { FilePicker } = ChromeUtils.importESModule(
      "chrome://zotero/content/modules/filePicker.mjs",
    );
    const picker = new FilePicker();
    picker.init(Zotero.getMainWindow(), "Choose zpm export folder", picker.modeGetFolder);
    if (saved && await IOUtils.exists(saved)) {
      picker.displayDirectory = saved;
    }
    const result = await picker.show();
    if (result !== picker.returnOK) {
      return null;
    }
    Zotero.Prefs.set(ZPM_PREF_OUTPUT, picker.file);
    return picker.file;
  },

  async chooseExecutable() {
    try {
      const saved = String(Zotero.Prefs.get(ZPM_PREF_EXECUTABLE) || "");
      const { FilePicker } = ChromeUtils.importESModule(
        "chrome://zotero/content/modules/filePicker.mjs",
      );
      const picker = new FilePicker();
      picker.init(Zotero.getMainWindow(), "Choose the zpm executable", picker.modeOpen);
      if (saved && await IOUtils.exists(saved)) {
        picker.displayDirectory = PathUtils.parent(saved);
      }
      const result = await picker.show();
      if (result !== picker.returnOK) {
        return null;
      }
      if (!picker.file || !await IOUtils.exists(picker.file)) {
        throw new Error("The selected zpm executable does not exist.");
      }
      Zotero.Prefs.set(ZPM_PREF_EXECUTABLE, picker.file);
      this.alert("zpm executable saved", picker.file);
      return picker.file;
    } catch (error) {
      Zotero.logError(error);
      this.alert("Could not save zpm executable", error.message || String(error));
      return null;
    }
  },

  async findExecutable() {
    const { Subprocess } = ChromeUtils.importESModule(
      "resource://gre/modules/Subprocess.sys.mjs",
    );
    const configured = String(Zotero.Prefs.get(ZPM_PREF_EXECUTABLE) || "");
    const environment = Subprocess.getEnvironment();
    const home = environment.HOME || environment.USERPROFILE || "";
    const candidates = [configured];
    if (Zotero.isMac) {
      candidates.push("/opt/homebrew/bin/zpm", "/usr/local/bin/zpm");
    } else if (Zotero.isLinux) {
      candidates.push("/home/linuxbrew/.linuxbrew/bin/zpm", "/usr/local/bin/zpm", "/usr/bin/zpm");
    } else if (Zotero.isWin && home) {
      candidates.push(PathUtils.join(home, ".local", "bin", "zpm.exe"));
    }
    if (home) {
      candidates.push(PathUtils.join(home, ".local", "bin", Zotero.isWin ? "zpm.exe" : "zpm"));
    }
    for (const candidate of candidates) {
      if (candidate && await IOUtils.exists(candidate)) {
        return candidate;
      }
    }
    try {
      return await Subprocess.pathSearch(Zotero.isWin ? "zpm.exe" : "zpm", environment);
    } catch (_error) {
      throw new Error(
        "Install zpm first (Homebrew: brew install sbilmis/tap/zpm), then choose Check zpm Installation again.",
      );
    }
  },

  async runProcess(command, args) {
    const { Subprocess } = ChromeUtils.importESModule(
      "resource://gre/modules/Subprocess.sys.mjs",
    );
    const process = await Subprocess.call({
      command,
      arguments: args,
      environmentAppend: true,
      stderr: "stdout",
    });
    const outputPromise = process.stdout.readString();
    const { exitCode } = await process.wait();
    return { exitCode, output: zpmTrimOutput(await outputPromise) };
  },

  async buildSnapshot(rootCollection, includeAnnotations) {
    const descendants = Zotero.Collections.getByParent(rootCollection.id, true, false);
    const collections = [rootCollection, ...descendants]
      .filter((collection, index, values) => values.findIndex((value) => value.id === collection.id) === index)
      .sort((a, b) => a.id - b.id);
    const snapshot = {
      schema_version: ZPM_SNAPSHOT_SCHEMA,
      zotero_version: Zotero.version,
      data_dir: Zotero.DataDirectory.dir,
      collections: collections.map((collection) => ({
        id: collection.id,
        key: collection.key,
        name: collection.name,
        parent_id: collection.parentID || null,
        library_id: collection.libraryID,
      })),
      attachments: {},
      annotations: {},
      notes: {},
    };

    for (const collection of collections) {
      await collection.loadDataType("childItems");
      const childItems = collection.getChildItems(false, false);
      const attachments = [];
      for (const item of childItems) {
        await item.loadAllData();
        let attachmentItems = [];
        if (item.isRegularItem()) {
          attachmentItems = await Zotero.Items.getAsync(item.getAttachments(false));
          if (includeAnnotations) {
            await this.captureNotes(snapshot, item);
          }
        } else if (item.isFileAttachment()) {
          attachmentItems = [item];
        }
        for (const attachment of attachmentItems) {
          if (!attachment?.isFileAttachment()) {
            continue;
          }
          await attachment.loadAllData();
          const metadataItem = attachment.parentID
            ? await Zotero.Items.getAsync(attachment.parentID)
            : attachment;
          if (metadataItem !== attachment) {
            await metadataItem.loadAllData();
          }
          attachments.push({
            attachment_id: attachment.id,
            attachment_key: attachment.key,
            item_id: metadataItem.id,
            item_key: metadataItem.key,
            title: metadataItem.getField("title") || null,
            date: metadataItem.getField("date") || null,
            creators: metadataItem.isRegularItem()
              ? metadataItem.getCreatorsJSON().map(zpmCreatorName).filter(Boolean)
              : [],
            content_type: attachment.attachmentContentType || null,
            source_path: await attachment.getFilePathAsync() || null,
            original_path: attachment.attachmentPath || "",
            doi: metadataItem.getField("DOI") || null,
            tags: zpmTags(metadataItem),
          });
          if (includeAnnotations) {
            await this.captureAnnotations(snapshot, attachment);
            await this.captureNotes(snapshot, attachment);
          }
        }
      }
      snapshot.attachments[String(collection.id)] = attachments.sort(
        (a, b) => a.attachment_id - b.attachment_id,
      );
    }
    return snapshot;
  },

  async captureAnnotations(snapshot, attachment) {
    if (snapshot.annotations[String(attachment.id)]) {
      return;
    }
    await attachment.loadDataType("childItems");
    const annotations = attachment.getAnnotations(false, false);
    const captured = [];
    for (const annotation of annotations) {
      let imagePath = null;
      if (
        ["image", "ink"].includes(annotation.annotationType)
        && await Zotero.Annotations.hasCacheImage(annotation)
      ) {
        imagePath = Zotero.Annotations.getCacheImagePath(annotation);
      }
      captured.push({
        annotation_id: annotation.id,
        annotation_key: annotation.key,
        attachment_id: attachment.id,
        annotation_type: annotation.annotationType,
        text: annotation.annotationText || null,
        comment: annotation.annotationComment || null,
        color: annotation.annotationColor || null,
        page_label: annotation.annotationPageLabel || null,
        sort_index: annotation.annotationSortIndex || "",
        position: annotation.annotationPosition || "",
        author_name: annotation.annotationAuthorName || null,
        date_added: annotation.dateAdded || "",
        date_modified: annotation.dateModified || "",
        tags: zpmTags(annotation),
        image_path: imagePath,
      });
    }
    snapshot.annotations[String(attachment.id)] = captured;
  },

  async captureNotes(snapshot, parent) {
    if (snapshot.notes[String(parent.id)]) {
      return;
    }
    await parent.loadDataType("childItems");
    const noteIDs = parent.getNotes(false);
    const notes = noteIDs.length ? await Zotero.Items.getAsync(noteIDs) : [];
    snapshot.notes[String(parent.id)] = notes.map((note) => ({
      note_id: note.id,
      note_key: note.key,
      parent_item_id: parent.id,
      title: note.getNoteTitle() || null,
      content: note.getNote() || "",
      date_added: note.dateAdded || "",
      date_modified: note.dateModified || "",
      tags: zpmTags(note),
    }));
  },

  alert(title, message) {
    Services.prompt.alert(Zotero.getMainWindow(), title, zpmTrimOutput(message));
  },
};

if (typeof module !== "undefined") {
  module.exports = {
    zpmCommandArguments,
    zpmCreatorName,
    zpmTrimOutput,
  };
}
