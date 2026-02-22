"""Tests for aftr refs — unit, CLI, and integration layers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from subprocess import TimeoutExpired
from unittest.mock import MagicMock, call, patch

import pytest
from typer.testing import CliRunner

from aftr.commands.refs_cmd import refs_app
from aftr.refs import (
    GITIGNORE_ENTRY,
    RefsSource,
    SyncResult,
    ensure_gitignore,
    get_remote_commit,
    load_refs_config,
    load_refs_state,
    save_refs_config,
    save_refs_state,
    sync_source,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """A clean project directory (simulates a user's repo root)."""
    return tmp_path


@pytest.fixture
def project_with_source(project_dir: Path) -> Path:
    """A project dir with one source already registered."""
    sources = [
        RefsSource(
            name="guides",
            url="https://example.com/repo",
            path="docs/guides",
            branch="main",
        )
    ]
    save_refs_config(project_dir, sources)
    return project_dir


# ---------------------------------------------------------------------------
# Layer 1 — Unit tests
# ---------------------------------------------------------------------------


class TestConfigIO:
    def test_load_refs_config_empty(self, project_dir: Path) -> None:
        result = load_refs_config(project_dir)
        assert result == []

    def test_save_then_load_refs_config(self, project_dir: Path) -> None:
        sources = [
            RefsSource(name="alpha", url="https://a.example/repo", path="docs/a", branch="main"),
            RefsSource(name="beta", url="https://b.example/repo", path="docs/b", branch="dev"),
        ]
        save_refs_config(project_dir, sources)
        loaded = load_refs_config(project_dir)

        assert len(loaded) == 2
        assert loaded[0].name == "alpha"
        assert loaded[0].url == "https://a.example/repo"
        assert loaded[0].path == "docs/a"
        assert loaded[0].branch == "main"
        assert loaded[1].name == "beta"
        assert loaded[1].branch == "dev"

    def test_load_refs_config_optional_local_dir(self, project_dir: Path) -> None:
        """When local_dir is absent from TOML, it defaults to name."""
        aftr_dir = project_dir / ".aftr"
        aftr_dir.mkdir()
        (aftr_dir / "refs.toml").write_text(
            '[[sources]]\nname = "myref"\nurl = "https://example.com"\npath = "docs"\nbranch = "main"\n',
            encoding="utf-8",
        )
        loaded = load_refs_config(project_dir)
        assert len(loaded) == 1
        assert loaded[0].local_dir == "myref"


class TestStateIO:
    def test_load_refs_state_missing(self, project_dir: Path) -> None:
        state = load_refs_state(project_dir)
        assert state == {"sources": {}}

    def test_load_refs_state_corrupt_json(self, project_dir: Path) -> None:
        aftr_dir = project_dir / ".aftr"
        aftr_dir.mkdir()
        (aftr_dir / ".state.json").write_text("not valid json{{{", encoding="utf-8")
        state = load_refs_state(project_dir)
        assert state == {"sources": {}}

    def test_save_then_load_refs_state(self, project_dir: Path) -> None:
        state = {
            "sources": {
                "guides": {
                    "last_commit": "abc123def456",
                    "synced_at": "2024-01-15T10:30:00+00:00",
                }
            }
        }
        save_refs_state(project_dir, state)
        loaded = load_refs_state(project_dir)
        assert loaded["sources"]["guides"]["last_commit"] == "abc123def456"
        assert loaded["sources"]["guides"]["synced_at"] == "2024-01-15T10:30:00+00:00"


class TestEnsureGitignore:
    def test_ensure_gitignore_creates_file(self, project_dir: Path) -> None:
        ensure_gitignore(project_dir)
        gitignore = project_dir / ".gitignore"
        assert gitignore.exists()
        assert GITIGNORE_ENTRY in gitignore.read_text()

    def test_ensure_gitignore_appends(self, project_dir: Path) -> None:
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("*.pyc\n", encoding="utf-8")
        ensure_gitignore(project_dir)
        content = gitignore.read_text()
        assert GITIGNORE_ENTRY in content
        assert "*.pyc" in content

    def test_ensure_gitignore_idempotent(self, project_dir: Path) -> None:
        ensure_gitignore(project_dir)
        ensure_gitignore(project_dir)
        content = (project_dir / ".gitignore").read_text()
        assert content.count(GITIGNORE_ENTRY) == 1

    def test_ensure_gitignore_preserves_existing_content(self, project_dir: Path) -> None:
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("*.log\nbuild/\n", encoding="utf-8")
        ensure_gitignore(project_dir)
        content = gitignore.read_text()
        assert "*.log" in content
        assert "build/" in content
        assert GITIGNORE_ENTRY in content


class TestGetRemoteCommit:
    def test_get_remote_commit_success(self) -> None:
        mock_result = MagicMock(returncode=0, stdout="abc123\trefs/heads/main\n")
        with patch("aftr.refs.shutil.which", return_value="/usr/bin/git"), \
             patch("aftr.refs.subprocess.run", return_value=mock_result):
            sha = get_remote_commit("https://example.com/repo", "main")
        assert sha == "abc123"

    def test_get_remote_commit_nonzero(self) -> None:
        mock_result = MagicMock(returncode=1, stdout="")
        with patch("aftr.refs.shutil.which", return_value="/usr/bin/git"), \
             patch("aftr.refs.subprocess.run", return_value=mock_result):
            sha = get_remote_commit("https://example.com/repo", "main")
        assert sha is None

    def test_get_remote_commit_empty_stdout(self) -> None:
        mock_result = MagicMock(returncode=0, stdout="")
        with patch("aftr.refs.shutil.which", return_value="/usr/bin/git"), \
             patch("aftr.refs.subprocess.run", return_value=mock_result):
            sha = get_remote_commit("https://example.com/repo", "main")
        assert sha is None

    def test_get_remote_commit_git_not_found(self) -> None:
        with patch("aftr.refs.shutil.which", return_value=None):
            sha = get_remote_commit("https://example.com/repo", "main")
        assert sha is None

    def test_get_remote_commit_timeout(self) -> None:
        with patch("aftr.refs.shutil.which", return_value="/usr/bin/git"), \
             patch("aftr.refs.subprocess.run", side_effect=TimeoutExpired("git", 30)):
            sha = get_remote_commit("https://example.com/repo", "main")
        assert sha is None


class TestSyncSource:
    def _make_source(self, **kwargs) -> RefsSource:
        defaults = dict(
            name="guides",
            url="https://example.com/repo",
            path="guides",
            branch="main",
        )
        defaults.update(kwargs)
        return RefsSource(**defaults)

    def test_sync_already_up_to_date(self, project_dir: Path) -> None:
        source = self._make_source()
        save_refs_state(
            project_dir,
            {"sources": {"guides": {"last_commit": "deadbeef", "synced_at": "2024-01-01"}}},
        )
        with patch("aftr.refs.shutil.which", return_value="/usr/bin/git"), \
             patch("aftr.refs.get_remote_commit", return_value="deadbeef"):
            result = sync_source(project_dir, source)
        assert result.status == "up_to_date"
        assert result.commit == "deadbeef"

    def test_sync_force_bypasses_up_to_date(self, project_dir: Path, tmp_path: Path) -> None:
        source = self._make_source()
        save_refs_state(
            project_dir,
            {"sources": {"guides": {"last_commit": "deadbeef", "synced_at": "2024-01-01"}}},
        )
        fake_tmpdir = tmp_path / "fake_clone"
        fake_tmpdir.mkdir()
        (fake_tmpdir / "guides").mkdir()
        (fake_tmpdir / "guides" / "file.md").write_text("# Guide")

        ls_remote = MagicMock(returncode=0, stdout="deadbeef\trefs/heads/main\n")
        clone_ok = MagicMock(returncode=0, stderr="")
        sparse_ok = MagicMock(returncode=0, stderr="")

        with patch("aftr.refs.shutil.which", return_value="/usr/bin/git"), \
             patch("aftr.refs.tempfile.mkdtemp", return_value=str(fake_tmpdir)), \
             patch("aftr.refs.subprocess.run", side_effect=[ls_remote, clone_ok, sparse_ok]):
            result = sync_source(project_dir, source, force=True)
        assert result.status == "updated"

    def test_sync_updated(self, project_dir: Path, tmp_path: Path) -> None:
        source = self._make_source()
        # No prior state — remote SHA differs from nothing
        fake_tmpdir = tmp_path / "fake_clone"
        fake_tmpdir.mkdir()
        guides_dir = fake_tmpdir / "guides"
        guides_dir.mkdir()
        (guides_dir / "python.md").write_text("# Python Guide")
        (guides_dir / "sql.md").write_text("# SQL Guide")

        ls_remote = MagicMock(returncode=0, stdout="newsha123\trefs/heads/main\n")
        clone_ok = MagicMock(returncode=0, stderr="")
        sparse_ok = MagicMock(returncode=0, stderr="")

        with patch("aftr.refs.shutil.which", return_value="/usr/bin/git"), \
             patch("aftr.refs.tempfile.mkdtemp", return_value=str(fake_tmpdir)), \
             patch("aftr.refs.subprocess.run", side_effect=[ls_remote, clone_ok, sparse_ok]):
            result = sync_source(project_dir, source)

        assert result.status == "updated"
        assert result.commit == "newsha123"
        assert (project_dir / ".aftr" / "guides" / "python.md").exists()
        assert (project_dir / ".aftr" / "guides" / "sql.md").exists()
        # State updated
        state = load_refs_state(project_dir)
        assert state["sources"]["guides"]["last_commit"] == "newsha123"

    def test_sync_overwrites_existing_files(self, project_dir: Path, tmp_path: Path) -> None:
        source = self._make_source()
        # Pre-create old destination
        old_dest = project_dir / ".aftr" / "guides"
        old_dest.mkdir(parents=True)
        (old_dest / "old_file.md").write_text("old content")

        fake_tmpdir = tmp_path / "fake_clone2"
        fake_tmpdir.mkdir()
        guides_dir = fake_tmpdir / "guides"
        guides_dir.mkdir()
        (guides_dir / "new_file.md").write_text("# New")

        ls_remote = MagicMock(returncode=0, stdout="sha999\trefs/heads/main\n")
        clone_ok = MagicMock(returncode=0, stderr="")
        sparse_ok = MagicMock(returncode=0, stderr="")

        with patch("aftr.refs.shutil.which", return_value="/usr/bin/git"), \
             patch("aftr.refs.tempfile.mkdtemp", return_value=str(fake_tmpdir)), \
             patch("aftr.refs.subprocess.run", side_effect=[ls_remote, clone_ok, sparse_ok]):
            result = sync_source(project_dir, source)

        assert result.status == "updated"
        assert not (project_dir / ".aftr" / "guides" / "old_file.md").exists()
        assert (project_dir / ".aftr" / "guides" / "new_file.md").exists()

    def test_sync_git_not_available(self, project_dir: Path) -> None:
        source = self._make_source()
        with patch("aftr.refs.shutil.which", return_value=None):
            result = sync_source(project_dir, source)
        assert result.status == "error"
        assert "PATH" in result.message or "git" in result.message.lower()

    def test_sync_ls_remote_fails(self, project_dir: Path) -> None:
        source = self._make_source()
        ls_remote_fail = MagicMock(returncode=1, stdout="", stderr="fatal: not a repo")
        with patch("aftr.refs.shutil.which", return_value="/usr/bin/git"), \
             patch("aftr.refs.subprocess.run", return_value=ls_remote_fail):
            result = sync_source(project_dir, source)
        assert result.status == "error"

    def test_sync_clone_fails(self, project_dir: Path) -> None:
        source = self._make_source()
        ls_remote = MagicMock(returncode=0, stdout="sha1\trefs/heads/main\n")
        clone_fail = MagicMock(returncode=128, stderr="fatal: clone error")

        with patch("aftr.refs.shutil.which", return_value="/usr/bin/git"), \
             patch("aftr.refs.subprocess.run", side_effect=[ls_remote, clone_fail]):
            result = sync_source(project_dir, source)
        assert result.status == "error"
        assert "clone" in result.message.lower() or "fatal" in result.message.lower()

    def test_sync_path_not_in_repo(self, project_dir: Path, tmp_path: Path) -> None:
        source = self._make_source(path="nonexistent/path")
        fake_tmpdir = tmp_path / "empty_clone"
        fake_tmpdir.mkdir()
        # No 'nonexistent/path' directory created

        ls_remote = MagicMock(returncode=0, stdout="sha1\trefs/heads/main\n")
        clone_ok = MagicMock(returncode=0, stderr="")
        sparse_ok = MagicMock(returncode=0, stderr="")

        with patch("aftr.refs.shutil.which", return_value="/usr/bin/git"), \
             patch("aftr.refs.tempfile.mkdtemp", return_value=str(fake_tmpdir)), \
             patch("aftr.refs.subprocess.run", side_effect=[ls_remote, clone_ok, sparse_ok]):
            result = sync_source(project_dir, source)
        assert result.status == "error"
        assert "not found" in result.message.lower() or "nonexistent" in result.message

    def test_sync_cleanup_on_error(self, project_dir: Path, tmp_path: Path) -> None:
        source = self._make_source()
        fake_tmpdir = tmp_path / "timeout_clone"
        fake_tmpdir.mkdir()

        ls_remote = MagicMock(returncode=0, stdout="sha1\trefs/heads/main\n")

        with patch("aftr.refs.shutil.which", return_value="/usr/bin/git"), \
             patch("aftr.refs.tempfile.mkdtemp", return_value=str(fake_tmpdir)), \
             patch("aftr.refs.subprocess.run", side_effect=[ls_remote, TimeoutExpired("git", 120)]):
            result = sync_source(project_dir, source)

        assert result.status == "error"
        assert "timed out" in result.message.lower()
        # Temp dir should be cleaned up by finally block
        assert not fake_tmpdir.exists()


# ---------------------------------------------------------------------------
# Layer 2 — CLI tests
# ---------------------------------------------------------------------------


class TestRefsList:
    def test_list_no_sources(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(project_dir)
        result = runner.invoke(refs_app, ["list"])
        assert result.exit_code == 0
        assert "No sources" in result.stdout

    def test_list_with_sources(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        save_refs_config(
            project_dir,
            [
                RefsSource(name="alpha", url="https://a.com/repo", path="docs", branch="main"),
                RefsSource(name="beta", url="https://b.com/repo", path="guides", branch="main"),
            ],
        )
        monkeypatch.chdir(project_dir)
        result = runner.invoke(refs_app, ["list"])
        assert result.exit_code == 0
        assert "alpha" in result.stdout
        assert "beta" in result.stdout

    def test_list_shows_last_synced(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        save_refs_config(
            project_dir,
            [RefsSource(name="docs", url="https://x.com/repo", path="docs", branch="main")],
        )
        save_refs_state(
            project_dir,
            {"sources": {"docs": {"last_commit": "abc", "synced_at": "2024-06-01T12:00:00+00:00"}}},
        )
        monkeypatch.chdir(project_dir)
        result = runner.invoke(refs_app, ["list"])
        assert result.exit_code == 0
        assert "2024-06-01" in result.stdout


class TestRefsAdd:
    def test_add_creates_refs_toml(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(project_dir)
        result = runner.invoke(
            refs_app,
            ["add", "--url", "https://example.com/repo", "--path", "docs", "--name", "docs", "--branch", "main"],
        )
        assert result.exit_code == 0
        assert (project_dir / ".aftr" / "refs.toml").exists()
        sources = load_refs_config(project_dir)
        assert len(sources) == 1
        assert sources[0].name == "docs"
        assert sources[0].url == "https://example.com/repo"

    def test_add_updates_gitignore(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(project_dir)
        runner.invoke(
            refs_app,
            ["add", "--url", "https://example.com/repo", "--path", "docs", "--name", "docs", "--branch", "main"],
        )
        gitignore = project_dir / ".gitignore"
        assert gitignore.exists()
        assert GITIGNORE_ENTRY in gitignore.read_text()

    def test_add_defaults_local_dir_to_name(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(project_dir)
        runner.invoke(
            refs_app,
            ["add", "--url", "https://example.com/repo", "--path", "docs", "--name", "myrefs", "--branch", "main"],
        )
        sources = load_refs_config(project_dir)
        assert sources[0].local_dir == "myrefs"

    def test_add_custom_local_dir(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(project_dir)
        runner.invoke(
            refs_app,
            [
                "add",
                "--url", "https://example.com/repo",
                "--path", "docs",
                "--name", "myrefs",
                "--branch", "main",
                "--local-dir", "custom_dir",
            ],
        )
        sources = load_refs_config(project_dir)
        assert sources[0].local_dir == "custom_dir"

    def test_add_duplicate_name_errors(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        save_refs_config(
            project_dir,
            [RefsSource(name="docs", url="https://example.com/repo", path="docs", branch="main")],
        )
        monkeypatch.chdir(project_dir)
        result = runner.invoke(
            refs_app,
            ["add", "--url", "https://other.com/repo", "--path", "docs", "--name", "docs", "--branch", "main"],
        )
        assert result.exit_code == 1
        assert "docs" in result.stdout

    def test_add_second_source_appends(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(project_dir)
        runner.invoke(
            refs_app,
            ["add", "--url", "https://a.com/repo", "--path", "docs", "--name", "first", "--branch", "main"],
        )
        runner.invoke(
            refs_app,
            ["add", "--url", "https://b.com/repo", "--path", "guides", "--name", "second", "--branch", "main"],
        )
        sources = load_refs_config(project_dir)
        names = [s.name for s in sources]
        assert "first" in names
        assert "second" in names


class TestRefsSync:
    def _mock_sync_up_to_date(self, name: str) -> SyncResult:
        return SyncResult(name=name, status="up_to_date", message="Already up to date.", commit="abc12345")

    def _mock_sync_updated(self, name: str) -> SyncResult:
        return SyncResult(name=name, status="updated", message="Synced successfully.", commit="newsha12")

    def _mock_sync_error(self, name: str) -> SyncResult:
        return SyncResult(name=name, status="error", message="Connection failed.")

    def test_sync_no_sources(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(project_dir)
        result = runner.invoke(refs_app, ["sync"])
        assert result.exit_code == 0
        assert "No sources" in result.stdout

    def test_sync_unknown_name(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        save_refs_config(
            project_dir,
            [RefsSource(name="a", url="https://example.com/repo", path="docs", branch="main")],
        )
        monkeypatch.chdir(project_dir)
        result = runner.invoke(refs_app, ["sync", "b"])
        assert result.exit_code == 1

    def test_sync_all_up_to_date(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        save_refs_config(
            project_dir,
            [
                RefsSource(name="a", url="https://example.com/repo", path="docs/a", branch="main"),
                RefsSource(name="b", url="https://example.com/repo", path="docs/b", branch="main"),
            ],
        )
        monkeypatch.chdir(project_dir)
        with patch("aftr.refs.sync_source", side_effect=[
            self._mock_sync_up_to_date("a"),
            self._mock_sync_up_to_date("b"),
        ]):
            result = runner.invoke(refs_app, ["sync"])
        assert result.exit_code == 0
        assert "Already up to date" in result.stdout

    def test_sync_all_one_updated(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        save_refs_config(
            project_dir,
            [
                RefsSource(name="a", url="https://example.com/repo", path="docs/a", branch="main"),
                RefsSource(name="b", url="https://example.com/repo", path="docs/b", branch="main"),
            ],
        )
        monkeypatch.chdir(project_dir)
        with patch("aftr.refs.sync_source", side_effect=[
            self._mock_sync_up_to_date("a"),
            self._mock_sync_updated("b"),
        ]):
            result = runner.invoke(refs_app, ["sync"])
        assert result.exit_code == 0
        assert "Updated" in result.stdout

    def test_sync_named_source(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        save_refs_config(
            project_dir,
            [
                RefsSource(name="a", url="https://example.com/repo", path="docs/a", branch="main"),
                RefsSource(name="b", url="https://example.com/repo", path="docs/b", branch="main"),
            ],
        )
        monkeypatch.chdir(project_dir)
        with patch("aftr.refs.sync_source") as mock_sync:
            mock_sync.return_value = self._mock_sync_up_to_date("a")
            result = runner.invoke(refs_app, ["sync", "a"])
        assert result.exit_code == 0
        assert mock_sync.call_count == 1
        assert mock_sync.call_args[0][1].name == "a"

    def test_sync_error_exits_nonzero(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        save_refs_config(
            project_dir,
            [RefsSource(name="a", url="https://example.com/repo", path="docs", branch="main")],
        )
        monkeypatch.chdir(project_dir)
        with patch("aftr.refs.sync_source", return_value=self._mock_sync_error("a")):
            result = runner.invoke(refs_app, ["sync"])
        assert result.exit_code == 1
        assert "Connection failed" in result.stdout

    def test_sync_force_flag(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        save_refs_config(
            project_dir,
            [RefsSource(name="a", url="https://example.com/repo", path="docs", branch="main")],
        )
        monkeypatch.chdir(project_dir)
        with patch("aftr.refs.sync_source") as mock_sync:
            mock_sync.return_value = self._mock_sync_updated("a")
            result = runner.invoke(refs_app, ["sync", "--force"])
        assert result.exit_code == 0
        _, kwargs = mock_sync.call_args
        assert kwargs.get("force") is True


class TestRefsRemove:
    def test_remove_unknown_name(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(project_dir)
        result = runner.invoke(refs_app, ["remove", "nonexistent"])
        assert result.exit_code == 1

    def test_remove_confirmed(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        save_refs_config(
            project_dir,
            [RefsSource(name="docs", url="https://example.com/repo", path="docs", branch="main")],
        )
        monkeypatch.chdir(project_dir)
        result = runner.invoke(refs_app, ["remove", "docs"], input="y\n")
        assert result.exit_code == 0
        sources = load_refs_config(project_dir)
        assert not any(s.name == "docs" for s in sources)

    def test_remove_aborted(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        save_refs_config(
            project_dir,
            [RefsSource(name="docs", url="https://example.com/repo", path="docs", branch="main")],
        )
        monkeypatch.chdir(project_dir)
        result = runner.invoke(refs_app, ["remove", "docs"], input="n\n")
        assert result.exit_code == 0
        sources = load_refs_config(project_dir)
        assert any(s.name == "docs" for s in sources)

    def test_remove_cleans_state(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        save_refs_config(
            project_dir,
            [RefsSource(name="docs", url="https://example.com/repo", path="docs", branch="main")],
        )
        save_refs_state(
            project_dir,
            {"sources": {"docs": {"last_commit": "abc", "synced_at": "2024-01-01"}}},
        )
        monkeypatch.chdir(project_dir)
        runner.invoke(refs_app, ["remove", "docs"], input="y\n")
        state = load_refs_state(project_dir)
        assert "docs" not in state.get("sources", {})

    def test_remove_delete_files(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        save_refs_config(
            project_dir,
            [RefsSource(name="docs", url="https://example.com/repo", path="docs", branch="main")],
        )
        local_dir = project_dir / ".aftr" / "docs"
        local_dir.mkdir(parents=True)
        (local_dir / "file.md").write_text("# Doc")
        monkeypatch.chdir(project_dir)
        result = runner.invoke(refs_app, ["remove", "docs", "--delete-files"], input="y\n")
        assert result.exit_code == 0
        assert not local_dir.exists()

    def test_remove_delete_files_missing_dir(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        save_refs_config(
            project_dir,
            [RefsSource(name="docs", url="https://example.com/repo", path="docs", branch="main")],
        )
        monkeypatch.chdir(project_dir)
        result = runner.invoke(refs_app, ["remove", "docs", "--delete-files"], input="y\n")
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Layer 3 — Integration tests (real git, no network)
# ---------------------------------------------------------------------------


@pytest.fixture
def local_bare_repo(tmp_path: Path):
    """A real local bare git repo seeded with markdown files.

    Returns (remote_url, project_dir) where remote_url points to the bare repo.
    """
    remote = tmp_path / "remote"
    work = tmp_path / "work"
    project = tmp_path / "project"
    project.mkdir()

    # Init bare repo
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    # Clone to work tree
    subprocess.run(["git", "clone", str(remote), str(work)], check=True, capture_output=True)

    # Configure git identity for commits
    subprocess.run(["git", "-C", str(work), "config", "user.email", "test@example.com"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work), "config", "user.name", "Test User"], check=True, capture_output=True)

    # Seed files
    guides = work / "guides"
    guides.mkdir()
    (guides / "python.md").write_text("# Python Guide\n\nContent here.")
    (guides / "sql.md").write_text("# SQL Guide\n\nContent here.")

    subprocess.run(["git", "-C", str(work), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work), "commit", "-m", "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work), "push", "origin", "HEAD:main"], check=True, capture_output=True)

    return remote, work, project


@pytest.mark.integration
class TestIntegration:
    def test_integration_sync_copies_files(self, local_bare_repo) -> None:
        remote, work, project = local_bare_repo
        source = RefsSource(name="guides", url=str(remote), path="guides", branch="main")
        save_refs_config(project, [source])

        result = sync_source(project, source)

        assert result.status == "updated", result.message
        assert (project / ".aftr" / "guides" / "python.md").exists()
        assert (project / ".aftr" / "guides" / "sql.md").exists()

    def test_integration_state_written(self, local_bare_repo) -> None:
        remote, work, project = local_bare_repo
        source = RefsSource(name="guides", url=str(remote), path="guides", branch="main")

        result = sync_source(project, source)

        assert result.status == "updated", result.message
        state = load_refs_state(project)
        src_state = state["sources"]["guides"]
        assert src_state["last_commit"] == result.commit
        assert "synced_at" in src_state

    def test_integration_sync_twice_is_up_to_date(self, local_bare_repo) -> None:
        remote, work, project = local_bare_repo
        source = RefsSource(name="guides", url=str(remote), path="guides", branch="main")

        first = sync_source(project, source)
        assert first.status == "updated", first.message

        second = sync_source(project, source)
        assert second.status == "up_to_date"

    def test_integration_sync_after_remote_update(self, local_bare_repo) -> None:
        remote, work, project = local_bare_repo
        source = RefsSource(name="guides", url=str(remote), path="guides", branch="main")

        first = sync_source(project, source)
        assert first.status == "updated", first.message

        # Push a new commit to the remote
        (work / "guides" / "updated.md").write_text("# Updated")
        subprocess.run(["git", "-C", str(work), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(work), "commit", "-m", "update"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(work), "push", "origin", "HEAD:main"], check=True, capture_output=True)

        second = sync_source(project, source)
        assert second.status == "updated"
        assert second.commit != first.commit
        assert (project / ".aftr" / "guides" / "updated.md").exists()

    def test_integration_gitignore_created(self, local_bare_repo, monkeypatch: pytest.MonkeyPatch) -> None:
        remote, work, project = local_bare_repo
        monkeypatch.chdir(project)

        result = runner.invoke(
            refs_app,
            [
                "add",
                "--url", str(remote),
                "--path", "guides",
                "--name", "guides",
                "--branch", "main",
            ],
        )
        assert result.exit_code == 0

        gitignore = project / ".gitignore"
        assert gitignore.exists()
        assert GITIGNORE_ENTRY in gitignore.read_text()
