# TODO

## Measurement accuracy

- The audio filter passes more noise than it looks like it does, and
  that biases SINAD low.  `make_audio_filter(fs, 200, 4000)` is not a
  brickwall: the cutoffs are roughly half-amplitude edges (-4.10 dB at
  200 Hz, -6.01 dB at 4 kHz at 48 kHz), giving a white-noise ENBW of
  3457 Hz at 48 kHz and 3662 Hz at 16 kHz.  Against an ideal
  300-3000 Hz band that is 1.13-1.32 dB of extra noise, so a true 12 dB
  point reads about 10.8-11 dB.  Decide what band we actually want and
  design the filter to hit it -- note TIA-603-E does not specify an
  analyzer band-pass at all (see below), so this is our choice to make
  and then to state.

- The fundamental is whichever spectral peak is largest, so near
  sensitivity the meter can measure the wrong thing.  Verified: with a
  2.5 kHz spur 6 dB above the 1 kHz tone, the estimator locks to
  2.5 kHz and reports 6.08 dB.  Hum, CTCSS leakage, or an oscillation
  could do the same on a real receiver.  We know the modulation is
  1 kHz; search near it, and flag records where the tone is absent or
  badly displaced rather than returning a plausible number.

## Robustness

- `source_digilent.read()` polls for `DwfState.Done` with no timeout and
  no sleep, so a stalled device hangs the program while spinning a core.
  If `Done` arrives with no samples, `np.concatenate([])` raises.

- `auto_plot.py` inverts a noisy curve: `interp1d` sorts by SINAD rather
  than power, so a non-monotonic sweep can report a plausible but wrong
  12 dB sensitivity.  Pick the crossing in power order.

- `auto_sinad.py` records the sweep but never interpolates the 12 dB
  point; only `auto_plot.py` does, and only for the plot annotation.

- The Keithley and the pyvisa `ResourceManager` are opened and never
  closed, on success or on exception.  Low stakes now that the Keithley
  is opt-in.

- `agc.py` squares in the input dtype, so int16 input overflows before
  `np.mean` sees it.  Nothing wires the AGC in today.

## TIA-603 conformance

The measurement is fairly describable as an unweighted, RMS-like,
200-4000 Hz software SINAD using the TIA ratio definition.  It should
not be called a TIA-603 reference sensitivity measurement until at
least the following are settled.  Section numbers are from TIA-603-E
and were read from a secondary source, so check them against the real
standard before relying on any of it.

- The generator is never configured for the standard test signal:
  §1.3.3.5 wants 1 kHz modulation at 60% of maximum permissible
  deviation.  `auto_sinad.py` sets only power, so carrier frequency,
  deviation, and FM enable depend on undocumented front-panel state.

- §2.1.4 wants rated audio output established first, and the reported
  sensitivity to be the worse of the 12 dB SINAD point and the point
  where output has dropped 3 dB.  We do neither.

- The audio load (§1.3.3.10), receiver state (standard frequency,
  de-emphasis, unsquelched), and cable/matching loss between generator
  and receiver input are all uncontrolled and undocumented.

- The notch in `vendored/pysnr` is adaptive rather than a characterized
  filter: its width moves with record length, sample rate, and noise
  realization.  TIA wants >=40 dB at the fundamental and <=0.6 dB at
  half and twice it.  Simulations suggest it is comparable, but we have
  not measured it ourselves.

## Looked at, not worth fixing

- The median refill in `vendored/pysnr` estimates the noise floor from
  the median over the whole spectrum, which after our band-pass is
  86.5 dB below the true in-band noise, because 89% of bins are in the
  stopband.  The estimate really is that wrong, but it only fills the
  notched bins -- 21 of 6001 -- so it moves total noise power by
  0.0001 dB.  Left alone deliberately; do not "fix" it without
  measuring the effect first.

- `vendored/pysnr/utils.py` has a mis-normalized FFT branch in
  `periodogram()`.  It is unreachable: `sinad_signal` never passes
  `method=`.

- `auto_plot.py` draws the 12 dB annotation as a circle because the
  `"ro"` format string overrides `marker="x"`.
