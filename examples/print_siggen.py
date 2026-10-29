#
# An example signal generator plugin.  It drives no hardware: it prints
# what it is asked to do, which also makes it a dry run for a sweep.
#
#   uv run ./auto_sinad.py --siggen-plugin examples/print_siggen.py:PrintSigGen \
#       -G print -f 146.52e6 ...
#
# Note that it imports nothing from sinad_meter.
#


class PrintSigGen:
    api_version = 1
    name = "print"
    pretty_name = "Print (no hardware)"
    default_resource = "none"

    def __init__(self, _resource_manager, resource_name):
        self.resource_name = resource_name

    def open(self):
        print(f"[{self.name}] open {self.resource_name}")

    def close(self):
        print(f"[{self.name}] close")

    def set_frequency(self, frequency_Hz):
        print(f"[{self.name}] carrier {frequency_Hz:g} Hz")

    def set_fm(self, rate_Hz, deviation_Hz):
        print(f"[{self.name}] FM {rate_Hz:g} Hz rate, {deviation_Hz:g} Hz deviation")

    def set_power(self, power_dBm):
        print(f"[{self.name}] power {power_dBm:g} dBm")

    def set_output(self, on):
        print(f"[{self.name}] output {'on' if on else 'off'}")
