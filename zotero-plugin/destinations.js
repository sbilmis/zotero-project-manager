/* Desktop destination helpers; also exercised without Zotero in Node tests. */
var ZPMDestinations = (() => {
  const NOTEBOOK_URL = "https://notebook.google.com/";

  function notebookURL(value) {
    const url = new URL(value || NOTEBOOK_URL);
    if (url.protocol !== "https:"
        || !["notebook.google.com", "notebooklm.google.com"].includes(url.hostname)
        || url.username || url.password || (url.port && url.port !== "443")) {
      throw new Error("Use an HTTPS notebook.google.com or notebooklm.google.com URL.");
    }
    return url.href;
  }

  function rememberedNotebookURL(value) {
    const input = String(value || "").trim();
    if (!input || input.length > 2048) throw new Error("Paste the URL of an open notebook.");
    const url = new URL(notebookURL(input));
    const match = url.pathname.match(/^(?:\/u\/[0-9]+)?\/notebook\/([A-Za-z0-9_-]+)\/?$/);
    if (!match || ["new", "create"].includes(match[1].toLowerCase())) {
      throw new Error("Open the notebook and copy its address, not the Notebook home page.");
    }
    // Keep Google's account selector, but omit tracking and source-selection state.
    const account = url.searchParams.get("authuser");
    url.search = "";
    if (account) url.searchParams.set("authuser", account);
    url.hash = "";
    return url.href;
  }

  function notebookLinkPreference(collection) {
    const libraryID = Number(collection?.libraryID);
    const key = String(collection?.key || "");
    if (!Number.isSafeInteger(libraryID) || libraryID < 1 || !/^[A-Z0-9]{8}$/.test(key)) {
      throw new Error("Select a saved Zotero collection before setting its notebook link.");
    }
    return "extensions.zpm.notebookLink." + libraryID + "." + key;
  }

  async function deliveryPlan(stats, fs) {
    const workspace = await fs.realPath(stats.workspace);
    const files = [];
    const seen = new Set();
    for (const relative of stats.deliveryFiles || []) {
      const parts = String(relative).split("/");
      if (parts.some((part) => !part || [".", "..", ".zpm"].includes(part)
          || part.includes("\\") || part.includes(":"))) {
        throw new Error("Unsafe delivery path: " + relative);
      }
      const candidate = await fs.realPath(fs.join(workspace, ...parts));
      if (!await fs.isWithin(candidate, workspace) || !await fs.isFile(candidate)) {
        throw new Error("Exported file is missing or outside its workspace: " + relative);
      }
      if (!seen.has(candidate)) {
        files.push({ path: candidate, relative });
        seen.add(candidate);
      }
    }
    return {
      workspace,
      name: workspace.replaceAll("\\", "/").split("/").pop(),
      files,
    };
  }

  const api = { NOTEBOOK_URL, notebookURL, rememberedNotebookURL, notebookLinkPreference, deliveryPlan };
  if (typeof module !== "undefined") module.exports = api;
  return api;
})();
