#! /usr/bin/env python3

import argparse
import sys

import numpy as np
import pandas as pd
import pyvisa

import filters
import source as source_pkg
from instruments import hp_8662a, keithley_2015, rs_smb100a
from vendored import pysnr

DEFAULT_RS_SMB100A_SIG_GEN_RESOURCE = "TCPIP::rssmb100a180609.local::INSTR"
DEFAULT_HP_8663A_SIG_GEN_RESOURCE = "TCPIP::e5810a::gpib0,25::INSTR"
DEFAULT_KEITHLEY_2015_RESOURCE = "TCPIP::e5810a::gpib0,22::INSTR"

DEFAULT_SIGGEN = "hp8663a"


def _make_hp8663a(_resource_manager, resource_name):
    return hp_8662a.HP8663A(resource_name)


def _make_rs_smb100a(resource_manager, resource_name):
    return rs_smb100a.RhodeSchwarzSMB100A(resource_manager, resource_name)


# Signal generator name -> (factory, default VISA resource).  The two
# drivers take different arguments, hence the factories.
SIGGENS = {
    "hp8663a": (_make_hp8663a, DEFAULT_HP_8663A_SIG_GEN_RESOURCE),
    "rssmb100a": (_make_rs_smb100a, DEFAULT_RS_SMB100A_SIG_GEN_RESOURCE),
}


def make_siggen(name, resource_manager, resource_name=None):
    """
    Makes a signal generator by name.

    Args:
        name (str): a key of SIGGENS
        resource_manager (pyvisa.ResourceManager): the resource manager
        resource_name (str): VISA resource, or None for the default

    Returns:
        the signal generator
    """
    (factory, default_resource_name) = SIGGENS[name]
    return factory(resource_manager, resource_name or default_resource_name)


def _summarize(readings):
    """
    Summarizes a set of readings, ignoring those that were invalid.

    Out-of-range instrument responses are recorded as NaN, so a plain
    mean would let one bad reading poison the whole set.

    Args:
        readings (list[float]): the readings, possibly containing NaN

    Returns:
        (float, float, int): mean, standard deviation, and how many
                             readings were valid.  Mean and standard
                             deviation are NaN if none were.
    """
    readings = np.asarray(readings, dtype=float)
    valid = readings[~np.isnan(readings)]
    if valid.size == 0:
        return (float("nan"), float("nan"), 0)
    return (valid.mean(), valid.std(), valid.size)


def _open_keithley(resource_manager, resource_name, hpf_cutoff, lpf_cutoff):
    """
    Opens and configures the Keithley 2015 as a SINAD reference.

    Args:
        resource_manager (pyvisa.ResourceManager): the resource manager
        resource_name (str): VISA resource of the meter
        hpf_cutoff (float): highpass cutoff (Hz), or None
        lpf_cutoff (float): lowpass cutoff (Hz), or None

    Returns:
        keithley_2015.Keithley2015: the opened meter
    """
    meter = keithley_2015.Keithley2015(resource_manager, resource_name).open()
    meter.inst.timeout = 10e3
    meter.reset()
    meter.write(":SENS:FUNC 'dist'")
    meter.write(":SENS:DIST:TYPE SINAD")
    meter.write(":SENS:DIST:SFIL NONE")
    meter.write(":SENS:DIST:FREQ:AUTO ON")
    meter.write(":SENS:DIST:SFIL NONE")  # CCITT?
    meter.write(":SENS:DIST:RANG:AUTO ON")
    meter.write(":UNIT:DIST DB")
    # LCO/HCO are the Keithley's low and high cutoffs, i.e. the passband
    # edges, matching hpf_cutoff and lpf_cutoff respectively.
    if hpf_cutoff is not None:
        assert hpf_cutoff >= 20
        meter.write(f":SENS:DIST:LCO {int(hpf_cutoff)}")
        meter.write(":SENS:DIST:LCO:STATE ON")
    if lpf_cutoff is not None:
        assert lpf_cutoff <= 50_000
        meter.write(f":SENS:DIST:HCO {int(lpf_cutoff)}")
        meter.write(":SENS:DIST:HCO:STATE ON")
    return meter


