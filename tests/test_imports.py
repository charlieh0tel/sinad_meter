#
# Every dependency is justified by an import somewhere, so importing
# everything is what verifies the dependency list.  The scripts are
# __main__-guarded and the backends touch no hardware at import, so this
# runs no instrument I/O.
#

import importlib
import pathlib

import pytest

import source

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
    unusable = {
        name: e
        for name, e in source.UNAVAILABLE_BACKENDS.items()
        if isinstance(e, source.UnusableBackendError)
    }
    missing = source.UNAVAILABLE_BACKENDS.keys() - unusable.keys()
    assert not missing, source.describe_unavailable_backends()
    # A machine that cannot run a backend, such as a CI runner with no
    # audio server, is not a missing dependency.  Skip, so that it shows
    # as not checked rather than as passing.
    if unusable:
        pytest.skip("; ".join(f"{name}: {e}" for name, e in sorted(unusable.items())))
    assert [s.name for s in registry]
