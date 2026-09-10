/* global ChromeUtils, Components, IOUtils, PathUtils, Services, ZPMNativeExporter, ZPMDestinations, Zotero */

const ZPM_PLUGIN_ID = "zpm@zotero-project-manager";
const ZPM_PREF_OUTPUT = "extensions.zpm.outputDir";
const ZPM_PREF_ANNOTATION_LAYOUT = "extensions.zpm.annotationLayout";
const ZPM_PREF_INCLUDE_NON_PDF = "extensions.zpm.includeNonPdf";
const ZPM_PREF_FILENAME_TEMPLATE = "extensions.zpm.filenameTemplate";
const ZPM_ANNOTATION_LAYOUTS = new Set(["separate", "sidecar", "bundle"]);
const ZPM_SNAPSHOT_SCHEMA = 1;
const ZPM_MAX_OUTPUT = 12000;

function zpmCreatorName(creator) {
  return String(creator.lastName || creator.name || creator.firstName || "").trim();
}

function zpmTags(item) {
  return item.getTags().map((value) => String(value.tag)).sort((a, b) => a.localeCompare(b));
}

function zpmTrimOutput(output) {
  const text = String(output || "").trim();
  if (text.length <= ZPM_MAX_OUTPUT) {
    return text;
  }
  return text.slice(0, ZPM_MAX_OUTPUT) + "\n…output truncated…";
}

const ZPMZoteroFileSystem = {
  join(...parts) {
    return PathUtils.join(...parts);
  },

  async exists(path) {
    return IOUtils.exists(path);
  },

  async stat(path) {
    const value = await IOUtils.stat(path);
    return {
      size: Number(value.size || 0),
      mtimeMs: Number(value.lastModified || 0),
      type: value.type,
    };
  },

  async isFile(path) {
    try {
      return (await IOUtils.stat(path)).type === "regular";
    } catch (_error) {
      return false;
    }
  },

  async makeDir(path) {
    await IOUtils.makeDirectory(path, { createAncestors: true, ignoreExisting: true });
  },

  async readText(path) {
    return IOUtils.readUTF8(path);
  },

  async writeTextAtomic(path, content) {
    const parent = PathUtils.parent(path);
    await this.makeDir(parent);
    const temporary = PathUtils.join(
      parent,
      `.${PathUtils.filename(path)}.${Date.now()}-${Math.random().toString(16).slice(2)}.tmp`,
    );
    try {
      await IOUtils.writeUTF8(temporary, content);
      await IOUtils.move(temporary, path, { noOverwrite: false });
    } finally {
      await IOUtils.remove(temporary, { ignoreAbsent: true });
    }
  },

  async copyAtomic(source, destination) {
    const parent = PathUtils.parent(destination);
    await this.makeDir(parent);
    const temporary = PathUtils.join(
      parent,
      `.${PathUtils.filename(destination)}.${Date.now()}-${Math.random().toString(16).slice(2)}.tmp`,
    );
    try {
      await IOUtils.copy(source, temporary, { noOverwrite: true });
      await IOUtils.move(temporary, destination, { noOverwrite: false });
    } finally {
      await IOUtils.remove(temporary, { ignoreAbsent: true });
    }
  },

  async hash(path) {
    const hasher = Components.classes["@mozilla.org/security/hash;1"]
      .createInstance(Components.interfaces.nsICryptoHash);
    hasher.init(hasher.SHA256);
    let offset = 0;
    const chunkSize = 1024 * 1024;
    while (true) {
      const chunk = await IOUtils.read(path, { offset, maxBytes: chunkSize });
      if (!chunk.length) break;
      hasher.update(chunk, chunk.length);
      offset += chunk.length;
      if (chunk.length < chunkSize) break;
    }
    const binary = hasher.finish(false);
    return Array.from(binary, (character) => character.charCodeAt(0).toString(16).padStart(2, "0"))
      .join("");
  },

  async listFiles(root) {
    const files = [];
    const walk = async (directory, relative) => {
      for (const child of await IOUtils.getChildren(directory)) {
        const name = PathUtils.filename(child);
        const childRelative = relative ? `${relative}/${name}` : name;
        const info = await IOUtils.stat(child);
        if (info.type === "directory") await walk(child, childRelative);
        else if (info.type === "regular") files.push(childRelative);
      }
    };
    if (await IOUtils.exists(root)) await walk(root, "");
    return files;
  },

  async listDirectories(root) {
    const directories = [];
    const walk = async (directory, relative) => {
      for (const child of await IOUtils.getChildren(directory)) {
        const info = await IOUtils.stat(child);
        if (info.type !== "directory") continue;
        const name = PathUtils.filename(child);
        const childRelative = relative ? `${relative}/${name}` : name;
        directories.push(childRelative);
        await walk(child, childRelative);
      }
    };
    if (await IOUtils.exists(root)) await walk(root, "");
    return directories;
  },

  async removeFile(path) {
    await IOUtils.remove(path, { ignoreAbsent: true });
  },

  async realPath(path) {
    const file = Components.classes["@mozilla.org/file/local;1"]
      .createInstance(Components.interfaces.nsIFile);
    file.initWithPath(path);
    file.normalize();
    return file.path;
  },

  async isWithin(path, parent) {
    const normalize = (value) => {
      let normalized = String(PathUtils.normalize(value)).replaceAll("\\", "/").replace(/\/+$/g, "");
      if (Zotero.isWin) normalized = normalized.toLowerCase();
      return normalized;
    };
    const child = normalize(path);
    const root = normalize(parent);
    return child === root || child.startsWith(`${root}/`);
  },
};

