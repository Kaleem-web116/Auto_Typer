"""
Auto Typer - Simulates keyboard input with optional typos
Requires: pip install pynput
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import random
import string
from pynput.keyboard import Controller, Key

keyboard = Controller()

# --- Typo logic ---

QWERTY_NEIGHBORS = {
    'q': 'wa', 'w': 'qase', 'e': 'wsdr', 'r': 'edft', 't': 'rfgy',
    'y': 'tghu', 'u': 'yhji', 'i': 'ujko', 'o': 'iklp', 'p': 'ol',
    'a': 'qwsz', 's': 'awedxz', 'd': 'serfcx', 'f': 'drtgvc',
    'g': 'ftyhbv', 'h': 'gyujnb', 'j': 'huikmn', 'k': 'jiolm',
    'l': 'kop', 'z': 'asx', 'x': 'zsdc', 'c': 'xdfv', 'v': 'cfgb',
    'b': 'vghn', 'n': 'bhjm', 'm': 'njk',
}

def get_typo_char(char):
    """Return a nearby key on QWERTY layout."""
    lower = char.lower()
    if lower in QWERTY_NEIGHBORS:
        neighbor = random.choice(QWERTY_NEIGHBORS[lower])
        return neighbor.upper() if char.isupper() else neighbor
    return char


def type_text(text, wpm, typo_chance, typo_correction_delay, stop_event, status_var):
    """Core typing function run in a background thread."""
    chars_per_second = (wpm * 5) / 60  # avg 5 chars per word
    base_delay = 1.0 / chars_per_second

    status_var.set("Typing...")

    for i, char in enumerate(text):
        if stop_event.is_set():
            status_var.set("Stopped.")
            return

        # Decide whether to introduce a typo
        if char.isalpha() and random.random() < typo_chance:
            typo = get_typo_char(char)
            keyboard.type(typo)
            time.sleep(typo_correction_delay)
            # Backspace the typo
            keyboard.press(Key.backspace)
            keyboard.release(Key.backspace)
            time.sleep(base_delay * random.uniform(0.8, 1.4))

        # Type the correct character
        keyboard.type(char)

        # Natural variance in delay
        delay = base_delay * random.uniform(0.6, 1.6)
        # Extra pause after punctuation / space
        if char in '.!?,;:':
            delay *= random.uniform(2.0, 3.5)
        elif char == ' ':
            delay *= random.uniform(1.1, 1.5)

        time.sleep(delay)

    status_var.set("Done!")


# --- GUI ---

class AutoTyperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Typer")
        self.root.resizable(False, False)
        self.stop_event = threading.Event()
        self._build_ui()

    def _build_ui(self):
        root = self.root
        PAD = 12

        # ── Header ──────────────────────────────────────────────
        header = tk.Frame(root, bg="#1a1a2e", pady=10)
        header.pack(fill="x")
        tk.Label(
            header, text="⌨  Auto Typer",
            font=("Courier New", 18, "bold"),
            bg="#1a1a2e", fg="#e0e0ff"
        ).pack()
        tk.Label(
            header, text="paste text → hit Start → switch to target window",
            font=("Courier New", 9),
            bg="#1a1a2e", fg="#888aaa"
        ).pack()

        # ── Main body ────────────────────────────────────────────
        body = tk.Frame(root, bg="#12121f", padx=PAD, pady=PAD)
        body.pack(fill="both", expand=True)

        # Text input
        tk.Label(body, text="Text to type:", font=("Courier New", 10, "bold"),
                 bg="#12121f", fg="#c8c8ff", anchor="w").pack(fill="x")
        self.text_box = scrolledtext.ScrolledText(
            body, width=58, height=8,
            font=("Courier New", 10),
            bg="#0d0d1a", fg="#e8e8ff",
            insertbackground="#e8e8ff",
            relief="flat", borderwidth=6,
            wrap="word"
        )
        self.text_box.pack(fill="x", pady=(4, 12))

        # Settings grid
        settings = tk.Frame(body, bg="#12121f")
        settings.pack(fill="x", pady=(0, 12))

        def label(parent, text, row, col):
            tk.Label(parent, text=text, font=("Courier New", 9),
                     bg="#12121f", fg="#888aaa").grid(
                row=row, column=col, sticky="w", padx=(0, 6), pady=3)

        def slider(parent, from_, to, default, row, col, fmt=None):
            var = tk.DoubleVar(value=default)
            s = ttk.Scale(parent, from_=from_, to=to, variable=var,
                          orient="horizontal", length=160)
            s.grid(row=row, column=col+1, sticky="ew", padx=(0, 16))
            display = tk.Label(parent, font=("Courier New", 9),
                               bg="#12121f", fg="#e0c0ff", width=6)
            display.grid(row=row, column=col+2, sticky="w")

            def update(*_):
                v = var.get()
                display.config(text=fmt(v) if fmt else f"{v:.1f}")
            var.trace_add("write", update)
            update()
            return var

        label(settings, "Typing speed (WPM):", 0, 0)
        self.wpm_var = slider(settings, 20, 200, 60, 0, 0,
                              fmt=lambda v: f"{int(v)} wpm")

        label(settings, "Typo chance:", 1, 0)
        self.typo_var = slider(settings, 0, 0.3, 0.05, 1, 0,
                               fmt=lambda v: f"{v*100:.0f}%")

        label(settings, "Correction delay (s):", 2, 0)
        self.delay_var = slider(settings, 0.05, 1.0, 0.2, 2, 0,
                                fmt=lambda v: f"{v:.2f}s")

        label(settings, "Startup delay (s):", 3, 0)
        self.startup_var = slider(settings, 1, 10, 3, 3, 0,
                                  fmt=lambda v: f"{int(v)}s")

        # ── Buttons ───────────────────────────────────────────────
        btn_frame = tk.Frame(body, bg="#12121f")
        btn_frame.pack(fill="x")

        btn_style = dict(font=("Courier New", 11, "bold"), relief="flat",
                         padx=20, pady=6, cursor="hand2")

        self.start_btn = tk.Button(
            btn_frame, text="▶  Start", bg="#2d2d6e", fg="#e0e0ff",
            activebackground="#4040a0", activeforeground="white",
            command=self.start_typing, **btn_style
        )
        self.start_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = tk.Button(
            btn_frame, text="■  Stop", bg="#3d1a1a", fg="#ffaaaa",
            activebackground="#6d2020", activeforeground="white",
            state="disabled", command=self.stop_typing, **btn_style
        )
        self.stop_btn.pack(side="left")

        self.clear_btn = tk.Button(
            btn_frame, text="✕  Clear", bg="#1e1e2e", fg="#888aaa",
            activebackground="#2a2a40", activeforeground="#ccccff",
            command=lambda: self.text_box.delete("1.0", "end"),
            **btn_style
        )
        self.clear_btn.pack(side="right")

        # ── Status bar ────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(body, textvariable=self.status_var,
                 font=("Courier New", 9), bg="#12121f", fg="#55ff99",
                 anchor="w").pack(fill="x", pady=(10, 0))

        # Style the sliders
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Horizontal.TScale",
                        troughcolor="#2a2a4a", background="#5050b0",
                        sliderthickness=14)

    def start_typing(self):
        text = self.text_box.get("1.0", "end-1c")
        if not text.strip():
            self.status_var.set("No text entered.")
            return

        delay = int(self.startup_var.get())
        self.status_var.set(f"Starting in {delay}s — switch to your target window!")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.stop_event.clear()

        def run():
            time.sleep(delay)
            if not self.stop_event.is_set():
                type_text(
                    text=text,
                    wpm=self.wpm_var.get(),
                    typo_chance=self.typo_var.get(),
                    typo_correction_delay=self.delay_var.get(),
                    stop_event=self.stop_event,
                    status_var=self.status_var,
                )
            self.root.after(0, self._reset_buttons)

        threading.Thread(target=run, daemon=True).start()

    def stop_typing(self):
        self.stop_event.set()

    def _reset_buttons(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = AutoTyperApp(root)
    root.mainloop()
