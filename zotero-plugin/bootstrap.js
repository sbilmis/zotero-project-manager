var ZPMPlugin;

function install() {}

async function startup({ id, version, rootURI }) {
  await Zotero.initializationPromise;
  Services.scriptloader.loadSubScript(rootURI + "zpm.js");
  await ZPMPlugin.startup({ id, version, rootURI });
}

function onMainWindowLoad({ window }) {
  ZPMPlugin?.addToWindow(window);
}

function onMainWindowUnload({ window }) {
  ZPMPlugin?.removeFromWindow(window);
}

function shutdown(_data, reason) {
  if (reason === APP_SHUTDOWN) {
    return;
  }
  ZPMPlugin?.shutdown();
  ZPMPlugin = undefined;
}

function uninstall() {}
