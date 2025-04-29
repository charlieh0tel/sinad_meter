import numpy as np
import scipy.filter


class MovingAverageFilter:
    def __init__(self, window_size):
        self.window_size = window_size
        self.data = np.array([])

    def update(self, value):
        self.data = np.append(self.data, value)
        if len(self.data) > self.window_size:
            self.data = self.data[1:]

    def __call__(self):
        if len(self.data) > 0:
            return np.mean(self.data)
        else:
            return 0


class FirFilter:
    def __init__(self, taps):
        self._taps = taps
        self._state = np.zeros(len(taps) - 1)

    def __call__(self, samples):
        filtered_samples, self._state = scipy.filter.lfilter(
            self._taps, 1.0, samples, zi=self._state)
        return filtered_samples


def make_fir_lowpass_filter(sample_frequency, cutoff_frequency, numtaps=101):
    """
    Makes a linear-phase FIR low-pass filter.

    Args:
        sample_frequency (int): The sampling rate of the audio data (Hz).
        cutoff_frequency (float): The desired cutoff frequency (Hz).
        numtaps (int): The number of taps (coefficients) in the filter.
                       Must be odd.

    Returns:
        numpy.ndarray: The FIR filter coefficients (taps).
    """
    assert (numtaps % 2 != 0)
    nyquist = sample_frequency / 2.
    normalized_cutoff = cutoff_frequency / nyquist
    taps = scipy.filter.firwin(numtaps, normalized_cutoff, pass_zero='lowpass')
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
        numpy.ndarray: The FIR filter coefficients (taps).
    """
    assert (numtaps % 2 != 0)
    nyquist = sample_frequency / 2.
    normalized_lowcut = lowcut_frequency / nyquist
    normalized_highcut = highcut_frequency / nyquist
    taps = scipy.filter.firwin(numtaps,
                               [normalized_lowcut, normalized_highcut],
                               pass_zero='bandpass')
    return FirFilter(taps)
