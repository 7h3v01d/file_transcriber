"""
╔══════════════════════════════════════════════════════════╗
║   FILE TRANSCRIBER v3.2  by Leon Priest                  ║
║   Codebase → Context. Intelligently.                     ║
╚══════════════════════════════════════════════════════════╝

What's new in v3.2:
  • 🌳 Tree Manager tab — full FileTreeManager Pro integrated
      - Generate visual tree from scanned files (one click)
      - Edit tree text manually with live preview
      - Build real folder structure from any tree diagram
      - Export tree as a .zip scaffold
      - Load built-in project structure presets
      - Save / load custom .tree preset files
      - All panels themed to match File Transcriber

What was new in v3.0/3.1:
  • AI Codebase Summary — one-click Claude-powered project overview
  • Live File Preview — click any file to instantly preview it
  • Smart Importance Scoring — entry points and key files ranked first
  • Recent Folders — quick-access history of your last 8 projects
  • Per-File Token Bar Chart — visual token distribution at a glance
  • "Copy for Claude" mode — structured XML with role hints for LLM context
  • Animated spinner status bar during long operations
  • File search/filter within matched files
  • Keyboard shortcuts (Ctrl+S scan, Ctrl+T transcribe, Ctrl+Shift+C copy)
"""

import os
import sys
import json
import fnmatch
import zipfile
import tempfile
import threading
from pathlib import Path
from datetime import datetime

try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False

try:
    import urllib.request
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
except ImportError:
    print("tkinter is required. Install it via your system package manager.")
    sys.exit(1)

# ─────────────────────────────────────────────
# CONSTANTS & PRESETS
# ─────────────────────────────────────────────

APP_NAME    = "File Transcriber"
APP_VERSION = "3.2"

RECENT_FILE = os.path.join(os.path.expanduser("~"), ".file_transcriber_recent.json")
MAX_RECENT  = 8

PRESETS = {
    "🐍 Python Project": {
        "include": "*.py, *.toml, *.ini, *.cfg, *.yaml, *.yml, *.json, *.md, *.env.example, *.gitignore, *.j2",
        "exclude": "__pycache__, *.pyc, *.pyo, *env*, *.egg-info, dist, build, .git, *.whl, *.rar, *.zip",
    },
    "🌐 Web Project": {
        "include": "*.js, *.ts, *.jsx, *.tsx, *.html, *.css, *.scss, *.json, *.md, *.yaml, *.yml",
        "exclude": "node_modules, dist, build, .git, *.min.js, *.min.css, *.map, *.lock",
    },
    "📄 All Code": {
        "include": "*.py, *.js, *.ts, *.jsx, *.tsx, *.java, *.c, *.cpp, *.h, *.cs, *.go, *.rs, *.rb, *.php, *.swift, *.kt, *.sh",
        "exclude": "__pycache__, node_modules, .git, *.pyc, *.class, dist, build, *.min.js",
    },
    "📋 Config & Docs": {
        "include": "*.yaml, *.yml, *.toml, *.ini, *.json, *.md, *.rst, *.txt, *.gitignore, *.env.example",
        "exclude": ".git, __pycache__, node_modules, *.lock",
    },
    "🔧 Custom": {
        "include": "",
        "exclude": "",
    },
}

OUTPUT_FORMATS = ["Plain Text", "Markdown", "XML", "✨ Copy for Claude"]

ENTRY_POINT_NAMES = {
    "main.py", "app.py", "server.py", "index.js", "index.ts", "main.js",
    "main.ts", "main.go", "main.rs", "main.c", "main.cpp", "app.js",
    "app.ts", "manage.py", "__main__.py", "cli.py", "run.py", "start.js",
}
CONFIG_NAMES = {
    "pyproject.toml", "setup.py", "setup.cfg", "package.json", "cargo.toml",
    "go.mod", "dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "makefile", "rakefile", "justfile", ".env.example", "readme.md",
}
HIGH_VALUE_EXTS = {".py", ".ts", ".tsx", ".go", ".rs", ".java", ".cs"}

# ─────────────────────────────────────────────
# FILE TEMPLATES  (for Tree Manager scaffolding)
# ─────────────────────────────────────────────

FILE_TEMPLATES = {
    ".py":    '"""Auto-generated Python file"""\n\nif __name__ == "__main__":\n    pass\n',
    ".json":  '{}\n',
    ".md":    '# New Document\n',
    ".rst":   '# New RST Document\n',
    ".sh":    '#!/bin/bash\n\n# Auto-generated shell script\n',
    ".yml":   '# Auto-generated YAML file\n',
    ".yaml":  '# Auto-generated YAML file\n',
    ".qss":   '/* Auto-generated QSS file */\n',
    ".txt":   '# Auto-generated text file\n',
    ".ipynb": '# Auto-generated Jupyter Notebook\n',
    ".toml":  '# Auto-generated TOML file\n',
    ".cfg":   '# Auto-generated config file\n',
    ".ini":   '# Auto-generated INI file\n',
}

# ─────────────────────────────────────────────
# TREE STRUCTURE PRESETS  (from FileTreeManagerPro)
# ─────────────────────────────────────────────

TREE_PRESETS = {
    "Top-Level Structure": """project_name/
├── .gitignore
├── README.md
├── LICENSE.md
├── pyproject.toml
├── setup.cfg
├── setup.py
├── venv/
└── src/""",
    "Internal Package Structure (src/)": """src/
└── project_name/
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   └── utils.py
    ├── models/
    │   ├── __init__.py
    │   ├── user.py
    │   └── product.py
    ├── api/
    │   ├── __init__.py
    │   └── routes.py
    └── cli.py""",
    "Testing Directory (tests/)": """project_name/
└── tests/
    ├── __init__.py
    ├── test_core.py
    ├── test_api.py
    └── conftest.py""",
    "Other Directories (docs/, scripts/, data/)": """project_name/
├── docs/
│   ├── index.rst
│   └── conf.py
├── scripts/
│   ├── install.sh
│   └── deploy.py
└── data/
    ├── raw/
    └── processed/""",
    "pip-installable Package with CLI": """my_package_project/
├── .github/
│   └── workflows/
│       └── ci.yml
├── .gitignore
├── pyproject.toml
├── README.md
├── LICENSE.md
├── requirements.txt
├── src/
│   └── my_package/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── core.py
│       ├── utils.py
│       └── models/
│           ├── __init__.py
│           └── data_models.py
└── tests/
    ├── __init__.py
    ├── test_cli.py
    ├── test_core.py
    └── conftest.py""",
    "Project with CLI and GUI": """my_package_project/
├── .github/
│   └── workflows/
│       └── ci.yml
├── .gitignore
├── pyproject.toml
├── README.md
├── LICENSE.md
├── requirements.txt
├── src/
│   └── my_package/
│       ├── __init__.py
│       ├── __main__.py
│       ├── core/
│       │   ├── __init__.py
│       │   └── logic.py
│       ├── cli/
│       │   ├── __init__.py
│       │   └── commands.py
│       └── gui/
│           ├── __init__.py
│           ├── main_window.py
│           ├── widgets.py
│           └── assets/
│               ├── icon.png
│               └── style.qss
└── tests/
    ├── __init__.py
    ├── test_cli.py
    ├── test_core.py
    ├── test_gui.py
    └── conftest.py""",
    "Standard CLI Project": """my_cli_app_project/
├── .gitignore
├── pyproject.toml
├── README.md
├── LICENSE.md
├── requirements.txt
├── src/
│   └── my_cli_app/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       └── core/
│           ├── __init__.py
│           ├── logic.py
│           └── utils.py
└── tests/
    ├── __init__.py
    ├── test_cli.py
    ├── test_core.py
    └── conftest.py""",
    "Minimal Microservice / API-Only Structure": """simple_api_project/
├── .gitignore
├── pyproject.toml
├── README.md
├── LICENSE.md
├── requirements.txt
├── src/
│   └── simple_api/
│       ├── __init__.py
│       └── routes.py
├── run.py
└── tests/
    ├── test_routes.py
    └── conftest.py""",
    "Data Science / Analysis Workflow": """data_insights_project/
├── README.md
├── pyproject.toml
├── environment.yml
├── notebooks/
│   ├── exploration.ipynb
│   └── modeling.ipynb
├── src/
│   └── analysis/
│       ├── __init__.py
│       ├── preprocessing.py
│       ├── train.py
│       └── visualize.py
├── data/
│   ├── raw/
│   └── cleaned/
└── tests/
    ├── test_train.py
    └── test_preprocessing.py""",
    "Library with Plugin Architecture": """plugin_library_project/
├── README.md
├── pyproject.toml
├── src/
│   └── pluginlib/
│       ├── __init__.py
│       ├── core.py
│       ├── cli.py
│       └── plugins/
│           ├── __init__.py
│           ├── plugin_foo.py
│           └── plugin_bar.py
└── tests/
    ├── test_core.py
    ├── test_plugins.py
    └── conftest.py""",
    "Security-Focused or Encryption Library": """securex_project/
├── README.md
├── pyproject.toml
├── requirements.txt
├── src/
│   └── securex/
│       ├── __init__.py
│       ├── crypto/
│       │   ├── __init__.py
│       │   ├── encrypt.py
│       │   └── decrypt.py
│       └── auth/
│           ├── __init__.py
│           └── login.py
└── tests/
    ├── test_encrypt.py
    ├── test_auth.py
    └── conftest.py""",
}

# ─────────────────────────────────────────────
# THEMES
# ─────────────────────────────────────────────

