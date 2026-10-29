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
  and then to state.  `tests/test_filters.py` pins these figures, so
  update it along with this note.

- `sinad.measure()` looks for the test tone within 10% of where it
  should be (1 kHz in `auto_sinad.py`, `--tone` in `sinad_meter.py`), so
  a bigger spur no longer becomes the signal.  But when the tone is
  absent or outside that window it still returns a plausible number,
  measuring whatever peak is there.  Flag those records instead.

## Robustness

- `source_digilent.read()` polls for `DwfState.Done` with no timeout and
  no sleep, so a stalled device hangs the program while spinning a core.
  If `Done` arrives with no samples, `np.concatenate([])` raises.

- `auto_sinad.py` records the sweep but never interpolates the 12 dB
  point; only `auto_plot.py` does, and only for the plot annotation.

- The Keithley and the pyvisa `ResourceManager` are opened and never
  closed, on success or on exception.  Low stakes now that the Keithley
  is opt-in.

## TIA-603 conformance

The measurement is fairly describable as an unweighted, RMS-like,
200-4000 Hz software SINAD using the TIA ratio definition.  It should
not be called a TIA-603 reference sensitivity measurement until at
least the following are settled.  Section numbers are from TIA-603-E
and were read from a secondary source, so check them against the real
standard before relying on any of it.

- FM on the HP 8663A (`set_fm` in the ee-instruments driver) was
  written from the Operation and Calibration Manual, 08663-90069
  (`third_party/9018-05372.pdf`), and has not been tried on an
  instrument.  Check on one: the deviation and rate actually produced,
  that a rejected entry raises rather than sweeping, and that no other
  modulation was left on from the front panel (neither generator turns
  AM or pulse off).

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
