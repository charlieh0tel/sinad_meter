#
# PortAudio audio source.
#

import sys

import sounddevice

import source


class PortAudioSource(source.Source):
    name: str = "portaudio"
    pretty_name: str = "PortAudio Source"

    @staticmethod
    def default_sample_frequency():
        return 48_000

    @staticmethod
    def default_record_length():
        return 250e-3

    @staticmethod
    def augment_argparse(parser):
        parser.add_argument(
            "-d", "--device",
            type=str,
            required=True,
            help="audio device to open"
        )

    def __init__(self, args):
        self._num_samples = round(args.sample_frequency * args.record_length)
        try:
            self._stream = sounddevice.Stream(samplerate=args.sample_frequency,
                                              device=args.device)
        except ValueError as e:
            print(f"failed to open sound device: {e})", file=sys.stderr)
            print("try:", file=sys.stderr)
            for d in sounddevice.query_devices():
                index = d['index']
                name = d['name']
                max_input_channels = d['max_input_channels']
                if not max_input_channels:
                    continue
                print(f" {index:2} {name:40s} input_channels={max_input_channels}",
                      file=sys.stderr)
            raise
        self._channel = 0

    def start(self):
        self._stream.start()

    def stop(self):
        self._stream.stop()

    def close(self):
        self._stream.close()

    def read(self):
        samples = self._stream.read(self._num_samples)
        return samples[0][:, self._channel]

    def sample_range(self):
        return (-1., 1.)

    def sample_unit(self):
        return "AU"

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_args):
        self.stop()
        self.close()


#
source.SOURCE_REGISTRY.register(PortAudioSource)
