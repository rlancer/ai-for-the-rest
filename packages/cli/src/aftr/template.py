"""Template model and loading functionality."""

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Optional

import tomlkit

from aftr import config


@dataclass
class Template:
    """Represents a project template configuration."""

    # Template metadata
    name: str
    description: str = ""
    version: str = "1.0.0"
    source_url: str = ""

    # Project configuration
    requires_python: str = ">=3.11"
    dependencies: dict[str, str] = field(default_factory=dict)
    optional_dependencies: dict[str, list[str]] = field(default_factory=dict)

    # mise configuration
    mise_tools: dict[str, str] = field(default_factory=dict)

    # Directory structure
    extra_directories: list[str] = field(default_factory=list)

    # Additional files to create
    files: dict[str, str] = field(default_factory=dict)

    # uv configuration
    uv_indexes: list[dict[str, str]] = field(default_factory=list)
    uv_sources: dict[str, dict[str, str]] = field(default_factory=dict)

    # Notebook configuration
    notebook_include_example: bool = True
    notebook_imports: list[str] = field(default_factory=list)


def parse_template(content: str) -> Template:
    """Parse a TOML template string into a Template object.

    Args:
        content: TOML string content.

    Returns:
        Parsed Template object.
    """
    doc = tomlkit.parse(content)

    # Extract template metadata
    template_section = doc.get("template", {})
    name = template_section.get("name", "unnamed")
    description = template_section.get("description", "")
    version = template_section.get("version", "1.0.0")
    source_url = template_section.get("source_url", "")

    # Extract project configuration
    project_section = doc.get("project", {})
    requires_python = project_section.get("requires-python", ">=3.11")

    # Parse dependencies
    dependencies = {}
    deps_section = project_section.get("dependencies", {})
    for pkg, ver in deps_section.items():
        dependencies[pkg] = ver

    # Parse optional dependencies
    optional_deps = {}
    opt_deps_section = project_section.get("optional-dependencies", {})
    for group, pkgs in opt_deps_section.items():
        optional_deps[group] = list(pkgs)

    # Extract mise configuration
    mise_section = doc.get("mise", {})
    mise_tools = {}
    for tool, ver in mise_section.items():
        mise_tools[tool] = ver

    # Extract directories
    dirs_section = doc.get("directories", {})
    extra_directories = list(dirs_section.get("include", []))

    # Extract files
    files = {}
    files_section = doc.get("files", {})
    for file_path, file_config in files_section.items():
        if isinstance(file_config, dict):
            content_val = file_config.get("content", "")
            files[file_path] = content_val
        elif isinstance(file_config, str):
            files[file_path] = file_config

    # Extract uv configuration
    uv_section = doc.get("uv", {})
    uv_indexes = []
    for idx in uv_section.get("indexes", []):
        uv_indexes.append({str(k): str(v) for k, v in idx.items()})
    uv_sources = {}
    for pkg, src in uv_section.get("sources", {}).items():
        uv_sources[str(pkg)] = {str(k): str(v) for k, v in src.items()}

    # Extract notebook configuration
    notebook_section = doc.get("notebook", {})
    notebook_include_example = notebook_section.get("include_example", True)
    notebook_imports = list(notebook_section.get("imports", []))

    return Template(
        name=name,
        description=description,
        version=version,
        source_url=source_url,
        requires_python=requires_python,
        dependencies=dependencies,
        optional_dependencies=optional_deps,
        mise_tools=mise_tools,
        extra_directories=extra_directories,
        files=files,
        uv_indexes=uv_indexes,
        uv_sources=uv_sources,
        notebook_include_example=notebook_include_example,
        notebook_imports=notebook_imports,
    )


def load_default_template() -> Template:
    """Load the built-in default template.

    Returns:
        The default Template object.
    """
    # Use importlib.resources to load the bundled template
    template_files = resources.files("aftr.templates")
    default_toml = template_files.joinpath("default.toml")
    content = default_toml.read_text(encoding="utf-8")
    return parse_template(content)


def load_template(name: str) -> Optional[Template]:
    """Load a template by name.

    Args:
        name: Template name. 'default' loads the built-in template.

    Returns:
        Template object if found, None otherwise.
    """
    if name == "default":
        return load_default_template()

    template_path = config.get_template_path(name)
    if not template_path.exists():
        return None

    content = template_path.read_text(encoding="utf-8")
    return parse_template(content)


def save_template(name: str, content: str) -> Path:
    """Save a template to the templates directory.

    Args:
        name: Template name (without .toml extension).
        content: TOML template content.

    Returns:
        Path where the template was saved.
    """
    config.ensure_config_dirs()
    template_path = config.get_template_path(name)
    template_path.write_text(content, encoding="utf-8")
    return template_path


def get_default_template_content() -> str:
    """Get the raw content of the default template.

    Returns:
        Default template TOML content as a string.
    """
    template_files = resources.files("aftr.templates")
    default_toml = template_files.joinpath("default.toml")
    return default_toml.read_text(encoding="utf-8")


def list_available_templates() -> list[str]:
    """List all available template names.

    Returns:
        List of template names, always includes 'default'.
    """
    templates = ["default"]

    # Add registered templates that exist
    registered = config.get_registered_templates()
    for name in registered:
        if config.template_exists(name) and name not in templates:
            templates.append(name)

    return sorted(templates)


def get_template_info(name: str) -> Optional[dict]:
    """Get information about a template.

    Args:
        name: Template name.

    Returns:
        Dictionary with template info, or None if not found.
    """
    template = load_template(name)
    if template is None:
        return None

    source_url = config.get_template_source_url(name) or template.source_url

    return {
        "name": template.name,
        "description": template.description,
        "version": template.version,
        "source_url": source_url,
        "requires_python": template.requires_python,
        "dependencies_count": len(template.dependencies),
        "extra_files_count": len(template.files),
        "extra_directories": template.extra_directories,
        "is_builtin": name == "default",
    }
