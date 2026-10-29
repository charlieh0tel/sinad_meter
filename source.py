import argparse
from typing import Self

import numpy as np
import numpy.typing as npt
import registries

import backends


class Source:
    name: str = "error"
    pretty_name: str = "error"

    def __init__(self, args: argparse.Namespace) -> None:
        pass

    @staticmethod
    def default_sample_frequency() -> float:
        raise NotImplementedError("default_sample_frequency is not implemented")

    @staticmethod
    def default_record_length() -> float:
        raise NotImplementedError("default_record_length is not implemented")

    # Whether read() returns consecutive samples of one uninterrupted
    # stream.  Record-based backends return an independent capture each
    # call, with a gap in between, so stateful filtering must not carry
    # across reads.
    continuous: bool = True

    @staticmethod
    def augment_argparse(parser: argparse.ArgumentParser) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def close(self) -> None:
        pass

    def read(self) -> npt.NDArray[np.floating]:
        raise NotImplementedError("read is not implemented")

    def sample_range(self) -> tuple[float, float]:
        raise NotImplementedError("sample_range is not implemented")

    def sample_unit(self) -> str:
        raise NotImplementedError("sample_unit is not implemented")

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *_args: object) -> None:
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
UNAVAILABLE_BACKENDS: dict[str, ImportError | OSError] = {}


def load_sources() -> SourceRegistry:
    """
    Imports the source backends, each of which registers itself.

    Backends that cannot be imported are skipped and recorded in
    UNAVAILABLE_BACKENDS.

    Returns:
        SourceRegistry: the populated registry
    """
    backends.import_backends(BACKEND_MODULES, UNAVAILABLE_BACKENDS)
    return SOURCE_REGISTRY


def describe_unavailable_backends() -> list[str]:
    """
    Describes the backends that failed to import, for use in messages.

    Returns:
        list[str]: one line per unavailable backend, empty if all loaded
    """
    return backends.describe_unavailable(UNAVAILABLE_BACKENDS)