THEMES = {
    "dark": {
        "bg":           "#0d1117",
        "surface":      "#161b22",
        "surface2":     "#21262d",
        "border":       "#30363d",
        "accent":       "#58a6ff",
        "accent2":      "#3fb950",
        "danger":       "#f85149",
        "warn":         "#e3b341",
        "purple":       "#bc8cff",
        "text":         "#e6edf3",
        "text_muted":   "#8b949e",
        "text_dim":     "#484f58",
        "header_bg":    "#0d1117",
        "tree_select":  "#1f6feb",
        "button_bg":    "#21262d",
        "button_hover": "#30363d",
        "preview_bg":   "#0d1117",
        "bar_fill":     "#1f6feb",
        "bar_bg":       "#21262d",
    },
    "light": {
        "bg":           "#f6f8fa",
        "surface":      "#ffffff",
        "surface2":     "#f0f3f6",
        "border":       "#d0d7de",
        "accent":       "#0969da",
        "accent2":      "#1a7f37",
        "danger":       "#cf222e",
        "warn":         "#9a6700",
        "purple":       "#6639ba",
        "text":         "#1f2328",
        "text_muted":   "#636c76",
        "text_dim":     "#afb8c1",
        "header_bg":    "#ffffff",
        "tree_select":  "#dbeafe",
        "button_bg":    "#f0f3f6",
        "button_hover": "#e0e5ea",
        "preview_bg":   "#fdfdfd",
        "bar_fill":     "#0969da",
        "bar_bg":       "#dbeafe",
    },
}

# ─────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────

def estimate_tokens(text):
    return max(1, len(text) // 4)

def format_size(n_bytes):
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} TB"

def format_number(n):
    return f"{n:,}"

def detect_encoding(file_path):
    if HAS_CHARDET:
        try:
            with open(file_path, "rb") as f:
                raw = f.read(20000)
            result = chardet.detect(raw)
            return result.get("encoding") or "utf-8"
        except Exception:
            return "utf-8"
    return "utf-8"

def read_file_safe(file_path):
    try:
        encoding = detect_encoding(file_path)
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            return f.read(), None
    except Exception as e:
        return "", str(e)

def load_gitignore_patterns(folder):
    gitignore_path = os.path.join(folder, ".gitignore")
    patterns = []
    if os.path.isfile(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line.rstrip("/"))
        except Exception:
            pass
    return patterns

def matches_any(name, patterns):
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(name.lower(), pattern.lower()):
            return True
    return False

def score_file_importance(file_path):
    name  = os.path.basename(file_path).lower()
    ext   = Path(file_path).suffix.lower()
    score = 0
    if name in ENTRY_POINT_NAMES:
        score += 100
    if name in CONFIG_NAMES:
        score += 80
    if ext in HIGH_VALUE_EXTS:
        score += 20
    score -= file_path.count(os.sep) * 3
    return score

# ─────────────────────────────────────────────
# RECENT FOLDERS
# ─────────────────────────────────────────────

def load_recent_folders():
    try:
        if os.path.isfile(RECENT_FILE):
            with open(RECENT_FILE, "r") as f:
                data = json.load(f)
            return [p for p in data if os.path.isdir(p)]
    except Exception:
        pass
    return []

def save_recent_folders(folders):
    try:
        with open(RECENT_FILE, "w") as f:
            json.dump(folders[:MAX_RECENT], f)
    except Exception:
        pass

def push_recent_folder(folder, existing):
    updated = [folder] + [f for f in existing if f != folder]
    return updated[:MAX_RECENT]

# ─────────────────────────────────────────────
# FILE SELECTION
# ─────────────────────────────────────────────

def should_include(file_path, include_patterns, exclude_patterns):
    name = os.path.basename(file_path)
    if matches_any(name, exclude_patterns):
        return False
    if not include_patterns:
        return True
    return matches_any(name, include_patterns)

def should_exclude_dir(dir_path, exclude_patterns):
    name = os.path.basename(dir_path)
    return matches_any(name, exclude_patterns)

def collect_files(root_folder, include_patterns, exclude_patterns,
                  gitignore_patterns=None, max_depth=None):
    collected = []
    all_exclude = list(exclude_patterns)
    if gitignore_patterns:
        all_exclude.extend(gitignore_patterns)

    def _recurse(folder, depth):
        if max_depth is not None and depth > max_depth:
            return
        try:
            for item in sorted(os.listdir(folder)):
                full_path = os.path.join(folder, item)
                if os.path.isdir(full_path):
                    if not should_exclude_dir(full_path, all_exclude):
                        _recurse(full_path, depth + 1)
                else:
                    if should_include(full_path, include_patterns, all_exclude):
                        collected.append(full_path)
        except PermissionError:
            pass

    _recurse(root_folder, 0)
    return collected

# ─────────────────────────────────────────────
# OUTPUT FORMATTERS
# ─────────────────────────────────────────────

def build_file_tree(files, root_folder):
    lines = [f"📁 {os.path.basename(root_folder)}", ""]
    rel_paths = sorted([os.path.relpath(f, root_folder) for f in files])
    dirs_seen = set()

    for rp in rel_paths:
        parts = Path(rp).parts
        for i, part in enumerate(parts[:-1]):
            dir_key = os.sep.join(parts[:i + 1])
            if dir_key not in dirs_seen:
                dirs_seen.add(dir_key)
                indent = "  " * i + "  ├─ "
                lines.append(f"{indent}📂 {part}/")
        indent = "  " * (len(parts) - 1) + "  └─ "
        lines.append(f"{indent}📄 {parts[-1]}")

    return "\n".join(lines)


def build_file_tree_ascii(files, root_folder):
    """Build a proper ASCII tree compatible with FileTreeManager's parser."""
    root_name = os.path.basename(root_folder)
    lines = [f"{root_name}/"]

    rel_paths = sorted([os.path.relpath(f, root_folder) for f in files])

    # Build nested dict structure
    tree_dict = {}
    for rp in rel_paths:
        parts = Path(rp).parts
        node = tree_dict
        for part in parts[:-1]:
            node = node.setdefault(part + "/", {})
        node[parts[-1]] = None  # file leaf

    def _render(node, prefix=""):
        items = sorted(node.keys(), key=lambda x: (x.endswith("/") is False, x.lower()))
        for i, key in enumerate(items):
            is_last = (i == len(items) - 1)
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{key}")
            if node[key] is not None:
                extension = "    " if is_last else "│   "
                _render(node[key], prefix + extension)

    _render(tree_dict)
    return "\n".join(lines)


def format_output_plain(files, root_folder, tree):
    parts = [
        f"Generated by {APP_NAME} v{APP_VERSION} — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 60,
        f"Source: {root_folder}",
        f"Files:  {len(files)}",
        "=" * 60, "", tree, "", "=" * 60, "",
    ]
    for file_path in sorted(files):
        rel = os.path.relpath(file_path, root_folder)
        content, err = read_file_safe(file_path)
        parts.append(f"┌── {rel} {'─' * max(0, 56 - len(rel))}")
        parts.append(f"[ERROR: {err}]" if err else content)
        parts.append(f"└── end of {rel}")
        parts.append("")
    return "\n".join(parts)


def format_output_markdown(files, root_folder, tree):
    lang_map = {
        "py": "python", "js": "javascript", "ts": "typescript",
        "jsx": "jsx", "tsx": "tsx", "html": "html", "css": "css",
        "scss": "scss", "json": "json", "yaml": "yaml", "yml": "yaml",
        "toml": "toml", "sh": "bash", "rs": "rust", "go": "go",
        "java": "java", "c": "c", "cpp": "cpp", "h": "c",
        "md": "markdown", "xml": "xml", "sql": "sql",
    }
    parts = [
        "# Codebase Export", "",
        f"**Source:** `{root_folder}`  ",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"**Files:** {len(files)}", "",
        "## File Tree", "```", tree, "```", "", "---", "",
    ]
    for file_path in sorted(files):
        rel  = os.path.relpath(file_path, root_folder)
        lang = lang_map.get(Path(file_path).suffix.lstrip("."), "")
        content, err = read_file_safe(file_path)
        parts.append(f"## `{rel}`")
        parts.append("")
        if err:
            parts.append(f"> ⚠️ Error: {err}")
        else:
            parts += [f"```{lang}", content, "```"]
        parts.append("")
    return "\n".join(parts)


def format_output_xml(files, root_folder, tree):
    import xml.sax.saxutils as sax
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<codebase source="{sax.escape(root_folder)}" generated="{datetime.now().isoformat()}" file_count="{len(files)}">',
        f"  <file_tree><![CDATA[\n{tree}\n  ]]></file_tree>",
        "  <files>",
    ]
    for file_path in sorted(files):
        rel  = os.path.relpath(file_path, root_folder)
        ext  = Path(file_path).suffix.lstrip(".")
        size = os.path.getsize(file_path)
        content, err = read_file_safe(file_path)
        parts.append(f'    <file path="{sax.escape(rel)}" ext="{ext}" size="{size}">')
        if err:
            parts.append(f'      <e>{sax.escape(err)}</e>')
        else:
            parts.append(f'      <content><![CDATA[\n{content}\n      ]]></content>')
        parts.append("    </file>")
    parts += ["  </files>", "</codebase>"]
    return "\n".join(parts)