var ZPMPlugin = {
  id: ZPM_PLUGIN_ID,
  rootURI: "",
  menuID: null,
  exportInProgress: false,

  async startup({ id, rootURI }) {
    this.id = id;
    this.rootURI = rootURI;
    await Zotero.PreferencePanes.register({
      pluginID: this.id,
      id: "zpm-preferences",
      label: "Zotero Project Manager",
      src: "preferences.xhtml",
      scripts: ["preferences.js"],
      stylesheets: ["preferences.css"],
      helpURL: "https://github.com/sbilmis/zotero-project-manager#zotero-9-companion-plugin",
    });
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
                void plugin.exportSelected(context, false, false);
              },
            },
            {
              menuType: "menuitem",
              l10nID: "zpm-menu-export-annotations",
              onCommand(_event, context) {
                void plugin.exportSelected(context, true, false);
              },
            },
            {
              menuType: "menuitem",
              l10nID: "zpm-menu-export-notebooklm",
              onCommand(_event, context) {
                void plugin.exportSelected(context, true, true, "gemini-notebook");
              },
            },
            {
              menuType: "menuitem",
              l10nID: "zpm-menu-notebook-link",
              onCommand(_event, context) {
                plugin.setNotebookLink(context);
              },
            },
            {
              menuType: "menuitem",
              l10nID: "zpm-menu-export-devonthink",
              onShowing(_event, context) {
                context.setVisible(Boolean(Zotero.isMac));
              },
              onCommand(_event, context) {
                void plugin.exportSelected(context, true, false, "devonthink");
              },
            },
            { menuType: "separator" },
            {
              menuType: "menuitem",
              l10nID: "zpm-menu-settings",
              onCommand() {
                Zotero.Utilities.Internal.openPreferences("zpm-preferences");
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

  async exportSelected(context, annotations, notebooklm, destination = null) {
    if (this.exportInProgress) {
      this.alert("Export in progress", "Wait for the current export or app handoff to finish.");
      return;
    }
    this.exportInProgress = true;
    try {
      const row = context.collectionTreeRow;
      if (!row?.isCollection() || !row.ref?.key) {
        throw new Error("Select a Zotero collection before exporting.");
      }
      const outputDir = await this.chooseOutputDirectory(false);
      if (!outputDir) {
        return;
      }
      const annotationLayout = notebooklm ? "sidecar" : this.annotationLayout();
      const snapshot = await this.buildSnapshot(row.ref, annotations);
      const stats = await ZPMNativeExporter.exportSnapshot(
        snapshot,
        ZPMZoteroFileSystem,
        row.ref.key,
        {
          outputDir,
          exportAnnotations: annotations,
          includeNonPdf: notebooklm
            || Boolean(Zotero.Prefs.get(ZPM_PREF_INCLUDE_NON_PDF)),
          annotationLayout,
          notebooklm,
          filenameTemplate: String(
            Zotero.Prefs.get(ZPM_PREF_FILENAME_TEMPLATE) || "author_year_title",
          ),
        },
      );
      if (destination) {
        await this.sendExport(stats, destination, row.ref);
        return;
      }
      this.alert(
        notebooklm ? "Gemini Notebook export complete" : "Export complete",
        `${stats.collectionName}: ${stats.copied} copied, ${stats.updated} updated, `
          + `${stats.unchanged} unchanged, ${stats.missing} missing.\n\n${stats.workspace}`
          + (stats.retainedSettings.length
            ? `\n\nExisting workspace settings retained (${stats.retainedSettings.join(", ")}).`
            : "")
          + (stats.notebooklmSources
            ? `\n\nPrepared sources: ${stats.notebooklmSources}.`
            : "")
          + (stats.notebooklmSourceLimitExceeded
            ? "\nThis exceeds 50 sources; select a subset if required by your plan."
            : ""),
      );
    } catch (error) {
      Zotero.logError(error);
      this.alert("zpm export failed", error.message || String(error));
    } finally {
      this.exportInProgress = false;
    }
  },

  setNotebookLink(context) {
    if (this.exportInProgress) {
      this.alert("Export in progress", "Wait for the current export or app handoff to finish.");
      return;
    }
    try {
      const row = context.collectionTreeRow;
      if (!row?.isCollection() || !row.ref?.key) {
        throw new Error("Select a Zotero collection before setting its notebook link.");
      }
      const url = this.promptNotebookLink(row.ref, false);
      if (url === null) return;
      this.alert(
        "Gemini Notebook link",
        url === ZPMDestinations.NOTEBOOK_URL
          ? "The saved link was cleared for this collection. No notebook or sources were deleted."
          : "Link saved for " + row.ref.name + ". Send to Gemini Notebook will open this notebook.\n\n"
            + "Use the Google account that can access it. Nothing has been uploaded.",
      );
    } catch (error) {
      Zotero.logError(error);
      this.alert("Could not save notebook link", error.message || String(error));
    }
  },

  promptNotebookLink(collection, forSend) {
    const preference = ZPMDestinations.notebookLinkPreference(collection);
    const input = { value: String(Zotero.Prefs.get(preference) || "") };
    const message = "Notebook for " + collection.name + "\n\n"
      + "Open or create your notebook in the browser, then paste its full URL here. "
      + "The link is remembered for this collection, including after a Zotero restart or collection rename.\n\n"
      + (forSend
        ? "Leave this blank to open the Notebook home page without saving a link. Cancel stops the handoff; exported files remain."
        : "Leave this blank and press OK to forget the saved link. Cancel keeps it unchanged.")
      + "\n\nUse the correct Google account. This does not create a notebook or upload files.";
    while (Services.prompt.prompt(
      Zotero.getMainWindow(), "Set Gemini Notebook Link", message, input, null, { value: false },
    )) {
      if (!String(input.value).trim()) {
        if (!forSend && Zotero.Prefs.get(preference) !== undefined) {
          Zotero.Prefs.clear(preference);
        }
        return ZPMDestinations.NOTEBOOK_URL;
      }
      let url;
      try {
        url = ZPMDestinations.rememberedNotebookURL(input.value);
      } catch (error) {
        this.alert("Invalid notebook link", error.message || String(error));
        continue;
      }
      Zotero.Prefs.set(preference, url);
      return url;
    }
    return null;
  },

  notebookURLForCollection(collection) {
    const preference = ZPMDestinations.notebookLinkPreference(collection);
    const saved = Zotero.Prefs.get(preference);
    if (saved) {
      try {
        return ZPMDestinations.rememberedNotebookURL(saved);
      } catch (_error) {
        this.alert("Invalid saved notebook link", "Please replace the saved link, or cancel and use Set Gemini Notebook Link to clear it.");
      }
    }
    return this.promptNotebookLink(collection, true);
  },

  async sendExport(stats, destination, collection) {
    const plan = await ZPMDestinations.deliveryPlan(stats, ZPMZoteroFileSystem);
    if (!plan.files.length) {
      this.alert("No files to send", "This collection has no available exported files.");
      return;
    }
    if (destination === "devonthink") {
      try {
        const result = await this.runDesktopScript("devonthink.applescript", plan);
        this.alert("DEVONthink 4", result);
      } catch (error) {
        throw new Error("Your files were exported to " + stats.workspace
          + ", but the DEVONthink 4 handoff failed: " + error.message);
      }
      return;
    }
    const notebookURL = this.notebookURLForCollection(collection);
    if (notebookURL === null) return;
    this.alert(
      "Ready for Gemini Notebook",
      plan.files.length + " files are ready, including exported notes and annotations.\n\n"
        + (notebookURL === ZPMDestinations.NOTEBOOK_URL
          ? "Next, the Notebook home page and prepared files will open. Open or create a notebook. "
          : "Next, your saved notebook and prepared files will open. ")
        + "Drag the selected files into Add sources. "
        + "You can also use Upload files.\n\n"
        + "Nothing has been uploaded yet. Check the Sources panel after uploading; "
        + "repeated uploads can create duplicates.\n\n"
        + (plan.files.length > 50 ? "Choose a subset if this exceeds your plan's source limit.\n\n" : "")
        + stats.workspace,
    );
    Zotero.launchURL(notebookURL);
    if (Zotero.isMac) {
      try {
        await this.runDesktopScript("reveal-files.applescript", plan);
        return;
      } catch (error) {
        Zotero.logError(error);
      }
    }
    // Opening the folder remains useful if selecting files is unavailable.
    Zotero.File.reveal(plan.files[0].path);
  },

  async runDesktopScript(scriptName, plan, groupID = "") {
    if (!Zotero.isMac) throw new Error("DEVONthink integration requires macOS.");
    const { Subprocess } = ChromeUtils.importESModule("resource://gre/modules/Subprocess.sys.mjs");
    const directory = Components.classes["@mozilla.org/file/local;1"]
      .createInstance(Components.interfaces.nsIFile);
    directory.initWithPath(PathUtils.tempDir);
    directory.append("zpm-handoff");
    directory.createUnique(Components.interfaces.nsIFile.DIRECTORY_TYPE, 0o700);
    const planPath = PathUtils.join(directory.path, "files.json");
    const scriptPath = PathUtils.join(directory.path, scriptName);
    let process;
    let timer;
    const window = Zotero.getMainWindow();
    try {
      const source = await Zotero.File.getContentsAsync(this.rootURI + "scripts/" + scriptName);
      await IOUtils.writeUTF8(scriptPath, source);
      await IOUtils.writeUTF8(planPath, JSON.stringify(plan));
      process = await Subprocess.call({
        command: "/usr/bin/osascript",
        arguments: [scriptPath, planPath, groupID],
        stderr: "pipe",
      });
      if (process.stdin) await process.stdin.close();
      let timedOut = false;
      timer = window.setTimeout(() => {
        timedOut = true;
        void process.kill();
      }, 600000);
      const readOutput = async (pipe) => {
        let output = "";
        while (true) {
          const chunk = await pipe.readString();
          if (!chunk) break;
          if (output.length < 12000) output += chunk.slice(0, 12000 - output.length);
        }
        return output.trim();
      };
      const [stdout, stderr, result] = await Promise.all([
        readOutput(process.stdout), readOutput(process.stderr), process.wait(),
      ]);
      if (timedOut) throw new Error("The handoff timed out. Check the app before retrying.");
      if (result.exitCode !== 0) {
        const appName = scriptName === "reveal-files.applescript" ? "Finder" : "DEVONthink";
        throw new Error((stderr || "The app did not accept the files.")
          + "\nIf macOS denied access, allow Zotero to control " + appName + " in "
          + "System Settings → Privacy & Security → Automation.");
      }
      return stdout;
    } finally {
      if (timer) window.clearTimeout(timer);
      await IOUtils.remove(directory.path, { recursive: true, ignoreAbsent: true });
    }
  },

  annotationLayout() {
    const value = String(Zotero.Prefs.get(ZPM_PREF_ANNOTATION_LAYOUT) || "separate");
    return ZPM_ANNOTATION_LAYOUTS.has(value) ? value : "separate";
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
    zpmCreatorName,
    zpmTrimOutput,
    ZPMPlugin,
    ZPM_ANNOTATION_LAYOUTS,
  };
}
