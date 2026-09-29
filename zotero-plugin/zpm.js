/* global ChromeUtils, Components, IOUtils, PathUtils, Services, ZPMPicker, ZPMLinks, ZPMLinkMenus, ZPMNativeExporter, Zotero */

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
  exportInProgress: false,

  async startup({ id, rootURI }) {
    this.id = id;
    this.rootURI = rootURI;
    await Zotero.PreferencePanes.register({
      pluginID: this.id,
      id: "zpm-preferences",
      label: "ZPM",
      src: "preferences.xhtml",
      scripts: ["preferences.js"],
      stylesheets: ["preferences.css"],
      helpURL: "https://github.com/sbilmis/zotero-project-manager#zotero-plugin",
    });
    for (const window of Zotero.getMainWindows()) {
      this.addToWindow(window);
    }
    ZPMLinkMenus.start(this);
    ZPMPicker.start();
    Zotero.debug("zpm companion plugin started");
  },

  addToWindow(window) {
    window.MozXULElement.insertFTLIfNeeded("zpm.ftl");
  },

  removeFromWindow(window) {
    window.document.querySelector('link[href="zpm.ftl"]')?.remove();
  },

  shutdown() {
    ZPMPicker.stop();
    ZPMLinkMenus.stop();
    for (const window of Zotero.getMainWindows()) {
      this.removeFromWindow(window);
    }
    Zotero.debug("zpm companion plugin stopped");
  },

  selectedExportCollections(context) {
    // Prefer Zotero 10's complete selection, including any unsupported rows.
    const rows = context && "collectionTreeRows" in context
      ? context.collectionTreeRows : [context?.collectionTreeRow];
    if (!Array.isArray(rows) || !rows.length
        || rows.some((row) => !row?.isCollection?.() || !row.ref
          || !Number.isSafeInteger(row.ref.id) || row.ref.id <= 0
          || !Number.isSafeInteger(row.ref.libraryID) || row.ref.libraryID <= 0
          || row.ref.deleted)) {
      throw new Error("Select one or more Zotero collections, without libraries, searches, or other rows.");
    }
    const collections = rows.map((row) => row.ref);
    for (const collection of collections) ZPMLinks.key(collection.key);
    if (collections.some((collection) => collection.libraryID !== collections[0].libraryID)) {
      throw new Error("Select collections from one Zotero library at a time.");
    }
    return [...new Map(collections.map((collection) => [collection.id, collection])).values()];
  },

  exportRoots(collections) {
    // Exporting a parent already includes all descendants, even when a child
    // appears before its parent in Zotero's selection order.
    const selectedIDs = new Set(collections.map((collection) => collection.id));
    const coveredIDs = new Set();
    for (const collection of collections) {
      for (const child of Zotero.Collections.getByParent(collection.id, true, false)) {
        if (child.id !== collection.id && selectedIDs.has(child.id)) coveredIDs.add(child.id);
      }
    }
    const roots = collections.filter((collection) => !coveredIDs.has(collection.id));
    if (!roots.length) throw new Error("Cannot determine export roots for the selected collections.");
    return { roots, covered: collections.filter((collection) => coveredIDs.has(collection.id)) };
  },

  async exportSelected(context, annotations) {
    if (this.exportInProgress) {
      this.alert("Export in progress", "Wait for the current export to finish.");
      return;
    }
    this.exportInProgress = true;
    try {
      const { roots, covered } = this.exportRoots(this.selectedExportCollections(context));
      const outputDir = await this.chooseOutputDirectory(false);
      if (!outputDir) {
        return;
      }
      const options = {
        outputDir,
        exportAnnotations: annotations,
        includeNonPdf: Boolean(Zotero.Prefs.get(ZPM_PREF_INCLUDE_NON_PDF)),
        annotationLayout: this.annotationLayout(),
        filenameTemplate: String(Zotero.Prefs.get(ZPM_PREF_FILENAME_TEMPLATE) || "author_year_title"),
      };
      const results = [], failures = [];
      // Serial exports share one destination and one concurrency guard. The
      // exporter can safely resolve same-name workspaces after each completes.
      for (const collection of roots) {
        try {
          const snapshot = await this.buildSnapshot(collection, annotations);
          results.push(await ZPMNativeExporter.exportSnapshot(
            snapshot, ZPMZoteroFileSystem, collection.key, { ...options },
          ));
        } catch (error) {
          Zotero.logError(error);
          failures.push(`${collection.name} [${collection.key}]: ${error.message || String(error)}`);
        }
      }
      const summary = [];
      if (roots.length > 1) summary.push(`Exported ${results.length} of ${roots.length} collections.`);
      if (failures.length) {
        summary.push(`Failed:\n${failures.join("\n")}\n\nFailed exports may have written some files. Fix the error and re-export to retry.`);
      }
      for (const stats of results) {
        summary.push(`${stats.collectionName}: ${stats.copied} copied, ${stats.updated} updated, `
          + `${stats.unchanged} unchanged, ${stats.missing} missing.\n${stats.workspace}`
          + (stats.retainedSettings.length
            ? `\nExisting workspace settings retained (${stats.retainedSettings.join(", ")}).` : ""));
      }
      if (covered.length) {
        summary.push(`Included within a selected parent collection: ${covered.map((collection) => collection.name).join(", ")}.`);
      }
      this.alert(
        failures.length ? (results.length ? "Export finished with errors" : "zpm export failed") : "Export complete",
        summary.join("\n\n"),
      );
    } catch (error) {
      Zotero.logError(error);
      this.alert("zpm export failed", error.message || String(error));
    } finally {
      this.exportInProgress = false;
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
    ZPM_ANNOTATION_LAYOUTS,
    ZPMPlugin,
  };
}
