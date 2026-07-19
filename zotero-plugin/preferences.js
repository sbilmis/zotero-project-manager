/* global ChromeUtils, IOUtils, Zotero, document */

const ZPM_PREFERENCES = {
  output: "extensions.zpm.outputDir",
  layout: "extensions.zpm.annotationLayout",
  includeNonPdf: "extensions.zpm.includeNonPdf",
  filenameTemplate: "extensions.zpm.filenameTemplate",
};

var ZPMPreferences = {
  initialized: false,

  init() {
    if (this.initialized) return;
    this.initialized = true;
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
      this.setStatus("Attachment preference saved.", "success");
    });
    this.filenameTemplate.addEventListener("change", () => {
      Zotero.Prefs.set(ZPM_PREFERENCES.filenameTemplate, this.filenameTemplate.value);
      this.setStatus("Filename preference saved.", "success");
    });
    this.layout.addEventListener("change", () => {
      Zotero.Prefs.set(ZPM_PREFERENCES.layout, this.layout.value);
      this.describeLayout();
      this.setStatus("Annotation layout saved.", "success");
    });
    document.getElementById("zpm-preferences-output-button").addEventListener(
      "click",
      () => void this.chooseOutput(),
    );
  },

  saveOutput() {
    Zotero.Prefs.set(ZPM_PREFERENCES.output, this.output.value.trim());
    this.setStatus("Export folder saved.", "success");
  },

  async chooseOutput() {
    const { FilePicker } = ChromeUtils.importESModule(
      "chrome://zotero/content/modules/filePicker.mjs",
    );
    const picker = new FilePicker();
    picker.init(Zotero.getMainWindow(), "Choose zpm export folder", picker.modeGetFolder);
    if (this.output.value && await IOUtils.exists(this.output.value)) {
      picker.displayDirectory = this.output.value;
    }
    const result = await picker.show();
    if (result === picker.returnOK) {
      this.output.value = picker.file;
      this.saveOutput();
    }
  },

  describeLayout() {
    const descriptions = {
      separate: "PDFs follow the collection hierarchy; generated files live under Annotations/.",
      sidecar: "Each annotation Markdown file and its image assets sit beside the corresponding PDF.",
      bundle: "Each paper receives a folder containing its PDF, annotations.md, and image assets.",
    };
    this.layoutDescription.textContent = descriptions[this.layout.value];
  },

  setStatus(message, kind) {
    this.status.textContent = message;
    this.status.dataset.kind = kind;
  },
};
