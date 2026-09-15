/* global Zotero */

// Zotero.Utilities.allowedKeyChars: eight uppercase characters, excluding 0, 1, O.
// Formatting and copying have no export, filesystem, network, or process dependencies.
var ZPMLinks = {
  key(value) {
    if (typeof value !== "string" || !/^[23456789ABCDEFGHIJKLMNPQRSTUVWXYZ]{8}$/.test(value)
        || value.length !== 8) {
      throw new Error("Missing or invalid Zotero key. Select a saved entry in My Library; keys must be eight uppercase Zotero characters (no 0, 1, or O).");
    }
    return value;
  },

  personal(object, userLibraryID) {
    if (!Number.isInteger(userLibraryID) || userLibraryID <= 0
        || !object || object.libraryID !== userLibraryID) {
      throw new Error("Only entries in My Library are supported; group libraries are not supported.");
    }
    if (object.deleted) throw new Error("Restore the entry from Trash before copying its link.");
    this.key(object.key);
  },

  collection(collection, userLibraryID) {
    this.personal(collection, userLibraryID);
    return { kind: "collection", key: collection.key, label: collection.name };
  },

  item(item, userLibraryID) {
    this.personal(item, userLibraryID);
    let kind;
    if (item.isRegularItem?.()) kind = "item";
    else if (item.isFileAttachment?.() && item.attachmentContentType === "application/pdf") kind = "pdf";
    else throw new Error("Select a paper record or PDF file attachment. Notes, annotations in the item list, and non-PDF attachments are not supported.");
    return { kind, key: item.key, label: item.getField("title") };
  },

  itemInCollection(item, collection, userLibraryID) {
    const target = this.item(item, userLibraryID);
    this.personal(collection, userLibraryID);
    if (target.kind !== "item") throw new Error("Select a paper record for a link in this collection.");
    if (!Number.isInteger(collection.id) || !item.getCollections().includes(collection.id)) {
      throw new Error("This paper is not directly in the selected collection. Open its own collection or copy an ordinary item link.");
    }
    return { ...target, collection: collection.key };
  },

  selection(items, userLibraryID, multiple = false) {
    if (!Array.isArray(items) || (multiple ? items.length < 2 : items.length !== 1)) {
      throw new Error(multiple
        ? "Select at least two paper records or PDF attachments for Copy Multiple Links."
        : "Select exactly one entry. Use Copy Multiple Links for a batch.");
    }
    // Validate the entire batch before writing anything to the clipboard.
    return items.map((item) => this.item(item, userLibraryID));
  },

  pageIndex(value) {
    if (!Number.isSafeInteger(value) || value < 0 || value >= Number.MAX_SAFE_INTEGER) {
      throw new Error("No valid PDF page at this position. Right-click one page thumbnail in the PDF reader sidebar.");
    }
    return value + 1;
  },

  page(attachment, pageIndex, userLibraryID) {
    const target = this.item(attachment, userLibraryID);
    if (target.kind !== "pdf") throw new Error("Page links require a PDF attachment.");
    const page = this.pageIndex(pageIndex);
    return { ...target, page, label: `${target.label || "PDF"} — PDF page ${page}` };
  },

  annotation(attachment, annotation, userLibraryID) {
    this.personal(annotation, userLibraryID);
    if (!annotation.isAnnotation?.() || annotation.parentID !== attachment?.id) {
      throw new Error("Select a saved annotation belonging to this PDF attachment.");
    }
    let position;
    try { position = JSON.parse(annotation.annotationPosition); }
    catch (_error) { throw new Error("The annotation has no valid saved PDF position."); }
    const target = this.page(attachment, position?.pageIndex, userLibraryID);
    return {
      ...target,
      annotation: annotation.key,
      label: `${target.label} — ${annotation.annotationText || annotation.annotationComment || "Annotation"}`,
    };
  },

  label(value, fallback) {
    // Fullwidth brackets keep Org's delimiters unambiguous. Replace controls,
    // including hard newlines, but retain ordinary Unicode text.
    return String(value || fallback).replace(/\[/g, "［").replace(/\]/g, "］")
      .replace(/[\s\u0000-\u001f\u007f-\u009f]+/g, " ").trim() || fallback;
  },

  format(target, format) {
    const key = this.key(target.key);
    if (!["collection", "item", "pdf"].includes(target.kind)) throw new Error("Unsupported link destination.");
    let suffix = "";
    if (target.page !== undefined || target.annotation !== undefined) {
      if (target.kind !== "pdf" || !Number.isSafeInteger(target.page) || target.page < 1) {
        throw new Error("PDF page links require a positive physical page number.");
      }
      suffix = `?page=${target.page}`;
      if (target.annotation !== undefined) suffix += `&annotation=${this.key(target.annotation)}`;
    }
    let itemPath = "select/library/items";
    let orgSuffix = suffix;
    if (target.collection !== undefined) {
      if (target.kind !== "item") throw new Error("Collection context is supported only for paper records.");
      const collection = this.key(target.collection);
      itemPath = `select/library/collections/${collection}/items`;
      orgSuffix = `?collection=${collection}`;
    }
    const path = target.kind === "collection" ? "select/library/collections"
      : target.kind === "item" ? itemPath : "open-pdf/library/items";
    const uri = `zotero://${path}/${key}${suffix}`;
    const label = this.label(target.label, `${target.kind === "pdf" ? "PDF" : target.kind} ${key}`);
    if (format === "uri") return uri;
    if (format === "org") return `[[zotero-${target.kind}:${key}${orgSuffix}][${label}]]`;
    // Escape Markdown punctuation and HTML/entity delimiters in visible text.
    if (format === "markdown") return `[${label.replace(/[\\`*_{}()!#<>&|~]/g, "\\$&")}](${uri})`;
    throw new Error("Unsupported link format. Choose Org, Markdown, or Zotero URI.");
  },

  text(targets, format) {
    if (!targets.length) throw new Error("No supported entries selected.");
    return targets.map((target) => this.format(target, format)).join("\n");
  },
};

