/* global ChromeUtils, IOUtils, Zotero, document */

const ZPM_PREFERENCES = {
  output: "extensions.zpm.outputDir",
  layout: "extensions.zpm.annotationLayout",
  includeNonPdf: "extensions.zpm.includeNonPdf",
  filenameTemplate: "extensions.zpm.filenameTemplate",
};

var ZPMPreferences = {
  initialized: false,
  choosingOutput: false,

  init() {
    if (this.initialized) return;
    document.defaultView.MozXULElement.insertFTLIfNeeded("zpm.ftl");
    this.output = document.getElementById("zpm-preferences-output");
    this.layout = document.getElementById("zpm-preferences-layout-select");
    this.includeNonPdf = document.getElementById("zpm-preferences-include-non-pdf");
    this.filenameTemplate = document.getElementById("zpm-preferences-filename-select");
    this.status = document.getElementById("zpm-preferences-status");
    this.layoutDescription = document.getElementById(
      "zpm-preferences-layout-description",
    );

    this.output.value = String(Zotero.Prefs.get(ZPM_PREFERENCES.output) || "");
    this.includeNonPdf.checked = Boolean(Zotero.Prefs.get(ZPM_PREFERENCES.includeNonPdf));
    this.filenameTemplate.value = String(
      Zotero.Prefs.get(ZPM_PREFERENCES.filenameTemplate) || "author_year_title",
    );
    const savedLayout = String(Zotero.Prefs.get(ZPM_PREFERENCES.layout) || "separate");
    this.layout.value = ["separate", "sidecar", "bundle"].includes(savedLayout)
      ? savedLayout
      : "separate";
    this.describeLayout();

    this.output.addEventListener("change", () => this.saveOutput());
    this.includeNonPdf.addEventListener("change", () => {
      Zotero.Prefs.set(ZPM_PREFERENCES.includeNonPdf, this.includeNonPdf.checked);
      this.setStatus("zpm-status-attachment-saved", "success");
    });
    this.filenameTemplate.addEventListener("change", () => {
      Zotero.Prefs.set(ZPM_PREFERENCES.filenameTemplate, this.filenameTemplate.value);
      this.setStatus("zpm-status-filename-saved", "success");
    });
    this.layout.addEventListener("change", () => {
      Zotero.Prefs.set(ZPM_PREFERENCES.layout, this.layout.value);
      this.describeLayout();
      this.setStatus("zpm-status-layout-saved", "success");
    });
    document.getElementById("zpm-preferences-output-button").addEventListener(
      "click",
      () => this.chooseOutput(),
    );
    this.initialized = true;
  },

  saveOutput() {
    Zotero.Prefs.set(ZPM_PREFERENCES.output, this.output.value.trim());
    this.setStatus("zpm-status-export-folder-saved", "success");
  },

  async chooseOutput() {
    if (this.choosingOutput) return;
    this.choosingOutput = true;
    const button = document.getElementById("zpm-preferences-output-button");
    button.disabled = true;
    try {
      const { FilePicker } = ChromeUtils.importESModule(
        "chrome://zotero/content/modules/filePicker.mjs",
      );
      const picker = new FilePicker();
      // Attach the native dialog to Settings, not the potentially obscured or
      // closed Zotero library window.
      picker.init(document.defaultView, "Choose zpm export folder", picker.modeGetFolder);
      const currentPath = this.output.value.trim();
      if (currentPath) {
        try {
          if ((await IOUtils.stat(currentPath)).type === "directory") {
            picker.displayDirectory = currentPath;
          }
        } catch (_error) {
          // A stale or invalid saved path must not block choosing a replacement.
        }
      }
      const result = await picker.show();
      if (result === picker.returnOK) {
        this.output.value = picker.file;
        this.saveOutput();
      }
    } catch (error) {
      Zotero.logError(error);
      this.setStatus("zpm-status-choose-folder-error", "error", { error: error.message || String(error) });
    } finally {
      this.choosingOutput = false;
      button.disabled = false;
    }
  },

  describeLayout() {
    const descriptions = {
      separate: "zpm-layout-description-separate",
      sidecar: "zpm-layout-description-sidecar",
      bundle: "zpm-layout-description-bundle",
    };
    document.l10n.formatValue(descriptions[this.layout.value]).then((value) => {
      this.layoutDescription.textContent = value;
    });
  },

  setStatus(messageId, kind, args = undefined) {
    document.l10n.formatValue(messageId, args).then((message) => {
      this.status.textContent = message;
      this.status.dataset.kind = kind;
    });
  },
};
