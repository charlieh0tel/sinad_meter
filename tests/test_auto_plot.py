from pathlib import Path

import pandas as pd
import pytest

import auto_plot

DATA = Path(__file__).parent.parent / "data"


def test_sensitivity_interpolates_between_steps():
    power_dBm = [-120.0, -118.0, -116.0, -114.0]
    sinad_dB = [6.0, 10.0, 14.0, 18.0]
    assert auto_plot.sensitivity_dBm(power_dBm, sinad_dB) == pytest.approx(-117.0)


def test_sensitivity_of_a_sweep_that_never_reaches_12_dB_is_an_error():
    with pytest.raises(ValueError):
        auto_plot.sensitivity_dBm([-120.0, -118.0, -116.0], [3.0, 6.0, 9.0])


def test_sensitivity_of_a_recorded_sweep():
    """Pins the published HP 8663A figure, which the README shows."""
    df = pd.read_csv(DATA / "sinad_tk981_sn30900133_hp8663a.csv")
    assert auto_plot.sensitivity_dBm(
        df["power_dBm"], df["sinad_mean_dB"]
    ) == pytest.approx(-114.125, abs=0.001)


def test_sensitivity_of_a_noisy_sweep_is_its_first_crossing():
    # SINAD dips after first passing 12 dB, as a real sweep can near
    # sensitivity.  The crossing is between -118 and -116 dBm; sorting by
    # SINAD instead pairs 11 dB at -114 with 13 dB at -116 and says -115.
    power_dBm = [-120.0, -118.0, -116.0, -114.0, -112.0, -110.0]
    sinad_dB = [5.0, 10.0, 13.0, 11.0, 14.0, 20.0]
    assert auto_plot.sensitivity_dBm(power_dBm, sinad_dB) == pytest.approx(
        -118.0 + 2.0 * (12.0 - 10.0) / (13.0 - 10.0)
    )