var ZPMLinkMenus = {
  menuIDs: [],
  readerHandlers: [],
  active: false,

  start(plugin) {
    this.active = true;
    this.plugin = plugin;
    for (const kind of ["collection", "item"]) {
      const menus = [this.copyMenu(kind, "single", "zpm-copy-root")];
      if (kind === "item") {
        menus.push(this.copyMenu(kind, "multiple", "zpm-copy-multiple"));
        menus.push(this.copyMenu(kind, "in-collection", "zpm-copy-in-collection"));
      } else {
        menus.push({
          menuType: "submenu", l10nID: "zpm-export-root",
          onShowing: (_event, context) => context.setEnabled(Boolean(context.collectionTreeRow?.isCollection?.())),
          menus: [false, true].map((annotations) => ({
            menuType: "menuitem",
            l10nID: annotations ? "zpm-menu-export-annotations" : "zpm-menu-export-pdfs",
            onCommand: (_event, context) => { void plugin.exportSelected(context, annotations); },
          })),
        });
        menus.push({ menuType: "separator" }, {
          menuType: "menuitem", l10nID: "zpm-menu-settings",
          onCommand: () => Zotero.Utilities.Internal.openPreferences("zpm-preferences"),
        });
      }
      this.menuIDs.push(Zotero.MenuManager.registerMenu({
        menuID: `zpm-${kind}`, pluginID: plugin.id, target: `main/library/${kind}`,
        menus: [{ menuType: "submenu", l10nID: "zpm-menu-root", menus }],
      }));
    }
    for (const type of ["createViewContextMenu", "createThumbnailContextMenu", "createAnnotationContextMenu"]) {
      const handler = (event) => {
        if (this.active) this.readerMenu(type, event);
      };
      Zotero.Reader.registerEventListener(type, handler, plugin.id);
      this.readerHandlers.push([type, handler]);
    }
  },

  copyMenu(kind, destination, l10nID) {
    const getTargets = (context) => this.targets(context, kind, destination);
    const setEnabled = (context) => {
      try { getTargets(context); context.setEnabled(true); }
      catch (_error) { context.setEnabled(false); }
    };
    return {
      menuType: "submenu", l10nID,
      onShowing: (_event, context) => {
        let visible = true;
        if (kind === "item") {
          const multiple = context.items?.length > 1;
          visible = destination === "multiple" ? multiple : !multiple;
          if (destination === "in-collection") {
            try { getTargets(context); } catch (_error) { visible = false; }
          }
        }
        context.setVisible(visible);
        setEnabled(context);
      },
      menus: ["org", "markdown", "uri"].map((format) => ({
        menuType: "menuitem", l10nID: `zpm-format-${format}`,
        onShowing: (_event, context) => setEnabled(context),
        onCommand: (_event, context) => this.copy(() => getTargets(context), format),
      })),
    };
  },

  stop() {
    this.active = false;
    for (const id of this.menuIDs) Zotero.MenuManager.unregisterMenu(id);
    this.menuIDs = [];
    // Zotero 9.0's public unregisterEventListener has an inverted filter that
    // removes OTHER plugins' listeners. Use its plugin-scoped cleanup instead,
    // also used by Zotero's own plugin shutdown observer (fixed upstream).
    if (Zotero.Reader._unregisterEventListenerByPluginID) {
      Zotero.Reader._unregisterEventListenerByPluginID(this.plugin.id);
    } else {
      for (const [type, handler] of this.readerHandlers) Zotero.Reader.unregisterEventListener(type, handler);
    }
    this.readerHandlers = [];
  },

  targets(context, kind, destination) {
    const libraryID = Zotero.Libraries.userLibraryID;
    if (kind === "collection") {
      const row = context.collectionTreeRow;
      if (!row?.isCollection?.()) throw new Error("Right-click a collection under My Library.");
      return [ZPMLinks.collection(row.ref, libraryID)];
    }
    const targets = ZPMLinks.selection(context.items, libraryID, destination === "multiple");
    if (destination === "in-collection") {
      const row = context.collectionTreeRow;
      if (!row?.isCollection?.()) throw new Error("Open a collection before copying a link in this collection.");
      return [ZPMLinks.itemInCollection(context.items[0], row.ref, libraryID)];
    }
    return targets;
  },

  copy(getTargets, format) {
    if (!this.active) return;
    try {
      const text = ZPMLinks.text(getTargets(), format);
      Zotero.Utilities.Internal.copyTextToClipboard(text);
    } catch (error) {
      Zotero.logError(error);
      this.plugin.alert("Cannot copy Zotero link", error.message || String(error));
    }
  },

  readerTargets(type, { reader, params }) {
    const libraryID = Zotero.Libraries.userLibraryID;
    const attachment = Zotero.Items.get(reader.itemID);
    if (type === "createAnnotationContextMenu") {
      if (!Array.isArray(params.ids) || params.ids.length !== 1) {
        throw new Error("Select exactly one saved PDF annotation.");
      }
      ZPMLinks.personal(attachment, libraryID);
      const key = ZPMLinks.key(params.ids[0]);
      const annotation = Zotero.Items.getByLibraryAndKey(libraryID, key);
      return [ZPMLinks.annotation(attachment, annotation, libraryID)];
    }
    let pageIndex = params.position?.pageIndex;
    if (type === "createThumbnailContextMenu") {
      if (!Array.isArray(params.pageIndexes) || params.pageIndexes.length !== 1) {
        throw new Error("Select exactly one PDF page thumbnail.");
      }
      [pageIndex] = params.pageIndexes;
    }
    return [ZPMLinks.page(attachment, pageIndex, libraryID)];
  },

  readerMenu(type, event) {
    const getTargets = () => this.readerTargets(type, event);
    let disabled = false;
    try { getTargets(); } catch (_error) { disabled = true; }
    const name = type === "createAnnotationContextMenu" ? "Annotation" : "PDF Page";
    const formats = [["org", "Org"], ["markdown", "Markdown"], ["uri", "Zotero URI"]];
    const commands = formats.map(([format, label]) => ({
      label, disabled,
      onCommand: () => this.copy(getTargets, format),
    }));
    event.append({
      label: "ZPM",
      groups: [[{ label: `Copy ${name} Link`, groups: [commands] }]],
    });
  },
};

if (typeof module !== "undefined") module.exports = { ZPMLinks, ZPMLinkMenus };
