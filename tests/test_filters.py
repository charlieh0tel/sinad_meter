import numpy as np
import pytest
import scipy.signal

import filters

# The band auto_sinad.py uses.
HPF_CUTOFF = 200.0
LPF_CUTOFF = 4000.0


def _response_dB(audio_filter, frequencies, sample_frequency):
    (_, h) = scipy.signal.freqz(
        audio_filter._taps, worN=frequencies, fs=sample_frequency
    )
    return 20 * np.log10(np.abs(h))


def _noise_bandwidth(audio_filter, sample_frequency):
    """
    The white-noise equivalent bandwidth (Hz), against the passband peak.

    That is, the width of a brickwall filter with the same peak gain
    that would pass the same white-noise power.
    """
    taps = audio_filter._taps
    (_, h) = scipy.signal.freqz(taps, worN=1 << 16, fs=sample_frequency)
    peak_power = np.max(np.abs(h) ** 2)
    return np.sum(taps**2) * sample_frequency / 2 / peak_power


@pytest.mark.parametrize(
    ("hpf_cutoff", "lpf_cutoff", "kind"),
    [
        (HPF_CUTOFF, LPF_CUTOFF, "bandpass"),
        (None, LPF_CUTOFF, "lowpass"),
        (HPF_CUTOFF, None, "highpass"),
    ],
)
def test_audio_filter_is_the_one_its_cutoffs_imply(hpf_cutoff, lpf_cutoff, kind):
    sample_frequency = 48_000
    audio_filter = filters.make_audio_filter(sample_frequency, hpf_cutoff, lpf_cutoff)
    (low, mid, high) = _response_dB(
        audio_filter, [20.0, 1000.0, 20_000.0], sample_frequency
    )
    passes_low = low > -3
    passes_high = high > -3
    assert mid > -1
    assert (passes_low, passes_high) == {
        "bandpass": (False, False),
        "lowpass": (True, False),
        "highpass": (False, True),
    }[kind]


def test_no_cutoffs_is_no_filter():
    assert filters.make_audio_filter(48_000, None, None) is None


def test_crossed_cutoffs_are_rejected():
    with pytest.raises(ValueError, match="must be below"):
        filters.make_audio_filter(48_000, LPF_CUTOFF, HPF_CUTOFF)


def test_filtering_in_pieces_matches_filtering_at_once():
    """Continuous sources rely on the delay line carrying across reads."""
    samples = np.random.default_rng(0).standard_normal(10_000)
    whole = filters.make_audio_filter(48_000, HPF_CUTOFF, LPF_CUTOFF)(samples)
    pieces = filters.make_audio_filter(48_000, HPF_CUTOFF, LPF_CUTOFF)
    joined = np.concatenate([pieces(chunk) for chunk in np.array_split(samples, 7)])
    np.testing.assert_allclose(joined, whole)


def test_reset_forgets_the_previous_record():
    """Record-based sources reset between reads, so no record sees another's tail."""
    rng = np.random.default_rng(1)
    (first, second) = (rng.standard_normal(1000), rng.standard_normal(1000))
    audio_filter = filters.make_audio_filter(48_000, HPF_CUTOFF, LPF_CUTOFF)
    audio_filter(first)
    audio_filter.reset()
    fresh = filters.make_audio_filter(48_000, HPF_CUTOFF, LPF_CUTOFF)
    np.testing.assert_allclose(audio_filter(second), fresh(second))


#
# The filter is not a brickwall, which biases SINAD low (see TODO.md).
# These pin today's response at the figures TODO.md quotes, so that a
# redesign changes them deliberately, along with TODO.md, rather than
# silently.
#


def test_band_edges_are_where_todo_says():
    (at_hpf, at_lpf) = _response_dB(
        filters.make_audio_filter(48_000, HPF_CUTOFF, LPF_CUTOFF),
        [HPF_CUTOFF, LPF_CUTOFF],
        48_000,
    )
    assert at_hpf == pytest.approx(-4.10, abs=0.01)
    assert at_lpf == pytest.approx(-6.01, abs=0.01)


@pytest.mark.parametrize(
    ("sample_frequency", "expected_Hz"), [(48_000, 3457), (16_000, 3662)]
)
def test_noise_bandwidth_is_what_todo_says(sample_frequency, expected_Hz):
    audio_filter = filters.make_audio_filter(sample_frequency, HPF_CUTOFF, LPF_CUTOFF)
    assert _noise_bandwidth(audio_filter, sample_frequency) == pytest.approx(
        expected_Hz, abs=1
    )
