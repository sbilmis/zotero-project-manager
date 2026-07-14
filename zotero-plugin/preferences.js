/* global ChromeUtils, IOUtils, PathUtils, Zotero, document */

const ZPM_PREFERENCES = {
  output: "extensions.zpm.outputDir",
  executable: "extensions.zpm.executablePath",
  layout: "extensions.zpm.annotationLayout",
};

var ZPMPreferences = {
  initialized: false,

  init() {
    if (this.initialized) {
      return;
    }
    this.initialized = true;
    this.output = document.getElementById("zpm-preferences-output");
    this.executable = document.getElementById("zpm-preferences-executable");
    this.layout = document.getElementById("zpm-preferences-layout-select");
    this.status = document.getElementById("zpm-preferences-status");
    this.layoutDescription = document.getElementById(
      "zpm-preferences-layout-description",
    );

    this.output.value = String(Zotero.Prefs.get(ZPM_PREFERENCES.output) || "");
    this.executable.value = String(
      Zotero.Prefs.get(ZPM_PREFERENCES.executable) || "",
    );
    const savedLayout = String(Zotero.Prefs.get(ZPM_PREFERENCES.layout) || "separate");
    this.layout.value = ["separate", "sidecar", "bundle"].includes(savedLayout)
      ? savedLayout
      : "separate";
    this.describeLayout();

    this.output.addEventListener("change", () => this.savePath("output"));
    this.executable.addEventListener("change", () => this.savePath("executable"));
    this.layout.addEventListener("change", () => {
      Zotero.Prefs.set(ZPM_PREFERENCES.layout, this.layout.value);
      this.describeLayout();
      this.setStatus("Annotation layout saved.", "success");
    });
    document.getElementById("zpm-preferences-output-button").addEventListener(
      "click",
      () => void this.chooseOutput(),
    );
    document.getElementById("zpm-preferences-executable-button").addEventListener(
      "click",
      () => void this.chooseExecutable(),
    );
    document.getElementById("zpm-preferences-test-button").addEventListener(
      "click",
      () => void this.testExecutable(),
    );
  },

  savePath(kind) {
    const field = kind === "output" ? this.output : this.executable;
    Zotero.Prefs.set(ZPM_PREFERENCES[kind], field.value.trim());
    this.setStatus(`${kind === "output" ? "Export folder" : "Executable"} saved.`, "success");
  },

  async chooseOutput() {
    const selected = await this.pickPath(
      "Choose zpm export folder",
      "folder",
      this.output.value,
    );
    if (selected) {
      this.output.value = selected;
      this.savePath("output");
    }
  },

  async chooseExecutable() {
    const selected = await this.pickPath(
      "Choose the zpm executable",
      "file",
      this.executable.value,
    );
    if (selected) {
      this.executable.value = selected;
      this.savePath("executable");
    }
  },

  async pickPath(title, kind, current) {
    const { FilePicker } = ChromeUtils.importESModule(
      "chrome://zotero/content/modules/filePicker.mjs",
    );
    const picker = new FilePicker();
    const mode = kind === "folder" ? picker.modeGetFolder : picker.modeOpen;
    picker.init(Zotero.getMainWindow(), title, mode);
    if (current && await IOUtils.exists(current)) {
      picker.displayDirectory = kind === "folder" ? current : PathUtils.parent(current);
    }
    const result = await picker.show();
    return result === picker.returnOK ? picker.file : null;
  },

  async testExecutable() {
    try {
      const { Subprocess } = ChromeUtils.importESModule(
        "resource://gre/modules/Subprocess.sys.mjs",
      );
      const command = await this.findExecutable(Subprocess);
      const process = await Subprocess.call({
        command,
        arguments: ["--version"],
        environmentAppend: true,
        stderr: "stdout",
      });
      const output = (await process.stdout.readString()).trim();
      const { exitCode } = await process.wait();
      if (exitCode !== 0) {
        throw new Error(output || `zpm exited with status ${exitCode}`);
      }
      this.setStatus(`${output || "zpm is ready."} (${command})`, "success");
    } catch (error) {
      this.setStatus(error.message || String(error), "error");
    }
  },

  async findExecutable(Subprocess) {
    const configured = this.executable.value.trim();
    if (configured) {
      if (await IOUtils.exists(configured)) {
        return configured;
      }
      throw new Error("The configured executable does not exist.");
    }

    const environment = Subprocess.getEnvironment();
    const home = environment.HOME || environment.USERPROFILE || "";
    const executableName = Zotero.isWin ? "zpm.exe" : "zpm";
    const candidates = [];
    if (Zotero.isMac) {
      candidates.push("/opt/homebrew/bin/zpm", "/usr/local/bin/zpm");
    } else if (Zotero.isLinux) {
      candidates.push(
        "/home/linuxbrew/.linuxbrew/bin/zpm",
        "/usr/local/bin/zpm",
        "/usr/bin/zpm",
      );
    }
    if (home) {
      candidates.push(PathUtils.join(home, ".local", "bin", executableName));
    }
    for (const candidate of candidates) {
      if (await IOUtils.exists(candidate)) {
        return candidate;
      }
    }
    try {
      return await Subprocess.pathSearch(executableName, environment);
    } catch (_error) {
      throw new Error(
        "zpm was not found. Install it with Homebrew or choose a custom executable.",
      );
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
