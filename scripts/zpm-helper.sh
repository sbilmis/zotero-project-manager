#!/usr/bin/env bash

# Convenience helpers for a source checkout of Zotero Project Manager.
#
# Optional environment overrides:
#   ZPM_PROJECT_DIR  Project checkout (default: ~/zotero-collection-mirror)
#   ZPM_ZOTERO_DIR   Zotero data directory (default: ~/Zotero)
#   ZPM_OUTPUT_DIR   Export parent directory (default: ~/ResearchProjects)

zpm_project_dir="${ZPM_PROJECT_DIR:-$HOME/zotero-collection-mirror}"
zpm_zotero_dir="${ZPM_ZOTERO_DIR:-$HOME/Zotero}"
zpm_output_dir="${ZPM_OUTPUT_DIR:-$HOME/ResearchProjects}"

_zpm_python() {
    local python_path="$zpm_project_dir/.venv/bin/python"
    if [[ ! -x "$python_path" ]]; then
        printf 'zpm: virtual environment not found at %s\n' "$python_path" >&2
        printf 'Run: cd %s && python -m venv .venv && .venv/bin/pip install -e .\n' \
            "$zpm_project_dir" >&2
        return 1
    fi
    printf '%s\n' "$python_path"
}

zpm_collections() {
    local python_path
    python_path="$(_zpm_python)" || return 1
    "$python_path" -m zotero_project_manager list \
        --zotero-dir "$zpm_zotero_dir" "$@"
}

zpm_export() {
    if [[ $# -eq 0 ]]; then
        printf 'Usage: zpm_export COLLECTION [COLLECTION ...] [zpm export options]\n' >&2
        return 2
    fi

    local python_path
    python_path="$(_zpm_python)" || return 1
    "$python_path" -m zotero_project_manager export "$@" \
        --zotero-dir "$zpm_zotero_dir" \
        --output "$zpm_output_dir"
}

zpm_my_ai() {
    zpm_export "My-AI" "$@"
}
