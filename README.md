# Software SINAD meter

This is a software SINAD meter.  It display both the audio waveform
and the SINAD for the current acquisition window and a filtered SINAD
value as text.

![Image](images/running-on-portaudio.png)
![Image](images/running-on-pydwf-on-ad3.png)

For acquisition the code supports:
- bog-standard audio capture devices that PortAudio can talk to
- Digilent devices supported by pydwf (but only AD3 is known to work)

It has only been tested on Linux.  (It might work on Windoze; it might not.)

## Running

Dependencies are managed with [uv](https://docs.astral.sh/uv/).  The
environment is created on demand, so there is nothing to install first:

```
uv run ./sinad_meter.py
```

`uv run` works for the other scripts here too, e.g. `uv run ./auto_sinad.py`.


73 DE AI6KG<br />
Christopher Hoover<br />
Mountain View, California

