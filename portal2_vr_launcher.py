import os
import sys
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext, filedialog
import webbrowser
import requests
import zipfile
import io
import json

LAUNCHER_VERSION = "2.0"

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MOD_DIR = os.path.join(BASE_DIR, "modfiles")
CONFIG_FILE = os.path.join(BASE_DIR, "settings.json")
ICON_PATH = os.path.join(BASE_DIR, "icon.ico")
LAUNCH_OPTIONS = "-insecure -window -novid +mat_motion_blur_percent_of_screen_max 0 +mat_queue_mode 0 +mat_vsync 0 +mat_antialias 0 +mat_grain_scale_override 0 -width 1280 -height 720"

class SettingsManager:
    def __init__(self):
        self.show_console = True
        self.dark_mode = True
        self.portal2_path = ""
        self.saved_mod_version = ""
        self.installed_files = []
        self.verifymodfiles = []
        self.load()

    def load(self):
        if not os.path.exists(CONFIG_FILE):
            self.save()
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.show_console = data.get("show_console", True)
            self.dark_mode = data.get("dark_mode", True)
            self.portal2_path = data.get("portal2_path", "")
            self.saved_mod_version = data.get("saved_mod_version", "")
            self.installed_files = data.get("installed_files", [])
            self.verifymodfiles = data.get("verifymodfiles", [])
        except Exception:
            pass

    def save(self):
        try:
            data = {
                "show_console": self.show_console,
                "dark_mode": self.dark_mode,
                "portal2_path": self.portal2_path,
                "saved_mod_version": self.saved_mod_version,
                "installed_files": self.installed_files,
                "verifymodfiles": self.verifymodfiles
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

class ModManager:
    def __init__(self, settings, gui_log, gui_log_success, gui_update_status):
        self.settings = settings
        self.gui_log = gui_log
        self.gui_log_success = gui_log_success
        self.gui_update_status = gui_update_status

    def scan_modfiles(self):
        out = []
        if not os.path.isdir(MOD_DIR):
            return out
        for r, dirs, files in os.walk(MOD_DIR):
            for f in files:
                rel = os.path.relpath(os.path.join(r,f), MOD_DIR).replace("\\","/")
                out.append(rel)
        self.settings.verifymodfiles = out
        self.settings.save()
        return out

    def detect_installed_modfiles(self):
        installed = []
        if self.settings.portal2_path and self.settings.verifymodfiles:
            for f in self.settings.verifymodfiles:
                if os.path.isfile(os.path.join(self.settings.portal2_path, f)):
                    installed.append(f)
        self.settings.installed_files = installed
        self.settings.save()
        return installed

    def is_mod_installed(self):
        if not self.settings.portal2_path:
            return False
        check_files = self.settings.installed_files if self.settings.installed_files else self.settings.verifymodfiles
        return bool(check_files) and all(os.path.isfile(os.path.join(self.settings.portal2_path, f)) for f in check_files)

    def install_mod(self):
        if not self.settings.portal2_path:
            self.gui_log("Install failed: Portal 2 folder not set.")
            return
        if not self.settings.verifymodfiles:
            self.gui_log("Install failed: No mod files found. Run Update Mod Files first.")
            return
        try:
            installed = []
            for f in self.settings.verifymodfiles:
                src = os.path.join(MOD_DIR, f)
                dst = os.path.join(self.settings.portal2_path, f)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                installed.append(f)
                self.gui_log(f"Copied {f}")
            self.settings.installed_files = installed
            self.settings.save()
            self.gui_log_success("Install successful.")
            self.gui_update_status()
        except Exception as e:
            self.gui_log(f"Install failed: {e}")

    def uninstall_mod(self):
        if not self.settings.portal2_path:
            self.gui_log("Uninstall failed: Portal 2 folder not set.")
            return
        try:
            for f in self.settings.installed_files:
                full = os.path.join(self.settings.portal2_path, f)
                if os.path.isfile(full):
                    os.remove(full)
                    self.gui_log(f"Removed {f}")
            self.settings.installed_files = []
            self.settings.save()
            self.gui_log_success("Uninstall successful.")
            self.gui_update_status()
        except Exception as e:
            self.gui_log(f"Uninstall failed: {e}")

    def launch_portal2_vr(self):
        if not self.is_mod_installed():
            self.gui_log("Launch failed: Mod not installed.")
            return
        try:
            subprocess.Popen([os.path.join(self.settings.portal2_path, "portal2.exe")] + LAUNCH_OPTIONS.split())
            self.gui_log("Launching Portal 2 VR")
        except Exception as e:
            self.gui_log(f"Launch error: {e}")

    def download_latest_mod_worker(self):
        self.gui_log("Fetching releases from GitHub...")
        url = "https://api.github.com/repos/Gistix/portal2vr/releases"
        try:
            r = requests.get(url, timeout=15)
            releases = r.json()
            if not releases:
                self.gui_log("No releases found on GitHub.")
                return
            latest = releases[0]
            tag = latest.get("tag_name","unknown")
            assets = latest.get("assets", [])
            zip_asset = next((a for a in assets if a.get("name","").lower().endswith(".zip")), None)
            if not zip_asset:
                self.gui_log("No ZIP asset found in latest release.")
                return
            name = zip_asset.get("name","mod.zip")
            dl_url = zip_asset.get("browser_download_url")
            self.gui_log(f"Downloading {name} ...")
            resp = requests.get(dl_url, stream=True, timeout=30)
            total = int(resp.headers.get("content-length") or 0)
            buf = io.BytesIO()
            read = 0
            for chunk in resp.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                buf.write(chunk)
                read += len(chunk)
                pct = int(read / total * 100) if total else 0
                self.gui_log(f"Download progress: {pct}%")
            if os.path.isdir(MOD_DIR):
                shutil.rmtree(MOD_DIR)
            os.makedirs(MOD_DIR, exist_ok=True)
            self.gui_log("Extracting archive...")
            with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as z:
                members = z.namelist()
                for i, member in enumerate(members, start=1):
                    z.extract(member, MOD_DIR)
                    pct = int(i / len(members) * 100)
                    self.gui_log(f"Extract progress: {pct}%")
            self.settings.saved_mod_version = tag
            self.scan_modfiles()
            self.detect_installed_modfiles()
            self.settings.save()
            self.gui_log_success(f"Downloaded and extracted mod {tag}")
            self.gui_update_status()
        except Exception as e:
            self.gui_log(f"Mod update failed: {e}")

    def start_download_latest_mod(self):
        t = threading.Thread(target=self.download_latest_mod_worker, daemon=True)
        t.start()


class VRLauncherApp:
    def __init__(self):
        self.settings = SettingsManager()
        self.root = tk.Tk()
        self.root.title("Portal 2 VR Launcher")
        try:
            self.root.iconbitmap(ICON_PATH)
        except Exception:
            pass
        self.mod_manager = ModManager(self.settings, self.gui_log, self.gui_log_success, self.update_status)
        self.setup_ui()
        self.apply_theme_all(self.root)
        if not self.settings.verifymodfiles:
            self.mod_manager.scan_modfiles()
        if self.settings.portal2_path:
            self.mod_manager.detect_installed_modfiles()
        self.update_status()

    def gui_log(self, msg):
        self.root.after(0, lambda: self._append_console(msg))

    def gui_log_success(self, msg):
        self.root.after(0, lambda: (self._append_console("-"*24), self._append_console(msg), self._append_console("-"*24)))

    def _append_console(self, text):
        self.console_text.config(state=tk.NORMAL)
        self.console_text.insert(tk.END, text + "\n")
        self.console_text.config(state=tk.DISABLED)
        self.console_text.see(tk.END)

    def setup_ui(self):
        self.root.geometry("315x450" if self.settings.show_console else "315x180")
        tk.Label(self.root, text="Portal 2 VR Launcher", font=("Arial", 14)).pack()
        self.status_label = tk.Label(self.root, text="Mod Status: Unknown")
        self.status_label.pack()
        frame = tk.Frame(self.root)
        frame.pack(pady=20)
        self.launch_button = tk.Button(frame, text="Launch Portal 2 VR", height=2, command=self.mod_manager.launch_portal2_vr, state=tk.DISABLED)
        self.install_button = tk.Button(frame, text="Install", height=2, command=self.mod_manager.install_mod)
        self.settings_button = tk.Button(frame, text="Settings", width=10, height=4, command=self.open_settings)
        self.launch_button.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.install_button.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self.settings_button.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=2, pady=2)
        self.console_text = scrolledtext.ScrolledText(self.root, wrap=tk.WORD)
        self.console_text.config(state=tk.DISABLED)
        if self.settings.show_console:
            self.console_text.pack(pady=5)

    def open_settings(self):
        self.settings_win = tk.Toplevel(self.root)
        self.settings_win.title("Settings")
        self.settings_win.geometry("450x450")
        try:
            self.settings_win.iconbitmap(ICON_PATH)
        except Exception:
            pass
        tk.Label(self.settings_win, text="Settings", font=("Arial", 16)).pack(pady=(5,2))
        tk.Label(self.settings_win, text="Guide:\n1. Choose your Portal 2 installation folder.\n2. Install or uninstall the VR mod.\n3. Launch the game through the main menu.", justify="left").pack(pady=(0,5))
        grid = tk.Frame(self.settings_win)
        grid.pack(pady=5)
        self.console_btn = tk.Button(grid, text=("Hide Console" if self.settings.show_console else "Show Console"), width=20, height=2, command=self.toggle_console)
        self.console_btn.grid(row=0, column=0, padx=2, pady=2)
        self.dark_btn = tk.Button(grid, text=("Disable Dark Mode" if self.settings.dark_mode else "Enable Dark Mode"), width=20, height=2, command=self.toggle_dark_mode)
        self.dark_btn.grid(row=0, column=1, padx=2, pady=2)
        tk.Button(grid, text="Select Portal 2 Folder", width=20, height=2, command=self.select_folder).grid(row=1, column=0, padx=2, pady=2)
        tk.Button(grid, text="Update Mod Files", width=20, height=2, command=self.mod_manager.start_download_latest_mod).grid(row=1, column=1, padx=2, pady=2)
        tk.Label(self.settings_win, text="Portal 2 folder:").pack(pady=(10,0))
        self.folder_label = tk.Label(self.settings_win, text=(self.settings.portal2_path if self.settings.portal2_path else "Portal 2 folder not set"))
        self.folder_label.pack(pady=(0,10))
        tk.Label(self.settings_win, text=f"Launcher by EPOS - v{LAUNCHER_VERSION}").pack(pady=(0,2))
        self.mod_version_label = tk.Label(self.settings_win, text=f"VR Mod by Gistix - {self.settings.saved_mod_version if self.settings.saved_mod_version else 'unknown'}")
        self.mod_version_label.pack(pady=(0,10))
        gh = tk.Frame(self.settings_win)
        gh.pack(pady=5)
        tk.Button(gh, text="Launcher on GitHub", width=20, height=2, command=lambda: webbrowser.open("https://github.com/EPOS05/portal2vr_launcher")).grid(row=0, column=0, padx=2)
        tk.Button(gh, text="Mod on GitHub", width=20, height=2, command=lambda: webbrowser.open("https://github.com/Gistix/portal2vr")).grid(row=0, column=1, padx=2)
        self.apply_theme_all(self.settings_win)
        self.refresh_setting_buttons()

    def toggle_dark_mode(self):
        self.settings.dark_mode = not self.settings.dark_mode
        self.settings.save()
        self.apply_theme_all(self.root)
        if hasattr(self, 'settings_win') and self.settings_win.winfo_exists():
            self.apply_theme_all(self.settings_win)
        self.refresh_setting_buttons()

    def toggle_console(self):
        self.settings.show_console = not self.settings.show_console
        self.settings.save()
        if self.settings.show_console:
            self.console_text.pack(pady=5)
            self.root.geometry("315x450")
        else:
            self.console_text.pack_forget()
            self.root.geometry("315x180")
        self.refresh_setting_buttons()

    def refresh_setting_buttons(self):
        try:
            self.console_btn.config(text="Hide Console" if self.settings.show_console else "Show Console")
            self.dark_btn.config(text="Disable Dark Mode" if self.settings.dark_mode else "Enable Dark Mode")
        except Exception:
            pass

    def apply_theme_all(self, widget):
        bg = "#333" if self.settings.dark_mode else "SystemButtonFace"
        fg = "white" if self.settings.dark_mode else "black"
        btn_bg = "#444" if self.settings.dark_mode else "SystemButtonFace"
        btn_act = "#555" if self.settings.dark_mode else "SystemButtonFace"
        txt_bg = "#222" if self.settings.dark_mode else "white"
        txt_fg = "white" if self.settings.dark_mode else "black"
        try:
            if isinstance(widget, (tk.Tk, tk.Toplevel, tk.Frame, tk.LabelFrame)):
                widget.configure(bg=bg)
            elif isinstance(widget, tk.Label):
                widget.configure(bg=bg, fg=fg)
            elif isinstance(widget, tk.Button):
                widget.configure(bg=btn_bg, fg=fg, activebackground=btn_act)
            elif isinstance(widget, (tk.Text, scrolledtext.ScrolledText)):
                widget.configure(bg=txt_bg, fg=txt_fg, insertbackground=fg)
        except Exception:
            pass
        for child in widget.winfo_children():
            self.apply_theme_all(child)

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Portal 2 Folder")
        if folder:
            self.settings.portal2_path = folder
            self.settings.save()
            self.mod_manager.detect_installed_modfiles()
            self.update_status()
            self.refresh_folder_label()

    def refresh_folder_label(self):
        try:
            self.folder_label.config(text=(self.settings.portal2_path if self.settings.portal2_path else "Portal 2 folder not set"))
        except Exception:
            pass

    def refresh_mod_label(self):
        try:
            self.mod_version_label.config(text=f"VR Mod by Gistix - {self.settings.saved_mod_version if self.settings.saved_mod_version else 'unknown'}")
        except Exception:
            pass

    def update_status(self):
        if self.mod_manager.is_mod_installed():
            self.status_label.config(text="Mod Status: Installed")
            self.install_button.config(text="Uninstall", command=self.mod_manager.uninstall_mod)
            self.launch_button.config(state=tk.NORMAL)
        else:
            self.status_label.config(text="Mod Status: Uninstalled")
            self.install_button.config(text="Install", command=self.mod_manager.install_mod)
            self.launch_button.config(state=tk.DISABLED)
        self.refresh_mod_label()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = VRLauncherApp()
    app.run()
