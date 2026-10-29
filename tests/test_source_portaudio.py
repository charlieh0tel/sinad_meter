import importlib
import sys

import pytest

import source

# How sounddevice fails on a machine with PortAudio but no audio host: it
# defines PortAudioError, then raises it while starting PortAudio at the
# end of its own import.
FAILING_SOUNDDEVICE = """
class PortAudioError(Exception):
    pass

raise {error}("Error initializing PortAudio: PulseAudio_Initialize: "
              "Can't connect to server")
"""


@pytest.fixture
def import_with_sounddevice(tmp_path, monkeypatch):
    """Imports source_portaudio fresh, with a sounddevice that raises error."""

    def run(error):
        (tmp_path / "sounddevice.py").write_text(
            FAILING_SOUNDDEVICE.format(error=error)
        )
        monkeypatch.syspath_prepend(str(tmp_path))
        for name in ("sounddevice", "source_portaudio"):
            monkeypatch.delitem(sys.modules, name, raising=False)
        importlib.import_module("source_portaudio")

    return run


def test_portaudio_that_cannot_start_is_unusable(import_with_sounddevice):
    with pytest.raises(source.UnusableBackendError, match="PortAudio could not start"):
        import_with_sounddevice("PortAudioError")


def test_other_import_errors_propagate(import_with_sounddevice):
    with pytest.raises(ValueError):
        import_with_sounddevice("ValueError")
