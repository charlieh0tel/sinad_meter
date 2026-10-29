#! /usr/bin/env python3

import argparse
import sys

import numpy as np
import pandas as pd
import pyvisa

import filters
import siggen as siggen_pkg
import sinad as sinad_pkg
import source as source_pkg
from instruments import keithley_2015

DEFAULT_KEITHLEY_2015_RESOURCE = "TCPIP::e5810a::gpib0,22::INSTR"

DEFAULT_SIGGEN = "hp8663a"

# TIA-603 test modulation tone.
TONE_FREQUENCY_HZ = 1000.0

# TIA-603 standard test modulation: 1 kHz at 60% of the maximum
# permissible deviation, which is 5 kHz for 25 kHz channels.
DEFAULT_MOD_RATE_HZ = 1000.0
DEFAULT_DEVIATION_HZ = 3000.0


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


def _fm_settings(args):
    """
    Resolves the FM to configure from the command line.

    Args:
        args (argparse.Namespace): the parsed arguments

    Returns:
        (float, float): modulation rate and deviation in Hz, or
                        (None, None) to leave the front panel's
                        modulation alone

    Raises:
        ValueError: if the arguments conflict
    """
    if args.modulation_from_front_panel:
        if args.mod_rate is not None or args.deviation is not None:
            raise ValueError(
                "--mod-rate and --deviation conflict with --modulation-from-front-panel"
            )
        return (None, None)
    return (
        DEFAULT_MOD_RATE_HZ if args.mod_rate is None else args.mod_rate,
        DEFAULT_DEVIATION_HZ if args.deviation is None else args.deviation,
    )


def run(
    source_class,
    source_args,
    siggen_class,
    siggen_resource_name,
    carrier_Hz,
    mod_rate_Hz,
    deviation_Hz,
    keithley_resource_name,
    output_path,
):
    hpf_cutoff = 200.0
    lpf_cutoff = 4000.0

    rm = pyvisa.ResourceManager("@py")
    siggen_resource = siggen_class(
        rm, siggen_resource_name or siggen_class.default_resource
    )

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

    powers_dBm = np.linspace(-125, -95, 51)
    with siggen_pkg.opened(siggen_resource) as siggen:
        siggen.set_frequency(carrier_Hz)
        if mod_rate_Hz is not None:
            siggen.set_fm(mod_rate_Hz, deviation_Hz)
        siggen.set_power(powers_dBm[0])
        siggen.set_output(True)
        for power_dBm in powers_dBm:
            print(f"{power_dBm:6.3f}", end="")
            sys.stdout.flush()

            siggen.set_power(power_dBm)

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

                    (sinad, _) = sinad_pkg.measure(
                        samples, sample_frequency, TONE_FREQUENCY_HZ
                    )
                    sinad_dB_readings.append(sinad)

                    if keithley_meter is None:
                        continue

                    keithley_sinad_dB = float(keithley_meter.query(":READ?"))
                    if keithley_sinad_dB > 1e6:
                        keithley_sinad_dB = float("nan")
                    keithley_sinad_dB_readings.append(keithley_sinad_dB)

                    keithley_freq_Hz = float(keithley_meter.query(":SENS:DIST:FREQ?"))
                    if keithley_freq_Hz > 1e6:
                        keithley_freq_Hz = float("nan")
                    keithley_freq_Hz_readings.append(keithley_freq_Hz)

                (sinad_mean_dB, sinad_std_dB, sinad_n) = _summarize(sinad_dB_readings)
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
                # Invalid readings are dropped from the means, so say
                # so; the counts are not carried in the CSV.
                discarded = (len(sinad_dB_readings) - sinad_n) + (
                    len(keithley_sinad_dB_readings) - keithley_sinad_n
                )
                if discarded:
                    print(f" ({discarded} readings discarded)", end="")
                print()
                row = {
                    "power_dBm": power_dBm,
                    "sinad_mean_dB": sinad_mean_dB,
                    "sinad_std_dB": sinad_std_dB,
                    "carrier_Hz": carrier_Hz,
                    "mod_rate_Hz": mod_rate_Hz,
                    "deviation_Hz": deviation_Hz,
                    "modulation": (
                        "front_panel" if mod_rate_Hz is None else "configured"
                    ),
                }
                if keithley_meter is not None:
                    row.update(
                        {
                            "keithley_sinad_mean_dB": keithley_sinad_mean_dB,
                            "keithley_sinad_std_dB": keithley_sinad_std_dB,
                            "keithley_freq_mean_Hz": keithley_freq_mean_Hz,
                            "keithley_freq_std_Hz": keithley_freq_std_Hz,
                        }
                    )
                data.append(row)
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"wrote {output_path}")


def main():
    registry = source_pkg.load_sources()
    siggen_registry = siggen_pkg.load_siggens()
    for line in (
        source_pkg.describe_unavailable_backends()
        + siggen_pkg.describe_unavailable_backends()
    ):
        print(f"note: {line}", file=sys.stderr)

    # Plugin files are loaded before the main parser is built, so that
    # -G can offer them.
    plugin_parser = argparse.ArgumentParser(add_help=False)
    plugin_parser.add_argument(
        "--siggen-plugin",
        action="append",
        default=[],
        dest="siggen_plugins",
        metavar="FILE.py:CLASS",
        help="Loads a signal generator from a Python file.  May be repeated.",
    )
    (plugin_args, _) = plugin_parser.parse_known_args()
    for spec in plugin_args.siggen_plugins:
        try:
            siggen_pkg.load_plugin_file(spec)
        except (ValueError, *siggen_pkg.PLUGIN_ERRORS) as e:
            plugin_parser.error(f"--siggen-plugin {spec}: {e}")

    parser = argparse.ArgumentParser(description="SINAD Meter", parents=[plugin_parser])

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
        choices=sorted(s.name for s in siggen_registry),
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
        "-f",
        "--frequency",
        type=float,
        help="carrier frequency, in Hz (required)",
    )
    parser.add_argument(
        "--mod-rate",
        dest="mod_rate",
        type=float,
        help=f"FM rate, in Hz (default: {DEFAULT_MOD_RATE_HZ:g} Hz)",
    )
    parser.add_argument(
        "--deviation",
        type=float,
        help=f"FM deviation, in Hz (default: {DEFAULT_DEVIATION_HZ:g} Hz, "
        "60%% of 5 kHz for 25 kHz channels; use 1500 for 12.5 kHz)",
    )
    parser.add_argument(
        "--modulation-from-front-panel",
        action="store_true",
        dest="modulation_from_front_panel",
        help="Leave modulation as set on the generator's front panel, for "
        "generators that cannot set FM.  Recorded as such in the CSV.",
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

    # Checked here rather than with required=True so that --help-source
    # works without it.
    if args.frequency is None:
        parser.error("--frequency is required")
    try:
        (mod_rate_Hz, deviation_Hz) = _fm_settings(args)
    except ValueError as e:
        parser.error(str(e))
    if mod_rate_Hz is None:
        print(
            "warning: modulation is whatever the front panel was left at",
            file=sys.stderr,
        )

    output_path = args.output or f"auto_sinad_{args.siggen}.csv"
    run(
        source_class,
        source_args,
        siggen_registry.get(args.siggen),
        args.siggen_resource,
        args.frequency,
        mod_rate_Hz,
        deviation_Hz,
        args.keithley_resource if args.keithley else None,
        output_path,
    )


if __name__ == "__main__":
    main()
