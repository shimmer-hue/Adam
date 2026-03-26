#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/utility/context_compilation.sh [options]

Build a shareable markdown bundle of the codebase for external review or tooling.

Default includes:
  - AGENTS.md, README.md, pyproject.toml, .gitignore
  - docs/, eden/, tests/, scripts/, examples/

Default excludes:
  - .git, .venv, data, assets, exports, tmp
  - __pycache__, .pytest_cache, *.pyc, .DS_Store

Options:
  --output PATH           Write the bundle to a specific file.
  --full                  Walk the whole repo instead of the default include set.
  --include-diff          Append the current git diff.
  --max-file-bytes BYTES  Per-file inclusion cap before truncation. Default: 200000.
  --print-path            Print only the output path after generation.
  -h, --help              Show this help text.
EOF
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"

output_path=""
full_mode=0
include_diff=0
max_file_bytes=200000
print_path=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      [[ $# -ge 2 ]] || { echo "Missing value for --output" >&2; exit 1; }
      output_path="$2"
      shift 2
      ;;
    --full)
      full_mode=1
      shift
      ;;
    --include-diff)
      include_diff=1
      shift
      ;;
    --max-file-bytes)
      [[ $# -ge 2 ]] || { echo "Missing value for --max-file-bytes" >&2; exit 1; }
      max_file_bytes="$2"
      shift 2
      ;;
    --print-path)
      print_path=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$max_file_bytes" in
  ''|*[!0-9]*)
    echo "--max-file-bytes must be a positive integer." >&2
    exit 1
    ;;
esac

timestamp="$(date +%Y%m%d_%H%M%S)"
if [[ -z "$output_path" ]]; then
  output_path="${repo_root}/exports/context/adam_codebase_context_${timestamp}.md"
