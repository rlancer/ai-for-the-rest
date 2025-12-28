"""Tests for the aftr init command."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aftr.cli import app

runner = CliRunner()


class TestCli:
    """Test CLI basics."""

    def test_help(self) -> None:
        """CLI shows help when invoked with --help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "init" in result.stdout

    def test_init_help(self) -> None:
        """Init command shows help when invoked with --help."""
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "Scaffold a new Python data project" in result.stdout

    def test_init_missing_name_shows_error(self) -> None:
        """Init shows error when NAME is missing."""
        result = runner.invoke(app, ["init"])
        # Typer shows usage info when required arg is missing
        assert result.exit_code != 0 or "NAME" in result.stdout


class TestInitCommand:
    """Test the init command."""

    def test_creates_project_directory(self, tmp_path: Path) -> None:
        """Init creates the project directory."""
        result = runner.invoke(app, ["init", "my-project", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / "my-project").is_dir()

    def test_creates_directory_structure(self, tmp_path: Path) -> None:
        """Init creates all expected directories."""
        runner.invoke(app, ["init", "test-proj", "--path", str(tmp_path)])

        project = tmp_path / "test-proj"
        assert (project / "notebooks").is_dir()
        assert (project / "src" / "test_proj").is_dir()
        assert (project / "data").is_dir()
        assert (project / "outputs").is_dir()

    def test_creates_pyproject_toml(self, tmp_path: Path) -> None:
        """Init creates a valid pyproject.toml."""
        runner.invoke(app, ["init", "data-analysis", "--path", str(tmp_path)])

        pyproject = tmp_path / "data-analysis" / "pyproject.toml"
        assert pyproject.exists()
        content = pyproject.read_text()
        assert 'name = "data-analysis"' in content
        assert 'version = "0.1.0"' in content
        assert "pandas" in content
        assert "polars" in content
        assert "papermill" in content

    def test_creates_mise_toml(self, tmp_path: Path) -> None:
        """Init creates .mise.toml with correct tools."""
        runner.invoke(app, ["init", "myproj", "--path", str(tmp_path)])

        mise = tmp_path / "myproj" / ".mise.toml"
        assert mise.exists()
        content = mise.read_text()
        assert 'python = "3.12"' in content
        assert 'uv = "latest"' in content

    def test_creates_gitignore(self, tmp_path: Path) -> None:
        """Init creates .gitignore with expected patterns."""
        runner.invoke(app, ["init", "proj", "--path", str(tmp_path)])

        gitignore = tmp_path / "proj" / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert "__pycache__/" in content
        assert ".venv/" in content
        assert "data/" in content
        assert "outputs/" in content
        assert ".ipynb_checkpoints/" in content

    def test_creates_init_py(self, tmp_path: Path) -> None:
        """Init creates __init__.py in the src module."""
        runner.invoke(app, ["init", "my-pkg", "--path", str(tmp_path)])

        init_py = tmp_path / "my-pkg" / "src" / "my_pkg" / "__init__.py"
        assert init_py.exists()
        content = init_py.read_text()
        assert "__version__" in content
        assert "my-pkg" in content

    def test_creates_example_notebook(self, tmp_path: Path) -> None:
        """Init creates a valid Jupyter notebook."""
        runner.invoke(app, ["init", "nb-project", "--path", str(tmp_path)])

        notebook = tmp_path / "nb-project" / "notebooks" / "example.ipynb"
        assert notebook.exists()

        # Verify it's valid JSON
        content = json.loads(notebook.read_text())
        assert content["nbformat"] == 4
        assert len(content["cells"]) == 3

        # Check for papermill parameters tag
        cells_with_params = [
            c
            for c in content["cells"]
            if c.get("metadata", {}).get("tags") == ["parameters"]
        ]
        assert len(cells_with_params) == 1

    def test_creates_readme(self, tmp_path: Path) -> None:
        """Init creates README.md with project info."""
        runner.invoke(app, ["init", "readme-test", "--path", str(tmp_path)])

        readme = tmp_path / "readme-test" / "README.md"
        assert readme.exists()
        content = readme.read_text()
        assert "# readme-test" in content
        assert "uv sync" in content
        assert "papermill" in content

    def test_hyphenated_name_converts_to_underscore(self, tmp_path: Path) -> None:
        """Hyphens in project name are converted to underscores for module."""
        runner.invoke(app, ["init", "my-data-project", "--path", str(tmp_path)])

        # Directory uses hyphens
        assert (tmp_path / "my-data-project").is_dir()
        # Module uses underscores
        assert (tmp_path / "my-data-project" / "src" / "my_data_project").is_dir()


class TestInitErrors:
    """Test init command error handling."""

    def test_fails_if_directory_exists(self, tmp_path: Path) -> None:
        """Init fails if project directory already exists."""
        existing = tmp_path / "existing-project"
        existing.mkdir()

        result = runner.invoke(
            app, ["init", "existing-project", "--path", str(tmp_path)]
        )
        assert result.exit_code == 1
        assert "already exists" in result.stdout

    def test_fails_if_nested_directory_exists(self, tmp_path: Path) -> None:
        """Init fails even if directory was created externally."""
        # Create directory with some content
        existing = tmp_path / "has-content"
        existing.mkdir()
        (existing / "some-file.txt").write_text("content")

        result = runner.invoke(app, ["init", "has-content", "--path", str(tmp_path)])
        assert result.exit_code == 1


class TestInitWithDefaultPath:
    """Test init command with default path (current directory)."""

    def test_creates_in_current_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Init creates project in current directory when no path specified."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "default-path-proj"])
        assert result.exit_code == 0
        assert (tmp_path / "default-path-proj").is_dir()
        assert (tmp_path / "default-path-proj" / "pyproject.toml").exists()
