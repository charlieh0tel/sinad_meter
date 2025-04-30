import numpy as np
import scipy.signal


class FirFilter:
    def __init__(self, taps):
        self._taps = taps
        self._state = np.zeros(len(taps) - 1)

    def __call__(self, samples):
        filtered_samples, new_state = scipy.signal.lfilter(
            self._taps, 1., samples, zi=self._state)
        self._state = new_state
        return filtered_samples


def make_moving_average_filter(window_length):
    """
    Makes a moving average filter.

    Args:
        window_length (int): length of window

    Returns:
        FirFilter: the filter
    """
    taps = np.ones(window_length) / window_length
    return FirFilter(taps)


def make_fir_lowpass_filter(sample_frequency, cutoff_frequency, numtaps=101):
    """
    Makes a linear-phase FIR low-pass filter.

    Args:
        sample_frequency (int): The sampling rate of the audio data (Hz).
        cutoff_frequency (float): The desired cutoff frequency (Hz).
        numtaps (int): The number of taps (coefficients) in the filter.
                       Must be odd.

    Returns:
        FirFilter: the filter
    """
    assert (numtaps % 2 != 0)
    nyquist = sample_frequency / 2.
    normalized_cutoff = cutoff_frequency / nyquist
    taps = scipy.signal.firwin(numtaps, normalized_cutoff, pass_zero='lowpass')
    return FirFilter(taps)


def make_fir_highpass_filter(sample_frequency, cutoff_frequency, numtaps=101):
    """
    Makes a linear-phase FIR high-pass filter.

    Args:
        sample_frequency (int): The sampling rate of the audio data (Hz).
        cutoff_frequency (float): The desired cutoff frequency (Hz).
        numtaps (int): The number of taps (coefficients) in the filter.
                       Must be odd.

    Returns:
        FirFilter: the filter
    """
    assert (numtaps % 2 != 0)
    nyquist = sample_frequency / 2.
    normalized_cutoff = cutoff_frequency / nyquist
    taps = scipy.signal.firwin(
        numtaps, normalized_cutoff, pass_zero='highpass')
    return FirFilter(taps)


def make_fir_bandpass_filter(sample_frequency,
                             lowcut_frequency, highcut_frequency, numtaps=101):
    """
    Makes a linear-phase FIR band-pass filter.

    Args:
        sample_frequency (int): The sampling rate of the audio data (Hz).
        lowcut_frequency (float): The lower cutoff frequency (Hz).
        highcut_frequency (float): The upper cutoff frequency (Hz).
        numtaps (int): The number of taps (coefficients) in the filter.
                       Must be odd.

    Returns:
        FirFilter: the filter
    """
    assert (numtaps % 2 != 0)
    nyquist = sample_frequency / 2.
    normalized_lowcut = lowcut_frequency / nyquist
    normalized_highcut = highcut_frequency / nyquist
    taps = scipy.signal.firwin(numtaps,
                               [normalized_lowcut, normalized_highcut],
                               pass_zero='bandpass')
    return FirFilter(taps)
