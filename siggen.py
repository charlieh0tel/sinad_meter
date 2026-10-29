import contextlib
import importlib.metadata
import importlib.util
import pathlib

import registries
import registries.errors

import backends

#
# A signal generator is a class with these members.  It need not import
# or subclass anything from here, so that one can be written and
# installed without changing this project; see the README.
#
#   api_version (int)        -- API_VERSION
#   name (str)               -- what -G selects it by
#   pretty_name (str)        -- for messages
#   default_resource (str)   -- VISA resource used when none is given
#   __init__(resource_manager, resource_name)
#   open(), close()
#   set_frequency(frequency_Hz)
#   set_fm(rate_Hz, deviation_Hz)
#                            -- FM from the internal modulation source.
#                               Raises NotImplementedError if the
#                               generator cannot do it.
#   set_power(power_dBm)     -- takes effect immediately, even with the
#                               output on
#   set_output(on)
#
# Use it through opened(), which owns turning the output off.
#


API_VERSION = 1

REQUIRED_MEMBERS = (
    "api_version",
    "name",
    "pretty_name",
    "default_resource",
    "open",
    "close",
    "set_frequency",
    "set_fm",
    "set_power",
    "set_output",
)

# Installed packages declare plugins under this entry point group.
ENTRY_POINT_GROUP = "sinad_meter.siggens"


class InvalidSigGenError(Exception):
    pass


# What loading a plugin can fail with, short of the plugin's own code
# raising at import, which is left to propagate.
PLUGIN_ERRORS = (
    ImportError,
    OSError,
    SyntaxError,
    AttributeError,
    InvalidSigGenError,
    registries.errors.BaseRegistrationError,
)


class SigGenRegistry(registries.Registry):
    lookup_attrs = ("name",)


SIGGEN_REGISTRY = SigGenRegistry()


def register(siggen_class):
    """
    Checks a signal generator class against the contract and registers it.

    Args:
        siggen_class: the class

    Raises:
        InvalidSigGenError: if it lacks members or targets another API
        registries.errors.BaseRegistrationError: if it is already
            registered, or its name is taken
    """
    missing = [m for m in REQUIRED_MEMBERS if not hasattr(siggen_class, m)]
    if missing:
        raise InvalidSigGenError(f"{siggen_class!r} lacks {', '.join(missing)}")
    if siggen_class.api_version != API_VERSION:
        raise InvalidSigGenError(
            f"{siggen_class!r} is for API version {siggen_class.api_version}, "
            f"not {API_VERSION}"
        )
    SIGGEN_REGISTRY.register(siggen_class)


# Each backend registers itself in SIGGEN_REGISTRY when imported.
BACKEND_MODULES = ("siggen_hp8663a", "siggen_rs_smb100a")

# Backends and plugins that failed to load, as name -> the exception.
UNAVAILABLE_BACKENDS = {}


def load_siggens():
    """
    Imports the built-in signal generators, then any installed plugins.

    Built-ins go first so that they keep their names if a plugin
    collides.  Those that cannot be loaded are skipped and recorded in
    UNAVAILABLE_BACKENDS.

    Returns:
        SigGenRegistry: the populated registry
    """
    backends.import_backends(BACKEND_MODULES, UNAVAILABLE_BACKENDS)
    for entry_point in importlib.metadata.entry_points(group=ENTRY_POINT_GROUP):
        try:
            siggen_class = entry_point.load()
            if siggen_class not in SIGGEN_REGISTRY:
                register(siggen_class)
        except PLUGIN_ERRORS as e:
            UNAVAILABLE_BACKENDS[f"plugin {entry_point.value}"] = e
    return SIGGEN_REGISTRY


def load_plugin_file(spec):
    """
    Loads a signal generator class from a Python file and registers it.

    Args:
        spec (str): "path/to/file.py:ClassName"

    Returns:
        the class

    Raises:
        ValueError: if spec is malformed
        any of PLUGIN_ERRORS: if the class cannot be loaded or registered
    """
    (path, _, class_name) = spec.rpartition(":")
    if not path or not class_name:
        raise ValueError(f"expected FILE.py:CLASS, not {spec!r}")
    module_spec = importlib.util.spec_from_file_location(
        f"siggen_plugin_{pathlib.Path(path).stem}", path
    )
    if module_spec is None:
        raise ImportError(f"{path} is not a Python file")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    siggen_class = getattr(module, class_name)
    register(siggen_class)
    return siggen_class


def describe_unavailable_backends():
    """
    Describes the backends that failed to import, for use in messages.

    Returns:
        list[str]: one line per unavailable backend, empty if all loaded
    """
    return backends.describe_unavailable(UNAVAILABLE_BACKENDS)


@contextlib.contextmanager
def opened(siggen):
    """
    Opens a signal generator for the duration of a with block.

    The output is turned off on the way out, however we leave, so that
    the generator is never left transmitting.  This is done here rather
    than trusted to each generator's close().

    Args:
        siggen: the signal generator

    Yields:
        the signal generator, opened
    """
    siggen.open()
    try:
        yield siggen
    finally:
        try:
            siggen.set_output(False)
        finally:
            siggen.close()
