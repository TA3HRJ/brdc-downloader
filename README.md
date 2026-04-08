# BRDC Ephemeris Downloader

> **⚠ Legal Warning**
> The GPS-SIM file generation feature is intended solely for **experimental and educational purposes** in a controlled RF environment (e.g. Faraday cage, shielded lab).
> Broadcasting GPS signals — even simulated ones — **may be illegal in your jurisdiction** and can interfere with navigation systems, aviation, and emergency services.
> You are solely responsible for ensuring compliance with all applicable local laws and regulations before use.
> The authors of this software accept no liability for any misuse.

A Windows GUI application that downloads GPS broadcast ephemeris (BRDC) files from [NASA CDDIS](https://cddis.nasa.gov/archive/gnss/data/daily/) and optionally generates **PortaPack Mayhem GPS-SIM** files (`.C8` + `.TXT`).

![Python](https://img.shields.io/badge/Python-3.8+-blue) ![License](https://img.shields.io/badge/License-MIT-green) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

## Features

- GUI interface — no command line needed
- Downloads RINEX 2 (`brdc*.YYn`) or RINEX 3 (`BRDC00IGS_R_*`) navigation files
- Date picker with automatic Day-of-Year (DOY) calculation
- Auto-decompresses `.gz` files
- Optional `.brdc` extension rename
- **GPS-SIM output:** generates `.C8` + `.TXT` files ready for PortaPack Mayhem
  - Configurable latitude, longitude, height, sample rate, duration
  - Default TX parameters pre-filled (GPS L1: 1575.420 MHz)
- NASA Earthdata Login authentication
- Auto-installs `requests` dependency on first run

## Requirements

- [Python 3.8+](https://www.python.org/downloads/)
- A free [NASA Earthdata](https://urs.earthdata.nasa.gov/users/new) account
- *(For GPS-SIM only)* [gps-sdr-sim](https://github.com/osqzss/gps-sdr-sim) compiled executable

## Usage

1. Double-click `BRDC_Downloader.bat` — the GUI opens (no console window)
2. Enter your Earthdata username and password
3. Select the date
4. Choose RINEX format and output options
5. *(Optional)* Enable **GPS-SIM Output**, set your location and parameters
6. Click **Download**

To create a Desktop shortcut, run `Create_Desktop_Shortcut.bat` once.

## GPS-SIM Output (PortaPack Mayhem)

When enabled, after downloading and decompressing the BRDC file, the app runs `gps-sdr-sim` to generate:

| File | Description |
|------|-------------|
| `gpssim.C8` | Raw IQ baseband GPS signal (8-bit signed) |
| `gpssim.TXT` | TX parameters: center frequency + sample rate |

The `.TXT` file format:
```
center_frequency=1575420000
sample_rate=2600000
```

### Getting gps-sdr-sim

Download or compile from: https://github.com/osqzss/gps-sdr-sim  
Point the app to `gps-sdr-sim.exe` using the Browse button.

### Default Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| Center frequency | 1575.420 MHz | GPS L1, fixed |
| Sample rate | 2.6 MHz | Recommended for PortaPack |
| Latitude / Longitude | 0.0 / 0.0 | Change to your location |
| Height | 0 m | Meters above sea level |
| Duration | 300 s | 5 minutes |

## BRDC File Naming

| Format  | Example filename           | Note                        |
|---------|----------------------------|-----------------------------|
| RINEX 2 | `brdc0970.26n`             | Standard GPS nav, year 2026 |
| RINEX 3 | `BRDC00IGS_R_2026097...`   | Multi-constellation         |
| .brdc   | `brdc0970.brdc`            | Same content, renamed       |

## Authentication

CDDIS requires a free Earthdata account. Register at:  
https://urs.earthdata.nasa.gov/users/new

Your credentials are **never stored** — entered each session in the GUI.

## License

MIT — see [LICENSE](LICENSE)
