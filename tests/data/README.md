MATLAB-generated reference signals from the pysnr project
(https://github.com/psambit9791/pysnr, MIT, Copyright (c) 2022 Sambit
Paul), taken from its `test/data`.  Each holds `x`, `noise`, `Fs`, `Fi`
and `N`; the SINAD values MATLAB reports for them are asserted in
`tests/test_sinad.py`.  They pin the estimator in `vendored/pysnr`
against the implementation it was cloned from.
