#! /usr/bin/env python3

import keithley_2015
import rs_smb100a
import hp_8662a
import argparse
import sys

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
import pysnr
import pandas as pd
import pyvisa

import filters
import source as source_pkg
import source_digilent          # for effect
import source_portaudio         # for effect


# Gross.  For development.  DO NOT SUBMIT.
sys.path.append("/home/ch/src/ee_stuff/instruments")

DEFAULT_RS_SMB100A_SIG_GEN_RESOURCE = "TCPIP::rssmb100a180609.local::INSTR"
DEFAULT_HP_8663A_SIG_GEN_RESOURCE = "TCPIP::e5810a::gpib0,25::INSTR"
DEFAULT_KEITHLEY_2015_RESOURCE = "TCPIP::e5810a::gpib0,22::INSTR"


def run(source_class, source_args):
    lpf_cutoff = 200.
    hpf_cutoff = 4000.

    rm = pyvisa.ResourceManager('@py')
    siggen_resource = rs_smb100a.RhodeSchwarzSMB100A(
        rm, DEFAULT_RS_SMB100A_SIG_GEN_RESOURCE)

    # siggen_resource = hp_8662a.HP8663A(DEFAULT_HP_8663A_SIG_GEN_RESOURCE)

    keithley_meter = keithley_2015.Keithley2015(
        rm, DEFAULT_KEITHLEY_2015_RESOURCE).open()
    keithley_meter.inst.timeout = 10e3
    keithley_meter.reset()
    keithley_meter.write(":SENS:FUNC 'dist'")
    keithley_meter.write(":SENS:DIST:TYPE SINAD")
    keithley_meter.write(":SENS:DIST:SFIL NONE")
    keithley_meter.write(":SENS:DIST:FREQ:AUTO ON")
    keithley_meter.write(":SENS:DIST:SFIL NONE")  # CCITT?
    keithley_meter.write(":SENS:DIST:RANG:AUTO ON")
    keithley_meter.write(":UNIT:DIST DB")
    assert lpf_cutoff is None or hpf_cutoff is None or lpf_cutoff < hpf_cutoff
    if lpf_cutoff is not None:
        assert lpf_cutoff >= 20
        keithley_meter.write(f":SENS:DIST:LCO {int(lpf_cutoff)}")
        keithley_meter.write(":SENS:DIST:LCO:STATE ON")
    if hpf_cutoff is not None:
        assert hpf_cutoff <= 50_000
        keithley_meter.write(f":SENS:DIST:HCO {int(hpf_cutoff)}")
        keithley_meter.write(":SENS:DIST:HCO:STATE ON")

    sample_frequency = source_args.sample_frequency
    record_length = source_args.record_length
    num_samples = round(sample_frequency * record_length)

    filter = None
    if lpf_cutoff and hpf_cutoff:
        filter = filters.make_fir_bandpass_filter(
            sample_frequency, lpf_cutoff, hpf_cutoff)
    elif lpf_cutoff:
        filter = filters.make_fir_lowpass_filter(sample_frequency, lpf_cutoff)
    elif hpf_cutoff:
        filter = filters.make_fir_highpass_filter(sample_frequency, hpf_cutoff)

    data = []

    with siggen_resource as siggen:
        siggen.set_output(False)
        for power_dBm in np.linspace(-125, -95, 51):
            print(f"{power_dBm:6.3f}", end="")
            sys.stdout.flush()

            siggen.set_power(power_dBm)
            siggen.set_output(True)

            with source_class(source_args) as source:
                sinad_dB_readings = []
                keithley_sinad_dB_readings = []
                keithley_freq_Hz_readings = []
                for n in range(128):
                    samples = source.read()
                    assert len(samples) == num_samples

                    if filter:
                        samples = filter(samples)

                        t = np.arange(len(samples)) / sample_frequency

                        (sinad, _) = pysnr.sinad_signal(samples,
                                                        fs=sample_frequency)

                        sinad_dB_readings.append(sinad)

                        keithley_sinad_dB = float(
                            keithley_meter.query(":READ?"))
                        if keithley_sinad_dB > 1e6:
                            keithely_sinad_dB = float('nan')
                        keithley_sinad_dB_readings.append(keithley_sinad_dB)
                        keithley_freq_Hz = float(
                            keithley_meter.query(":SENS:DIST:FREQ?"))
                        if keithley_freq_Hz > 1e6:
                            keithley_freq_Hz = float('nan')
                        keithley_freq_Hz_readings.append(keithley_freq_Hz)

                sinad_dB_readings = np.array(sinad_dB_readings)
                sinad_mean_dB = sinad_dB_readings.mean()
                sinad_std_dB = sinad_dB_readings.std()
                keithley_sinad_dB_readings = np.array(
                    keithley_sinad_dB_readings)
                keithley_sinad_mean_dB = keithley_sinad_dB_readings.mean()
                keithley_sinad_std_dB = keithley_sinad_dB_readings.std()
                keithley_freq_Hz_readings = np.array(keithley_freq_Hz_readings)
                keithley_freq_mean_Hz = keithley_freq_Hz_readings.mean()
                keithley_freq_std_Hz = keithley_freq_Hz_readings.std()

                print(f" sinad={sinad_mean_dB:10.3f} dB std={
                      sinad_std_dB:10.3f} dB", end="")
                print(f" keithley_sinad={keithley_sinad_mean_dB:10.3f} dB keithley_std={
                      keithley_sinad_std_dB:10.3f}", end="")
                print(f" keithley_freq={keithley_freq_mean_Hz:10.3f} Hz keithley_std={
                      keithley_freq_std_Hz:10.3f} Hz", end="")
                print()
                data.append(dict(power_dBm=power_dBm,
                                 sinad_mean_dB=sinad_mean_dB,
                                 sinad_std_dB=sinad_std_dB,
                                 keithley_sinad_mean_dB=keithley_sinad_mean_dB,
                                 keithley_sinad_std_dB=keithley_sinad_std_dB,
                                 keithley_freq_mean_Hz=keithley_freq_mean_Hz,
                                 keithley_freq_std_Hz=keithley_freq_std_Hz))
    df = pd.DataFrame(data)
    df.to_csv("auto_sinad.csv", index=False)


def main():
    parser = argparse.ArgumentParser(
        description="SINAD Meter")

    parser.add_argument(
        "-S", "--source",
        choices=[source.name for source in source_pkg.SOURCE_REGISTRY],
        default="portaudio",
        help="Selects source.")
    parser.add_argument(
        "--help-source",
        action="store_true",
        dest="help_source",
        help="Prints usage related to selected source.")

    (args, unparsed_args) = parser.parse_known_args()

    source_class = source_pkg.SOURCE_REGISTRY.get(args.source)
    source_parser = argparse.ArgumentParser(
        description=f"SINAD Meter using {source_class.pretty_name}")
    default_sample_frequency = source_class.default_sample_frequency()
    source_parser.add_argument(
        "-s", "--sample-frequency",
        type=float,
        default=default_sample_frequency,
        help=f"sample frequency, in samples per second (default: {default_sample_frequency} Hz)")

    default_record_length = source_class.default_record_length()
    source_parser.add_argument(
        "-r", "--record-length",
        type=float,
        default=default_record_length,
        help=f"record length, in seconds (default: {default_record_length} s)")

    source_class.augment_argparse(source_parser)
    if args.help_source:
        source_parser.print_help()
        return
    source_args = source_parser.parse_args(args=unparsed_args)

    run(source_class, source_args)


if __name__ == "__main__":
    main()
