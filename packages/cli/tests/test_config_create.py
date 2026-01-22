"""Tests for the aftr config create-from-project command."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from aftr.cli import app
from aftr import config

runner = CliRunner()


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Create a sample project structure for testing."""
    project = tmp_path / "sample-project"
    project.mkdir()

    # Create pyproject.toml
    (project / "pyproject.toml").write_text(
        """[project]
name = "sample-project"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "polars>=1.0.0",
    "duckdb>=1.0.0",
]
""",
        encoding="utf-8",
    )

    # Create .mise.toml
    (project / ".mise.toml").write_text(
        """[tools]
uv = "latest"

[settings]
python.uv_venv_auto = true
""",
        encoding="utf-8",
    )

    # Create source directory
    src = project / "src" / "sample_project"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text('"""Sample project."""\n', encoding="utf-8")

    # Create a custom file
    (project / "README.md").write_text(
        "# sample-project\n\nA test project.\n", encoding="utf-8"
    )

    # Create .gitignore
    (project / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n.venv/\ndata/\noutputs/\n", encoding="utf-8"
    )

    return project


@pytest.fixture
def sample_project_with_aftrignore(sample_project: Path) -> Path:
    """Create a sample project with .aftrignore."""
    (sample_project / ".aftrignore").write_text(
        "extra_data/\n*.log\n", encoding="utf-8"
    )
    return sample_project


class TestCreateFromProjectHelp:
    """Test help and basic invocation."""

    def test_help(self) -> None:
        """Command shows help text."""
        result = runner.invoke(app, ["config", "create-from-project", "--help"])
        assert result.exit_code == 0
        assert "Create a template from an existing project" in result.stdout
        assert ".gitignore" in result.stdout
        assert ".aftrignore" in result.stdout


