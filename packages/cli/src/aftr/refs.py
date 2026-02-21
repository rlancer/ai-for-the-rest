"""Core logic for aftr refs — shared markdown reference management."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import tomlkit

AFTR_DIR = ".aftr"
REFS_CONFIG = "refs.toml"
REFS_STATE = ".state.json"
GITIGNORE_ENTRY = ".aftr/.state.json"


@dataclass
class RefsSource:
    name: str
    url: str
    path: str
    branch: str = "main"
    local_dir: str = field(default="")

    def __post_init__(self) -> None:
        if not self.local_dir:
            self.local_dir = self.name


@dataclass
class SyncResult:
    name: str
    status: str  # "up_to_date" | "updated" | "error"
    message: str
    commit: str | None = None


# ---------------------------------------------------------------------------
# Config I/O
# ---------------------------------------------------------------------------


def _aftr_dir(project_dir: Path) -> Path:
    return project_dir / AFTR_DIR


def load_refs_config(project_dir: Path) -> list[RefsSource]:
    config_path = _aftr_dir(project_dir) / REFS_CONFIG
    if not config_path.exists():
        return []
    doc = tomlkit.parse(config_path.read_text(encoding="utf-8"))
    sources = []
    for item in doc.get("sources", []):
        sources.append(
            RefsSource(
                name=str(item["name"]),
                url=str(item["url"]),
                path=str(item["path"]),
                branch=str(item.get("branch", "main")),
                local_dir=str(item.get("local_dir", item["name"])),
            )
        )
    return sources


def save_refs_config(project_dir: Path, sources: list[RefsSource]) -> None:
    aftr_dir = _aftr_dir(project_dir)
    aftr_dir.mkdir(exist_ok=True)
    config_path = aftr_dir / REFS_CONFIG

    doc = tomlkit.document()
    aot: tomlkit.items.AoT = tomlkit.aot()
    for src in sources:
        t = tomlkit.table()
        t.add("name", src.name)
        t.add("url", src.url)
        t.add("path", src.path)
        t.add("branch", src.branch)
        if src.local_dir != src.name:
            t.add("local_dir", src.local_dir)
        aot.append(t)
    doc.add("sources", aot)
    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")


# ---------------------------------------------------------------------------
# State I/O
# ---------------------------------------------------------------------------


def load_refs_state(project_dir: Path) -> dict:
    state_path = _aftr_dir(project_dir) / REFS_STATE
    if not state_path.exists():
        return {"sources": {}}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"sources": {}}


def save_refs_state(project_dir: Path, state: dict) -> None:
    aftr_dir = _aftr_dir(project_dir)
    aftr_dir.mkdir(exist_ok=True)
    state_path = aftr_dir / REFS_STATE
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git_available() -> bool:
    return shutil.which("git") is not None


def get_remote_commit(url: str, branch: str) -> str | None:
    """Return the current HEAD SHA for a remote branch, or None on failure."""
    if not _git_available():
        return None
    try:
        result = subprocess.run(
            ["git", "ls-remote", url, f"refs/heads/{branch}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
        return line.split("\t")[0] if line else None
    except (subprocess.TimeoutExpired, OSError):
        return None


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def sync_source(
    project_dir: Path, source: RefsSource, force: bool = False
) -> SyncResult:
    """Sync a single source into .aftr/<local_dir>/."""
    if not _git_available():
        return SyncResult(
            name=source.name,
            status="error",
            message=(
                "git is required for refs sync. "
                "Install git and ensure it is on your PATH."
            ),
        )

    # Check remote commit
    remote_sha = get_remote_commit(source.url, source.branch)
    if remote_sha is None:
        return SyncResult(
            name=source.name,
            status="error",
            message=f"Could not reach remote '{source.url}' (branch: {source.branch}). "
            "Check the URL, branch name, and your network connection.",
        )

    # Compare with stored state
    state = load_refs_state(project_dir)
    source_state = state.get("sources", {}).get(source.name, {})
    if not force and source_state.get("last_commit") == remote_sha:
        return SyncResult(
            name=source.name,
            status="up_to_date",
            message="Already up to date.",
            commit=remote_sha,
        )

    # Sparse-clone into temp dir
    tmpdir = Path(tempfile.mkdtemp())
    try:
        clone_result = subprocess.run(
            [
                "git",
                "clone",
                "--depth=1",
                "--filter=blob:none",
                "--sparse",
                "--branch",
                source.branch,
                source.url,
                str(tmpdir),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if clone_result.returncode != 0:
            return SyncResult(
                name=source.name,
                status="error",
                message=f"git clone failed:\n{clone_result.stderr.strip()}",
            )

        checkout_result = subprocess.run(
            ["git", "-C", str(tmpdir), "sparse-checkout", "set", source.path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if checkout_result.returncode != 0:
            return SyncResult(
                name=source.name,
                status="error",
                message=f"git sparse-checkout failed:\n{checkout_result.stderr.strip()}",
            )

        # Copy files
        src_path = tmpdir / source.path
        if not src_path.exists():
            return SyncResult(
                name=source.name,
                status="error",
                message=f"Path '{source.path}' not found in repository.",
            )

        dest_path = _aftr_dir(project_dir) / source.local_dir
        if dest_path.exists():
            shutil.rmtree(dest_path)
        shutil.copytree(src_path, dest_path)

    except subprocess.TimeoutExpired:
        return SyncResult(
            name=source.name,
            status="error",
            message="git operation timed out.",
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # Update state
    state.setdefault("sources", {})[source.name] = {
        "last_commit": remote_sha,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }
    save_refs_state(project_dir, state)

    return SyncResult(
        name=source.name,
        status="updated",
        message="Synced successfully.",
        commit=remote_sha,
    )


# ---------------------------------------------------------------------------
# .gitignore helper
# ---------------------------------------------------------------------------


def ensure_gitignore(project_dir: Path) -> None:
    """Add .aftr/.state.json to .gitignore if not already present."""
    gitignore_path = project_dir / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        if any(line.strip() == GITIGNORE_ENTRY for line in lines):
            return
        # Append with a trailing newline
        separator = "\n" if content and not content.endswith("\n") else ""
        gitignore_path.write_text(
            content + separator + GITIGNORE_ENTRY + "\n", encoding="utf-8"
        )
    else:
        gitignore_path.write_text(GITIGNORE_ENTRY + "\n", encoding="utf-8")
