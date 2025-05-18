#! /usr/bin/env python3

from pathlib import Path
import sys

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
import pandas as pd
from scipy.interpolate import interp1d


def main(argv):
    path = Path(argv[1])
    df = pd.read_csv(path)

    plt.figure(figsize=(12, 8))

    plt.errorbar(df['power_dBm'],
                 df['sinad_mean_dB'],
                 yerr=df['sinad_std_dB'],
                 fmt='o', label="AI6KG soft meter")

    plt.errorbar(df['power_dBm'],
                 df['keithley_sinad_mean_dB'],
                 yerr=df['keithley_sinad_std_dB'],
                 fmt='+', label="Keithley 2015")

    interp_func = interp1d(df['sinad_mean_dB'], df['power_dBm'], kind='linear')

    target_sinad = 12.
    try:
        interpolated_power = interp_func(target_sinad)
        plt.annotate(f'{target_sinad} dB SINAD @: {interpolated_power:.2f} dBm\n(interpolated)',
                     xy=(interpolated_power, target_sinad),
                     xytext=(interpolated_power + 5, target_sinad - 3),
                     arrowprops=dict(facecolor='blue', shrink=0.05, alpha=0.25))
        plt.plot(interpolated_power, target_sinad,
                 'ro', markersize=8, marker='x')
    except ValueError as e:
        print(f"Could not interpolate for SINAD={target_sinad} dB: {e}")

    plt.xlabel('Power (dBm)')
    plt.ylabel('SINAD (dB)')
    plt.title(path)
    plt.grid(True)
    plt.legend()

    png_path = path.with_suffix(".png")
    plt.savefig(png_path)
    plt.show()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
