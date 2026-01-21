"""Configuration directory management and template registry."""

from pathlib import Path
from typing import Optional

import platformdirs
import tomlkit


def get_config_dir() -> Path:
    """Get the aftr configuration directory path.

    Returns:
        ~/.config/aftr/ on Linux/macOS
        ~/AppData/Local/aftr/ on Windows
    """
    return Path(platformdirs.user_config_dir("aftr", appauthor=False))


def get_templates_dir() -> Path:
    """Get the templates directory path."""
    return get_config_dir() / "templates"


def get_registry_path() -> Path:
    """Get the registry.toml file path."""
    return get_config_dir() / "registry.toml"


def ensure_config_dirs() -> None:
    """Ensure configuration directories exist."""
    get_config_dir().mkdir(parents=True, exist_ok=True)
    get_templates_dir().mkdir(parents=True, exist_ok=True)


def load_registry() -> dict:
    """Load the template registry.

    Returns:
        Registry dictionary with 'templates' key containing template metadata.
    """
    registry_path = get_registry_path()
    if not registry_path.exists():
        return {"templates": {}}

    content = registry_path.read_text(encoding="utf-8")
    return tomlkit.parse(content)


def save_registry(registry: dict) -> None:
    """Save the template registry.

    Args:
        registry: Registry dictionary to save.
    """
    ensure_config_dirs()
    registry_path = get_registry_path()

    # Convert to tomlkit document for nice formatting
    doc = tomlkit.document()
    if "templates" in registry:
        doc["templates"] = registry["templates"]
    else:
        doc["templates"] = {}

    registry_path.write_text(tomlkit.dumps(doc), encoding="utf-8")


def register_template(name: str, source_url: Optional[str] = None) -> None:
    """Register a template in the registry.

    Args:
        name: Template name (must match the template file name without .toml).
        source_url: Optional URL where the template was fetched from.
    """
    registry = load_registry()
    if "templates" not in registry:
        registry["templates"] = {}

    registry["templates"][name] = {
        "source_url": source_url or "",
    }
    save_registry(registry)


def unregister_template(name: str) -> bool:
    """Remove a template from the registry.

    Args:
        name: Template name to remove.

    Returns:
        True if template was removed, False if it didn't exist.
    """
    registry = load_registry()
    if "templates" not in registry or name not in registry["templates"]:
        return False

    del registry["templates"][name]
    save_registry(registry)
    return True


def get_registered_templates() -> dict:
    """Get all registered templates.

    Returns:
        Dictionary mapping template names to their metadata.
    """
    registry = load_registry()
    return registry.get("templates", {})


def get_template_source_url(name: str) -> Optional[str]:
    """Get the source URL for a registered template.

    Args:
        name: Template name.

    Returns:
        Source URL if registered and has one, None otherwise.
    """
    registry = load_registry()
    templates = registry.get("templates", {})
    if name in templates:
        url = templates[name].get("source_url", "")
        return url if url else None
    return None


def get_template_path(name: str) -> Path:
    """Get the path to a template file.

    Args:
        name: Template name.

    Returns:
        Path to the template file (may not exist).
    """
    return get_templates_dir() / f"{name}.toml"


def template_exists(name: str) -> bool:
    """Check if a template file exists.

    Args:
        name: Template name.

    Returns:
        True if template file exists.
    """
    return get_template_path(name).exists()
