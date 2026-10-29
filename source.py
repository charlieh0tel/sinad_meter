import registries

import backends


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


class UnusableBackendError(ImportError):
    """
    A backend whose packages are installed but which this machine cannot
    run, such as PortAudio with no audio server to connect to.
    """


# Each backend registers itself in SOURCE_REGISTRY when imported.
BACKEND_MODULES = ("source_digilent", "source_portaudio")

# Backends whose import failed, as module name -> the exception.
UNAVAILABLE_BACKENDS = {}


def load_sources():
    """
    Imports the source backends, each of which registers itself.

    Backends that cannot be imported are skipped and recorded in
    UNAVAILABLE_BACKENDS.

    Returns:
        SourceRegistry: the populated registry
    """
    backends.import_backends(BACKEND_MODULES, UNAVAILABLE_BACKENDS)
    return SOURCE_REGISTRY


def describe_unavailable_backends():
    """
    Describes the backends that failed to import, for use in messages.

    Returns:
        list[str]: one line per unavailable backend, empty if all loaded
    """
    return backends.describe_unavailable(UNAVAILABLE_BACKENDS)
