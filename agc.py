import numpy as np
import scipy.signal


class AutomaticGainControl:
    """
    A simple Automatic Gain Control (AGC) class for processing data in batches.

    This AGC adjusts the gain of incoming signal batches to maintain a target
    Root Mean Square (RMS) level. It uses a simple exponential smoothing
    filter to update the internal gain state between batches, providing
    a form of attack/release behavior. The applied gain itself is also
    smoothed to prevent abrupt changes.

    Parameters
    ----------
    target_rms : float
        The desired RMS level of the output signal. Must be positive.
    smoothing_factor : float, optional
        The smoothing factor (alpha) for the exponential filter, between 0 and 1.
        This factor is used for both the power estimate smoothing and the
        applied gain smoothing. A smaller value results in slower gain changes
        (longer attack/release). A larger value results in faster gain changes.
        Defaults to 0.01.
    initial_gain : float, optional
        The initial gain to apply before processing the first batch.
        Must be positive. Defaults to 1.0.
    """

    def __init__(self, target_rms: float, smoothing_factor: float = 0.01,
                 initial_gain: float = 1.0):
        if not 0.0 <= smoothing_factor <= 1.0:
            raise ValueError("smoothing_factor must be between 0 and 1.")
        if target_rms <= 0:
            raise ValueError("target_rms must be positive.")
        if initial_gain <= 0:
            raise ValueError("initial_gain must be positive.")

        self._target_rms = target_rms
        self._smoothing_factor = smoothing_factor
        self._current_gain = initial_gain
        self._current_power_estimate = (target_rms / initial_gain)**2

    def __call__(self, samples: np.ndarray) -> np.ndarray:
        """
        Applies AGC to a batch of samples.

        Parameters
        ----------
        samples : np.ndarray
            A NumPy array containing the signal samples for the current batch.

        Returns
        -------
        np.ndarray
            The samples with gain applied.
        """

        if samples.size == 0:
            return samples

        # Calculate the instantaneous power of the current batch using
        # mean square as power.
        current_batch_power = np.mean(samples**2)

        # Update the internal power estimate using exponential smoothing.
        self._current_power_estimate = (
            self._smoothing_factor * current_batch_power +
            (1 - self._smoothing_factor) * self._current_power_estimate)

        # Calculate the required gain based on the smoothed power estimate
        # Ensure power estimate is non-zero before division and sqrt
        estimated_rms = np.sqrt(max(1e-10, self._current_power_estimate))

        # Calculate the target gain needed to bring the estimated RMS
        # to the target RMS.
        target_gain = self._target_rms / estimated_rms

        smoothed_gain = (
            self._smoothing_factor * target_gain +
            (1 - self._smoothing_factor) * self._current_gain
        )

        self._current_gain = smoothed_gain
        return samples * smoothed_gain

    def get_current_gain(self) -> float:
        """ Returns the smoothed gain that was applied to the most
        recently processed batch."""
        return self._current_gain

    def get_current_power_estimate(self) -> float:
        """Returns the internal smoothed power estimate after
        processing the last batch."""
        return self._current_power_estimate
