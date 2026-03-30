"""
Auto Typer - Simulates keyboard input with optional typos
Requires: pip install pynput pystray Pillow
"""

import os
import json
import threading
import time
import random
import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog

from pynput.keyboard import Controller, Key, KeyCode, Listener
import pystray
from PIL import Image, ImageDraw

keyboard = Controller()

QWERTY_NEIGHBORS = {
    'q': 'wa', 'w': 'qase', 'e': 'wsdr', 'r': 'edft', 't': 'rfgy',
    'y': 'tghu', 'u': 'yhji', 'i': 'ujko', 'o': 'iklp', 'p': 'ol',
    'a': 'qwsz', 's': 'awedxz', 'd': 'serfcx', 'f': 'drtgvc',
    'g': 'ftyhbv', 'h': 'gyujnb', 'j': 'huikmn', 'k': 'jiolm',
    'l': 'kop', 'z': 'asx', 'x': 'zsdc', 'c': 'xdfv', 'v': 'cfgb',
    'b': 'vghn', 'n': 'bhjm', 'm': 'njk',
}

PROFILE_PRESETS = {
    "Hunt & Peck": {"recommended_wpm": 30, "variance_min": 1.3, "variance_max": 2.2},
    "Casual": {"recommended_wpm": 60, "variance_min": 0.8, "variance_max": 1.4},
    "Fast Typist": {"recommended_wpm": 120, "variance_min": 0.5, "variance_max": 1.0},
    "Programmer": {"recommended_wpm": 100, "variance_min": 0.6, "variance_max": 1.2},
}

DEFAULT_CONFIG = {
    "theme": "dark",
    "hotkey": "F6",
}


def get_typo_char(char):
    lower = char.lower()
    if lower in QWERTY_NEIGHBORS:
        neighbor = random.choice(QWERTY_NEIGHBORS[lower])
        return neighbor.upper() if char.isupper() else neighbor
    return char


def type_text(text, wpm, typo_chance, double_char_chance, missed_space_chance,
              wrong_cap_chance, transpose_chance, typo_correction_delay,
              startup_delay, profile_settings,
              stop_event, status_callback, progress_callback, finished_callback):
    if status_callback:
        status_callback("Typing...")

    chars_total = len(text)
    time.sleep(startup_delay)
    missed_space_pending = False
    i = 0

    while i < chars_total:
        if stop_event.is_set():
            if status_callback:
                status_callback("Stopped.")
            if finished_callback:
                finished_callback()
            return

        char = text[i]

        base_cps = (wpm * 5) / 60
        base_delay = 1.0 / base_cps
        variance = random.uniform(profile_settings['variance_min'], profile_settings['variance_max'])
        delay = base_delay * variance

        if char in '.!?,;:':
            delay *= random.uniform(2.0, 3.5)
        elif char == ' ':
            delay *= random.uniform(1.1, 1.6)

        if char == ' ' and random.random() < missed_space_chance:
            missed_space_pending = True
            i += 1
            if progress_callback:
                progress_callback(i / chars_total * 100)
            time.sleep(delay)
            continue

        if i + 1 < chars_total and char.isalpha() and text[i + 1].isalpha() and random.random() < transpose_chance:
            next_char = text[i + 1]
            keyboard.type(next_char + char)
            time.sleep(typo_correction_delay)
            keyboard.press(Key.backspace); keyboard.release(Key.backspace)
            keyboard.press(Key.backspace); keyboard.release(Key.backspace)
            keyboard.type(char + next_char)
            i += 2
            if progress_callback:
                progress_callback(i / chars_total * 100)
            time.sleep(delay)
            continue

        if char.isalpha() and random.random() < wrong_cap_chance:
            typo_char = char.swapcase()
            keyboard.type(typo_char)
            time.sleep(typo_correction_delay)
            keyboard.press(Key.backspace); keyboard.release(Key.backspace)
            keyboard.type(char)
            i += 1
            if progress_callback:
                progress_callback(i / chars_total * 100)
            time.sleep(delay)
            continue

        if char.isalpha() and random.random() < double_char_chance:
            keyboard.type(char * 2)
            time.sleep(typo_correction_delay)
            keyboard.press(Key.backspace); keyboard.release(Key.backspace)
            i += 1
            if progress_callback:
                progress_callback(i / chars_total * 100)
            time.sleep(delay)
            continue

        if char.isalpha() and random.random() < typo_chance:
            typo = get_typo_char(char)
            keyboard.type(typo)
            time.sleep(typo_correction_delay)
            keyboard.press(Key.backspace); keyboard.release(Key.backspace)

        if missed_space_pending:
            keyboard.type(' ')
            missed_space_pending = False

        keyboard.type(char)
        i += 1

        if progress_callback:
            progress_callback(i / chars_total * 100)

        time.sleep(delay)

    if status_callback:
        status_callback("Done!")
    if finished_callback:
        finished_callback()


class AutoTyperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Typer")
        self.root.resizable(False, False)
        self.stop_event = threading.Event()

        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.app_dir, "config.json")
        self.presets_dir = os.path.join(self.app_dir, "presets")
        os.makedirs(self.presets_dir, exist_ok=True)

        self.config = self.load_config()
        self.current_theme_name = self.config.get("theme", "dark")
        self.hotkey_string = self.config.get("hotkey", "F6")

        self.theme_definitions = {
            "dark": {
                "bg": "#12121f", "fg": "#e0e0ff", "panel_bg": "#12121f", "accent_bg": "#1a1a2e",
                "button_bg": "#2d2d6e", "button_fg": "#e0e0ff", "entry_bg": "#0d0d1a", "entry_fg": "#e8e8ff",
            },
            "light": {
                "bg": "#f5f5f5", "fg": "#202020", "panel_bg": "#dddddd", "accent_bg": "#eeeeee",
                "button_bg": "#4a90e2", "button_fg": "white", "entry_bg": "white", "entry_fg": "#202020",
            },
        }

        self.hotkey_key = self.parse_hotkey(self.hotkey_string)
        self.presets = {}

        self.build_ui()
        self.load_presets()
        self.apply_theme(self.current_theme_name)
        self.setup_hotkey_listener()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def parse_hotkey(self, key_str):
        key_str = key_str.strip().lower()
        key_map = {
            "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
            "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
            "f9": Key.f9, "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
        }
        if key_str in key_map:
            return key_map[key_str]
        if len(key_str) == 1:
            return KeyCode.from_char(key_str)
        return Key.f6

    def setup_hotkey_listener(self):
        def on_press(key):
            try:
                if key == self.hotkey_key:
                    self.root.after(0, self.toggle_typing)
            except Exception:
                pass

        self.listener = Listener(on_press=on_press)
        self.listener.daemon = True
        self.listener.start()

    def apply_theme(self, theme_name):
        theme = self.theme_definitions.get(theme_name, self.theme_definitions["dark"])
        self.current_theme_name = theme_name
        self.config["theme"] = theme_name
        self.save_config()

        self.root.configure(bg=theme["bg"])
        self.header.configure(bg=theme["accent_bg"])
        self.body.configure(bg=theme["bg"])

        for w in self.theme_widgets:
            if isinstance(w, tk.Label):
                w.configure(bg=theme["panel_bg"], fg=theme["fg"])
            elif isinstance(w, tk.Button):
                w.configure(bg=theme["button_bg"], fg=theme["button_fg"], activebackground=theme["accent_bg"])
            elif isinstance(w, (tk.Entry, scrolledtext.ScrolledText)):
                try:
                    w.configure(bg=theme["entry_bg"], fg=theme["entry_fg"], insertbackground=theme["entry_fg"])
                except Exception:
                    pass
            elif isinstance(w, ttk.Combobox):
                try:
                    w.configure(background=theme["entry_bg"], foreground=theme["entry_fg"])
                except Exception:
                    pass

    def build_ui(self):
        root = self.root
        PAD = 12

        self.header = tk.Frame(root, bg="#1a1a2e", pady=10)
        self.header.pack(fill="x")
        title = tk.Label(self.header, text="⌨  Auto Typer", font=("Courier New", 18, "bold"))
        title.pack()
        subtitle = tk.Label(self.header, text="paste text → hit Start or F6 → switch to target window", font=("Courier New", 9))
        subtitle.pack()

        self.theme_btn = tk.Button(self.header, text="Toggle Theme", command=self.toggle_theme)
        self.theme_btn.pack(side="right", padx=8, pady=4)

        self.body = tk.Frame(root, bg="#12121f", padx=PAD, pady=PAD)
        self.body.pack(fill="both", expand=True)

        tk.Label(self.body, text="Text to type:", font=("Courier New", 10, "bold")).pack(fill="x")
        self.text_box = scrolledtext.ScrolledText(self.body, width=58, height=8, font=("Courier New", 10), wrap="word")
        self.text_box.pack(fill="x", pady=(4, 12))

        self.progress = ttk.Progressbar(self.body, maximum=100, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 10))

        settings = tk.Frame(self.body)
        settings.pack(fill="x", pady=(0, 12))

        def label(parent, text, r, c):
            l = tk.Label(parent, text=text, font=("Courier New", 9))
            l.grid(row=r, column=c, sticky="w", padx=(0, 6), pady=3)
            return l

        def slider(parent, from_, to, default, r, c, fmt=None):
            var = tk.DoubleVar(value=default)
            s = ttk.Scale(parent, from_=from_, to=to, variable=var, orient="horizontal", length=160)
            s.grid(row=r, column=c+1, sticky="ew", padx=(0, 16))
            display = tk.Label(parent, font=("Courier New", 9), width=6)
            display.grid(row=r, column=c+2, sticky="w")

            def update(*_):
                v = var.get()
                display.config(text=fmt(v) if fmt else f"{v:.1f}")
            var.trace_add("write", update)
            update()
            return var

        label(settings, "Typing speed (WPM):", 0, 0)
        self.wpm_var = slider(settings, 20, 200, 60, 0, 0, fmt=lambda v: f"{int(v)} wpm")

        label(settings, "Typo chance:", 1, 0)
        self.typo_var = slider(settings, 0, 0.3, 0.05, 1, 0, fmt=lambda v: f"{v*100:.0f}%")

        label(settings, "Double-char typo:", 2, 0)
        self.double_var = slider(settings, 0, 0.2, 0.03, 2, 0, fmt=lambda v: f"{v*100:.0f}%")

        label(settings, "Missed-space typo:", 3, 0)
        self.missed_space_var = slider(settings, 0, 0.2, 0.04, 3, 0, fmt=lambda v: f"{v*100:.0f}%")

        label(settings, "Caps typo:", 4, 0)
        self.wrong_cap_var = slider(settings, 0, 0.2, 0.04, 4, 0, fmt=lambda v: f"{v*100:.0f}%")

        label(settings, "Transpose typo:", 5, 0)
        self.transpose_var = slider(settings, 0, 0.2, 0.04, 5, 0, fmt=lambda v: f"{v*100:.0f}%")

        label(settings, "Correction delay (s):", 6, 0)
        self.delay_var = slider(settings, 0.05, 1.0, 0.2, 6, 0, fmt=lambda v: f"{v:.2f}s")

        label(settings, "Startup delay (s):", 7, 0)
        self.startup_var = slider(settings, 1, 10, 3, 7, 0, fmt=lambda v: f"{int(v)}s")

        util_frame = tk.Frame(self.body)
        util_frame.pack(fill="x", pady=(0, 10))

        tk.Label(util_frame, text="Profile:", font=("Courier New", 9)).pack(side="left")
        self.profile_choice = ttk.Combobox(util_frame, values=list(PROFILE_PRESETS.keys()), state="readonly", width=14)
        self.profile_choice.set("Casual")
        self.profile_choice.pack(side="left", padx=6)
        self.profile_choice.bind("<<ComboboxSelected>>", self.on_profile_selected)

        tk.Label(util_frame, text="Hotkey:", font=("Courier New", 9)).pack(side="left", padx=(10, 0))
        self.hotkey_entry = tk.Entry(util_frame, width=6)
        self.hotkey_entry.insert(0, self.hotkey_string)
        self.hotkey_entry.pack(side="left", padx=(2, 2))
        tk.Button(util_frame, text="Set", command=self.set_hotkey).pack(side="left")

        btn_frame = tk.Frame(self.body)
        btn_frame.pack(fill="x")

        self.start_btn = tk.Button(btn_frame, text="▶  Start", command=self.start_typing)
        self.stop_btn = tk.Button(btn_frame, text="■  Stop", state="disabled", command=self.stop_typing)
        self.clear_btn = tk.Button(btn_frame, text="✕  Clear", command=lambda: self.text_box.delete("1.0", "end"))
        self.clipboard_btn = tk.Button(btn_frame, text="📋 Paste from Clipboard", command=self.paste_clipboard)

        self.start_btn.pack(side="left", padx=(0, 8))
        self.stop_btn.pack(side="left", padx=(0, 8))
        self.clipboard_btn.pack(side="left", padx=(0, 8))
        self.clear_btn.pack(side="right")

        preset_frame = tk.Frame(self.body)
        preset_frame.pack(fill="x", pady=(10, 0))

        tk.Label(preset_frame, text="Preset:").pack(side="left")
        self.preset_choice = ttk.Combobox(preset_frame, state="readonly", width=20)
        self.preset_choice.pack(side="left", padx=(5, 5))
        self.preset_choice.bind("<<ComboboxSelected>>", self.load_selected_preset)

        tk.Button(preset_frame, text="Save", command=self.save_preset).pack(side="left", padx=(0, 5))
        tk.Button(preset_frame, text="Delete", command=self.delete_preset).pack(side="left")

        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(self.body, textvariable=self.status_var, font=("Courier New", 9)).pack(fill="x", pady=(10, 0))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Horizontal.TScale", troughcolor="#2a2a4a", background="#5050b0", sliderthickness=14)

        self.theme_widgets = [title, subtitle, self.theme_btn, self.text_box, self.progress,
                              self.start_btn, self.stop_btn, self.clear_btn, self.clipboard_btn,
                              self.profile_choice, self.hotkey_entry, self.preset_choice]

        self.on_profile_selected()

    def toggle_theme(self):
        new_theme = "light" if self.current_theme_name == "dark" else "dark"
        self.apply_theme(new_theme)

    def on_profile_selected(self, event=None):
        profile_name = self.profile_choice.get() or "Casual"
        profile = PROFILE_PRESETS.get(profile_name, PROFILE_PRESETS["Casual"])
        self.wpm_var.set(profile["recommended_wpm"])

    def set_hotkey(self):
        value = self.hotkey_entry.get().strip()
        if not value:
            return
        self.hotkey_string = value
        self.hotkey_key = self.parse_hotkey(value)
        self.config["hotkey"] = value
        self.save_config()
        self.status_var.set(f"Hotkey set to {value}.")

    def paste_clipboard(self):
        try:
            text = self.root.clipboard_get()
            self.text_box.delete("1.0", "end")
            self.text_box.insert("1.0", text)
            self.status_var.set("Pasted text from clipboard.")
        except Exception:
            self.status_var.set("Clipboard unavailable.")

    def _reset_buttons(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.progress['value'] = 0

    def start_typing(self):
        text = self.text_box.get("1.0", "end-1c")
        if not text.strip():
            self.status_var.set("No text entered.")
            return

        self.status_var.set("Starting...")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.stop_event.clear()

        profile_name = self.profile_choice.get() or "Casual"
        profile_settings = PROFILE_PRESETS.get(profile_name, PROFILE_PRESETS["Casual"])

        def status_callback(value):
            self.root.after(0, lambda: self.status_var.set(value))

        def progress_callback(value):
            self.root.after(0, lambda: self.progress.configure(value=value))

        def finished_callback():
            self.root.after(0, self._reset_buttons)

        def run():
            type_text(
                text=text,
                wpm=self.wpm_var.get(),
                typo_chance=self.typo_var.get(),
                double_char_chance=self.double_var.get(),
                missed_space_chance=self.missed_space_var.get(),
                wrong_cap_chance=self.wrong_cap_var.get(),
                transpose_chance=self.transpose_var.get(),
                typo_correction_delay=self.delay_var.get(),
                startup_delay=self.startup_var.get(),
                profile_settings=profile_settings,
                stop_event=self.stop_event,
                status_callback=status_callback,
                progress_callback=progress_callback,
                finished_callback=finished_callback,
            )

        threading.Thread(target=run, daemon=True).start()

    def stop_typing(self):
        self.stop_event.set()
        self.status_var.set("Stopping...")

    def toggle_typing(self):
        if self.start_btn['state'] == "normal":
            self.start_typing()
        else:
            self.stop_typing()

    def load_presets(self):
        self.presets = {}
        names = []
        for filename in os.listdir(self.presets_dir):
            if filename.endswith('.json'):
                path = os.path.join(self.presets_dir, filename)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        name = data.get('name', os.path.splitext(filename)[0])
                        self.presets[name] = data
                        names.append(name)
                except Exception:
                    pass
        self.preset_choice['values'] = names

    def save_preset(self):
        name = simpledialog.askstring("Save Preset", "Preset name:")
        if not name:
            return
        preset = {
            'name': name,
            'text': self.text_box.get('1.0', 'end-1c'),
            'wpm': self.wpm_var.get(),
            'typo_chance': self.typo_var.get(),
            'double_char_chance': self.double_var.get(),
            'missed_space_chance': self.missed_space_var.get(),
            'wrong_cap_chance': self.wrong_cap_var.get(),
            'transpose_chance': self.transpose_var.get(),
            'delay': self.delay_var.get(),
            'startup': self.startup_var.get(),
            'profile': self.profile_choice.get(),
            'hotkey': self.hotkey_string,
        }
        path = os.path.join(self.presets_dir, f"{name}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(preset, f, indent=2)
        self.status_var.set(f"Saved preset '{name}'.")
        self.load_presets()
        self.preset_choice.set(name)

    def load_selected_preset(self, event=None):
        name = self.preset_choice.get()
        preset = self.presets.get(name)
        if not preset:
            return
        self.text_box.delete('1.0', 'end')
        self.text_box.insert('1.0', preset.get('text', ''))
        self.wpm_var.set(preset.get('wpm', 60))
        self.typo_var.set(preset.get('typo_chance', 0.05))
        self.double_var.set(preset.get('double_char_chance', 0.03))
        self.missed_space_var.set(preset.get('missed_space_chance', 0.04))
        self.wrong_cap_var.set(preset.get('wrong_cap_chance', 0.04))
        self.transpose_var.set(preset.get('transpose_chance', 0.04))
        self.delay_var.set(preset.get('delay', 0.2))
        self.startup_var.set(preset.get('startup', 3))
        self.profile_choice.set(preset.get('profile', 'Casual'))
        self.hotkey_string = preset.get('hotkey', self.hotkey_string)
        self.hotkey_entry.delete(0, 'end')
        self.hotkey_entry.insert(0, self.hotkey_string)
        self.hotkey_key = self.parse_hotkey(self.hotkey_string)
        self.config['hotkey'] = self.hotkey_string
        self.save_config()
        self.status_var.set(f"Loaded preset '{name}'.")

    def delete_preset(self):
        name = self.preset_choice.get()
        if not name:
            return
        path = os.path.join(self.presets_dir, f"{name}.json")
        if os.path.exists(path):
            os.remove(path)
            self.status_var.set(f"Deleted preset '{name}'.")
            self.load_presets()

    def on_close(self):
        self.minimize_to_tray()

    def minimize_to_tray(self):
        self.root.withdraw()
        self.status_var.set("Minimized to tray.")
        self.create_tray_icon()

    def create_tray_icon(self):
        def show_window(icon, item):
            self.root.after(0, self.restore_window)

        def start_typing(icon, item):
            self.root.after(0, self.start_typing)

        def stop_typing(icon, item):
            self.root.after(0, self.stop_typing)

        def quit_app(icon, item):
            try:
                icon.stop()
            except Exception:
                pass
            self.root.after(0, self.root.destroy)

        icon_image = Image.new('RGB', (64, 64), color=(28, 44, 95))
        draw = ImageDraw.Draw(icon_image)
        draw.text((12, 20), 'AT', fill='white')

        menu = pystray.Menu(
            pystray.MenuItem('Show', show_window),
            pystray.MenuItem('Start Typing', start_typing),
            pystray.MenuItem('Stop Typing', stop_typing),
            pystray.MenuItem('Quit', quit_app),
        )

        self.tray_icon = pystray.Icon('AutoTyper', icon_image, 'Auto Typer', menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def restore_window(self):
        self.root.deiconify()
        self.root.lift()


if __name__ == '__main__':
    root = tk.Tk()
    app = AutoTyperApp(root)
    root.mainloop()
