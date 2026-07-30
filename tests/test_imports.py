#
# Every dependency is justified by an import somewhere, so importing
# everything is what verifies the dependency list.  The scripts are
# __main__-guarded and the backends touch no hardware at import, so this
# runs no instrument I/O.
#

import importlib
import os
import pathlib

import pytest

import source

os.environ.setdefault("MPLBACKEND", "Agg")

ROOT = pathlib.Path(__file__).parent.parent

# The backends are loaded through load_sources(), which is forgiving by
# design; importing them here instead would raise before the tests below
# could say which one failed and why.
MODULES = sorted(
    p.stem
    for p in ROOT.glob("*.py")
    if p.stem not in source.BACKEND_MODULES and not p.stem.startswith("_")
)


def test_there_are_modules_to_import():
    assert MODULES


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    importlib.import_module(name)


def test_every_backend_loads():
    registry = source.load_sources()
    assert not source.UNAVAILABLE_BACKENDS, source.describe_unavailable_backends()
    assert [s.name for s in registry]
