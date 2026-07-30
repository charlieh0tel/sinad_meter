import os

# Importing auto_plot or sinad_meter pulls in matplotlib.pyplot, which
# picks its backend at import.  Set this before any test module runs
# rather than relying on the caller's environment.
os.environ.setdefault("MPLBACKEND", "Agg")
