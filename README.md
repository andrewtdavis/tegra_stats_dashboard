# Tegra Stats Dashboard

This script generates graphs in real time based on the output of `tegrastats` in Jetson development boards since the normal `nvtop` and other NVIDIA GPU utilities don't work with these devices.

Requires `asciichartpy`: `python3 -m pip install asciichartpy`

USAGE: `sudo tegrastats | python3 tegrastats_live_graph.py`