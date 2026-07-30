# Sweeps

`sinad_tk981_sn30900133_<generator>.csv` are SINAD sweeps of a TK981,
serial 30900133, measured against a Keithley 2015, one per signal
generator.

The `_s_over_nd` files are the same sweeps as originally recorded, when
this meter reported S/(N+D) -- MATLAB's and pysnr's definition, which
can go negative and does, to -4.6 dB.  The files without that suffix are
those numbers converted to (S+N+D)/(N+D), the radio definition the meter
now reports and the one the Keithley columns were always in:

    sinad_mean_dB -> 10*log10(1 + 10**(sinad_mean_dB/10))
    sinad_std_dB  -> sinad_std_dB / (1 + 10**(-sinad_mean_dB/10))

The second line propagates the error bars through the first, which
compresses them where the correction is largest.

Converting the recorded mean is not quite the mean of the converted
readings, since the conversion is not linear, but over the ~1 dB spread
of the 128 readings behind each point the difference is at most 0.027 dB,
and 0.016 dB near the 12 dB sensitivity point.  The raw records were not
kept, so this is as close as the old sweeps can be brought; anything
measured from now on is recorded in the radio definition directly.

The Keithley columns are untouched: it measures the radio definition, so
it never needed converting.