class TestCreateFromProject:
    """Test the create-from-project command."""

    def test_creates_template_from_project(
        self, sample_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Creates a template from an existing project."""
        # Use a temp config dir to avoid polluting real config
        monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path / "config")
        monkeypatch.setattr(
            config, "get_templates_dir", lambda: tmp_path / "config" / "templates"
        )
        monkeypatch.setattr(
            config, "get_registry_path", lambda: tmp_path / "config" / "registry.toml"
        )
        monkeypatch.setattr(
            config,
            "get_template_path",
            lambda name: tmp_path / "config" / "templates" / f"{name}.toml",
        )

        result = runner.invoke(
            app, ["config", "create-from-project", str(sample_project)]
        )
        assert result.exit_code == 0
        assert "Template created successfully" in result.stdout

        # Check template was saved
        template_path = tmp_path / "config" / "templates" / "sample-project.toml"
        assert template_path.exists()

        content = template_path.read_text()
        assert "Sample Project" in content or "sample-project" in content
        assert "polars" in content
        assert "duckdb" in content

    def test_respects_custom_name(
        self, sample_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Uses custom template name when provided."""
        monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path / "config")
        monkeypatch.setattr(
            config, "get_templates_dir", lambda: tmp_path / "config" / "templates"
        )
        monkeypatch.setattr(
            config, "get_registry_path", lambda: tmp_path / "config" / "registry.toml"
        )
        monkeypatch.setattr(
            config,
            "get_template_path",
            lambda name: tmp_path / "config" / "templates" / f"{name}.toml",
        )

        result = runner.invoke(
            app,
            [
                "config",
                "create-from-project",
                str(sample_project),
                "--name",
                "my-custom-template",
            ],
        )
        assert result.exit_code == 0

        template_path = tmp_path / "config" / "templates" / "my-custom-template.toml"
        assert template_path.exists()

    def test_replaces_project_name_with_placeholders(
        self, sample_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Project name is replaced with {{project_name}} placeholder."""
        monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path / "config")
        monkeypatch.setattr(
            config, "get_templates_dir", lambda: tmp_path / "config" / "templates"
        )
        monkeypatch.setattr(
            config, "get_registry_path", lambda: tmp_path / "config" / "registry.toml"
        )
        monkeypatch.setattr(
            config,
            "get_template_path",
            lambda name: tmp_path / "config" / "templates" / f"{name}.toml",
        )

        result = runner.invoke(
            app, ["config", "create-from-project", str(sample_project)]
        )
        assert result.exit_code == 0

        template_path = tmp_path / "config" / "templates" / "sample-project.toml"
        content = template_path.read_text()

        # README should have placeholder
        assert "{{project_name}}" in content

    def test_respects_gitignore(
        self, sample_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Files matching .gitignore patterns are excluded."""
        # Create a file that should be ignored
        pycache = sample_project / "__pycache__"
        pycache.mkdir()
        (pycache / "module.pyc").write_bytes(b"\x00\x01\x02")

        monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path / "config")
        monkeypatch.setattr(
            config, "get_templates_dir", lambda: tmp_path / "config" / "templates"
        )
        monkeypatch.setattr(
            config, "get_registry_path", lambda: tmp_path / "config" / "registry.toml"
        )
        monkeypatch.setattr(
            config,
            "get_template_path",
            lambda name: tmp_path / "config" / "templates" / f"{name}.toml",
        )

        result = runner.invoke(
            app, ["config", "create-from-project", str(sample_project)]
        )
        assert result.exit_code == 0

        template_path = tmp_path / "config" / "templates" / "sample-project.toml"
        content = template_path.read_text()

        # __pycache__ files should not be in template
        assert "module.pyc" not in content

    def test_respects_aftrignore(
        self,
        sample_project_with_aftrignore: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Files matching .aftrignore patterns are excluded."""
        project = sample_project_with_aftrignore

        # Create files that should be ignored via .aftrignore
        extra_data = project / "extra_data"
        extra_data.mkdir()
        (extra_data / "large_file.csv").write_text("lots,of,data")
        (project / "debug.log").write_text("log content")

        monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path / "config")
        monkeypatch.setattr(
            config, "get_templates_dir", lambda: tmp_path / "config" / "templates"
        )
        monkeypatch.setattr(
            config, "get_registry_path", lambda: tmp_path / "config" / "registry.toml"
        )
        monkeypatch.setattr(
            config,
            "get_template_path",
            lambda name: tmp_path / "config" / "templates" / f"{name}.toml",
        )

        result = runner.invoke(app, ["config", "create-from-project", str(project)])
        assert result.exit_code == 0

        template_path = tmp_path / "config" / "templates" / "sample-project.toml"
        content = template_path.read_text()

        # .aftrignore patterns should be excluded
        assert "large_file.csv" not in content
        assert "debug.log" not in content


class TestCreateFromProjectLimits:
    """Test file count and size limits."""

    def test_fails_with_too_many_files(
        self, sample_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fails when project has too many files."""
        # Create many small files
        for i in range(60):
            (sample_project / f"file_{i}.txt").write_text(f"content {i}")

        monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path / "config")
        monkeypatch.setattr(
            config, "get_templates_dir", lambda: tmp_path / "config" / "templates"
        )
        monkeypatch.setattr(
            config, "get_registry_path", lambda: tmp_path / "config" / "registry.toml"
        )
        monkeypatch.setattr(
            config,
            "get_template_path",
            lambda name: tmp_path / "config" / "templates" / f"{name}.toml",
        )

        result = runner.invoke(
            app, ["config", "create-from-project", str(sample_project)]
        )
        assert result.exit_code == 1
        assert "Too many files" in result.stdout
        assert ".aftrignore" in result.stdout

    def test_fails_with_large_file(
        self, sample_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fails when a file is too large."""
        # Create a large file (>100KB)
        large_content = "x" * (150 * 1024)  # 150KB
        (sample_project / "large_file.txt").write_text(large_content)

        monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path / "config")
        monkeypatch.setattr(
            config, "get_templates_dir", lambda: tmp_path / "config" / "templates"
        )
        monkeypatch.setattr(
            config, "get_registry_path", lambda: tmp_path / "config" / "registry.toml"
        )
        monkeypatch.setattr(
            config,
            "get_template_path",
            lambda name: tmp_path / "config" / "templates" / f"{name}.toml",
        )

        result = runner.invoke(
            app, ["config", "create-from-project", str(sample_project)]
        )
        assert result.exit_code == 1
        assert "size limit" in result.stdout
        assert "large_file.txt" in result.stdout


class TestCreateFromProjectErrors:
    """Test error handling."""

    def test_rejects_default_name(
        self, sample_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cannot create template named 'default'."""
        monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path / "config")
        monkeypatch.setattr(
            config, "get_templates_dir", lambda: tmp_path / "config" / "templates"
        )
        monkeypatch.setattr(
            config, "get_registry_path", lambda: tmp_path / "config" / "registry.toml"
        )
        monkeypatch.setattr(
            config,
            "get_template_path",
            lambda name: tmp_path / "config" / "templates" / f"{name}.toml",
        )

        result = runner.invoke(
            app,
            [
                "config",
                "create-from-project",
                str(sample_project),
                "--name",
                "default",
            ],
        )
        assert result.exit_code == 1
        assert "default" in result.stdout

    def test_prompts_for_overwrite(
        self, sample_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Prompts before overwriting existing template."""
        monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path / "config")
        monkeypatch.setattr(
            config, "get_templates_dir", lambda: tmp_path / "config" / "templates"
        )
        monkeypatch.setattr(
            config, "get_registry_path", lambda: tmp_path / "config" / "registry.toml"
        )
        monkeypatch.setattr(
            config,
            "get_template_path",
            lambda name: tmp_path / "config" / "templates" / f"{name}.toml",
        )

        # Create template first time
        result1 = runner.invoke(
            app, ["config", "create-from-project", str(sample_project)]
        )
        assert result1.exit_code == 0

        # Try to create again - should prompt (decline)
        result2 = runner.invoke(
            app, ["config", "create-from-project", str(sample_project)], input="n\n"
        )
        assert result2.exit_code == 0  # Aborted cleanly

    def test_force_overwrites_without_prompt(
        self, sample_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--force flag overwrites without prompting."""
        monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path / "config")
        monkeypatch.setattr(
            config, "get_templates_dir", lambda: tmp_path / "config" / "templates"
        )
        monkeypatch.setattr(
            config, "get_registry_path", lambda: tmp_path / "config" / "registry.toml"
        )
        monkeypatch.setattr(
            config,
            "get_template_path",
            lambda name: tmp_path / "config" / "templates" / f"{name}.toml",
        )

        # Create template first time
        result1 = runner.invoke(
            app, ["config", "create-from-project", str(sample_project)]
        )
        assert result1.exit_code == 0

        # Force overwrite
        result2 = runner.invoke(
            app, ["config", "create-from-project", str(sample_project), "--force"]
        )
        assert result2.exit_code == 0
        assert "Template created successfully" in result2.stdout
