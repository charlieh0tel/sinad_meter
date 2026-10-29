import contextlib

import registries

import backends

#
# A signal generator is a class with these members:
#
#   name (str)               -- what -G selects it by
#   pretty_name (str)        -- for messages
#   default_resource (str)   -- VISA resource used when none is given
#   __init__(resource_manager, resource_name)
#   open(), close()
#   set_power(power_dBm)     -- takes effect immediately, even with the
#                               output on
#   set_output(on)
#
# Use it through opened(), which owns turning the output off.
#


class SigGenRegistry(registries.Registry):
    lookup_attrs = ("name",)


SIGGEN_REGISTRY = SigGenRegistry()

# Each backend registers itself in SIGGEN_REGISTRY when imported.
BACKEND_MODULES = ("siggen_hp8663a", "siggen_rs_smb100a")

# Backends whose import failed, as module name -> the exception.
UNAVAILABLE_BACKENDS = {}


def load_siggens():
    """
    Imports the signal generator backends, each of which registers itself.

    Backends that cannot be imported are skipped and recorded in
    UNAVAILABLE_BACKENDS.

    Returns:
        SigGenRegistry: the populated registry
    """
    backends.import_backends(BACKEND_MODULES, UNAVAILABLE_BACKENDS)
    return SIGGEN_REGISTRY


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
