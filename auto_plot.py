#! /usr/bin/env python3

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from scipy.interpolate import interp1d


def main(argv):
    parser = argparse.ArgumentParser(description="Plots a SINAD sweep.")
    parser.add_argument("csv", type=Path, help="sweep CSV to plot")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="PNG to write (default: the CSV's name with a .png suffix, "
        "which overwrites any existing plot beside it)",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        dest="no_show",
        help="Write the PNG without opening a window.",
    )
    args = parser.parse_args(argv[1:])

    path = args.csv
    df = pd.read_csv(path)

    plt.figure(figsize=(12, 8))

    plt.errorbar(
        df["power_dBm"],
        df["sinad_mean_dB"],
        yerr=df["sinad_std_dB"],
        fmt="o",
        label="AI6KG soft meter",
    )

    # The Keithley is a check on the soft meter, not part of a sweep, so
    # it is only present in files from a run with --keithley.
    if "keithley_sinad_mean_dB" in df:
        plt.errorbar(
            df["power_dBm"],
            df["keithley_sinad_mean_dB"],
            yerr=df["keithley_sinad_std_dB"],
            fmt="+",
            label="Keithley 2015",
        )

    interp_func = interp1d(df["sinad_mean_dB"], df["power_dBm"], kind="linear")

    target_sinad = 12.0
    try:
        interpolated_power = interp_func(target_sinad)
        plt.annotate(
            f"{target_sinad} dB SINAD @: {interpolated_power:.2f} dBm\n(interpolated)",
            xy=(interpolated_power, target_sinad),
            xytext=(interpolated_power + 5, target_sinad - 3),
            arrowprops={"facecolor": "blue", "shrink": 0.05, "alpha": 0.25},
        )
        plt.plot(interpolated_power, target_sinad, "ro", markersize=8, marker="x")
    except ValueError as e:
        print(f"Could not interpolate for SINAD={target_sinad} dB: {e}")

    plt.xlabel("Power (dBm)")
    plt.ylabel("SINAD (dB)")
    plt.title(path)
    plt.grid(True)
    plt.legend()

    png_path = args.output or path.with_suffix(".png")
    plt.savefig(png_path)
    print(f"wrote {png_path}")
    if not args.no_show:
        plt.show()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