def format_output_for_claude(files, root_folder, tree):
    """Structured XML output with role hints optimised for LLM context windows."""
    import xml.sax.saxutils as sax
    project_name = os.path.basename(root_folder)

    entry_points, configs, sources, docs, others = [], [], [], [], []
    for f in files:
        name = os.path.basename(f).lower()
        ext  = Path(f).suffix.lower()
        if name in ENTRY_POINT_NAMES:
            entry_points.append(f)
        elif name in CONFIG_NAMES or ext in {".toml", ".ini", ".cfg", ".yaml", ".yml"}:
            configs.append(f)
        elif ext in {".md", ".rst", ".txt"}:
            docs.append(f)
        elif ext in HIGH_VALUE_EXTS | {".js", ".ts", ".jsx", ".tsx", ".html", ".css"}:
            sources.append(f)
        else:
            others.append(f)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<!--",
        f"  Codebase: {sax.escape(project_name)}",
        f"  Exported by File Transcriber v{APP_VERSION} — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"  Files: {len(files)} | Optimised for LLM context",
        "-->",
        f'<codebase name="{sax.escape(project_name)}" generated="{datetime.now().isoformat()}">',
        "",
        "  <!-- ═══ PROJECT STRUCTURE ═══ -->",
        "  <structure><![CDATA[",
        tree,
        "  ]]></structure>",
        "",
    ]

    def _section(title, file_list, role):
        if not file_list:
            return
        lines.append(f"  <!-- ═══ {title} ═══ -->")
        lines.append(f'  <section role="{role}">')
        for fp in sorted(file_list, key=score_file_importance, reverse=True):
            rel  = os.path.relpath(fp, root_folder)
            ext  = Path(fp).suffix.lstrip(".")
            size = os.path.getsize(fp)
            try:
                raw  = open(fp, errors="replace").read()
                tok  = estimate_tokens(raw)
            except Exception:
                tok  = "?"
            content, err = read_file_safe(fp)
            lines.append(f'    <file path="{sax.escape(rel)}" ext="{ext}" approx_tokens="{tok}">')
            if err:
                lines.append(f"      <e>{sax.escape(err)}</e>")
            else:
                lines.append(f"      <content><![CDATA[\n{content}\n      ]]></content>")
            lines.append("    </file>")
        lines.append("  </section>")
        lines.append("")

    _section("ENTRY POINTS",  entry_points, "entrypoint")
    _section("CONFIGURATION", configs,      "config")
    _section("DOCUMENTATION", docs,         "docs")
    _section("SOURCE FILES",  sources,      "source")
    _section("OTHER FILES",   others,       "other")

    lines.append("</codebase>")
    return "\n".join(lines)

# ─────────────────────────────────────────────
# TREE MANAGER UTILITIES
# ─────────────────────────────────────────────

def parse_tree_text(tree_text):
    """Parse an ASCII tree diagram into (path, is_dir) tuples."""
    lines = tree_text.strip().splitlines()
    path_stack = []
    paths = []
    for line in lines:
        if not line.strip():
            continue
        # Strip box-drawing chars: │ ├ └ ─ and spaces
        clean = line.lstrip("│├└─ \t")
        indent = len(line) - len(line.lstrip("│ \t"))
        level = indent // 4
        while len(path_stack) > level:
            path_stack.pop()
        is_dir = clean.endswith("/")
        name = clean.rstrip("/")
        if not name:
            continue
        path_stack_copy = list(path_stack) + [name + ("/" if is_dir else "")]
        path_stack.append(name)
        full_path = os.path.join(*path_stack)
        paths.append((full_path, is_dir))
    return paths

# ─────────────────────────────────────────────
# AI SUMMARY
# ─────────────────────────────────────────────

AI_PROVIDERS = ["Anthropic (Claude)", "Ollama (local)"]

DEFAULT_OLLAMA_URL   = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3"


