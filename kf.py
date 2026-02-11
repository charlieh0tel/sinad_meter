#! /usr/bin/env python3

import keithley_2015
import argparse
import sys

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
import pandas as pd
import pyvisa

DEFAULT_KEITHLEY_2015_RESOURCE = "TCPIP::e5810a::gpib0,22::INSTR"


def main(argv):
    rm = pyvisa.ResourceManager('@py')
    keithley_meter = keithley_2015.Keithley2015(
        rm, DEFAULT_KEITHLEY_2015_RESOURCE).open()

    keithley_meter.reset()
    keithley_meter.write(":SENS:FUNC 'freq'")

    data = []

    for _ in range(1000):
        freq_Hz = float(keithley_meter.query("READ?"))
        data.append(dict(freq_Hz=freq_Hz))

    df = pd.DataFrame(data)
    print(df['freq_Hz'].describe())

    df.to_csv("kf.csv", index=False)

    return 0



if __name__ == "__main__":
    sys.exit(main(sys.argv))