def run(
    source_class,
    source_args,
    siggen_name,
    siggen_resource_name,
    keithley_resource_name,
    output_path,
):
    hpf_cutoff = 200.0
    lpf_cutoff = 4000.0

    rm = pyvisa.ResourceManager("@py")
    siggen_resource = make_siggen(siggen_name, rm, siggen_resource_name)

    keithley_meter = None
    if keithley_resource_name:
        keithley_meter = _open_keithley(
            rm, keithley_resource_name, hpf_cutoff, lpf_cutoff
        )

    sample_frequency = source_args.sample_frequency
    record_length = source_args.record_length
    num_samples = round(sample_frequency * record_length)

    audio_filter = filters.make_audio_filter(sample_frequency, hpf_cutoff, lpf_cutoff)

    data = []

    with siggen_resource as siggen:
        try:
            for power_dBm in np.linspace(-125, -95, 51):
                print(f"{power_dBm:6.3f}", end="")
                sys.stdout.flush()

                siggen.set_power(power_dBm)
                siggen.set_output(True)

                with source_class(source_args) as source:
                    sinad_dB_readings = []
                    keithley_sinad_dB_readings = []
                    keithley_freq_Hz_readings = []
                    for _ in range(128):
                        samples = source.read()
                        assert len(samples) == num_samples

                        if audio_filter:
                            if not source.continuous:
                                audio_filter.reset()
                            samples = audio_filter(samples)

                        (sinad, _) = pysnr.sinad_signal(samples, fs=sample_frequency)
                        sinad_dB_readings.append(sinad)

                        if keithley_meter is None:
                            continue

                        keithley_sinad_dB = float(keithley_meter.query(":READ?"))
                        if keithley_sinad_dB > 1e6:
                            keithley_sinad_dB = float("nan")
                        keithley_sinad_dB_readings.append(keithley_sinad_dB)

                        keithley_freq_Hz = float(
                            keithley_meter.query(":SENS:DIST:FREQ?")
                        )
                        if keithley_freq_Hz > 1e6:
                            keithley_freq_Hz = float("nan")
                        keithley_freq_Hz_readings.append(keithley_freq_Hz)

                    (sinad_mean_dB, sinad_std_dB, sinad_n) = _summarize(
                        sinad_dB_readings
                    )
                    (
                        keithley_sinad_mean_dB,
                        keithley_sinad_std_dB,
                        keithley_sinad_n,
                    ) = _summarize(keithley_sinad_dB_readings)
                    (keithley_freq_mean_Hz, keithley_freq_std_Hz, _) = _summarize(
                        keithley_freq_Hz_readings
                    )

                    print(
                        f" sinad={sinad_mean_dB:10.3f} dB std={sinad_std_dB:10.3f} dB",
                        end="",
                    )
                    if keithley_meter is not None:
                        print(
                            f" keithley_sinad={keithley_sinad_mean_dB:10.3f} dB"
                            f" keithley_std={keithley_sinad_std_dB:10.3f}",
                            end="",
                        )
                        print(
                            f" keithley_freq={keithley_freq_mean_Hz:10.3f} Hz"
                            f" keithley_std={keithley_freq_std_Hz:10.3f} Hz",
                            end="",
                        )
                        discarded = len(keithley_sinad_dB_readings) - keithley_sinad_n
                        if discarded:
                            print(f" ({discarded} keithley readings discarded)", end="")
                    print()
                    row = {
                        "power_dBm": power_dBm,
                        "sinad_mean_dB": sinad_mean_dB,
                        "sinad_std_dB": sinad_std_dB,
                        "sinad_n": sinad_n,
                    }
                    if keithley_meter is not None:
                        row.update(
                            {
                                "keithley_sinad_mean_dB": keithley_sinad_mean_dB,
                                "keithley_sinad_std_dB": keithley_sinad_std_dB,
                                "keithley_sinad_n": keithley_sinad_n,
                                "keithley_freq_mean_Hz": keithley_freq_mean_Hz,
                                "keithley_freq_std_Hz": keithley_freq_std_Hz,
                            }
                        )
                    data.append(row)
        finally:
            # Never leave the generator transmitting, however we leave.
            siggen.set_output(False)
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"wrote {output_path}")


def main():
    registry = source_pkg.load_sources()
    for line in source_pkg.describe_unavailable_backends():
        print(f"note: {line}", file=sys.stderr)

    parser = argparse.ArgumentParser(description="SINAD Meter")

    parser.add_argument(
        "-S",
        "--source",
        choices=[source.name for source in registry],
        default="portaudio",
        help="Selects source.",
    )
    parser.add_argument(
        "--help-source",
        action="store_true",
        dest="help_source",
        help="Prints usage related to selected source.",
    )
    parser.add_argument(
        "-G",
        "--siggen",
        choices=sorted(SIGGENS),
        default=DEFAULT_SIGGEN,
        help=f"Selects signal generator (default: {DEFAULT_SIGGEN}).",
    )
    parser.add_argument(
        "--siggen-resource",
        dest="siggen_resource",
        help="VISA resource of the signal generator "
        "(default: depends on the generator)",
    )
    parser.add_argument(
        "-K",
        "--keithley",
        action="store_true",
        help="Also measure with the Keithley 2015, to check this meter "
        "against it.  Off by default: it roughly doubles the queries per "
        "reading and requires the meter to be connected.",
    )
    parser.add_argument(
        "--keithley-resource",
        dest="keithley_resource",
        default=DEFAULT_KEITHLEY_2015_RESOURCE,
        help=f"VISA resource of the Keithley 2015 "
        f"(default: {DEFAULT_KEITHLEY_2015_RESOURCE})",
    )
    parser.add_argument(
        "--output", help="CSV to write (default: auto_sinad_<siggen>.csv)"
    )

    (args, unparsed_args) = parser.parse_known_args()

    source_class = registry.get(args.source)
    source_parser = argparse.ArgumentParser(
        description=f"SINAD Meter using {source_class.pretty_name}"
    )
    default_sample_frequency = source_class.default_sample_frequency()
    source_parser.add_argument(
        "-s",
        "--sample-frequency",
        type=float,
        default=default_sample_frequency,
        help="sample frequency, in samples per second "
        f"(default: {default_sample_frequency} Hz)",
    )

    default_record_length = source_class.default_record_length()
    source_parser.add_argument(
        "-r",
        "--record-length",
        type=float,
        default=default_record_length,
        help=f"record length, in seconds (default: {default_record_length} s)",
    )

    source_class.augment_argparse(source_parser)
    if args.help_source:
        source_parser.print_help()
        return
    source_args = source_parser.parse_args(args=unparsed_args)

    output_path = args.output or f"auto_sinad_{args.siggen}.csv"
    run(
        source_class,
        source_args,
        args.siggen,
        args.siggen_resource,
        args.keithley_resource if args.keithley else None,
        output_path,
    )


if __name__ == "__main__":
    main()
