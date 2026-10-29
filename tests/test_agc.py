import numpy as np
import pytest

import agc


def _tone(rms, n=4800, dtype=float):
    """A sine of the given RMS, a whole number of cycles long."""
    samples = rms * np.sqrt(2) * np.sin(2 * np.pi * np.arange(n) / 48)
    return samples.astype(dtype)


def _rms(samples):
    return np.sqrt(np.mean(np.asarray(samples, dtype=float) ** 2))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"target_rms": 1.0, "smoothing_factor": -0.1},
        {"target_rms": 1.0, "smoothing_factor": 1.1},
        {"target_rms": 0.0},
        {"target_rms": 1.0, "initial_gain": 0.0},
    ],
)
def test_bad_parameters_are_rejected(kwargs):
    with pytest.raises(ValueError):
        agc.AutomaticGainControl(**kwargs)


def test_an_empty_batch_changes_nothing():
    gain = agc.AutomaticGainControl(target_rms=0.5, initial_gain=2.0)
    assert gain(np.array([])).size == 0
    assert gain.get_current_gain() == 2.0


def test_input_already_at_target_keeps_the_gain():
    # The power estimate starts where initial_gain would put the output on
    # target, so input at that level is a fixed point.
    gain = agc.AutomaticGainControl(target_rms=0.5, initial_gain=2.0)
    for _ in range(10):
        out = gain(_tone(0.25))
    assert gain.get_current_gain() == pytest.approx(2.0)
    assert _rms(out) == pytest.approx(0.5)


def test_no_smoothing_corrects_in_one_batch():
    gain = agc.AutomaticGainControl(target_rms=0.5, smoothing_factor=1.0)
    out = gain(_tone(0.1))
    assert gain.get_current_gain() == pytest.approx(5.0)
    assert _rms(out) == pytest.approx(0.5)


def test_full_smoothing_never_changes_the_gain():
    gain = agc.AutomaticGainControl(
        target_rms=0.5, smoothing_factor=0.0, initial_gain=3.0
    )
    for _ in range(10):
        out = gain(_tone(0.1))
    assert gain.get_current_gain() == 3.0
    assert _rms(out) == pytest.approx(0.3)


def test_steady_input_converges_to_target():
    gain = agc.AutomaticGainControl(target_rms=0.5, smoothing_factor=0.2)
    for _ in range(200):
        out = gain(_tone(0.05))
    assert _rms(out) == pytest.approx(0.5, rel=1e-3)


@pytest.mark.xfail(
    strict=True,
    reason="TODO.md: squares in the input dtype, so int16 overflows and "
    "the gain runs away",
)
def test_int16_input_gets_the_same_gain_as_float():
    # RMS 707 counts: each square is about 1e6, far past int16's 32767.
    as_float = agc.AutomaticGainControl(target_rms=0.5, smoothing_factor=1.0)
    as_float(_tone(707.0))
    as_int16 = agc.AutomaticGainControl(target_rms=0.5, smoothing_factor=1.0)
    as_int16(_tone(707.0, dtype=np.int16))
    assert as_int16.get_current_gain() == pytest.approx(
        as_float.get_current_gain(), rel=1e-3
    )
