"""Structural tests that enforce layering rules and code quality invariants."""

import ast
import os
from pathlib import Path

import pytest

API_ROOT = Path(__file__).parent.parent
APP_ROOT = API_ROOT / "app"

# Layer ordering: lower layers must not import from higher layers
LAYER_ORDER = ["types", "config", "repo", "service", "runtime"]

# Map of layer -> set of layers it must NOT import from
FORBIDDEN_IMPORTS: dict[str, set[str]] = {}
for i, layer in enumerate(LAYER_ORDER):
    # Each layer cannot import from layers above it
    FORBIDDEN_IMPORTS[layer] = set(LAYER_ORDER[i + 1 :])

NON_PRODUCTION_DIRS = {".venv", "__pycache__", "tests"}


def _get_python_files(directory: Path, excluded_dirs: set[str] | None = None) -> list[Path]:
    """Get all .py files in a directory recursively."""
    excluded_dirs = excluded_dirs or set()
    files = []
    for root, dirnames, filenames in os.walk(directory):
        dirnames[:] = sorted(name for name in dirnames if name not in excluded_dirs)
        for filename in sorted(filenames):
            if filename.endswith(".py"):
                files.append(Path(root) / filename)
    return files


def _get_application_python_files(api_root: Path = API_ROOT) -> list[Path]:
    """Get Python application files, excluding tests and tooling."""
    return _get_python_files(api_root, excluded_dirs=NON_PRODUCTION_DIRS)


def _get_imports(filepath: Path) -> list[str]:
    """Extract all import module names from a Python file."""
    try:
        tree = ast.parse(filepath.read_text())
    except SyntaxError:
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _layer_of_import(module: str) -> str | None:
    """Return the layer name if the import is from app.<layer>, else None."""
    if not module.startswith("app."):
        return None
    parts = module.split(".")
    if len(parts) >= 2:
        return parts[1]
    return None


def _repo_only_import_violations(
    modules: tuple[str, ...], label: str, api_root: Path = API_ROOT
) -> list[str]:
    """Find imports that must stay confined to app/repo/."""
    violations = []
    repo_root = api_root / "app" / "repo"
    for pyfile in _get_application_python_files(api_root):
        if pyfile.is_relative_to(repo_root):
            continue
        for imp in _get_imports(pyfile):
            if any(imp == module or imp.startswith(f"{module}.") for module in modules):
                rel = pyfile.relative_to(api_root)
                violations.append(f"{rel}: {label} imported outside repo/")
    return violations


def test_no_backward_imports():
    """Verify no layer imports from a higher layer."""
    violations = []
    for layer in LAYER_ORDER:
        layer_dir = APP_ROOT / layer
        if not layer_dir.exists():
            continue
        for pyfile in _get_python_files(layer_dir):
            for imp in _get_imports(pyfile):
                imported_layer = _layer_of_import(imp)
                if imported_layer and imported_layer in FORBIDDEN_IMPORTS[layer]:
                    rel = pyfile.relative_to(APP_ROOT.parent)
                    violations.append(
                        f"{rel}: {layer}/ imports from {imported_layer}/ ({imp})"
                    )
    assert violations == [], "Backward import violations:\n" + "\n".join(violations)


def test_boto3_only_in_repo():
    """Verify boto3 is only imported in app/repo/."""
    violations = _repo_only_import_violations(("boto3", "botocore"), "boto3/botocore")
    assert violations == [], "boto3 boundary violations:\n" + "\n".join(violations)


def test_httpx_only_in_repo():
    """Verify httpx is only imported in app/repo/."""
    violations = _repo_only_import_violations(("httpx",), "httpx")
    assert violations == [], "httpx boundary violations:\n" + "\n".join(violations)


@pytest.mark.parametrize(
    ("relative_path", "expected_violation"),
    [
        ("main.py", "main.py: httpx imported outside repo/"),
        ("worker.py", "worker.py: httpx imported outside repo/"),
        ("app/__init__.py", "app/__init__.py: httpx imported outside repo/"),
        ("app/runtime/startup.py", "app/runtime/startup.py: httpx imported outside repo/"),
    ],
)
def test_repo_only_imports_scan_non_repo_application_files(
    tmp_path: Path, relative_path: str, expected_violation: str
):
    """Verify repo-only import checks include non-repo production files."""
    target = tmp_path / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("import httpx\n")

    repo_root = tmp_path / "app" / "repo"
    repo_root.mkdir(parents=True)
    (repo_root / "client.py").write_text("import httpx\n")

    violations = _repo_only_import_violations(("httpx",), "httpx", api_root=tmp_path)

    assert violations == [expected_violation]


def test_file_size_limits():
    """Verify no Python file exceeds 300 lines."""
    violations = []
    for pyfile in _get_python_files(APP_ROOT):
        line_count = len(pyfile.read_text().splitlines())
        if line_count > 300:
            rel = pyfile.relative_to(APP_ROOT.parent)
            violations.append(f"{rel}: {line_count} lines (max 300)")
    assert violations == [], "File size violations:\n" + "\n".join(violations)


def test_all_layers_exist():
    """Verify all expected layer directories exist."""
    for layer in LAYER_ORDER:
        layer_dir = APP_ROOT / layer
        assert layer_dir.exists(), f"Missing layer directory: app/{layer}/"
        init_file = layer_dir / "__init__.py"
        assert init_file.exists(), f"Missing __init__.py in app/{layer}/"