elif [[ "$output_path" != /* ]]; then
  output_path="${repo_root}/${output_path}"
fi

output_dir="$(dirname -- "$output_path")"
mkdir -p "$output_dir"

python_bin=""
for candidate in \
  "${repo_root}/.venv/bin/python3.12" \
  "${repo_root}/.venv/bin/python" \
  "$(command -v python3.12 2>/dev/null || true)" \
  "$(command -v python3 2>/dev/null || true)"; do
  if [[ -n "${candidate}" && -x "${candidate}" ]]; then
    python_bin="${candidate}"
    break
  fi
done

if [[ -z "$python_bin" ]]; then
  echo "No usable Python interpreter found." >&2
  exit 1
fi

REPO_ROOT="$repo_root" \
OUTPUT_PATH="$output_path" \
FULL_MODE="$full_mode" \
INCLUDE_DIFF="$include_diff" \
MAX_FILE_BYTES="$max_file_bytes" \
"$python_bin" - <<'PY'
from __future__ import annotations

import os
import subprocess
from collections import Counter
from pathlib import Path

repo_root = Path(os.environ["REPO_ROOT"]).resolve()
output_path = Path(os.environ["OUTPUT_PATH"]).resolve()
full_mode = os.environ["FULL_MODE"] == "1"
include_diff = os.environ["INCLUDE_DIFF"] == "1"
max_file_bytes = int(os.environ["MAX_FILE_BYTES"])

default_roots = ["eden", "tests", "docs", "scripts", "examples"]
default_root_files = ["AGENTS.md", "README.md", "pyproject.toml", ".gitignore"]
excluded_dirs = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "assets",
    "data",
    "exports",
    "tmp",
    "eden_adam.egg-info",
}
allowed_suffixes = {
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".rst",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
allowed_names = {
    ".gitignore",
    "AGENTS.md",
    "Dockerfile",
    "Makefile",
    "README.md",
}
priority = {
    Path("AGENTS.md"): 0,
    Path("README.md"): 1,
    Path("pyproject.toml"): 2,
    Path(".gitignore"): 3,
    Path("docs/IMPLEMENTATION_TRUTH_TABLE.md"): 4,
    Path("docs/KNOWN_LIMITATIONS.md"): 5,
}


def run_git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        return f"(unavailable: {' '.join(args)}: {exc})"
    return result.stdout.strip()


def is_excluded(path: Path) -> bool:
    rel = path.relative_to(repo_root)
    return any(part in excluded_dirs for part in rel.parts[:-1])


def is_text_candidate(path: Path) -> bool:
    if path.name == ".DS_Store" or path.suffix == ".pyc":
        return False
    if path.name in allowed_names:
        return True
    if path.suffix.lower() in allowed_suffixes:
        return True
    return False


def candidate_paths() -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()

    def add_path(path: Path) -> None:
        if not path.exists() or path.is_dir():
            return
        if path in seen:
            return
        if is_excluded(path):
            return
        if is_text_candidate(path):
            seen.add(path)
            paths.append(path)

    if full_mode:
        for current_root, dirnames, filenames in os.walk(repo_root):
            current = Path(current_root)
            dirnames[:] = sorted(
                name for name in dirnames if name not in excluded_dirs and name != ".git"
            )
            for filename in sorted(filenames):
                add_path(current / filename)
    else:
        for name in default_root_files:
            add_path(repo_root / name)
        for name in default_roots:
            current_root = repo_root / name
            if not current_root.exists():
                continue
            for walk_root, dirnames, filenames in os.walk(current_root):
                current = Path(walk_root)
                dirnames[:] = sorted(name for name in dirnames if name not in excluded_dirs)
                for filename in sorted(filenames):
                    add_path(current / filename)

    return sorted(
        paths,
        key=lambda path: (
            priority.get(path.relative_to(repo_root), 100),
            path.relative_to(repo_root).as_posix(),
        ),
    )


def language_for(path: Path) -> str:
    suffix_map = {
        ".css": "css",
        ".csv": "csv",
        ".html": "html",
        ".ini": "ini",
        ".js": "javascript",
        ".json": "json",
        ".md": "markdown",
        ".py": "python",
        ".rst": "rst",
        ".sh": "bash",
        ".sql": "sql",
        ".toml": "toml",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".txt": "text",
        ".yaml": "yaml",
        ".yml": "yaml",
    }
    if path.name == "Dockerfile":
        return "dockerfile"
    if path.name == "Makefile":
        return "makefile"
    return suffix_map.get(path.suffix.lower(), "text")


def read_file(path: Path) -> tuple[str, bool]:
    raw = path.read_bytes()
    truncated = len(raw) > max_file_bytes
    if truncated:
        raw = raw[:max_file_bytes]
    return raw.decode("utf-8", errors="replace"), truncated


paths = candidate_paths()
relative_paths = [path.relative_to(repo_root).as_posix() for path in paths]
top_level_counts = Counter(rel.split("/", 1)[0] for rel in relative_paths)

branch = run_git("branch", "--show-current") or "(detached)"
head = run_git("rev-parse", "HEAD")
status = run_git("status", "--short") or "(clean)"
recent_commits = run_git("log", "--oneline", "-5") or "(no commits)"
diff_text = run_git("diff", "--no-ext-diff", "--minimal") if include_diff else ""

bundle_parts: list[str] = []
bundle_parts.append("# ADAM Codebase Context Bundle")
bundle_parts.append("")
bundle_parts.append("## Metadata")
bundle_parts.append("")
bundle_parts.append(f"- Generated from: `{repo_root}`")
bundle_parts.append(f"- Output file: `{output_path}`")
bundle_parts.append(f"- Branch: `{branch}`")
bundle_parts.append(f"- HEAD: `{head}`")
bundle_parts.append(f"- Mode: `{'full' if full_mode else 'default'}`")
bundle_parts.append(f"- File count: `{len(paths)}`")
bundle_parts.append(f"- Per-file byte cap: `{max_file_bytes}`")
bundle_parts.append("")
bundle_parts.append("## Default Exclusions")
bundle_parts.append("")
bundle_parts.append("- `.git`, `.venv`, `data`, `assets`, `exports`, `tmp`")
bundle_parts.append("- `__pycache__`, `.pytest_cache`, `*.pyc`, `.DS_Store`")
bundle_parts.append("")
bundle_parts.append("## Included Path Summary")
bundle_parts.append("")
for top_level, count in sorted(top_level_counts.items()):
    bundle_parts.append(f"- `{top_level}`: {count} files")
bundle_parts.append("")
bundle_parts.append("```text")
bundle_parts.extend(relative_paths)
bundle_parts.append("```")
bundle_parts.append("")
bundle_parts.append("## Git Status")
bundle_parts.append("")
bundle_parts.append("```text")
bundle_parts.append(status)
bundle_parts.append("```")
bundle_parts.append("")
bundle_parts.append("## Recent Commits")
bundle_parts.append("")
bundle_parts.append("```text")
bundle_parts.append(recent_commits)
bundle_parts.append("```")
bundle_parts.append("")

if include_diff:
    bundle_parts.append("## Current Diff")
    bundle_parts.append("")
    bundle_parts.append("```diff")
    bundle_parts.append(diff_text or "(no diff)")
    bundle_parts.append("```")
    bundle_parts.append("")

bundle_parts.append("## File Contents")
bundle_parts.append("")

for path in paths:
    rel = path.relative_to(repo_root).as_posix()
    content, truncated = read_file(path)
    size = path.stat().st_size
    bundle_parts.append(f"### `{rel}`")
    bundle_parts.append("")
    bundle_parts.append(f"- Size: `{size}` bytes")
    bundle_parts.append(f"- Truncated: `{'yes' if truncated else 'no'}`")
    bundle_parts.append("")
    bundle_parts.append(f"````{language_for(path)}")
    bundle_parts.append(content.rstrip("\n"))
    bundle_parts.append("````")
    bundle_parts.append("")

output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text("\n".join(bundle_parts), encoding="utf-8")
PY

ln -sfn "$output_path" "${output_dir}/latest.md"

if [[ "$print_path" -eq 1 ]]; then
  printf '%s\n' "$output_path"
else
  printf 'Wrote %s\n' "$output_path"
  printf 'Updated %s\n' "${output_dir}/latest.md"
fi
