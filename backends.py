import importlib

#
# A backend is a module that registers itself in some registry when
# imported, so a registry is only as complete as the set of its backends
# that have been imported.  These import a set of them in one place
# instead of relying on every script to import backends it never names.
#


def import_backends(module_names, unavailable):
    """
    Imports backend modules, each of which registers itself.

    A missing backend is not fatal: pydwf is of no interest if you are
    capturing through PortAudio, and vice versa.

    Args:
        module_names (Iterable[str]): the modules to import
        unavailable (dict): updated with module name -> the exception, for
                            each module that could not be imported
    """
    for module_name in module_names:
        try:
            importlib.import_module(module_name)
        except (ImportError, OSError) as e:
            # OSError, not just ImportError: a backend's Python package
            # can be installed while the shared library it binds to is
            # not, which is how sounddevice reports a missing PortAudio.
            unavailable[module_name] = e


def describe_unavailable(unavailable):
    """
    Describes the backends that could not be loaded, for use in messages.

    Args:
        unavailable (dict): name -> the exception, as from import_backends

    Returns:
        list[str]: one line per unavailable backend, empty if all loaded
    """
    return [f"{name} is unavailable: {e}" for name, e in sorted(unavailable.items())]
