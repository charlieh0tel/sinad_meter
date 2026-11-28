#
# PortAudio audio source.
#

import argparse
import sys
import threading
from collections.abc import Sequence
from typing import Any, TextIO

import numpy as np
import numpy.typing as npt

import source

try:
    import sounddevice
except Exception as e:
    # sounddevice starts PortAudio as the last step of its import, so a
    # machine with the library but no audio host -- a headless box whose
    # PortAudio talks to PulseAudio, say -- fails here with sounddevice's
    # own PortAudioError.  That class cannot be named before the import
    # succeeds, hence the check by name; anything else propagates.
    if type(e).__name__ != "PortAudioError":
        raise
    raise source.UnusableBackendError(f"PortAudio could not start: {e}") from e


def _int_or_str(text: str) -> int | str:
    # sounddevice selects a device by integer index or by a substring of
    # its name, so a bare number is an index and anything else is a name.
    try:
        return int(text)
    except ValueError:
        return text


def _print_input_devices(file: TextIO) -> None:
    for d in sounddevice.query_devices():
        if not d["max_input_channels"]:
            continue
        print(
            f" {d['index']:2} {d['name']:40s} input_channels={d['max_input_channels']}",
            file=file,
        )


class _ListDevicesAction(argparse.Action):
    # Lists devices and exits, like argparse's own --help. Because the
    # action runs as the option is consumed, it exits before argparse
    # enforces the required -d, so --list-devices needs no device.
    def __init__(self, option_strings: Sequence[str], dest: str, **kwargs: Any) -> None:
        super().__init__(
            option_strings, dest, nargs=0, default=argparse.SUPPRESS, **kwargs
        )

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        _print_input_devices(sys.stdout)
        parser.exit()


class PortAudioSource(source.Source):
    name: str = "portaudio"
    pretty_name: str = "PortAudio Source"
    # A background callback drains the device continuously, but read()
    # returns only the newest window and discards whatever piled up while
    # the caller was busy, so consecutive reads are not one uninterrupted
    # stream and stateful filtering must reset between them.
    continuous: bool = False

    @staticmethod
    def default_sample_frequency() -> float:
        return 48_000

    @staticmethod
    def default_record_length() -> float:
        return 250e-3

    @staticmethod
    def augment_argparse(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-d",
            "--device",
            type=_int_or_str,
            required=True,
            help="audio device to open: numeric index or name substring "
            "(see --list-devices)",
        )
        parser.add_argument(
            "--list-devices",
            action=_ListDevicesAction,
            help="list available input devices and exit",
        )

    def __init__(self, args: argparse.Namespace) -> None:
        self._num_samples = round(args.sample_frequency * args.record_length)
        self._channel = 0
        # Guards _blocks / _available and signals read() when a fresh
        # window has accumulated.
        self._cond = threading.Condition()
        self._blocks: list[npt.NDArray[np.float32]] = []
        self._available = 0
        self._overflowed = False
        try:
            # InputStream, not Stream: Stream is duplex and a scalar
            # device applies to both halves, so a capture-only device
            # fails to open.
            #
            # A callback stream (rather than a blocking read) keeps the
            # device drained even while the caller spends time rendering,
            # which is what prevents the input buffer from overflowing.
            self._stream = sounddevice.InputStream(
                samplerate=args.sample_frequency,
                device=args.device,
                callback=self._callback,
            )
        except ValueError as e:
            print(f"failed to open sound device: {e})", file=sys.stderr)
            print("try:", file=sys.stderr)
            _print_input_devices(sys.stderr)
            raise

    def _callback(
        self,
        indata: npt.NDArray[np.float32],
        _frames: int,
        _time: object,
        status: sounddevice.CallbackFlags,
    ) -> None:
        # Runs on PortAudio's thread; indata is reused after we return, so
        # copy the channel we keep.
        with self._cond:
            if status.input_overflow:
                self._overflowed = True
            self._blocks.append(indata[:, self._channel].copy())
            self._available += len(indata)
            self._cond.notify()

    def start(self) -> None:
        self._stream.start()

    def stop(self) -> None:
        self._stream.stop()

    def close(self) -> None:
        self._stream.close()

    def read(self) -> npt.NDArray[np.float32]:
        with self._cond:
            self._cond.wait_for(lambda: self._available >= self._num_samples)
            samples = np.concatenate(self._blocks)
            overflowed = self._overflowed
            # Drop everything: the next read starts fresh from live audio,
            # so the backlog captured while the caller was busy is thrown
            # away rather than played back late.
            self._blocks = []
            self._available = 0
            self._overflowed = False
        if overflowed:
            print(
                "PortAudioSource: input overflowed; samples were dropped",
                file=sys.stderr,
            )
        # The newest num_samples are one contiguous span; older backlog is
        # discarded to stay live.
        return samples[-self._num_samples :]

    def sample_range(self) -> tuple[float, float]:
        return (-1.0, 1.0)

    def sample_unit(self) -> str:
        return "AU"


source.SOURCE_REGISTRY.register(PortAudioSource)
