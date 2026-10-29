#! /usr/bin/env python3

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SENSITIVITY_SINAD_DB = 12.0


def sensitivity_dBm(power_dBm, sinad_dB, target_dB=SENSITIVITY_SINAD_DB):
    """
    Finds the power at which a sweep reaches a SINAD, by interpolation.

    This is the first point, going up in power, where SINAD rises
    through target_dB.  Near sensitivity a sweep is noisy and can dip
    back below it, so the curve cannot be inverted as a whole.

    Args:
        power_dBm (array-like): the power of each step (dBm)
        sinad_dB (array-like): the SINAD measured at each step (dB)
        target_dB (float): the SINAD to find (dB)

    Returns:
        float: the interpolated power (dBm)

    Raises:
        ValueError: if the sweep never rises through target_dB
    """
    order = np.argsort(power_dBm)
    power_dBm = np.asarray(power_dBm, dtype=float)[order]
    sinad_dB = np.asarray(sinad_dB, dtype=float)[order]
    crossings = np.flatnonzero(
        (sinad_dB[:-1] < target_dB) & (sinad_dB[1:] >= target_dB)
    )
    if crossings.size == 0:
        raise ValueError(f"the sweep never rises through {target_dB} dB SINAD")
    i = crossings[0]
    return float(np.interp(target_dB, sinad_dB[i : i + 2], power_dBm[i : i + 2]))


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

    target_sinad = SENSITIVITY_SINAD_DB
    try:
        interpolated_power = sensitivity_dBm(df["power_dBm"], df["sinad_mean_dB"])
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
