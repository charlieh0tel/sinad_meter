#
# SINAD measurement.
#

import numpy as np

from vendored import pysnr

# How far from the expected tone to look for it, as a fraction of its
# frequency.
TONE_SEARCH_FRACTION = 0.1


def measure(samples, sample_frequency, tone_frequency=None):
    """
    Measures the SINAD of a record.

    Two definitions are in use and both are standard.  Radio work, and
    the 12 dB SINAD sensitivity figure in particular, means

        (S+N+D)/(N+D)

    which is never below 0 dB: a vanishing tone approaches 1, not 0.
    ADC and DAC work means S/(N+D), the fundamental over the residual,
    which can go negative.  That is what MATLAB's sinad() returns, and
    pysnr follows MATLAB, so it is what the vendored code returns.

    This is a receiver sensitivity meter, so we want the first, and
    converting is exact: S/(N+D) + 1 = (S+N+D)/(N+D).  The difference
    only shows up at low SINAD -- +3.01 dB at 0, +0.27 dB at 12,
    +0.04 dB at 20 -- so readings well above the sensitivity point
    barely move.  It is also why the Keithley 2015, which measures the
    radio definition, bottoms out near 0 dB where pysnr goes to -4.

    The signal is the test tone.  Given its frequency, it is the largest
    peak near there, and anything bigger elsewhere -- hum, CTCSS leakage,
    a spur, an oscillation -- counts as noise and distortion, as it
    should.  Without it, the signal is the largest peak anywhere.

    Args:
        samples (numpy.ndarray): the record, as a 1-D array
        sample_frequency (float): sample rate of the record (Hz)
        tone_frequency (float): the test tone (Hz), or None for the
                                largest peak

    Returns:
        (float, float): the SINAD (dB) and the total noise-plus-
                        distortion power (dB)
    """
    fundamental_range = None
    if tone_frequency is not None:
        fundamental_range = (
            tone_frequency * (1 - TONE_SEARCH_FRACTION),
            tone_frequency * (1 + TONE_SEARCH_FRACTION),
        )
    (snr_dB, noise_dB) = pysnr.sinad_signal(
        samples, fs=sample_frequency, fundamental_range=fundamental_range
    )
    return (10.0 * np.log10(1.0 + 10.0 ** (snr_dB / 10.0)), noise_dB)
