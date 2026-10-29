import importlib.metadata
import pathlib

import pytest
import registries.errors

import siggen

EXAMPLES = pathlib.Path(__file__).parent.parent / "examples"
EXAMPLE_SPEC = f"{EXAMPLES / 'print_siggen.py'}:PrintSigGen"


@pytest.fixture
def registry():
    """The loaded registry, with whatever a test adds removed afterwards."""
    registry = siggen.load_siggens()
    before = set(registry)
    unavailable = dict(siggen.UNAVAILABLE_BACKENDS)
    yield registry
    for item in set(registry) - before:
        registry.unregister(item)
    siggen.UNAVAILABLE_BACKENDS.clear()
    siggen.UNAVAILABLE_BACKENDS.update(unavailable)


def write_plugin(tmp_path, body):
    path = tmp_path / "plugin.py"
    path.write_text(body)
    return path


def test_example_plugin_file_loads(registry):
    siggen_class = siggen.load_plugin_file(EXAMPLE_SPEC)
    assert registry.get("print") is siggen_class


def test_plugin_file_lacking_members_is_rejected(registry, tmp_path):
    path = write_plugin(tmp_path, "class Bad:\n    api_version = 1\n    name = 'bad'\n")
    with pytest.raises(siggen.InvalidSigGenError, match="set_fm"):
        siggen.load_plugin_file(f"{path}:Bad")
    assert registry.get_or_none("bad") is None


def test_plugin_file_for_another_api_version_is_rejected(registry, tmp_path):
    source = (EXAMPLES / "print_siggen.py").read_text()
    path = write_plugin(tmp_path, source.replace("api_version = 1", "api_version = 2"))
    with pytest.raises(siggen.InvalidSigGenError, match="API version 2"):
        siggen.load_plugin_file(f"{path}:PrintSigGen")


def test_plugin_cannot_take_a_built_in_name(registry, tmp_path):
    source = (EXAMPLES / "print_siggen.py").read_text()
    path = write_plugin(tmp_path, source.replace('"print"', '"hp8663a"'))
    with pytest.raises(registries.errors.RegistrationConflictError):
        siggen.load_plugin_file(f"{path}:PrintSigGen")
    assert registry.get("hp8663a").pretty_name == "HP 8663A"


def test_plugin_spec_needs_a_class(registry):
    with pytest.raises(ValueError, match="FILE.py:CLASS"):
        siggen.load_plugin_file(str(EXAMPLES / "print_siggen.py"))


def fake_entry_points(monkeypatch, *values):
    entry_points = [
        importlib.metadata.EntryPoint(
            name=value, value=value, group=siggen.ENTRY_POINT_GROUP
        )
        for value in values
    ]
    monkeypatch.setattr(importlib.metadata, "entry_points", lambda group: entry_points)


def test_entry_point_plugin_loads(registry, monkeypatch):
    monkeypatch.syspath_prepend(str(EXAMPLES))
    fake_entry_points(monkeypatch, "print_siggen:PrintSigGen")
    siggen.load_siggens()
    assert registry.get("print").pretty_name == "Print (no hardware)"
    # Loading again, as a second script would, is not a collision.
    siggen.load_siggens()
    assert "plugin print_siggen:PrintSigGen" not in siggen.UNAVAILABLE_BACKENDS


def test_broken_entry_point_is_reported_not_raised(registry, monkeypatch):
    fake_entry_points(monkeypatch, "no_such_module:Gen")
    siggen.load_siggens()
    assert any(
        "no_such_module" in line for line in siggen.describe_unavailable_backends()
    )