def call_anthropic_api(prompt, api_key, model="claude-sonnet-4-20250514"):
    import json as _json
    payload = _json.dumps({
        "model": model,
        "max_tokens": 512,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = _json.loads(resp.read().decode("utf-8"))
    return data["content"][0]["text"]


def call_ollama_api(prompt, base_url, model):
    import json as _json
    url     = base_url.rstrip("/") + "/api/chat"
    payload = _json.dumps({
        "model": model,
        "stream": False,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = _json.loads(resp.read().decode("utf-8"))
    return data["message"]["content"]


def fetch_ollama_models(base_url):
    import json as _json
    try:
        url = base_url.rstrip("/") + "/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def build_summary_prompt(files, root_folder):
    sorted_files = sorted(files, key=score_file_importance, reverse=True)
    sample       = sorted_files[:20]

    snippets = []
    for fp in sample:
        rel     = os.path.relpath(fp, root_folder)
        content, _ = read_file_safe(fp)
        preview = content[:800].replace("\n", " ")
        snippets.append(f"[{rel}]\n{preview}")

    file_list = "\n".join(os.path.relpath(f, root_folder) for f in sorted_files)

    return (
        f"You are a senior software engineer reviewing a codebase for the first time.\n\n"
        f"Project folder: {os.path.basename(root_folder)}\n\n"
        f"File list ({len(files)} files total):\n{file_list}\n\n"
        f"Key file previews:\n{'---'.join(snippets)}\n\n"
        f"Write a concise 3-4 sentence summary of this codebase covering:\n"
        f"1. What the project does\n"
        f"2. The tech stack / languages used\n"
        f"3. The overall architecture or structure\n"
        f"4. Any notable patterns or interesting things you notice\n\n"
        f"Be specific and direct. No fluff."
    )

# ─────────────────────────────────────────────
# MAIN APPLICATION
# ─────────────────────────────────────────────

class FileTranscriberApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1140x840")
        self.root.minsize(900, 660)

        self.theme_name = tk.StringVar(value="dark")
        self.T = THEMES["dark"]

        self._files_cache    = []
        self._scanning       = False
        self._debounce_id    = None
        self._pulse_id       = None
        self._pulse_state    = 0
        self._recent_folders = load_recent_folders()

        self.source_folder       = tk.StringVar()
        self.output_file         = tk.StringVar()
        self.output_format       = tk.StringVar(value=OUTPUT_FORMATS[0])
        self.preset_name         = tk.StringVar(value=list(PRESETS.keys())[0])
        self.include_list        = tk.StringVar(value=PRESETS[list(PRESETS.keys())[0]]["include"])
        self.exclude_list        = tk.StringVar(value=PRESETS[list(PRESETS.keys())[0]]["exclude"])
        self.use_gitignore       = tk.BooleanVar(value=True)
        self.split_output        = tk.BooleanVar(value=False)
        self.sort_by_importance  = tk.BooleanVar(value=False)
        self.max_tokens          = tk.StringVar(value="100000")
        self.status_text         = tk.StringVar(value="Select a folder to begin.")
        self.file_filter         = tk.StringVar()
        self.api_key             = tk.StringVar()
        self.ai_provider         = tk.StringVar(value=AI_PROVIDERS[0])
        self.ollama_url          = tk.StringVar(value=DEFAULT_OLLAMA_URL)
        self.ollama_model        = tk.StringVar(value=DEFAULT_OLLAMA_MODEL)

        self.stat_files  = tk.StringVar(value="—")
        self.stat_lines  = tk.StringVar(value="—")
        self.stat_size   = tk.StringVar(value="—")
        self.stat_tokens = tk.StringVar(value="—")

        self._build_ui()
        self._apply_theme()
        self._bind_events()

    # ══ UI BUILD ══════════════════════════════

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.master = tk.Frame(self.root)
        self.master.grid(row=0, column=0, sticky="nsew")
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(1, weight=1)
        self._build_header()
        self._build_body()
        self._build_footer()

    def _build_header(self):
        hdr = tk.Frame(self.master, height=60)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(2, weight=1)

        self.logo_lbl = tk.Label(hdr, text="⬡  FILE TRANSCRIBER",
                                 font=("Courier", 17, "bold"))
        self.logo_lbl.grid(row=0, column=0, padx=20, pady=14, sticky="w")

        self.sub_lbl = tk.Label(hdr, text=f"v{APP_VERSION}  ·  Codebase → Context. Intelligently.",
                                font=("Courier", 10))
        self.sub_lbl.grid(row=0, column=1, padx=5, sticky="w")

        self.shortcut_lbl = tk.Label(hdr, text="Ctrl+S scan  ·  Ctrl+T transcribe  ·  Ctrl+Shift+C copy",
                                     font=("Courier", 8))
        self.shortcut_lbl.grid(row=0, column=2, padx=10, sticky="e")

        self.theme_btn = tk.Button(hdr, text="☀  Light", font=("Courier", 10),
                                   relief="flat", cursor="hand2", bd=0,
                                   padx=12, pady=6, command=self._toggle_theme)
        self.theme_btn.grid(row=0, column=3, padx=(0, 12))

        self.hdr_frame = hdr

    def _build_body(self):
        body = tk.Frame(self.master)
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=0)
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, weight=1)
        body.rowconfigure(2, weight=1)

        self._build_source_row(body)
        self._build_left_panel(body)
        self._build_centre_panel(body)
        self._build_right_panel(body)
        self._build_output_row(body)

        self.body_frame = body

    def _build_source_row(self, body):
        src_frame = tk.Frame(body)
        src_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(12, 8))
        src_frame.columnconfigure(0, weight=1)

        tk.Label(src_frame, text="SOURCE FOLDER", font=("Courier", 9, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))

        self.src_entry = tk.Entry(src_frame, textvariable=self.source_folder, font=("Courier", 11))
        self.src_entry.grid(row=1, column=0, sticky="ew", padx=(0, 6))

        self.browse_btn = tk.Button(src_frame, text="Browse…", font=("Courier", 10),
                                    relief="flat", cursor="hand2", padx=12, pady=5,
                                    command=self._browse_source)
        self.browse_btn.grid(row=1, column=1, padx=(0, 6))

        self.recent_btn = tk.Button(src_frame, text="⟱ Recent", font=("Courier", 10),
                                    relief="flat", cursor="hand2", padx=12, pady=5,
                                    command=self._show_recent_menu)
        self.recent_btn.grid(row=1, column=2, padx=(0, 6))

        self.scan_btn = tk.Button(src_frame, text="⟳  Scan", font=("Courier", 10),
                                  relief="flat", cursor="hand2", padx=12, pady=5,
                                  command=self._trigger_scan)
        self.scan_btn.grid(row=1, column=3)

        self.src_frame = src_frame

    def _build_left_panel(self, body):
        left = tk.Frame(body, width=240)
        left.grid(row=1, column=0, rowspan=2, sticky="nsew", pady=8, padx=(0, 10))
        left.columnconfigure(0, weight=1)
        left.grid_propagate(False)

        tk.Label(left, text="PRESET", font=("Courier", 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=(8, 4))
        self.preset_menu = ttk.Combobox(left, textvariable=self.preset_name,
                                         values=list(PRESETS.keys()), state="readonly",
                                         font=("Courier", 10), width=26)
        self.preset_menu.grid(row=1, column=0, sticky="ew")
        self.preset_menu.bind("<<ComboboxSelected>>", self._on_preset_change)

        tk.Label(left, text="INCLUDE PATTERNS", font=("Courier", 9, "bold")).grid(
            row=2, column=0, sticky="w", pady=(10, 4))
        self.include_entry = tk.Entry(left, textvariable=self.include_list, font=("Courier", 9))
        self.include_entry.grid(row=3, column=0, sticky="ew")

        tk.Label(left, text="EXCLUDE PATTERNS", font=("Courier", 9, "bold")).grid(
            row=4, column=0, sticky="w", pady=(10, 4))
        self.exclude_entry = tk.Entry(left, textvariable=self.exclude_list, font=("Courier", 9))
        self.exclude_entry.grid(row=5, column=0, sticky="ew")

        opts = tk.Frame(left)
        opts.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        self.gitignore_chk = tk.Checkbutton(opts, text="  Respect .gitignore",
                                             variable=self.use_gitignore,
                                             font=("Courier", 10), cursor="hand2")
        self.gitignore_chk.grid(row=0, column=0, sticky="w")
        self.split_chk = tk.Checkbutton(opts, text="  Split by token limit",
                                         variable=self.split_output,
                                         font=("Courier", 10), cursor="hand2")
        self.split_chk.grid(row=1, column=0, sticky="w")
        self.importance_chk = tk.Checkbutton(opts, text="  Sort by importance",
                                              variable=self.sort_by_importance,
                                              font=("Courier", 10), cursor="hand2",
                                              command=self._refresh_file_list_display)
        self.importance_chk.grid(row=2, column=0, sticky="w")

        tok_frame = tk.Frame(left)
        tok_frame.grid(row=7, column=0, sticky="ew", pady=(8, 0))
        tk.Label(tok_frame, text="Token limit:", font=("Courier", 9)).grid(row=0, column=0, sticky="w")
        self.tokens_entry = tk.Entry(tok_frame, textvariable=self.max_tokens,
                                     font=("Courier", 9), width=10)
        self.tokens_entry.grid(row=0, column=1, padx=(8, 0))

        tk.Label(left, text="OUTPUT FORMAT", font=("Courier", 9, "bold")).grid(
            row=8, column=0, sticky="w", pady=(14, 4))
        fmt_frame = tk.Frame(left)
        fmt_frame.grid(row=9, column=0, sticky="ew")
        self.fmt_radios = []
        for i, fmt in enumerate(OUTPUT_FORMATS):
            rb = tk.Radiobutton(fmt_frame, text=fmt, variable=self.output_format,
                                value=fmt, font=("Courier", 9), cursor="hand2",
                                wraplength=220, justify="left")
            rb.grid(row=i, column=0, sticky="w", pady=1)
            self.fmt_radios.append(rb)

        # ── AI provider section ──
        tk.Label(left, text="AI SUMMARY", font=("Courier", 9, "bold")).grid(
            row=10, column=0, sticky="w", pady=(14, 4))

        prov_frame = tk.Frame(left)
        prov_frame.grid(row=11, column=0, sticky="ew")
        self.prov_radios = []
        for i, prov in enumerate(AI_PROVIDERS):
            rb = tk.Radiobutton(prov_frame, text=prov, variable=self.ai_provider,
                                value=prov, font=("Courier", 9), cursor="hand2",
                                command=self._on_provider_change)
            rb.grid(row=0, column=i, sticky="w", padx=(0, 8))
            self.prov_radios.append(rb)

        self.anthropic_frame = tk.Frame(left)
        self.anthropic_frame.grid(row=12, column=0, sticky="ew", pady=(6, 0))
        self.anthropic_frame.columnconfigure(0, weight=1)
        tk.Label(self.anthropic_frame, text="API Key", font=("Courier", 8)).grid(
            row=0, column=0, sticky="w")
        self.api_entry = tk.Entry(self.anthropic_frame, textvariable=self.api_key,
                                  font=("Courier", 9), show="•")
        self.api_entry.grid(row=1, column=0, sticky="ew")

        self.ollama_frame = tk.Frame(left)
        self.ollama_frame.columnconfigure(0, weight=1)
        tk.Label(self.ollama_frame, text="Ollama URL", font=("Courier", 8)).grid(
            row=0, column=0, sticky="w")
        self.ollama_url_entry = tk.Entry(self.ollama_frame, textvariable=self.ollama_url,
                                         font=("Courier", 9))
        self.ollama_url_entry.grid(row=1, column=0, sticky="ew")

        model_row = tk.Frame(self.ollama_frame)
        model_row.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        model_row.columnconfigure(0, weight=1)
        tk.Label(model_row, text="Model", font=("Courier", 8)).grid(row=0, column=0, sticky="w")
        self.ollama_model_combo = ttk.Combobox(model_row, textvariable=self.ollama_model,
                                               font=("Courier", 9), width=16)
        self.ollama_model_combo.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        self.refresh_models_btn = tk.Button(model_row, text="⟳", font=("Courier", 9),
                                            relief="flat", cursor="hand2", padx=6, pady=2,
                                            command=self._refresh_ollama_models)
        self.refresh_models_btn.grid(row=1, column=1)

        self.anthropic_frame.grid(row=12, column=0, sticky="ew", pady=(6, 0))

        self.ai_btn = tk.Button(left, text="✦  AI Summary", font=("Courier", 10, "bold"),
                                relief="flat", cursor="hand2", padx=10, pady=6,
                                command=self._run_ai_summary)
        self.ai_btn.grid(row=13, column=0, sticky="ew", pady=(6, 0))

        self.left_frame = left
        self.opts_frame = opts

    def _build_centre_panel(self, body):
        centre = tk.Frame(body)
        centre.grid(row=1, column=1, rowspan=2, sticky="nsew", pady=8, padx=(0, 10))
        centre.columnconfigure(0, weight=1)
        centre.rowconfigure(1, weight=1)

        hdr = tk.Frame(centre)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        hdr.columnconfigure(1, weight=1)
        tk.Label(hdr, text="MATCHED FILES", font=("Courier", 9, "bold")).grid(
            row=0, column=0, sticky="w")
        self.filter_entry = tk.Entry(hdr, textvariable=self.file_filter,
                                     font=("Courier", 9), width=20)
        self.filter_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        tk.Label(hdr, text="filter", font=("Courier", 8)).grid(row=0, column=2, padx=(4, 0))

        list_frame = tk.Frame(centre)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.file_list = tk.Listbox(list_frame, selectmode="extended",
                                    font=("Courier", 10), activestyle="none",
                                    bd=0, highlightthickness=1, relief="flat")
        self.file_list.grid(row=0, column=0, sticky="nsew")
        self.file_list.bind("<<ListboxSelect>>", self._on_file_select)

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_list.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.file_list.configure(yscrollcommand=vsb.set)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.file_list.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        self.file_list.configure(xscrollcommand=hsb.set)

        self.ctx_menu = tk.Menu(self.root, tearoff=0)
        self.ctx_menu.add_command(label="Remove from selection", command=self._remove_selected)
        self.file_list.bind("<Button-3>", self._show_ctx_menu)

        self.centre_frame = centre

    def _build_right_panel(self, body):
        right = tk.Frame(body, width=300)
        right.grid(row=1, column=2, rowspan=2, sticky="nsew", pady=8)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(6, weight=1)   # notebook row expands

        # ── Live Stats ──
        tk.Label(right, text="LIVE STATS", font=("Courier", 9, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(8, 4))

        stats_data = [
            ("Files",  self.stat_files,  "accent2"),
            ("Size",   self.stat_size,   "text"),
            ("Lines",  self.stat_lines,  "text_muted"),
            ("Tokens", self.stat_tokens, "warn"),
        ]
        self.stat_labels = {}
        stats_row = tk.Frame(right)
        stats_row.grid(row=1, column=0, columnspan=4, sticky="ew")
        for i, (label, var, ck) in enumerate(stats_data):
            cf = tk.Frame(stats_row)
            cf.grid(row=0, column=i, padx=(0, 14))
            tk.Label(cf, text=label, font=("Courier", 8)).grid(row=0, sticky="w")
            lv = tk.Label(cf, textvariable=var, font=("Courier", 13, "bold"))
            lv.grid(row=1, sticky="w")
            self.stat_labels[ck] = lv

        # ── Token chart ──
        tk.Label(right, text="TOKEN DISTRIBUTION  (top files by size)",
                 font=("Courier", 9, "bold")).grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(12, 4))
        self.chart_canvas = tk.Canvas(right, height=120, bd=0, highlightthickness=0)
        self.chart_canvas.grid(row=3, column=0, columnspan=4, sticky="ew")

        # ── Tabbed right panel (Preview + Tree Manager) ──
        self.right_notebook = ttk.Notebook(right)
        self.right_notebook.grid(row=6, column=0, columnspan=4, sticky="nsew", pady=(8, 0))

        # Tab 1 – File Preview
        preview_tab = tk.Frame(self.right_notebook)
        self.right_notebook.add(preview_tab, text="📄 Preview")
        preview_tab.columnconfigure(0, weight=1)
        preview_tab.rowconfigure(1, weight=1)

        tk.Label(preview_tab, text="FILE PREVIEW", font=("Courier", 9, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(4, 4))

        preview_frame = tk.Frame(preview_tab)
        preview_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        self.preview_text = tk.Text(preview_frame, font=("Courier", 9), wrap="none",
                                    bd=0, relief="flat", state="disabled",
                                    highlightthickness=1, cursor="arrow")
        self.preview_text.grid(row=0, column=0, sticky="nsew")
        pvsb = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview_text.yview)
        pvsb.grid(row=0, column=1, sticky="ns")
        self.preview_text.configure(yscrollcommand=pvsb.set)

        self.preview_label = tk.Label(preview_tab, text="", font=("Courier", 8), anchor="w")
        self.preview_label.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(2, 0))

        # Tab 2 – Tree Manager
        tree_tab = tk.Frame(self.right_notebook)
        self.right_notebook.add(tree_tab, text="🌳 Tree Manager")
        self._build_tree_manager_tab(tree_tab)

        self.right_frame = right

    def _build_tree_manager_tab(self, parent):
        """Build all Tree Manager controls inside the given parent frame."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(3, weight=1)   # editor expands
        parent.rowconfigure(5, weight=1)   # preview expands

        # ── Row 0: toolbar buttons ──
        toolbar = tk.Frame(parent)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(6, 4))

        self.tm_gen_btn = tk.Button(toolbar, text="⟳ From Scan",
                                    font=("Courier", 9), relief="flat", cursor="hand2",
                                    padx=8, pady=4, command=self._tm_generate_from_scan)
        self.tm_gen_btn.grid(row=0, column=0, padx=(0, 4))

        self.tm_build_btn = tk.Button(toolbar, text="⊕ Build",
                                      font=("Courier", 9), relief="flat", cursor="hand2",
                                      padx=8, pady=4, command=self._tm_build_structure)
        self.tm_build_btn.grid(row=0, column=1, padx=(0, 4))

        self.tm_zip_btn = tk.Button(toolbar, text="📦 Zip",
                                    font=("Courier", 9), relief="flat", cursor="hand2",
                                    padx=8, pady=4, command=self._tm_export_zip)
        self.tm_zip_btn.grid(row=0, column=2, padx=(0, 4))

        self.tm_save_btn = tk.Button(toolbar, text="💾 Save",
                                     font=("Courier", 9), relief="flat", cursor="hand2",
                                     padx=8, pady=4, command=self._tm_save_preset)
        self.tm_save_btn.grid(row=0, column=3, padx=(0, 4))

        self.tm_load_btn = tk.Button(toolbar, text="📂 Load",
                                     font=("Courier", 9), relief="flat", cursor="hand2",
                                     padx=8, pady=4, command=self._tm_load_preset_file)
        self.tm_load_btn.grid(row=0, column=4)

        # ── Row 1: preset selector ──
        preset_row = tk.Frame(parent)
        preset_row.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        preset_row.columnconfigure(0, weight=1)

        self.tm_preset_var = tk.StringVar(value="— Select Preset —")
        self.tm_preset_combo = ttk.Combobox(
            preset_row,
            textvariable=self.tm_preset_var,
            values=["— Select Preset —"] + list(TREE_PRESETS.keys()),
            state="readonly",
            font=("Courier", 9),
        )
        self.tm_preset_combo.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.tm_preset_combo.bind("<<ComboboxSelected>>", self._tm_load_preset)

        # ── Row 2: editor label ──
        tk.Label(parent, text="TREE EDITOR", font=("Courier", 9, "bold")).grid(
            row=2, column=0, sticky="w", pady=(4, 2))

        # ── Row 3: tree text editor ──
        editor_frame = tk.Frame(parent)
        editor_frame.grid(row=3, column=0, sticky="nsew")
        editor_frame.columnconfigure(0, weight=1)
        editor_frame.rowconfigure(0, weight=1)

        self.tm_editor = tk.Text(editor_frame, font=("Courier", 9), wrap="none",
                                 bd=0, relief="flat", highlightthickness=1, undo=True)
        self.tm_editor.grid(row=0, column=0, sticky="nsew")
        self.tm_editor.bind("<KeyRelease>", self._tm_update_preview)

        tm_vsb = ttk.Scrollbar(editor_frame, orient="vertical", command=self.tm_editor.yview)
        tm_vsb.grid(row=0, column=1, sticky="ns")
        self.tm_editor.configure(yscrollcommand=tm_vsb.set)
        tm_hsb = ttk.Scrollbar(editor_frame, orient="horizontal", command=self.tm_editor.xview)
        tm_hsb.grid(row=1, column=0, sticky="ew")
        self.tm_editor.configure(xscrollcommand=tm_hsb.set)

        # ── Row 4: preview label ──
        tk.Label(parent, text="LIVE PREVIEW", font=("Courier", 9, "bold")).grid(
            row=4, column=0, sticky="w", pady=(6, 2))

        # ── Row 5: live preview ──
        prev_frame = tk.Frame(parent)
        prev_frame.grid(row=5, column=0, sticky="nsew")
        prev_frame.columnconfigure(0, weight=1)
        prev_frame.rowconfigure(0, weight=1)

        self.tm_preview = tk.Text(prev_frame, font=("Courier", 8), wrap="none",
                                  bd=0, relief="flat", highlightthickness=1,
                                  state="disabled", cursor="arrow")
        self.tm_preview.grid(row=0, column=0, sticky="nsew")
        prev_vsb = ttk.Scrollbar(prev_frame, orient="vertical", command=self.tm_preview.yview)
        prev_vsb.grid(row=0, column=1, sticky="ns")
        self.tm_preview.configure(yscrollcommand=prev_vsb.set)

        # Store refs for theming
        self._tm_toolbar = toolbar
        self._tm_editor_frame = editor_frame
        self._tm_prev_frame = prev_frame
        self._tm_preset_row = preset_row

    def _build_output_row(self, body):
        out_frame = tk.Frame(body)
        out_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        out_frame.columnconfigure(0, weight=1)

        tk.Label(out_frame, text="OUTPUT FILE", font=("Courier", 9, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))
        self.out_entry = tk.Entry(out_frame, textvariable=self.output_file, font=("Courier", 11))
        self.out_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.out_browse_btn = tk.Button(out_frame, text="Browse…", font=("Courier", 10),
                                        relief="flat", cursor="hand2", padx=12, pady=5,
                                        command=self._browse_output)
        self.out_browse_btn.grid(row=1, column=1, padx=(0, 6))
        self.copy_btn = tk.Button(out_frame, text="⎘  Copy to Clipboard", font=("Courier", 10),
                                  relief="flat", cursor="hand2", padx=12, pady=5,
                                  command=self._copy_to_clipboard)
        self.copy_btn.grid(row=1, column=2)

        self.out_frame = out_frame

    def _build_footer(self):
        foot = tk.Frame(self.master, height=54)
        foot.grid(row=2, column=0, sticky="ew")
        foot.columnconfigure(2, weight=1)

        self.transcribe_btn = tk.Button(foot, text="▶  TRANSCRIBE",
                                        font=("Courier", 13, "bold"),
                                        relief="flat", cursor="hand2",
                                        padx=24, pady=10,
                                        command=self._start_transcribe)
        self.transcribe_btn.grid(row=0, column=0, padx=18, pady=8)

        self.progress = ttk.Progressbar(foot, mode="determinate", length=200)
        self.progress.grid(row=0, column=1, padx=(0, 12), sticky="w")

        self.status_lbl = tk.Label(foot, textvariable=self.status_text,
                                   font=("Courier", 10), anchor="w")
        self.status_lbl.grid(row=0, column=2, sticky="ew", padx=(0, 18))

        self.foot_frame = foot

    # ══ THEME ═════════════════════════════════

    def _apply_theme(self):
        T = THEMES[self.theme_name.get()]
        self.T = T

        for w in [self.root, self.master, self.hdr_frame, self.body_frame,
                  self.left_frame, self.centre_frame, self.right_frame,
                  self.foot_frame, self.src_frame, self.out_frame, self.opts_frame]:
            try:
                w.configure(bg=T["bg"])
            except Exception:
                pass

        for child in self.hdr_frame.winfo_children():
            try:
                if isinstance(child, tk.Label):
                    child.configure(bg=T["bg"], fg=T["text_muted"])
                elif isinstance(child, tk.Button):
                    child.configure(bg=T["button_bg"], fg=T["warn"],
                                    activebackground=T["button_hover"])
            except Exception:
                pass
        self.logo_lbl.configure(fg=T["accent"])
        self.sub_lbl.configure(fg=T["text"])

        self._theme_deep(self.left_frame, T)
        self._theme_deep(self.centre_frame, T)
        self._theme_deep(self.right_frame, T)
        self._theme_deep(self.src_frame, T)
        self._theme_deep(self.out_frame, T)

        color_map = {"accent2": T["accent2"], "text": T["text"],
                     "text_muted": T["text_muted"], "warn": T["warn"]}
        for key, lbl in self.stat_labels.items():
            lbl.configure(fg=color_map.get(key, T["text"]))

        self.file_list.configure(
            bg=T["surface"], fg=T["text"],
            selectbackground=T["tree_select"], selectforeground=T["text"],
            highlightcolor=T["border"], highlightbackground=T["border"])

        self.preview_text.configure(
            bg=T["preview_bg"], fg=T["text"],
            selectbackground=T["tree_select"],
            insertbackground=T["accent"],
            highlightbackground=T["border"],
            highlightcolor=T["accent"])

        # Tree Manager widgets
        self.tm_editor.configure(
            bg=T["surface"], fg=T["text"],
            selectbackground=T["tree_select"],
            insertbackground=T["accent"],
            highlightbackground=T["border"],
            highlightcolor=T["accent"])
        self.tm_preview.configure(
            bg=T["preview_bg"], fg=T["text_muted"],
            highlightbackground=T["border"],
            highlightcolor=T["border"])

        # TM toolbar buttons
        tm_btn_colors = {
            self.tm_gen_btn:   T["accent2"],
            self.tm_build_btn: T["accent"],
            self.tm_zip_btn:   T["warn"],
            self.tm_save_btn:  T["text_muted"],
            self.tm_load_btn:  T["text_muted"],
        }
        for btn, fg in tm_btn_colors.items():
            btn.configure(bg=T["button_bg"], fg=fg, activebackground=T["button_hover"])
        self._tm_toolbar.configure(bg=T["bg"])
        self._tm_preset_row.configure(bg=T["bg"])

        self.chart_canvas.configure(bg=T["bg"])
        self._redraw_chart()

        for entry in [self.src_entry, self.include_entry, self.exclude_entry,
                      self.out_entry, self.tokens_entry, self.filter_entry, self.api_entry]:
            try:
                entry.configure(bg=T["surface2"], fg=T["text"],
                                insertbackground=T["accent"], relief="flat", bd=4,
                                highlightthickness=1,
                                highlightbackground=T["border"],
                                highlightcolor=T["accent"])
            except Exception:
                pass

        self.browse_btn.configure(bg=T["button_bg"], fg=T["text"], activebackground=T["button_hover"])
        self.recent_btn.configure(bg=T["button_bg"], fg=T["text_muted"], activebackground=T["button_hover"])
        self.scan_btn.configure(bg=T["button_bg"], fg=T["accent2"], activebackground=T["button_hover"])
        self.out_browse_btn.configure(bg=T["button_bg"], fg=T["text"], activebackground=T["button_hover"])
        self.copy_btn.configure(bg=T["button_bg"], fg=T["accent"], activebackground=T["button_hover"])
        self.theme_btn.configure(bg=T["button_bg"], fg=T["warn"], activebackground=T["button_hover"])
        self.ai_btn.configure(bg=T["purple"], fg=T["bg"],
                              activebackground=T["purple"], activeforeground=T["bg"])
        for rb in self.prov_radios:
            rb.configure(bg=T["bg"], fg=T["text"], selectcolor=T["surface2"],
                         activebackground=T["bg"], activeforeground=T["accent"])
        self._theme_deep(self.anthropic_frame, T)
        self._theme_deep(self.ollama_frame, T)
        try:
            self.refresh_models_btn.configure(
                bg=T["button_bg"], fg=T["text_muted"],
                activebackground=T["button_hover"])
        except Exception:
            pass
        self.transcribe_btn.configure(bg=T["accent"], fg=T["bg"],
                                      activebackground=T["accent"], activeforeground=T["bg"])

        self.foot_frame.configure(bg=T["surface"])
        self.status_lbl.configure(bg=T["surface"], fg=T["text_muted"])
        self.preview_label.configure(bg=T["bg"], fg=T["text_dim"])

        for rb in self.fmt_radios:
            rb.configure(bg=T["bg"], fg=T["text"], selectcolor=T["surface2"],
                         activebackground=T["bg"], activeforeground=T["accent"])
        self.ctx_menu.configure(bg=T["surface2"], fg=T["text"])

        style = ttk.Style()
        style.theme_use("default")
        style.configure("TScrollbar", background=T["surface2"], troughcolor=T["bg"],
                        borderwidth=0, relief="flat")
        style.configure("TCombobox", fieldbackground=T["surface2"], background=T["surface2"],
                        foreground=T["text"], selectbackground=T["tree_select"])
        style.configure("TProgressbar", background=T["accent"], troughcolor=T["surface2"])

    def _theme_deep(self, w, T):
        try:
            if isinstance(w, tk.Frame):
                w.configure(bg=T["bg"])
            elif isinstance(w, tk.Label):
                w.configure(bg=T["bg"], fg=T["text_muted"])
            elif isinstance(w, tk.Button):
                w.configure(bg=T["button_bg"], fg=T["text"], activebackground=T["button_hover"])
            elif isinstance(w, tk.Checkbutton):
                w.configure(bg=T["bg"], fg=T["text"], selectcolor=T["surface2"],
                            activebackground=T["bg"], activeforeground=T["accent"])
            elif isinstance(w, tk.Entry):
                w.configure(bg=T["surface2"], fg=T["text"],
                            insertbackground=T["accent"], relief="flat",
                            highlightthickness=1,
                            highlightbackground=T["border"],
                            highlightcolor=T["accent"])
        except Exception:
            pass
        try:
            for child in w.winfo_children():
                self._theme_deep(child, T)
        except Exception:
            pass

    def _toggle_theme(self):
        if self.theme_name.get() == "dark":
            self.theme_name.set("light")
            self.theme_btn.configure(text="☾  Dark")
        else:
            self.theme_name.set("dark")
            self.theme_btn.configure(text="☀  Light")
        self._apply_theme()

    # ══ EVENTS ════════════════════════════════

    def _bind_events(self):
        self.source_folder.trace_add("write", lambda *_: self._on_folder_change())
        self.include_list.trace_add("write",  lambda *_: self._debounce_scan())
        self.exclude_list.trace_add("write",  lambda *_: self._debounce_scan())
        self.use_gitignore.trace_add("write", lambda *_: self._debounce_scan())
        self.file_filter.trace_add("write",   lambda *_: self._refresh_file_list_display())
        self.root.bind("<Control-s>", lambda _: self._trigger_scan())
        self.root.bind("<Control-t>", lambda _: self._start_transcribe())
        self.root.bind("<Control-S>", lambda _: self._trigger_scan())
        self.root.bind("<Control-T>", lambda _: self._start_transcribe())
        self.root.bind("<Control-C>", lambda _: self._copy_to_clipboard())

    def _on_folder_change(self):
        folder = self.source_folder.get()
        if folder and os.path.isdir(folder):
            self._trigger_scan()

    def _debounce_scan(self, delay=600):
        if self._debounce_id:
            self.root.after_cancel(self._debounce_id)
        self._debounce_id = self.root.after(delay, self._trigger_scan)

    def _on_preset_change(self, *_):
        name = self.preset_name.get()
        p = PRESETS.get(name, {})
        self.include_list.set(p.get("include", ""))
        self.exclude_list.set(p.get("exclude", ""))
        self._trigger_scan()

    def _on_file_select(self, event=None):
        sel = self.file_list.curselection()
        if not sel:
            return
        displayed = self._get_displayed_files()
        idx = sel[0]
        if idx < len(displayed):
            self._load_preview(displayed[idx])

    def _load_preview(self, file_path):
        root_folder = self.source_folder.get()
        rel  = os.path.relpath(file_path, root_folder)
        size = os.path.getsize(file_path)
        content, err = read_file_safe(file_path)

        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", tk.END)
        if err:
            self.preview_text.insert(tk.END, f"[Error: {err}]")
        else:
            lines = content.split("\n")
            preview = "\n".join(lines[:400])
            if len(lines) > 400:
                preview += f"\n\n… ({len(lines) - 400} more lines)"
            self.preview_text.insert(tk.END, preview)
        self.preview_text.configure(state="disabled")

        tokens = estimate_tokens(content)
        self.preview_label.configure(
            text=f"{rel}  ·  {format_size(size)}  ·  ~{format_number(tokens)} tokens")

    # ══ RECENT FOLDERS ════════════════════════

    def _show_recent_menu(self):
        menu = tk.Menu(self.root, tearoff=0)
        T = self.T
        menu.configure(bg=T["surface2"], fg=T["text"])
        if not self._recent_folders:
            menu.add_command(label="No recent folders", state="disabled")
        else:
            for folder in self._recent_folders:
                label = folder if len(folder) <= 60 else "…" + folder[-57:]
                menu.add_command(label=label, command=lambda f=folder: self.source_folder.set(f))
        menu.add_separator()
        menu.add_command(label="Clear history", command=self._clear_recent)
        x = self.recent_btn.winfo_rootx()
        y = self.recent_btn.winfo_rooty() + self.recent_btn.winfo_height()
        menu.tk_popup(x, y)

    def _clear_recent(self):
        self._recent_folders = []
        save_recent_folders([])

    # ══ FILE LIST DISPLAY ═════════════════════

    def _get_displayed_files(self):
        files      = list(self._files_cache)
        flt        = self.file_filter.get().strip().lower()
        root_folder = self.source_folder.get()
        if flt:
            files = [f for f in files if flt in os.path.relpath(f, root_folder).lower()]
        if self.sort_by_importance.get():
            files.sort(key=score_file_importance, reverse=True)
        else:
            files.sort()
        return files

    def _refresh_file_list_display(self):
        displayed   = self._get_displayed_files()
        root_folder = self.source_folder.get()
        self.file_list.delete(0, tk.END)
        for f in displayed:
            rel   = os.path.relpath(f, root_folder)
            star  = "★ " if score_file_importance(f) >= 80 else ""
            self.file_list.insert(tk.END, f"{star}{rel}")

    # ══ CHART ═════════════════════════════════

    def _redraw_chart(self):
        c     = self.chart_canvas
        T     = self.T
        c.delete("all")
        files = self._files_cache
        if not files:
            c.create_text(10, 50, text="No files scanned yet",
                          fill=T["text_dim"], font=("Courier", 9), anchor="w")
            return

        sized = [(f, os.path.getsize(f)) for f in files if os.path.exists(f)]
        sized.sort(key=lambda x: x[1], reverse=True)
        top   = sized[:12]
        max_sz = max(s for _, s in top) if top else 1

        c.update_idletasks()
        w      = max(c.winfo_width(), 280)
        bar_h  = 12
        pad_l  = 4
        pad_r  = 8
        gap    = 2
        bar_w  = w - pad_l - pad_r

        for i, (fp, sz) in enumerate(top):
            y1     = i * (bar_h + gap)
            y2     = y1 + bar_h
            fill_w = int(bar_w * sz / max_sz)
            c.create_rectangle(pad_l, y1, pad_l + bar_w, y2, fill=T["bar_bg"], outline="")
            c.create_rectangle(pad_l, y1, pad_l + fill_w, y2, fill=T["bar_fill"], outline="")
            name   = os.path.basename(fp)
            if len(name) > 30:
                name = name[:27] + "…"
            c.create_text(pad_l + 4, y1 + bar_h // 2, text=name,
                          fill=T["text"], font=("Courier", 7), anchor="w")

        c.configure(height=len(top) * (bar_h + gap))

    # ══ SCANNING ══════════════════════════════

    def _trigger_scan(self):
        folder = self.source_folder.get()
        if not folder or not os.path.isdir(folder):
            return
        if self._scanning:
            return
        self._scanning = True
        self.status_text.set("Scanning…")
        self.progress.configure(mode="indeterminate")
        self.progress.start(10)
        self._start_pulse()
        self.scan_btn.configure(state="disabled")
        threading.Thread(target=self._scan_worker, args=(folder,), daemon=True).start()

    def _scan_worker(self, folder):
        try:
            inc   = [p.strip() for p in self.include_list.get().split(",") if p.strip()]
            exc   = [p.strip() for p in self.exclude_list.get().split(",") if p.strip()]
            gi    = load_gitignore_patterns(folder) if self.use_gitignore.get() else []
            files = collect_files(folder, inc, exc, gi)
            self.root.after(0, self._scan_done, files)
        except Exception as e:
            self.root.after(0, self._scan_error, str(e))

    def _scan_done(self, files):
        self._scanning = False
        self._files_cache = files
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress["value"] = 0
        self.scan_btn.configure(state="normal")
        self._stop_pulse()

        folder = self.source_folder.get()
        self._recent_folders = push_recent_folder(folder, self._recent_folders)
        save_recent_folders(self._recent_folders)

        self._refresh_file_list_display()
        self._update_stats_from_cache()
        self._redraw_chart()
        self.status_text.set(f"Found {len(files)} files. Ready to transcribe.")

    def _scan_error(self, msg):
        self._scanning = False
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.scan_btn.configure(state="normal")
        self._stop_pulse()
        self.status_text.set(f"Scan error: {msg}")

    def _update_stats_from_cache(self):
        files = self._files_cache
        if not files:
            for v in [self.stat_files, self.stat_lines, self.stat_size, self.stat_tokens]:
                v.set("—")
            return
        self.stat_files.set(format_number(len(files)))
        total_size = sum(os.path.getsize(f) for f in files if os.path.exists(f))
        self.stat_size.set(format_size(total_size))
        self.stat_lines.set(f"~{format_number(total_size // 40)}")
        self.stat_tokens.set(f"~{format_number(total_size // 4)}")

    # ── Pulse animation ───────────────────────

    def _start_pulse(self):
        self._pulse_state = 0
        self._animate_pulse()

    def _animate_pulse(self):
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        f = frames[self._pulse_state % len(frames)]
        self.status_text.set(f"{f}  Working…")
        self._pulse_state += 1
        self._pulse_id = self.root.after(80, self._animate_pulse)

    def _stop_pulse(self):
        if self._pulse_id:
            self.root.after_cancel(self._pulse_id)
            self._pulse_id = None

    # ══ BROWSE ════════════════════════════════

    def _browse_source(self):
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.source_folder.set(folder)

    def _browse_output(self):
        fmt     = self.output_format.get()
        ext_map = {"Plain Text": ".txt", "Markdown": ".md",
                   "XML": ".xml", "✨ Copy for Claude": ".xml"}
        ext  = ext_map.get(fmt, ".txt")
        path = filedialog.asksaveasfilename(
            title="Choose Output File",
            defaultextension=ext,
            filetypes=[("All files", "*.*"), (fmt, f"*{ext}")],
        )
        if path:
            self.output_file.set(path)

    # ══ CONTEXT MENU ══════════════════════════

    def _show_ctx_menu(self, event):
        try:
            self.ctx_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.ctx_menu.grab_release()

    def _remove_selected(self):
        sel        = sorted(self.file_list.curselection(), reverse=True)
        displayed  = self._get_displayed_files()
        to_remove  = {displayed[i] for i in sel if i < len(displayed)}
        self._files_cache = [f for f in self._files_cache if f not in to_remove]
        self._refresh_file_list_display()
        self._update_stats_from_cache()
        self._redraw_chart()

    # ══ TRANSCRIBE ════════════════════════════

    def _build_content(self, files, root_folder):
        tree = build_file_tree(files, root_folder)
        fmt  = self.output_format.get()
        if fmt == "Markdown":
            return format_output_markdown(files, root_folder, tree)
        elif fmt == "XML":
            return format_output_xml(files, root_folder, tree)
        elif fmt == "✨ Copy for Claude":
            return format_output_for_claude(files, root_folder, tree)
        else:
            return format_output_plain(files, root_folder, tree)

    def _start_transcribe(self):
        files  = self._files_cache
        output = self.output_file.get()
        if not files:
            messagebox.showwarning("No Files", "No files found. Select a folder and scan first.")
            return
        if not output:
            messagebox.showwarning("No Output", "Please specify an output file.")
            return
        self.transcribe_btn.configure(state="disabled")
        self.progress.configure(mode="determinate", maximum=len(files))
        self.progress["value"] = 0
        self._start_pulse()
        threading.Thread(target=self._transcribe_worker,
                         args=(list(files), output), daemon=True).start()

    def _transcribe_worker(self, files, output_path):
        try:
            root_folder = self.source_folder.get()
            do_split    = self.split_output.get()
            max_tok     = int(self.max_tokens.get()) if self.max_tokens.get().isdigit() else 100000
            max_chars   = max_tok * 4

            content = self._build_content(files, root_folder)
            self.root.after(0, lambda: self.progress.configure(value=len(files)))

            if do_split and len(content) > max_chars:
                self._write_split(content, output_path, max_chars)
            else:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)

            n_tokens = estimate_tokens(content)
            self.root.after(0, self._transcribe_done, output_path, n_tokens)
        except Exception as e:
            self.root.after(0, self._transcribe_error, str(e))

    def _write_split(self, content, base_path, max_chars):
        stem, ext        = os.path.splitext(base_path)
        chunk, part, cl  = [], 1, 0
        for line in content.splitlines(keepends=True):
            if cl + len(line) > max_chars and chunk:
                with open(f"{stem}_part{part}{ext}", "w", encoding="utf-8") as f:
                    f.writelines(chunk)
                chunk, cl, part = [], 0, part + 1
            chunk.append(line)
            cl += len(line)
        if chunk:
            with open(f"{stem}_part{part}{ext}", "w", encoding="utf-8") as f:
                f.writelines(chunk)

    def _transcribe_done(self, output_path, n_tokens):
        self.transcribe_btn.configure(state="normal")
        self._stop_pulse()
        self.status_text.set(f"Done! ✓  {format_number(n_tokens)} tokens written.")
        self.progress["value"] = self.progress["maximum"]
        messagebox.showinfo("Transcription Complete",
                            f"Saved to:\n{output_path}\n\nEstimated tokens: {format_number(n_tokens)}")

    def _transcribe_error(self, msg):
        self.transcribe_btn.configure(state="normal")
        self._stop_pulse()
        self.status_text.set(f"Error: {msg}")
        messagebox.showerror("Error", f"Transcription failed:\n{msg}")

    # ══ CLIPBOARD ═════════════════════════════

    def _copy_to_clipboard(self):
        files = self._files_cache
        if not files:
            messagebox.showwarning("Nothing to Copy", "Scan a folder first.")
            return
        self.status_text.set("Building clipboard content…")
        self.root.update()
        try:
            content = self._build_content(files, self.source_folder.get())
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            n_tokens = estimate_tokens(content)
            self.status_text.set(f"Copied! ✓  ~{format_number(n_tokens)} tokens in clipboard.")
        except Exception as e:
            self.status_text.set(f"Clipboard error: {e}")

    # ══ AI SUMMARY ════════════════════════════

    def _on_provider_change(self):
        prov = self.ai_provider.get()
        if prov == "Ollama (local)":
            self.anthropic_frame.grid_remove()
            self.ollama_frame.grid(row=12, column=0, sticky="ew", pady=(6, 0))
            self._refresh_ollama_models()
        else:
            self.ollama_frame.grid_remove()
            self.anthropic_frame.grid(row=12, column=0, sticky="ew", pady=(6, 0))

    def _refresh_ollama_models(self):
        url    = self.ollama_url.get().strip() or DEFAULT_OLLAMA_URL
        models = fetch_ollama_models(url)
        if models:
            self.ollama_model_combo["values"] = models
            if self.ollama_model.get() not in models:
                self.ollama_model.set(models[0])
            self.status_text.set(f"Ollama: found {len(models)} model(s).")
        else:
            self.ollama_model_combo["values"] = []
            self.status_text.set("Ollama: no models found — is Ollama running?")

    def _run_ai_summary(self):
        files = self._files_cache
        if not files:
            messagebox.showwarning("No Files", "Scan a folder first.")
            return

        prov = self.ai_provider.get()

        if prov == "Anthropic (Claude)":
            key = self.api_key.get().strip() or os.environ.get("ANTHROPIC_API_KEY", "")
            if not key:
                messagebox.showwarning("API Key Required",
                                       "Enter your Anthropic API key in the left panel,\n"
                                       "or set the ANTHROPIC_API_KEY environment variable.")
                return
            kwargs = {"provider": "anthropic", "api_key": key}
        else:
            url   = self.ollama_url.get().strip() or DEFAULT_OLLAMA_URL
            model = self.ollama_model.get().strip() or DEFAULT_OLLAMA_MODEL
            kwargs = {"provider": "ollama", "ollama_url": url, "ollama_model": model}

        self.ai_btn.configure(state="disabled", text="✦  Thinking…")
        self._start_pulse()
        threading.Thread(target=self._ai_summary_worker,
                         args=(list(files), self.source_folder.get()),
                         kwargs=kwargs,
                         daemon=True).start()

    def _ai_summary_worker(self, files, root_folder, provider="anthropic",
                            api_key="", ollama_url="", ollama_model=""):
        try:
            prompt = build_summary_prompt(files, root_folder)
            if provider == "anthropic":
                summary = call_anthropic_api(prompt, api_key)
            else:
                summary = call_ollama_api(prompt,
                                          ollama_url or DEFAULT_OLLAMA_URL,
                                          ollama_model or DEFAULT_OLLAMA_MODEL)
            self.root.after(0, self._ai_summary_done, summary)
        except Exception as e:
            self.root.after(0, self._ai_summary_error, str(e))

    def _ai_summary_done(self, summary):
        self.ai_btn.configure(state="normal", text="✦  AI Summary")
        self._stop_pulse()
        prov = self.ai_provider.get()
        self.status_text.set(f"AI summary complete  ({prov}).")

        win = tk.Toplevel(self.root)
        win.title("✦ AI Codebase Summary")
        win.geometry("640x360")
        win.resizable(True, True)
        T = self.T
        win.configure(bg=T["bg"])

        tk.Label(win, text="✦  AI Codebase Summary",
                 font=("Courier", 13, "bold"),
                 bg=T["bg"], fg=T["purple"]).pack(padx=20, pady=(16, 8), anchor="w")

        txt = tk.Text(win, font=("Courier", 10), wrap="word",
                      bg=T["surface"], fg=T["text"], bd=0,
                      highlightthickness=1, highlightbackground=T["border"],
                      padx=12, pady=10, relief="flat")
        txt.pack(fill="both", expand=True, padx=20, pady=(0, 8))
        txt.insert(tk.END, summary)
        txt.configure(state="disabled")

        btn_frame = tk.Frame(win, bg=T["bg"])
        btn_frame.pack(fill="x", padx=20, pady=(0, 16))

        def _copy():
            self.root.clipboard_clear()
            self.root.clipboard_append(summary)

        tk.Button(btn_frame, text="⎘ Copy", font=("Courier", 10), relief="flat",
                  cursor="hand2", bg=T["button_bg"], fg=T["accent"],
                  padx=14, pady=6, command=_copy).pack(side="left")
        tk.Button(btn_frame, text="Close", font=("Courier", 10), relief="flat",
                  cursor="hand2", bg=T["button_bg"], fg=T["text_muted"],
                  padx=14, pady=6, command=win.destroy).pack(side="left", padx=(8, 0))

    def _ai_summary_error(self, msg):
        self.ai_btn.configure(state="normal", text="✦  AI Summary")
        self._stop_pulse()
        self.status_text.set(f"AI error: {msg}")
        messagebox.showerror("AI Summary Failed",
                             f"The AI request failed:\n\n{msg}\n\n"
                             f"For Ollama: ensure it's running at the configured URL\n"
                             f"and the model name is correct.")

    # ══ TREE MANAGER ══════════════════════════

    def _tm_generate_from_scan(self):
        """Populate the tree editor from the current file scan."""
        if not self._files_cache:
            messagebox.showwarning("No Files", "Scan a folder first.")
            return
        root_folder = self.source_folder.get()
        if not root_folder:
            messagebox.showwarning("No Folder", "No source folder selected.")
            return
        tree_text = build_file_tree_ascii(self._files_cache, root_folder)
        self.tm_editor.delete("1.0", tk.END)
        self.tm_editor.insert(tk.END, tree_text)
        self._tm_update_preview()
        # Switch to Tree Manager tab
        self.right_notebook.select(1)
        self.status_text.set(f"Tree generated from {len(self._files_cache)} scanned files.")

    def _tm_update_preview(self, event=None):
        """Refresh the live preview pane from the editor text."""
        try:
            raw = self.tm_editor.get("1.0", tk.END)
            paths = parse_tree_text(raw)
            self.tm_preview.configure(state="normal")
            self.tm_preview.delete("1.0", tk.END)
            for path, is_dir in paths:
                tag = "[DIR] " if is_dir else "[FILE]"
                self.tm_preview.insert(tk.END, f"{tag} {path}\n")
            self.tm_preview.configure(state="disabled")
        except Exception:
            self.tm_preview.configure(state="normal")
            self.tm_preview.delete("1.0", tk.END)
            self.tm_preview.insert(tk.END, "⚠️ Invalid tree format")
            self.tm_preview.configure(state="disabled")

    def _tm_build_structure(self):
        """Create the folder/file structure on disk from the tree editor."""
        tree_text = self.tm_editor.get("1.0", tk.END)
        if not tree_text.strip():
            messagebox.showwarning("Input Needed", "Tree editor is empty.")
            return
        dest_dir = filedialog.askdirectory(title="Choose Destination Folder")
        if not dest_dir:
            return
        try:
            paths = parse_tree_text(tree_text)
            created_dirs, created_files = 0, 0
            for path, is_dir in paths:
                full_path = os.path.join(dest_dir, path)
                if is_dir:
                    os.makedirs(full_path, exist_ok=True)
                    created_dirs += 1
                else:
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    ext = os.path.splitext(full_path)[1]
                    content = FILE_TEMPLATES.get(ext, "")
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    created_files += 1
            messagebox.showinfo(
                "🎉 Structure Created",
                f"Built in:\n{dest_dir}\n\n"
                f"{created_dirs} director{'ies' if created_dirs != 1 else 'y'}, "
                f"{created_files} file{'s' if created_files != 1 else ''} created."
            )
            self.status_text.set(f"Tree built: {created_dirs} dirs, {created_files} files.")
        except Exception as e:
            messagebox.showerror("Build Failed", str(e))
            self.status_text.set(f"Build error: {e}")

    def _tm_export_zip(self):
        """Export the tree structure as a .zip scaffold."""
        tree_text = self.tm_editor.get("1.0", tk.END)
        if not tree_text.strip():
            messagebox.showwarning("Input Needed", "Tree editor is empty.")
            return
        zip_path = filedialog.asksaveasfilename(
            title="Save Zip Scaffold",
            defaultextension=".zip",
            filetypes=[("Zip files", "*.zip"), ("All files", "*.*")],
        )
        if not zip_path:
            return
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                paths = parse_tree_text(tree_text)
                for path, is_dir in paths:
                    full_path = os.path.join(temp_dir, path)
                    if is_dir:
                        os.makedirs(full_path, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(full_path), exist_ok=True)
                        ext = os.path.splitext(full_path)[1]
                        content = FILE_TEMPLATES.get(ext, "")
                        with open(full_path, "w", encoding="utf-8") as f:
                            f.write(content)
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for root_dir, _, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root_dir, file)
                            arcname = os.path.relpath(file_path, start=temp_dir)
                            zipf.write(file_path, arcname)
            messagebox.showinfo("📦 Exported", f"Scaffold zipped to:\n{zip_path}")
            self.status_text.set(f"Zip exported: {os.path.basename(zip_path)}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))
            self.status_text.set(f"Zip error: {e}")

    def _tm_save_preset(self):
        """Save tree editor contents to a .tree file."""
        content = self.tm_editor.get("1.0", tk.END)
        if not content.strip():
            messagebox.showwarning("Nothing to Save", "Tree editor is empty.")
            return
        file_path = filedialog.asksaveasfilename(
            title="Save Tree Preset",
            defaultextension=".tree",
            filetypes=[("Tree files", "*.tree"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.status_text.set(f"Preset saved: {os.path.basename(file_path)}")

    def _tm_load_preset_file(self):
        """Load a .tree file into the editor."""
        file_path = filedialog.askopenfilename(
            title="Load Tree Preset",
            filetypes=[("Tree files", "*.tree"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.tm_editor.delete("1.0", tk.END)
            self.tm_editor.insert(tk.END, content)
            self._tm_update_preview()
            self.status_text.set(f"Preset loaded: {os.path.basename(file_path)}")

    def _tm_load_preset(self, event=None):
        """Load a built-in tree structure preset into the editor."""
        name = self.tm_preset_var.get()
        tree_text = TREE_PRESETS.get(name)
        if not tree_text:
            return
        self.tm_editor.delete("1.0", tk.END)
        self.tm_editor.insert(tk.END, tree_text)
        self._tm_update_preview()
        # Reset combo label so user can re-select same preset if they want
        self.tm_preset_var.set("— Select Preset —")
        self.status_text.set(f"Loaded preset: {name}")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def main():
    root = tk.Tk()
    root.resizable(True, True)
    try:
        root.tk.call("tk", "scaling", 1.2)
    except Exception:
        pass
    FileTranscriberApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
