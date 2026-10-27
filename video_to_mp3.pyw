# -*- coding: utf-8 -*-
"""
Video to MP3 Çevirici - Powered by MM
Portativ: ffmpeg.exe bu faylla eyni qovluqda olmalıdır.
"""

import os
import re
import sys
import queue
import shutil
import ctypes
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ---------------------------------------------------------------- High-DPI
if os.name == "nt":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# ---------------------------------------------------------------- Yollar
BASE_DIR = os.path.dirname(os.path.abspath(
    sys.executable if getattr(sys, "frozen", False) else __file__))
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def find_ffmpeg():
    local = os.path.join(BASE_DIR, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    if os.path.isfile(local):
        return local
    return shutil.which("ffmpeg")


def unique_path(path):
    """Mövcud faylı üzərinə yazmamaq üçün 'ad (1).mp3' kimi yeni ad verir."""
    base, ext = os.path.splitext(path)
    p, i = path, 1
    while os.path.exists(p):
        p = f"{base} ({i}){ext}"
        i += 1
    return p


# ---------------------------------------------------------------- Rənglər
BG, CARD, BORDER = "#f8fafc", "#ffffff", "#e2e8f0"
PRIMARY, PRIMARY_HOVER = "#2563eb", "#1d4ed8"
DANGER, DANGER_HOVER = "#dc2626", "#b91c1c"
TEXT, MUTED, OK = "#0f172a", "#64748b", "#16a34a"
FONT = "Segoe UI"

VIDEO_TYPES = [
    ("Video faylları", "*.mp4 *.avi *.mkv *.mov *.webm *.flv *.wmv *.m4v *.mpg *.mpeg *.3gp *.ts"),
    ("Bütün fayllar", "*.*"),
]
BITRATES = ["320k", "256k", "192k", "128k"]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video to MP3 Çevirici")
        self.configure(bg=BG)
        self.resizable(False, False)

        self.q = queue.Queue()
        self.proc = None
        self.cancelled = False
        self.running = False

        self.bitrate_var = tk.StringVar(value="320k")
        self.out_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Hazırdır...")
        self.status_color = MUTED

        self._window()
        self._styles()
        self._ui()

        if not find_ffmpeg():
            self._set_status("ffmpeg.exe tapılmadı! Faylı proqramın qovluğuna qoyun.", DANGER)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll)

    # ------------------------------------------------------------ Pəncərə
    def _window(self):
        scale = self.winfo_fpixels("1i") / 96.0
        w, h = int(540 * scale), int(470 * scale)
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TFrame", background=BG)
        s.configure("Card.TFrame", background=CARD, relief="solid",
                    borderwidth=1, bordercolor=BORDER)
        s.configure("TLabel", background=BG, foreground=TEXT, font=(FONT, 10))
        s.configure("Card.TLabel", background=CARD, foreground=TEXT, font=(FONT, 10))
        s.configure("Title.TLabel", background=BG, foreground="#1e293b", font=(FONT, 17, "bold"))
        s.configure("Sub.TLabel", background=BG, foreground=MUTED, font=(FONT, 9))
        s.configure("Footer.TLabel", background=BG, foreground="#94a3b8", font=(FONT, 8, "italic"))

        s.configure("TEntry", fieldbackground="#ffffff", foreground=TEXT,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                    padding=6, font=(FONT, 10))
        s.configure("TCombobox", fieldbackground="#ffffff", background="#ffffff",
                    foreground=TEXT, bordercolor=BORDER, arrowcolor=MUTED,
                    padding=5, font=(FONT, 10))
        s.map("TCombobox", fieldbackground=[("readonly", "#ffffff")])

        s.configure("Primary.TButton", background=PRIMARY, foreground="#ffffff",
                    font=(FONT, 11, "bold"), padding=(14, 10), borderwidth=0,
                    focusthickness=0, focuscolor=PRIMARY)
        s.map("Primary.TButton",
              background=[("disabled", "#93c5fd"), ("active", PRIMARY_HOVER)],
              foreground=[("disabled", "#ffffff")])
        s.configure("Danger.TButton", background=DANGER, foreground="#ffffff",
                    font=(FONT, 11, "bold"), padding=(14, 10), borderwidth=0,
                    focusthickness=0, focuscolor=DANGER)
        s.map("Danger.TButton",
              background=[("disabled", "#fca5a5"), ("active", DANGER_HOVER)],
              foreground=[("disabled", "#ffffff")])
        s.configure("Secondary.TButton", background="#e2e8f0", foreground=TEXT,
                    font=(FONT, 10), padding=(10, 6), borderwidth=0,
                    focusthickness=0, focuscolor="#e2e8f0")
        s.map("Secondary.TButton", background=[("active", "#cbd5e1"), ("disabled", "#f1f5f9")])
        s.configure("Blue.Horizontal.TProgressbar", troughcolor="#e2e8f0",
                    background=PRIMARY, bordercolor="#e2e8f0",
                    lightcolor=PRIMARY, darkcolor=PRIMARY, thickness=12)

    # ------------------------------------------------------------ İnterfeys
    def _ui(self):
        outer = ttk.Frame(self, padding=(26, 20, 26, 6))
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="🎵 Video to MP3 Çevirici", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Bir və ya bir neçə videonu yüksək keyfiyyətli səsə çevirin",
                  style="Sub.TLabel").pack(anchor="w", pady=(2, 14))

        card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        card.pack(fill="x")
        card.columnconfigure(0, weight=1)

        ttk.Label(card, text="Keyfiyyət (bitrate)", style="Card.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4))
        self.cb = ttk.Combobox(card, textvariable=self.bitrate_var, values=BITRATES,
                               state="readonly", width=10)
        self.cb.grid(row=1, column=0, sticky="w", pady=(0, 12))

        ttk.Label(card, text="Yadda saxlama qovluğu (boş = videonun öz qovluğu)",
                  style="Card.TLabel").grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 4))
        self.out_entry = ttk.Entry(card, textvariable=self.out_var)
        self.out_entry.grid(row=3, column=0, sticky="ew", padx=(0, 8))
        self.browse_btn = ttk.Button(card, text="Gözat...", style="Secondary.TButton",
                                     command=self._browse)
        self.browse_btn.grid(row=3, column=1)
        self.clear_btn = ttk.Button(card, text="✕", width=3, style="Secondary.TButton",
                                    command=lambda: self.out_var.set(""))
        self.clear_btn.grid(row=3, column=2, padx=(6, 0))

        btns = ttk.Frame(outer)
        btns.pack(fill="x", pady=(14, 10))
        btns.columnconfigure(0, weight=1)
        self.start_btn = ttk.Button(btns, text="📁 Video Seç və Çevir",
                                    style="Primary.TButton", command=self._start)
        self.start_btn.grid(row=0, column=0, sticky="ew")
        self.cancel_btn = ttk.Button(btns, text="Ləğv et", style="Danger.TButton",
                                     command=self._cancel, state="disabled")
        self.cancel_btn.grid(row=0, column=1, padx=(8, 0))

        prog = ttk.Frame(outer, style="Card.TFrame", padding=14)
        prog.pack(fill="x")
        self.bar = ttk.Progressbar(prog, style="Blue.Horizontal.TProgressbar",
                                   mode="determinate", maximum=100)
        self.bar.pack(fill="x")
        self.status_lbl = tk.Label(prog, textvariable=self.status_var, bg=CARD, fg=MUTED,
                                   font=(FONT, 9), wraplength=440, justify="left", anchor="w")
        self.status_lbl.pack(fill="x", pady=(8, 0))

        ttk.Label(self, text="Powered by MM", style="Footer.TLabel").pack(side="bottom", pady=(0, 10))

    # ------------------------------------------------------------ Köməkçilər
    def _set_status(self, text, color=MUTED):
        self.status_var.set(text)
        self.status_lbl.configure(fg=color)

    def _browse(self):
        d = filedialog.askdirectory(title="Qovluq seçin")
        if d:
            self.out_var.set(os.path.normpath(d))

    def _busy(self, on):
        self.running = on
        st = "disabled" if on else "normal"
        self.start_btn.configure(state=st)
        self.browse_btn.configure(state=st)
        self.clear_btn.configure(state=st)
        self.out_entry.configure(state=st)
        self.cb.configure(state="disabled" if on else "readonly")
        self.cancel_btn.configure(state="normal" if on else "disabled")

    def _indeterminate(self, on):
        if on:
            self.bar.configure(mode="indeterminate")
            self.bar.start(12)
        else:
            self.bar.stop()
            self.bar.configure(mode="determinate")

    # ------------------------------------------------------------ Başlat / Ləğv
    def _start(self):
        if self.running:
            return
        ff = find_ffmpeg()
        if not ff:
            messagebox.showerror("ffmpeg tapılmadı",
                                 "ffmpeg.exe faylı proqramın qovluğunda tapılmadı:\n\n"
                                 f"{BASE_DIR}\n\nFaylı bu qovluğa yerləşdirin.")
            return

        files = filedialog.askopenfilenames(title="Video seçin", filetypes=VIDEO_TYPES)
        if not files:
            return

        outdir = self.out_var.get().strip()
        if outdir:
            try:
                os.makedirs(outdir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Qovluq xətası", f"Qovluq yaradıla bilmədi:\n{e}")
                return

        self.cancelled = False
        self._busy(True)
        self._indeterminate(False)
        self.bar["value"] = 0
        self._set_status("Çevrilir, zəhmət olmasa gözləyin...", "#0284c7")

        threading.Thread(target=self._worker,
                         args=(ff, list(files), self.bitrate_var.get(), outdir),
                         daemon=True).start()

    def _cancel(self):
        if self.running:
            self.cancelled = True
            self._set_status("Ləğv edilir...", MUTED)
            self._kill()

    def _kill(self):
        p = self.proc
        if p and p.poll() is None:
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                                   creationflags=CREATE_NO_WINDOW,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    p.terminate()
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

    # ------------------------------------------------------------ Arxa fon işçisi
    def _worker(self, ff, files, bitrate, outdir):
        total = len(files)
        ok, failed = [], []
        dur_re = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
        time_re = re.compile(r"out_time_(?:us|ms)=(\d+)")
        kv_re = re.compile(r"^\w+=")

        for idx, src in enumerate(files):
            if self.cancelled:
                break
            name = os.path.basename(src)
            folder = outdir or os.path.dirname(src)
            dst = unique_path(os.path.join(folder, os.path.splitext(name)[0] + ".mp3"))
            prefix = f"[{idx + 1}/{total}] " if total > 1 else ""
            self.q.put(("busy", f"{prefix}Hazırlanır: {name}"))

            cmd = [ff, "-hide_banner", "-nostdin", "-n", "-i", src,
                   "-vn", "-map_metadata", "0",
                   "-c:a", "libmp3lame", "-b:a", bitrate,
                   "-progress", "pipe:1", "-nostats", dst]

            duration = None
            tail = []
            try:
                self.proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                    errors="replace", creationflags=CREATE_NO_WINDOW)

                for raw in self.proc.stdout:
                    line = raw.strip()
                    if not line:
                        continue
                    if duration is None:
                        m = dur_re.search(line)
                        if m:
                            duration = (int(m.group(1)) * 3600 + int(m.group(2)) * 60
                                        + float(m.group(3)))
                    m = time_re.match(line)
                    if m and duration:
                        cur = int(m.group(1)) / 1_000_000
                        frac = max(0.0, min(cur / duration, 1.0))
                        overall = (idx + frac) / total * 100
                        self.q.put(("prog", overall,
                                    f"{prefix}Çevrilir: {name}  •  {frac * 100:.0f}%"))
                    elif not kv_re.match(line):
                        tail.append(line)
                        tail = tail[-6:]

                code = self.proc.wait()
            except Exception as e:
                code, tail = -1, [str(e)]
            finally:
                self.proc = None

            if self.cancelled:
                self._remove(dst)
                break
            if code == 0 and os.path.isfile(dst):
                ok.append(dst)
            else:
                self._remove(dst)
                reason = "\n".join(tail[-3:]) if tail else f"ffmpeg xəta kodu: {code}"
                failed.append((name, reason))

        if self.cancelled:
            self.q.put(("cancelled",))
        else:
            self.q.put(("done", ok, failed))

    @staticmethod
    def _remove(path):
        try:
            if os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass

    # ------------------------------------------------------------ UI növbəsi
    def _poll(self):
        try:
            while True:
                m = self.q.get_nowait()
                k = m[0]
                if k == "prog":
                    if str(self.bar.cget("mode")) != "determinate":
                        self._indeterminate(False)
                    self.bar["value"] = m[1]
                    self._set_status(m[2], "#0284c7")
                elif k == "busy":
                    self._indeterminate(True)
                    self._set_status(m[1], "#0284c7")
                elif k == "cancelled":
                    self._indeterminate(False)
                    self.bar["value"] = 0
                    self._set_status("Çevirmə ləğv edildi.", MUTED)
                    self._busy(False)
                elif k == "done":
                    self._finish(m[1], m[2])
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _finish(self, ok, failed):
        self._indeterminate(False)
        self._busy(False)

        if ok and not failed:
            self.bar["value"] = 100
            self._set_status("Uğurla çevrildi! 🎉", OK)
            text = (f"Səs faylı uğurla yaradıldı:\n{ok[0]}" if len(ok) == 1
                    else f"{len(ok)} fayl uğurla çevrildi.")
            if messagebox.askyesno("Uğurlu", text + "\n\nQovluğu açmaq istəyirsiniz?"):
                self._reveal(ok[0])
        elif ok and failed:
            self.bar["value"] = 100
            self._set_status(f"{len(ok)} uğurlu, {len(failed)} xəta.", "#d97706")
            details = "\n\n".join(f"• {n}\n  {r}" for n, r in failed)
            messagebox.showwarning("Qismən uğurlu",
                                   f"{len(ok)} fayl çevrildi, {len(failed)} fayl alınmadı:\n\n{details}")
        else:
            self.bar["value"] = 0
            self._set_status("Xəta baş verdi!", DANGER)
            details = "\n\n".join(f"• {n}\n  {r}" for n, r in failed)
            messagebox.showerror("Xəta", f"Çevrilmə zamanı xəta baş verdi:\n\n{details}")

    @staticmethod
    def _reveal(path):
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", path])
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(path)])
        except Exception as e:
            messagebox.showerror("Xəta", f"Qovluq açıla bilmədi:\n{e}")

    def _on_close(self):
        if self.running:
            if not messagebox.askyesno("Çıxış", "Çevirmə davam edir. Çıxmaq istəyirsiniz?"):
                return
            self.cancelled = True
            self._kill()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
