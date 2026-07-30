#
# The estimator is pinned against MATLAB, which is what pysnr was
# cloned from, and the definition against closed-form signals.
#

from pathlib import Path

import numpy as np
import pytest
import scipy.io

import sinad
from vendored import pysnr

DATA = Path(__file__).parent / "data"

# What MATLAB's sinad() reports for these signals, from pysnr's own test
# suite.  MATLAB uses S/(N+D), so these pin the vendored estimator, not
# the definition we report.
MATLAB_SINAD_DB = {
    "sine_data": 57.0571,
    "cosine_data": 57.0566,
    "alias_data": 22.5389,
}


def _load(name):
    data = scipy.io.loadmat(str(DATA / f"{name}.mat"))
    signal = data["x"].flatten() + data["noise"].flatten()
    return (signal, float(data["Fs"].flatten()[0]))


def _to_radio_sinad(snr_dB):
    """The conversion under test, written out independently."""
    return 10.0 * np.log10(1.0 + 10.0 ** (snr_dB / 10.0))


@pytest.mark.parametrize(("name", "expected_dB"), MATLAB_SINAD_DB.items())
def test_vendored_matches_matlab(name, expected_dB):
    (signal, sample_frequency) = _load(name)
    (got_dB, _) = pysnr.sinad_signal(signal, fs=sample_frequency)
    assert got_dB == pytest.approx(expected_dB, abs=0.01)


@pytest.mark.parametrize("name", MATLAB_SINAD_DB)
def test_measure_is_the_converted_estimate(name):
    (signal, sample_frequency) = _load(name)
    (snr_dB, _) = pysnr.sinad_signal(signal, fs=sample_frequency)
    (got_dB, _) = sinad.measure(signal, sample_frequency)
    assert got_dB == pytest.approx(_to_radio_sinad(snr_dB), abs=1e-9)


@pytest.mark.parametrize(
    ("noise_power_ratio_dB", "expected_dB"),
    [(0.0, 3.01), (6.0, 6.97), (12.0, 12.27), (20.0, 20.04)],
)
def test_known_signal_to_noise(noise_power_ratio_dB, expected_dB):
    """A tone in noise of known power has a SINAD we can write down."""
    sample_frequency = 48_000
    n = sample_frequency
    t = np.arange(n) / sample_frequency
    tone = np.sin(2 * np.pi * 1000 * t)
    noise = np.random.default_rng(0).standard_normal(n)
    tone_power = 0.5
    noise *= np.sqrt(tone_power / 10 ** (noise_power_ratio_dB / 10)) / noise.std()
    (got_dB, _) = sinad.measure(tone + noise, sample_frequency)
    assert got_dB == pytest.approx(expected_dB, abs=0.25)


@pytest.mark.parametrize("harmonic_amplitude", [0.1, 0.02, 0.005])
def test_known_harmonic_distortion(harmonic_amplitude):
    """
    A tone plus one harmonic and no noise.

    The fundamental has power 1/2 and the harmonic (a**2)/2, so
    S/(N+D) is 1/a**2 and the SINAD we report is that plus one.
    """
    sample_frequency = 48_000
    n = sample_frequency
    t = np.arange(n) / sample_frequency
    signal = np.sin(2 * np.pi * 1000 * t) + harmonic_amplitude * np.sin(
        2 * np.pi * 2000 * t
    )
    expected_dB = _to_radio_sinad(-20 * np.log10(harmonic_amplitude))
    (got_dB, _) = sinad.measure(signal, sample_frequency)
    assert got_dB == pytest.approx(expected_dB, abs=0.5)


def test_never_negative_without_a_tone():
    """
    The radio definition is bounded below by 0 dB.

    This is the case that separates it from the ADC definition, which
    goes steeply negative here, and it is what the Keithley does.
    """
    sample_frequency = 48_000
    noise = np.random.default_rng(1).standard_normal(sample_frequency)
    (got_dB, _) = sinad.measure(noise, sample_frequency)
    (adc_dB, _) = pysnr.sinad_signal(noise, fs=sample_frequency)
    assert got_dB >= 0.0
    assert got_dB < 1.0
    assert adc_dB < -10.0
