/* global Zotero, ZPMLinks */

// Small read-only local bridge. No CORS or browser access, writes, or file paths.
var ZPMPicker = {
  path: "/zpm/papers",
  endpoint: null,

  start() {
    const picker = this;
    this.endpoint = class {
      supportedMethods = ["GET"];
      allowRequestsFromUnsafeWebContent = false;
      async init(request) { return picker.handle(request); }
    };
    Zotero.Server.Endpoints[this.path] = this.endpoint;
  },

  stop() {
    if (Zotero.Server.Endpoints[this.path] === this.endpoint) delete Zotero.Server.Endpoints[this.path];
    this.endpoint = null;
  },

  async handle({ method, headers, searchParams }) {
    const response = (status, body) => [status, "application/json", JSON.stringify(body)];
    if (method !== "GET") return response(405, { error: "Only GET is supported." });
    const normalized = Object.fromEntries(Object.entries(headers || {}).map(([key, value]) => [key.toLowerCase(), value]));
    if (normalized["x-zpm-client"] !== "emacs" || "origin" in normalized || "sec-fetch-site" in normalized) {
      return response(403, { error: "Use the local Emacs picker client." });
    }
    if (!Zotero.Prefs.get("httpServer.localAPI.enabled")) {
      return response(403, { code: "local_api_disabled", error: "In Zotero Settings → Advanced, enable ‘Allow other applications on this computer to communicate with Zotero’." });
    }
    try {
      if ([...searchParams.keys()].some(key => key !== "collection") || searchParams.getAll("collection").length > 1) {
        return response(400, { error: "Expected at most one collection key." });
      }
      const libraryID = Zotero.Libraries.userLibraryID;
      let collection;
      if (searchParams.has("collection")) {
        const key = ZPMLinks.key(searchParams.get("collection"));
        collection = await Zotero.Collections.getByLibraryAndKeyAsync(libraryID, key);
        if (!collection || collection.deleted) return response(404, { error: "The remembered collection no longer exists in My Library. Use zpm-forget-collection or remember another collection." });
      } else {
        const pane = Zotero.getMainWindow()?.ZoteroPane;
        try {
          collection = typeof pane?.getCollectionTreeRows === "function"
            ? ZPMLinks.selectedCollection({ collectionTreeRows: pane.getCollectionTreeRows() })
            : pane?.getSelectedCollection();
        } catch (_error) {
          collection = null;
        }
        if (!collection) return response(409, { error: "Select exactly one collection under My Library in Zotero, or use a note with a remembered collection." });
      }
      ZPMLinks.personal(collection, libraryID);
      await collection.loadDataType("childItems");
      const papers = [];
      for (const item of collection.getChildItems(false, false)) {
        if (item.deleted || !item.isRegularItem()) continue;
        ZPMLinks.personal(item, libraryID);
        await item.loadDataType("itemData");
        await item.loadDataType("creators");
        const title = ZPMLinks.label(item.getField("title"), "Untitled paper");
        const authors = item.getCreatorsJSON().map(c => c.lastName || c.name || c.firstName || "").filter(Boolean).join(", ");
        const year = String(item.getField("date") || "").match(/\b\d{4}\b/)?.[0] || "";
        papers.push({ key: item.key, title, authors: ZPMLinks.label(authors, "Unknown author"), year });
      }
      papers.sort((a, b) => a.title.localeCompare(b.title) || a.key.localeCompare(b.key));
      return response(200, { schema: 1, collection: { key: collection.key, name: collection.name }, papers });
    } catch (error) {
      Zotero.logError(error);
      return response(400, { error: error.message || "Unable to read this collection." });
    }
  },
};

if (typeof module !== "undefined") module.exports = { ZPMPicker };
