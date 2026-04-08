"""
BRDC GPS Ephemeris Downloader
Downloads RINEX broadcast navigation files from NASA CDDIS and
optionally generates PortaPack Mayhem GPS-SIM files (.C8 + .TXT).

Requires Earthdata Login (https://urs.earthdata.nasa.gov)
GPS-SIM generation requires gps-sdr-sim (https://github.com/osqzss/gps-sdr-sim)
"""

# Auto-install missing dependencies before anything else
import subprocess, sys

def _ensure(pkg, import_name=None):
    try:
        __import__(import_name or pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", pkg])

_ensure("requests")

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import requests
import gzip
import shutil
import os
from datetime import datetime, date
import calendar
import queue

CDDIS_BASE    = "https://cddis.nasa.gov/archive/gnss/data/daily"
EARTHDATA_HOST = "urs.earthdata.nasa.gov"
GPS_L1_HZ     = 1575420000

SAMPLE_RATES = {
    "2.6 MHz  (recommended)": 2600000,
    "2.5 MHz":                 2500000,
    "1.25 MHz (low res)":      1250000,
}


# ---------------------------------------------------------------------------
# Earthdata-aware requests session
# ---------------------------------------------------------------------------
class EarthdataSession(requests.Session):
    def __init__(self, username: str, password: str):
        super().__init__()
        self.auth = (username, password)

    def rebuild_auth(self, prepared_request, response):
        headers = prepared_request.headers
        if "Authorization" in headers:
            orig_host  = requests.utils.urlparse(response.request.url).hostname
            redir_host = requests.utils.urlparse(prepared_request.url).hostname
            if (orig_host != redir_host
                    and redir_host != EARTHDATA_HOST
                    and orig_host  != EARTHDATA_HOST):
                del headers["Authorization"]
        return


# ---------------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------------
def build_url_rinex2(year: int, doy: int):
    yy   = str(year)[-2:]
    doy3 = str(doy).zfill(3)
    fname = f"brdc{doy3}0.{yy}n.gz"
    return f"{CDDIS_BASE}/{year}/{doy3}/{yy}n/{fname}", fname


def build_url_rinex3(year: int, doy: int):
    doy3  = str(doy).zfill(3)
    fname = f"BRDC00IGS_R_{year}{doy3}0000_01D_MN.rnx.gz"
    return f"{CDDIS_BASE}/{year}/{doy3}/MN/{fname}", fname


def date_to_doy(year: int, month: int, day: int) -> int:
    return datetime(year, month, day).timetuple().tm_yday


# ---------------------------------------------------------------------------
# GPS-SIM worker  (called after successful BRDC download)
# ---------------------------------------------------------------------------
def gpssim_worker(
    exe_path: str,
    brdc_file: str,
    lat: float, lon: float, height: float,
    sample_rate: int,
    duration: int,
    output_prefix: str,
    dest_dir: str,
    log_q: queue.Queue,
):
    def log(msg, tag="info"):
        log_q.put((msg, tag))

    c8_path  = os.path.join(dest_dir, f"{output_prefix}.C8")
    txt_path = os.path.join(dest_dir, f"{output_prefix}.TXT")

    if not os.path.isfile(exe_path):
        log(f"gps-sdr-sim not found: {exe_path}", "error")
        log("Download from: https://github.com/osqzss/gps-sdr-sim", "warn")
        return

    cmd = [
        exe_path,
        "-e", brdc_file,
        "-l", f"{lat},{lon},{height}",
        "-b", "8",
        "-s", str(sample_rate),
        "-d", str(duration),
        "-o", c8_path,
    ]

    log(f"Running gps-sdr-sim ...")
    log("  " + " ".join(os.path.basename(c) if i > 0 else c for i, c in enumerate(cmd)))

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                log(f"  {line}")
        proc.wait()

        if proc.returncode != 0:
            log(f"gps-sdr-sim exited with code {proc.returncode}", "error")
            return

        # Write companion .TXT
        with open(txt_path, "w") as f:
            f.write(f"center_frequency={GPS_L1_HZ}\n")
            f.write(f"sample_rate={sample_rate}\n")

        log(f"GPS-SIM done: {c8_path}", "ok")
        log(f"             {txt_path}", "ok")

    except Exception as e:
        log(f"GPS-SIM error: {e}", "error")


# ---------------------------------------------------------------------------
# Download worker
# ---------------------------------------------------------------------------
def download_worker(
    username: str,
    password: str,
    url: str,
    fname: str,
    dest_dir: str,
    decompress: bool,
    rename_brdc: bool,
    gpssim_params: dict | None,
    log_q: queue.Queue,
    prog_q: queue.Queue,
):
    def log(msg, tag="info"):
        log_q.put((msg, tag))

    def prog(val):
        prog_q.put(val)

    gz_path    = os.path.join(dest_dir, fname)
    final_name = fname[:-3] if fname.endswith(".gz") else fname
    final_path = os.path.join(dest_dir, final_name)

    log(f"Connecting: {url}")

    try:
        session = EarthdataSession(username, password)
        session.headers.update({"User-Agent": "BRDCDownloader/1.0"})

        with session.get(url, stream=True, timeout=60) as resp:
            if resp.status_code == 401:
                log("Authentication failed — check username and password.", "error")
                prog(-1)
                return
            if resp.status_code == 404:
                log(f"File not found on server (404): {fname}", "error")
                log("Tip: try RINEX 3 format for this date.", "warn")
                prog(-1)
                return
            resp.raise_for_status()

            total      = int(resp.headers.get("content-length", 0))
            downloaded = 0
            log(f"Downloading: {fname}  ({total // 1024 if total else '?'} KB)")

            with open(gz_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            prog(int(downloaded * 100 / total))

        prog(100)
        log(f"Saved: {gz_path}", "ok")

        # ── Decompress ────────────────────────────────────────────────
        rinex_path = final_path   # path of the decompressed RINEX file
        if decompress:
            log("Decompressing .gz ...")
            try:
                with gzip.open(gz_path, "rb") as f_in, open(final_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
                os.remove(gz_path)

                if rename_brdc:
                    brdc_path  = os.path.splitext(final_path)[0] + ".brdc"
                    os.replace(final_path, brdc_path)
                    rinex_path = brdc_path
                    log(f"Done: {brdc_path}", "ok")
                else:
                    log(f"Done: {final_path}", "ok")
            except Exception as e:
                log(f"Decompression error: {e}", "error")
                log(f"Raw .gz file kept: {gz_path}", "warn")
                prog(-1)
                return
        else:
            log(f"Done (.gz kept): {gz_path}", "ok")

        # ── GPS-SIM generation ────────────────────────────────────────
        if gpssim_params and decompress:
            log("\n── GPS-SIM ─────────────────────────────────────────────")
            gpssim_worker(
                exe_path      = gpssim_params["exe"],
                brdc_file     = rinex_path,
                lat           = gpssim_params["lat"],
                lon           = gpssim_params["lon"],
                height        = gpssim_params["height"],
                sample_rate   = gpssim_params["sample_rate"],
                duration      = gpssim_params["duration"],
                output_prefix = gpssim_params["prefix"],
                dest_dir      = dest_dir,
                log_q         = log_q,
            )

    except requests.exceptions.ConnectionError:
        log("Connection error — check your internet connection.", "error")
        prog(-1)
    except requests.exceptions.Timeout:
        log("Timeout — server did not respond.", "error")
        prog(-1)
    except Exception as e:
        log(f"Unexpected error: {e}", "error")
        prog(-1)


# ---------------------------------------------------------------------------
# Main GUI
# ---------------------------------------------------------------------------
class BRDCApp(tk.Tk):
    RINEX_FORMATS = {"RINEX 2 (brdc*.YYn)": "r2", "RINEX 3 (BRDC00IGS_R_*)": "r3"}
    LOG_COLORS    = {"info": "#e0e0e0", "ok": "#66ff66", "warn": "#ffdd44", "error": "#ff5555"}

    def __init__(self):
        super().__init__()
        self.title("BRDC GPS Ephemeris Downloader")
        self.resizable(False, False)
        self._log_q:  queue.Queue = queue.Queue()
        self._prog_q: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None
        self._build_ui()
        self._poll_queues()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}
        frm = ttk.Frame(self, padding=10)
        frm.grid(row=0, column=0, sticky="nsew")

        # ── Credentials ──────────────────────────────────────────────
        cred_lf = ttk.LabelFrame(frm, text=" NASA Earthdata Credentials ", padding=6)
        cred_lf.grid(row=0, column=0, columnspan=2, sticky="ew", **pad)

        ttk.Label(cred_lf, text="Username:").grid(row=0, column=0, sticky="w")
        self._user_var = tk.StringVar()
        ttk.Entry(cred_lf, textvariable=self._user_var, width=28).grid(
            row=0, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(cred_lf, text="Password:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self._pass_var   = tk.StringVar()
        self._pass_entry = ttk.Entry(cred_lf, textvariable=self._pass_var, show="*", width=28)
        self._pass_entry.grid(row=1, column=1, sticky="ew", padx=(4, 0), pady=(4, 0))

        self._show_pass = tk.BooleanVar(value=False)
        ttk.Checkbutton(cred_lf, text="Show password",
                        variable=self._show_pass, command=self._toggle_pass
                        ).grid(row=2, column=1, sticky="w", pady=(2, 0))

        # ── Date ─────────────────────────────────────────────────────
        date_lf = ttk.LabelFrame(frm, text=" Date ", padding=6)
        date_lf.grid(row=1, column=0, columnspan=2, sticky="ew", **pad)
        today = date.today()

        ttk.Label(date_lf, text="Year:").grid(row=0, column=0, sticky="w")
        self._year_var = tk.IntVar(value=today.year)
        ttk.Spinbox(date_lf, from_=1992, to=today.year, textvariable=self._year_var,
                    width=6, command=self._update_doy_max
                    ).grid(row=0, column=1, sticky="w", padx=(4, 12))

        ttk.Label(date_lf, text="Month:").grid(row=0, column=2, sticky="w")
        self._month_var  = tk.IntVar(value=today.month)
        self._month_spin = ttk.Spinbox(date_lf, from_=1, to=12, textvariable=self._month_var,
                                       width=4, command=self._update_day_max)
        self._month_spin.grid(row=0, column=3, sticky="w", padx=(4, 12))

        ttk.Label(date_lf, text="Day:").grid(row=0, column=4, sticky="w")
        self._day_var  = tk.IntVar(value=today.day)
        self._day_spin = ttk.Spinbox(date_lf, from_=1, to=31, textvariable=self._day_var,
                                     width=4, command=self._on_date_change)
        self._day_spin.grid(row=0, column=5, sticky="w", padx=(4, 0))

        ttk.Label(date_lf, text="DOY:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self._doy_var = tk.IntVar()
        ttk.Label(date_lf, textvariable=self._doy_var, width=4).grid(
            row=1, column=1, sticky="w", pady=(4, 0))
        ttk.Button(date_lf, text="Today", command=self._set_today).grid(
            row=1, column=5, sticky="e", pady=(4, 0))
        self._update_doy()

        # ── Format & Options ─────────────────────────────────────────
        opt_lf = ttk.LabelFrame(frm, text=" Format & Options ", padding=6)
        opt_lf.grid(row=2, column=0, columnspan=2, sticky="ew", **pad)

        ttk.Label(opt_lf, text="Format:").grid(row=0, column=0, sticky="w")
        self._fmt_var = tk.StringVar(value="RINEX 2 (brdc*.YYn)")
        ttk.Combobox(opt_lf, textvariable=self._fmt_var,
                     values=list(self.RINEX_FORMATS.keys()),
                     state="readonly", width=28
                     ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self._decomp_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_lf, text="Decompress .gz file",
                        variable=self._decomp_var, command=self._on_decomp_toggle
                        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self._brdc_var = tk.BooleanVar(value=True)
        self._brdc_chk = ttk.Checkbutton(
            opt_lf,
            text="Save with .brdc extension  (same content, only extension changes)",
            variable=self._brdc_var)
        self._brdc_chk.grid(row=2, column=0, columnspan=2, sticky="w", pady=(2, 0))

        # ── Save Location ─────────────────────────────────────────────
        dest_lf = ttk.LabelFrame(frm, text=" Save Location ", padding=6)
        dest_lf.grid(row=3, column=0, columnspan=2, sticky="ew", **pad)

        self._dest_var = tk.StringVar(value=os.path.expanduser("~/Downloads"))
        ttk.Entry(dest_lf, textvariable=self._dest_var, width=38).grid(
            row=0, column=0, sticky="ew")
        ttk.Button(dest_lf, text="Browse…", command=self._browse_dest).grid(
            row=0, column=1, padx=(4, 0))
        dest_lf.columnconfigure(0, weight=1)

        # ── GPS-SIM (PortaPack Mayhem) ────────────────────────────────
        sim_lf = ttk.LabelFrame(frm, text=" GPS-SIM Output  (PortaPack Mayhem) ", padding=6)
        sim_lf.grid(row=4, column=0, columnspan=2, sticky="ew", **pad)

        self._sim_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(sim_lf, text="Generate .C8 + .TXT after download",
                        variable=self._sim_var, command=self._on_sim_toggle
                        ).grid(row=0, column=0, columnspan=4, sticky="w")

        # gps-sdr-sim.exe
        ttk.Label(sim_lf, text="gps-sdr-sim:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self._exe_var = tk.StringVar(value="gps-sdr-sim.exe")
        self._exe_entry = ttk.Entry(sim_lf, textvariable=self._exe_var, width=30)
        self._exe_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(4, 0), pady=(6, 0))
        self._exe_btn = ttk.Button(sim_lf, text="Browse…", command=self._browse_exe)
        self._exe_btn.grid(row=1, column=3, padx=(4, 0), pady=(6, 0))

        # Lat / Lon / Height
        ttk.Label(sim_lf, text="Latitude:").grid(row=2, column=0, sticky="w", pady=(4, 0))
        self._lat_var = tk.StringVar(value="0.000000")
        self._lat_entry = ttk.Entry(sim_lf, textvariable=self._lat_var, width=14)
        self._lat_entry.grid(row=2, column=1, sticky="w", padx=(4, 8), pady=(4, 0))

        ttk.Label(sim_lf, text="Longitude:").grid(row=2, column=2, sticky="w", pady=(4, 0))
        self._lon_var = tk.StringVar(value="0.000000")
        self._lon_entry = ttk.Entry(sim_lf, textvariable=self._lon_var, width=14)
        self._lon_entry.grid(row=2, column=3, sticky="w", padx=(4, 0), pady=(4, 0))

        ttk.Label(sim_lf, text="Height (m):").grid(row=3, column=0, sticky="w", pady=(4, 0))
        self._height_var = tk.StringVar(value="0")
        self._height_entry = ttk.Entry(sim_lf, textvariable=self._height_var, width=8)
        self._height_entry.grid(row=3, column=1, sticky="w", padx=(4, 8), pady=(4, 0))

        ttk.Label(sim_lf, text="Duration (s):").grid(row=3, column=2, sticky="w", pady=(4, 0))
        self._dur_var = tk.StringVar(value="300")
        self._dur_entry = ttk.Entry(sim_lf, textvariable=self._dur_var, width=8)
        self._dur_entry.grid(row=3, column=3, sticky="w", padx=(4, 0), pady=(4, 0))

        # Sample rate
        ttk.Label(sim_lf, text="Sample rate:").grid(row=4, column=0, sticky="w", pady=(4, 0))
        self._sr_var = tk.StringVar(value=list(SAMPLE_RATES.keys())[0])
        self._sr_combo = ttk.Combobox(sim_lf, textvariable=self._sr_var,
                                      values=list(SAMPLE_RATES.keys()),
                                      state="readonly", width=22)
        self._sr_combo.grid(row=4, column=1, columnspan=2, sticky="w", padx=(4, 0), pady=(4, 0))

        # Output prefix
        ttk.Label(sim_lf, text="Output name:").grid(row=5, column=0, sticky="w", pady=(4, 0))
        self._prefix_var = tk.StringVar(value="gpssim")
        self._prefix_entry = ttk.Entry(sim_lf, textvariable=self._prefix_var, width=16)
        self._prefix_entry.grid(row=5, column=1, sticky="w", padx=(4, 0), pady=(4, 0))
        ttk.Label(sim_lf, text=".C8 / .TXT", foreground="gray").grid(
            row=5, column=2, sticky="w", pady=(4, 0))

        # Center freq display (read-only info)
        ttk.Label(sim_lf, text="Center freq:", foreground="gray").grid(
            row=5, column=2, sticky="e", pady=(4, 0))
        ttk.Label(sim_lf, text="1575.420 MHz  (GPS L1, fixed)",
                  foreground="gray").grid(row=5, column=3, sticky="w", pady=(4, 0))

        # Legal warning label
        warn_text = (
            "⚠  Broadcasting GPS signals may be illegal in your jurisdiction and can\n"
            "    interfere with navigation systems. Use only in a shielded RF environment."
        )
        ttk.Label(sim_lf, text=warn_text, foreground="#ffdd44",
                  justify="left", wraplength=430
                  ).grid(row=6, column=0, columnspan=4, sticky="w", pady=(8, 0))

        self._sim_widgets = [
            self._exe_entry, self._exe_btn,
            self._lat_entry, self._lon_entry,
            self._height_entry, self._dur_entry,
            self._sr_combo, self._prefix_entry,
        ]
        self._on_sim_toggle()   # apply initial disabled state

        # ── Action buttons ────────────────────────────────────────────
        btn_frm = ttk.Frame(frm)
        btn_frm.grid(row=5, column=0, columnspan=2, sticky="ew", **pad)

        self._dl_btn = ttk.Button(btn_frm, text="Download", command=self._start_download)
        self._dl_btn.pack(side="left")
        ttk.Button(btn_frm, text="Open Folder", command=self._open_dest).pack(
            side="left", padx=(8, 0))

        # ── Progress ──────────────────────────────────────────────────
        self._prog_var = tk.IntVar(value=0)
        ttk.Progressbar(frm, variable=self._prog_var, maximum=100, length=460
                        ).grid(row=6, column=0, columnspan=2, sticky="ew", **pad)

        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(frm, textvariable=self._status_var, foreground="gray").grid(
            row=7, column=0, columnspan=2, sticky="w", padx=8)

        # ── Log ───────────────────────────────────────────────────────
        log_lf = ttk.LabelFrame(frm, text=" Log ", padding=4)
        log_lf.grid(row=8, column=0, columnspan=2, sticky="nsew", **pad)

        self._log_text = tk.Text(log_lf, height=10, width=62,
                                 bg="#1e1e1e", fg="#e0e0e0",
                                 font=("Consolas", 9), state="disabled", wrap="word")
        sb = ttk.Scrollbar(log_lf, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=sb.set)
        self._log_text.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        log_lf.columnconfigure(0, weight=1)

        for tag, color in self.LOG_COLORS.items():
            self._log_text.tag_configure(tag, foreground=color)

        frm.columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _on_sim_toggle(self):
        state = "normal" if self._sim_var.get() else "disabled"
        for w in self._sim_widgets:
            w.config(state=state)

    def _on_decomp_toggle(self):
        state = "normal" if self._decomp_var.get() else "disabled"
        self._brdc_chk.config(state=state)

    def _toggle_pass(self):
        self._pass_entry.config(show="" if self._show_pass.get() else "*")

    def _set_today(self):
        t = date.today()
        self._year_var.set(t.year)
        self._month_var.set(t.month)
        self._day_var.set(t.day)
        self._update_doy()

    def _update_day_max(self, *_):
        max_day = calendar.monthrange(self._year_var.get(), self._month_var.get())[1]
        self._day_spin.config(to=max_day)
        if self._day_var.get() > max_day:
            self._day_var.set(max_day)
        self._update_doy()

    def _update_doy_max(self, *_):
        self._update_day_max()

    def _on_date_change(self, *_):
        self._update_doy()

    def _update_doy(self):
        try:
            self._doy_var.set(date_to_doy(
                self._year_var.get(), self._month_var.get(), self._day_var.get()))
        except ValueError:
            self._doy_var.set(0)

    def _browse_dest(self):
        path = filedialog.askdirectory(title="Select save folder")
        if path:
            self._dest_var.set(path)

    def _browse_exe(self):
        path = filedialog.askopenfilename(
            title="Select gps-sdr-sim executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
        if path:
            self._exe_var.set(path)

    def _open_dest(self):
        path = self._dest_var.get()
        if os.path.isdir(path):
            os.startfile(path)
        else:
            messagebox.showwarning("Warning", "Folder not found.")

    def _log(self, msg: str, tag: str = "info"):
        self._log_text.config(state="normal")
        self._log_text.insert("end", msg + "\n", tag)
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def _set_status(self, msg: str):
        self._status_var.set(msg)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def _float(self, var: tk.StringVar, label: str, lo: float, hi: float) -> float | None:
        try:
            v = float(var.get())
            if not (lo <= v <= hi):
                raise ValueError
            return v
        except ValueError:
            messagebox.showerror("Invalid input",
                                 f"{label} must be a number between {lo} and {hi}.")
            return None

    def _int_pos(self, var: tk.StringVar, label: str) -> int | None:
        try:
            v = int(var.get())
            if v <= 0:
                raise ValueError
            return v
        except ValueError:
            messagebox.showerror("Invalid input", f"{label} must be a positive integer.")
            return None

    # ------------------------------------------------------------------
    # Download orchestration
    # ------------------------------------------------------------------
    def _start_download(self):
        if self._worker and self._worker.is_alive():
            messagebox.showinfo("Info", "A download is already in progress.")
            return

        username = self._user_var.get().strip()
        password = self._pass_var.get()
        if not username or not password:
            messagebox.showerror("Error", "Username and password are required.")
            return

        dest = self._dest_var.get().strip()
        if not os.path.isdir(dest):
            try:
                os.makedirs(dest, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create folder:\n{e}")
                return

        year, month, day = self._year_var.get(), self._month_var.get(), self._day_var.get()
        try:
            doy = date_to_doy(year, month, day)
        except ValueError as e:
            messagebox.showerror("Date Error", str(e))
            return

        fmt_key = self._fmt_var.get()
        url, fname = (build_url_rinex2 if self.RINEX_FORMATS[fmt_key] == "r2"
                      else build_url_rinex3)(year, doy)

        # ── Validate GPS-SIM params if enabled ────────────────────────
        gpssim_params = None
        if self._sim_var.get():
            if not self._decomp_var.get():
                messagebox.showerror(
                    "Error", "GPS-SIM requires 'Decompress .gz file' to be enabled.")
                return
            lat    = self._float(self._lat_var,    "Latitude",  -90,  90)
            lon    = self._float(self._lon_var,    "Longitude", -180, 180)
            height = self._float(self._height_var, "Height",    -500, 9000)
            dur    = self._int_pos(self._dur_var,  "Duration")
            if None in (lat, lon, height, dur):
                return
            prefix = self._prefix_var.get().strip() or "gpssim"
            gpssim_params = {
                "exe":         self._exe_var.get().strip(),
                "lat":         lat,
                "lon":         lon,
                "height":      height,
                "sample_rate": SAMPLE_RATES[self._sr_var.get()],
                "duration":    dur,
                "prefix":      prefix,
            }

        self._prog_var.set(0)
        self._set_status(f"Downloading: {fname}")
        self._dl_btn.config(state="disabled")
        self._log(f"\n── {datetime.now().strftime('%H:%M:%S')} ─────────────────────────────────")
        self._log(f"Date: {year}-{month:02d}-{day:02d}  DOY:{doy}  Format:{fmt_key}")
        if gpssim_params:
            self._log(
                f"GPS-SIM: lat={gpssim_params['lat']}  lon={gpssim_params['lon']}"
                f"  h={gpssim_params['height']}m"
                f"  sr={gpssim_params['sample_rate']}  dur={gpssim_params['duration']}s")

        self._worker = threading.Thread(
            target=download_worker,
            args=(username, password, url, fname, dest,
                  self._decomp_var.get(),
                  self._brdc_var.get() and self._decomp_var.get(),
                  gpssim_params,
                  self._log_q, self._prog_q),
            daemon=True,
        )
        self._worker.start()

    # ------------------------------------------------------------------
    # Queue polling
    # ------------------------------------------------------------------
    def _poll_queues(self):
        try:
            while True:
                msg, tag = self._log_q.get_nowait()
                self._log(msg, tag)
        except queue.Empty:
            pass

        try:
            while True:
                val = self._prog_q.get_nowait()
                if val < 0:
                    self._prog_var.set(0)
                    self._set_status("Error — see log panel.")
                    self._dl_btn.config(state="normal")
                elif val == 100:
                    self._prog_var.set(100)
                    self._set_status("Done.")
                    self._dl_btn.config(state="normal")
                else:
                    self._prog_var.set(val)
        except queue.Empty:
            pass

        self.after(100, self._poll_queues)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = BRDCApp()
    app.mainloop()
