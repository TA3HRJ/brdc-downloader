# BRDC Ephemeris Downloader

A simple Windows GUI application to download GPS broadcast ephemeris (BRDC) files from [NASA CDDIS](https://cddis.nasa.gov/archive/gnss/data/daily/).

![Python](https://img.shields.io/badge/Python-3.8+-blue) ![License](https://img.shields.io/badge/License-MIT-green) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

## Features

- GUI interface — no command line needed
- Downloads RINEX 2 (`brdc*.YYn`) or RINEX 3 (`BRDC00IGS_R_*`) navigation files
- Date picker with automatic Day-of-Year (DOY) calculation
- Auto-decompresses `.gz` files
- Optional `.brdc` extension rename
- NASA Earthdata Login authentication
- Auto-installs `requests` dependency on first run

## Requirements

- [Python 3.8+](https://www.python.org/downloads/)
- A free [NASA Earthdata](https://urs.earthdata.nasa.gov/users/new) account

## Usage

1. Double-click `BRDC_Indir.bat` — the GUI opens (no console window)
2. Enter your Earthdata username and password
3. Select the date
4. Choose RINEX format and output options
5. Click **İndir**

To create a Desktop shortcut, run `Masaustu_Kisayol_Olustur.bat` once.

## File Naming

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
