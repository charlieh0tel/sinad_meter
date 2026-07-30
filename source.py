import importlib

import registries


class Source:
    name: str = "error"
    pretty_name: str = "error"

    @staticmethod
    def default_sample_frequency():
        raise NotImplementedError("default_sample_frequency is not implemented")

    @staticmethod
    def default_record_length():
        raise NotImplementedError("default_record_length is not implemented")

    # Whether read() returns consecutive samples of one uninterrupted
    # stream.  Record-based backends return an independent capture each
    # call, with a gap in between, so stateful filtering must not carry
    # across reads.
    continuous: bool = True

    @staticmethod
    def augment_argparse(parser):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def close(self):
        pass

    def read(self):
        raise NotImplementedError("read is not implemented")

    def sample_range(self):
        raise NotImplementedError("sample_range is not implemented")

    def sample_unit(self):
        raise NotImplementedError("sample_unit is not implemented")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_args):
        self.stop()
        self.close()


class SourceRegistry(registries.Registry[type[Source]]):
    lookup_attrs = ("name",)


SOURCE_REGISTRY = SourceRegistry()


#
# Each backend registers itself when imported, so the registry is only
# as complete as the set of backends that have been imported.  Importing
# them here keeps that in one place instead of relying on every script
# to import backends it never names.
#
_BACKEND_MODULES = ("source_digilent", "source_portaudio")

# Backends whose import failed, as module name -> the ImportError.  A
# missing backend is not fatal: pydwf is of no interest if you are
# capturing through PortAudio, and vice versa.
UNAVAILABLE_BACKENDS = {}


def load_sources():
    """
    Imports the source backends, each of which registers itself.

    Backends that cannot be imported are skipped and recorded in
    UNAVAILABLE_BACKENDS.

    Returns:
        SourceRegistry: the populated registry
    """
    for module_name in _BACKEND_MODULES:
        try:
            importlib.import_module(module_name)
        except (ImportError, OSError) as e:
            # OSError, not just ImportError: a backend's Python package
            # can be installed while the shared library it binds to is
            # not, which is how sounddevice reports a missing PortAudio.
            UNAVAILABLE_BACKENDS[module_name] = e
    return SOURCE_REGISTRY


def describe_unavailable_backends():
    """
    Describes the backends that failed to import, for use in messages.

    Returns:
        list[str]: one line per unavailable backend, empty if all loaded
    """
    return [
        f"{module_name} is unavailable: {e}"
        for module_name, e in sorted(UNAVAILABLE_BACKENDS.items())
    ]
