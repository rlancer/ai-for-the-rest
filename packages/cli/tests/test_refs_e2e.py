"""End-to-end tests for aftr refs using the real ai-for-the-rest GitHub repo.

These tests require network access and a working git installation with SSH access
to github.com (or HTTPS access if the URL is changed). They are marked ``e2e``
and are skipped by default — run them explicitly:

    uv run pytest tests/test_refs_e2e.py -v -m e2e
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from aftr.commands.refs_cmd import refs_app
from aftr.refs import (
    GITIGNORE_ENTRY,
    RefsSource,
    load_refs_config,
    load_refs_state,
    save_refs_config,
    sync_source,
)

runner = CliRunner()

# ---------------------------------------------------------------------------
# Target — the repo that contains this very file
# ---------------------------------------------------------------------------

REMOTE_URL = "git@github.com:rlancer/ai-for-the-rest.git"
REMOTE_PATH = "docs"
REMOTE_BRANCH = "main"
SOURCE_NAME = "ai-for-the-rest-docs"

# Files we know exist inside docs/ on main.
KNOWN_DOC_FILES = [
    "aftr-cli-reference.md",
    "architecture.md",
    "getting-started.md",
    "templates.md",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Clean temporary directory that acts as a user's project root."""
    return tmp_path


@pytest.fixture()
def project_with_source_registered(
    project_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Project directory that already has the real source registered via CLI."""
    monkeypatch.chdir(project_dir)
    result = runner.invoke(
        refs_app,
        [
            "add",
            "--url", REMOTE_URL,
            "--path", REMOTE_PATH,
            "--name", SOURCE_NAME,
            "--branch", REMOTE_BRANCH,
        ],
    )
    assert result.exit_code == 0, f"add failed: {result.output}"
    return project_dir


@pytest.fixture()
def project_with_source_synced(
    project_dir: Path,
) -> tuple[Path, RefsSource]:
    """Project directory with the real source registered in refs.toml and synced."""
    source = RefsSource(
        name=SOURCE_NAME,
        url=REMOTE_URL,
        path=REMOTE_PATH,
        branch=REMOTE_BRANCH,
    )
    save_refs_config(project_dir, [source])
    result = sync_source(project_dir, source)
    assert result.status == "updated", f"initial sync failed: {result.message}"
    return project_dir, source


# ---------------------------------------------------------------------------
# E2E tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestE2ERefsAdd:
    """CLI `aftr refs add` with the real remote URL."""

    def test_add_registers_source_in_config(
        self, project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(project_dir)
        result = runner.invoke(
            refs_app,
            [
                "add",
                "--url", REMOTE_URL,
                "--path", REMOTE_PATH,
                "--name", SOURCE_NAME,
                "--branch", REMOTE_BRANCH,
            ],
        )
        assert result.exit_code == 0, result.output

        sources = load_refs_config(project_dir)
        assert len(sources) == 1
        src = sources[0]
        assert src.name == SOURCE_NAME
        assert src.url == REMOTE_URL
        assert src.path == REMOTE_PATH
        assert src.branch == REMOTE_BRANCH
        assert src.local_dir == SOURCE_NAME  # defaults to name

    def test_add_creates_gitignore_entry(
        self, project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(project_dir)
        runner.invoke(
            refs_app,
            [
                "add",
                "--url", REMOTE_URL,
                "--path", REMOTE_PATH,
                "--name", SOURCE_NAME,
                "--branch", REMOTE_BRANCH,
            ],
        )
        gitignore = project_dir / ".gitignore"
        assert gitignore.exists()
        assert GITIGNORE_ENTRY in gitignore.read_text(encoding="utf-8")

    def test_add_custom_local_dir(
        self, project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(project_dir)
        runner.invoke(
            refs_app,
            [
                "add",
                "--url", REMOTE_URL,
                "--path", REMOTE_PATH,
                "--name", SOURCE_NAME,
                "--branch", REMOTE_BRANCH,
                "--local-dir", "shared-docs",
            ],
        )
        sources = load_refs_config(project_dir)
        assert sources[0].local_dir == "shared-docs"


@pytest.mark.e2e
class TestE2ERefsSync:
    """Direct `sync_source` API against the real remote."""

    def test_sync_downloads_markdown_files(self, project_dir: Path) -> None:
        source = RefsSource(
            name=SOURCE_NAME,
            url=REMOTE_URL,
            path=REMOTE_PATH,
            branch=REMOTE_BRANCH,
        )
        result = sync_source(project_dir, source)

        assert result.status == "updated", result.message
        assert result.commit is not None and len(result.commit) == 40

        dest = project_dir / ".aftr" / SOURCE_NAME
        assert dest.is_dir()
        md_files = list(dest.glob("*.md"))
        assert len(md_files) > 0, "Expected at least one .md file in docs/"

    def test_sync_downloads_known_files(self, project_dir: Path) -> None:
        source = RefsSource(
            name=SOURCE_NAME,
            url=REMOTE_URL,
            path=REMOTE_PATH,
            branch=REMOTE_BRANCH,
        )
        sync_source(project_dir, source)

        dest = project_dir / ".aftr" / SOURCE_NAME
        for fname in KNOWN_DOC_FILES:
            assert (dest / fname).exists(), f"Expected '{fname}' to be synced from {REMOTE_PATH}/"

    def test_sync_writes_state(self, project_dir: Path) -> None:
        source = RefsSource(
            name=SOURCE_NAME,
            url=REMOTE_URL,
            path=REMOTE_PATH,
            branch=REMOTE_BRANCH,
        )
        result = sync_source(project_dir, source)

        state = load_refs_state(project_dir)
        src_state = state["sources"][SOURCE_NAME]
        assert src_state["last_commit"] == result.commit
        assert "synced_at" in src_state

    def test_sync_twice_is_up_to_date(self, project_dir: Path) -> None:
        source = RefsSource(
            name=SOURCE_NAME,
            url=REMOTE_URL,
            path=REMOTE_PATH,
            branch=REMOTE_BRANCH,
        )
        first = sync_source(project_dir, source)
        assert first.status == "updated", first.message

        second = sync_source(project_dir, source)
        assert second.status == "up_to_date"
        assert second.commit == first.commit

    def test_sync_force_re_downloads_same_commit(self, project_dir: Path) -> None:
        source = RefsSource(
            name=SOURCE_NAME,
            url=REMOTE_URL,
            path=REMOTE_PATH,
            branch=REMOTE_BRANCH,
        )
        first = sync_source(project_dir, source)
        assert first.status == "updated", first.message

        forced = sync_source(project_dir, source, force=True)
        assert forced.status == "updated"
        assert forced.commit == first.commit  # same commit, forced re-sync

        dest = project_dir / ".aftr" / SOURCE_NAME
        for fname in KNOWN_DOC_FILES:
            assert (dest / fname).exists()


@pytest.mark.e2e
class TestE2ERefsCLIRoundTrip:
    """Full CLI round-trips: add → sync → list → remove."""

    def test_cli_sync_reports_updated(
        self,
        project_with_source_registered: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project_dir = project_with_source_registered
        monkeypatch.chdir(project_dir)

        result = runner.invoke(refs_app, ["sync"])

        assert result.exit_code == 0, result.output
        assert "Updated" in result.stdout

    def test_cli_sync_files_land_on_disk(
        self,
        project_with_source_registered: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project_dir = project_with_source_registered
        monkeypatch.chdir(project_dir)
        runner.invoke(refs_app, ["sync"])

        dest = project_dir / ".aftr" / SOURCE_NAME
        assert dest.is_dir()
        for fname in KNOWN_DOC_FILES:
            assert (dest / fname).exists(), f"Missing {fname} after CLI sync"

    def test_cli_sync_twice_reports_up_to_date(
        self,
        project_with_source_registered: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project_dir = project_with_source_registered
        monkeypatch.chdir(project_dir)

        runner.invoke(refs_app, ["sync"])
        second = runner.invoke(refs_app, ["sync"])

        assert second.exit_code == 0, second.output
        assert "up to date" in second.stdout.lower()

    def test_cli_sync_force_flag(
        self,
        project_with_source_registered: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project_dir = project_with_source_registered
        monkeypatch.chdir(project_dir)

        runner.invoke(refs_app, ["sync"])
        result = runner.invoke(refs_app, ["sync", "--force"])

        assert result.exit_code == 0, result.output
        assert "Updated" in result.stdout

    def test_cli_sync_by_name(
        self,
        project_with_source_registered: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project_dir = project_with_source_registered
        monkeypatch.chdir(project_dir)

        result = runner.invoke(refs_app, ["sync", SOURCE_NAME])

        assert result.exit_code == 0, result.output
        assert "Updated" in result.stdout

    def test_cli_list_shows_source_and_commit(
        self,
        project_with_source_synced: tuple[Path, RefsSource],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project_dir, _ = project_with_source_synced
        monkeypatch.chdir(project_dir)

        result = runner.invoke(refs_app, ["list"])

        assert result.exit_code == 0, result.output
        # The table title is always present; the source name may be truncated by Rich
        assert "Registered Reference Sources" in result.stdout
        assert REMOTE_PATH in result.stdout
        assert REMOTE_BRANCH in result.stdout

    def test_cli_remove_deletes_registration(
        self,
        project_with_source_registered: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project_dir = project_with_source_registered
        monkeypatch.chdir(project_dir)

        result = runner.invoke(refs_app, ["remove", SOURCE_NAME], input="y\n")

        assert result.exit_code == 0, result.output
        sources = load_refs_config(project_dir)
        assert not any(s.name == SOURCE_NAME for s in sources)

    def test_cli_remove_with_delete_files(
        self,
        project_with_source_registered: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project_dir = project_with_source_registered
        monkeypatch.chdir(project_dir)

        runner.invoke(refs_app, ["sync"])

        dest = project_dir / ".aftr" / SOURCE_NAME
        assert dest.is_dir(), "Files should exist after sync before removal"

        result = runner.invoke(
            refs_app, ["remove", SOURCE_NAME, "--delete-files"], input="y\n"
        )

        assert result.exit_code == 0, result.output
        assert not dest.exists(), "Synced files should be deleted after remove --delete-files"

        sources = load_refs_config(project_dir)
        assert not any(s.name == SOURCE_NAME for s in sources)

    def test_cli_remove_clears_state(
        self,
        project_with_source_synced: tuple[Path, RefsSource],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project_dir, _ = project_with_source_synced
        monkeypatch.chdir(project_dir)

        runner.invoke(refs_app, ["remove", SOURCE_NAME], input="y\n")

        state = load_refs_state(project_dir)
        assert SOURCE_NAME not in state.get("sources", {})
