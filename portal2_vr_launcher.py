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
import tkinter.font as tkfont

LAUNCHER_VERSION = "3.0"
DEFAULT_LAUNCH_OPTIONS = "-insecure -window -novid +mat_motion_blur_percent_of_screen_max 0 +mat_queue_mode 0 +mat_vsync 0 +mat_antialias 0 +mat_grain_scale_override 0 -width 1280 -height 720"
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
MOD_DIR = os.path.join(BASE_DIR, "modfiles")
CONFIG_FILE = os.path.join(BASE_DIR, "settings.json")
ICON_PATH = os.path.join(BASE_DIR, "icon.ico")


class UIUtils:
    @staticmethod
    def title_label(parent, text):
        lbl = tk.Label(parent, text=text)
        f = tkfont.Font(lbl, lbl.cget("font"))
        f.configure(size=15, weight="bold")
        lbl.configure(font=f)
        return lbl

    @staticmethod
    def clickable_label(parent, text, url):
        lbl = tk.Label(parent, text=text, cursor="hand2")
        f = tkfont.Font(lbl, lbl.cget("font"))
        f.configure(underline=True)
        lbl.configure(font=f)
        lbl.bind("<Button-1>", lambda e: webbrowser.open(url))
        return lbl

    @staticmethod
    def apply_theme(widget, dark_mode):
        bg = "#333" if dark_mode else "SystemButtonFace"
        fg = "white" if dark_mode else "black"
        btn_bg = "#444" if dark_mode else "SystemButtonFace"
        btn_act = "#555" if dark_mode else "SystemButtonFace"
        txt_bg = "#222" if dark_mode else "white"
        txt_fg = "white" if dark_mode else "black"

        try:
            if isinstance(widget, (tk.Tk, tk.Toplevel, tk.Frame, tk.LabelFrame)):
                widget.configure(bg=bg)
            elif isinstance(widget, tk.Label):
                widget.configure(bg=bg, fg=fg)
            elif isinstance(widget, tk.Button):
                widget.configure(bg=btn_bg, fg=fg, activebackground=btn_act)
            elif isinstance(widget, (tk.Text, scrolledtext.ScrolledText, tk.Entry)):
                widget.configure(bg=txt_bg, fg=txt_fg, insertbackground=fg)
        except Exception:
            pass

        for child in widget.winfo_children():
            UIUtils.apply_theme(child, dark_mode)


class SettingsManager:
    def __init__(self):
        self.show_console = True
        self.dark_mode = True
        self.portal2_path = ""
        self.saved_mod_version = ""
        self.installed_files = []
        self.installed_folders_overwritten = {}
        self.verifymodfiles = []
        self.launch_options = DEFAULT_LAUNCH_OPTIONS
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
            self.installed_folders_overwritten = data.get("installed_folders_overwritten", {})
            self.verifymodfiles = data.get("verifymodfiles", [])
            self.launch_options = data.get("launch_options", DEFAULT_LAUNCH_OPTIONS)
        except Exception:
            self.save()

    def save(self):
        data = {
            "show_console": self.show_console,
            "dark_mode": self.dark_mode,
            "portal2_path": self.portal2_path,
            "saved_mod_version": self.saved_mod_version,
            "installed_files": self.installed_files,
            "installed_folders_overwritten": self.installed_folders_overwritten,
            "verifymodfiles": self.verifymodfiles,
            "launch_options": self.launch_options,
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass


class ModManager:
    def __init__(self, settings, log, log_success, update_status):
        self.settings = settings
        self.log = log
        self.log_success = log_success
        self.update_status = update_status

    def _game_path(self, rel):
        return os.path.join(self.settings.portal2_path, rel) if self.settings.portal2_path else ""

    def scan_modfiles(self):
        files = []
        if not os.path.isdir(MOD_DIR):
            return files
        for root, _, filenames in os.walk(MOD_DIR):
            for fn in filenames:
                rel = os.path.relpath(os.path.join(root, fn), MOD_DIR).replace("\\", "/")
                files.append(rel)
        self.settings.verifymodfiles = files
        self.settings.save()
        return files

    def detect_installed_modfiles(self):
        installed = []
        if self.settings.portal2_path and self.settings.verifymodfiles:
            for rel in self.settings.verifymodfiles:
                if os.path.isfile(self._game_path(rel)):
                    installed.append(rel)
        self.settings.installed_files = installed
        self.settings.save()
        return installed

    def is_mod_installed(self):
        if not self.settings.portal2_path:
            return False
        check = self.settings.installed_files or self.settings.verifymodfiles
        return bool(check) and all(os.path.isfile(self._game_path(f)) for f in check)

    def install_mod(self):
        if not self.settings.portal2_path:
            self.log("Install failed: Portal 2 folder not set.")
            return
        if not self.settings.verifymodfiles:
            self.log("Install failed: No mod files found. Run Update Mod Files first.")
            return
        try:
            installed = []
            folder_state = {}
            for rel in self.settings.verifymodfiles:
                src = os.path.join(MOD_DIR, rel)
                dst = self._game_path(rel)
                folder = os.path.dirname(dst)
                if folder not in folder_state:
                    folder_state[folder] = os.path.isdir(folder)
                os.makedirs(folder, exist_ok=True)
                shutil.copy2(src, dst)
                installed.append(rel)
                self.log("Copied " + rel)
            self.settings.installed_files = installed
            self.settings.installed_folders_overwritten = folder_state
            self.settings.save()
            self.log_success("Install successful.")
            self.update_status()
        except Exception as e:
            self.log("Install failed: " + str(e))

    def uninstall_mod(self):
        if not self.settings.portal2_path:
            self.log("Uninstall failed: Portal 2 folder not set.")
            return
        try:
            for rel in list(self.settings.installed_files):
                full = self._game_path(rel)
                if os.path.isfile(full):
                    os.remove(full)
                    self.log("Removed " + rel)

            folders = {os.path.dirname(self._game_path(rel)) for rel in self.settings.installed_files}
            for folder in sorted(folders, key=lambda p: -p.count(os.sep)):
                existed_before = self.settings.installed_folders_overwritten.get(folder, False)
                if existed_before:
                    continue
                try:
                    cur = folder
                    while cur and cur.startswith(self.settings.portal2_path) and os.path.isdir(cur) and not os.listdir(cur):
                        os.rmdir(cur)
                        self.log("Removed folder " + cur)
                        cur = os.path.dirname(cur)
                except Exception:
                    pass

            self.settings.installed_files = []
            self.settings.installed_folders_overwritten = {}
            self.settings.save()
            self.log_success("Uninstall successful.")
            self.update_status()
        except Exception as e:
            self.log("Uninstall failed: " + str(e))

    def launch_portal2_vr(self):
        if not self.is_mod_installed():
            self.log("Launch failed: Mod not installed.")
            return
        try:
            exe = os.path.join(self.settings.portal2_path, "portal2.exe")
            args = self.settings.launch_options.split() if self.settings.launch_options.strip() else []
            subprocess.Popen([exe] + args)
            self.log("Launching Portal 2 VR")
        except Exception as e:
            self.log("Launch error: " + str(e))

    def start_download_latest_mod(self):
        threading.Thread(target=self.download_latest_mod_worker, daemon=True).start()

    def download_latest_mod_worker(self):
        self.log("Fetching releases from GitHub...")
        url = "https://api.github.com/repos/Gistix/portal2vr/releases"
        try:
            r = requests.get(url, timeout=15)
            releases = r.json()
            if not releases:
                self.log("No releases found on GitHub.")
                return
            latest = releases[0]
            tag = latest.get("tag_name", "unknown")
            assets = latest.get("assets", [])
            zip_asset = next((a for a in assets if a.get("name", "").lower().endswith(".zip")), None)
            if not zip_asset:
                self.log("No ZIP asset found in latest release.")
                return
            name = zip_asset.get("name", "mod.zip")
            dl_url = zip_asset.get("browser_download_url")
            self.log("Downloading " + name + " ...")
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
                self.log(f"Download progress: {pct}%")
            if os.path.isdir(MOD_DIR):
                shutil.rmtree(MOD_DIR)
            os.makedirs(MOD_DIR, exist_ok=True)
            self.log("Extracting archive...")
            with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as z:
                members = z.namelist()
                for i, member in enumerate(members, start=1):
                    z.extract(member, MOD_DIR)
                    pct = int(i / len(members) * 100)
                    self.log(f"Extract progress: {pct}%")
            self.settings.saved_mod_version = tag
            self.scan_modfiles()
            self.detect_installed_modfiles()
            self.settings.save()
            self.log_success("Downloaded and extracted mod " + tag)
            self.update_status()
        except Exception as e:
            self.log("Mod update failed: " + str(e))


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
        UIUtils.apply_theme(self.root, self.settings.dark_mode)
        if not self.settings.verifymodfiles:
            self.mod_manager.scan_modfiles()
        if self.settings.portal2_path:
            self.mod_manager.detect_installed_modfiles()
        self.update_status()

    def gui_log(self, msg):
        self.root.after(0, lambda: self._append_console(msg))

    def gui_log_success(self, msg):
        self.root.after(0, lambda: (self._append_console("-" * 24), self._append_console(msg), self._append_console("-" * 24)))

    def _append_console(self, text):
        self.console_text.config(state=tk.NORMAL)
        self.console_text.insert(tk.END, text + "\n")
        self.console_text.config(state=tk.DISABLED)
        self.console_text.see(tk.END)

    def setup_ui(self):
        self.root.geometry("380x360" if self.settings.show_console else "380x190")
        UIUtils.title_label(self.root, "Portal 2 VR Launcher").pack()
        self.status_label = tk.Label(self.root, text="Mod Status: Unknown")
        self.status_label.pack()
        frame = tk.Frame(self.root)
        frame.pack(pady=20)
        self.launch_button = tk.Button(frame, text="Launch Portal 2 VR", width=20, height=4, command=self.mod_manager.launch_portal2_vr, state=tk.DISABLED)
        self.install_button = tk.Button(frame, text="Install", width=20, height=2, command=self.mod_manager.install_mod)
        self.settings_button = tk.Button(frame, text="Settings", width=20, height=2, command=self.open_settings)
        self.launch_button.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=2, pady=2)
        self.install_button.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        self.settings_button.grid(row=1, column=1, sticky="nsew", padx=2, pady=2)
        self.console_text = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=10, state=tk.DISABLED)
        if self.settings.show_console:
            self.console_text.pack(pady=5)

    def open_settings(self):
        self.settings_win = tk.Toplevel(self.root)
        self.settings_win.title("Settings")
        self.settings_win.geometry("380x360")
        try:
            self.settings_win.iconbitmap(ICON_PATH)
        except Exception:
            pass
        UIUtils.title_label(self.settings_win, "Settings").pack(pady=(5, 2))
        grid = tk.Frame(self.settings_win)
        grid.pack(pady=5)
        self.console_btn = tk.Button(grid, text=("Hide Console" if self.settings.show_console else "Show Console"), width=20, height=2, command=self.toggle_console)
        self.console_btn.grid(row=0, column=0, padx=2, pady=2)
        self.dark_btn = tk.Button(grid, text=("Disable Dark Mode" if self.settings.dark_mode else "Enable Dark Mode"), width=20, height=2, command=self.toggle_dark_mode)
        self.dark_btn.grid(row=0, column=1, padx=2, pady=2)
        tk.Button(grid, text="Select Game Folder", width=20, height=2, command=self.select_folder).grid(row=1, column=0, padx=2, pady=2)
        tk.Button(grid, text="Update Mod Files", width=20, height=2, command=self.mod_manager.start_download_latest_mod).grid(row=1, column=1, padx=2, pady=2)
        self.folder_label = tk.Label(self.settings_win, text=(self.settings.portal2_path if self.settings.portal2_path else "Portal 2 folder not set"))
        self.folder_label.pack(pady=(0, 10))
        launch_frame = tk.Frame(self.settings_win)
        launch_frame.pack(pady=(5, 5))
        tk.Label(launch_frame, text="Launch Options:").pack()
        self.launch_entry = tk.Entry(launch_frame, width=50)
        self.launch_entry.insert(0, self.settings.launch_options)
        self.launch_entry.pack()
        launch_btn_frame = tk.Frame(launch_frame)
        launch_btn_frame.pack()
        tk.Button(launch_btn_frame, text="Save Options", width=20, height=2, command=self.save_launch_args).grid(row=0, column=0, padx=2, pady=2)
        tk.Button(launch_btn_frame, text="Reset to Default", width=20, height=2, command=self.reset_launch_args).grid(row=0, column=1, padx=2, pady=2)
        UIUtils.clickable_label(self.settings_win, f"Launcher by EPOS - v{LAUNCHER_VERSION}", "https://github.com/EPOS05/portal2vr_launcher").pack(pady=(10, 2))
        self.mod_version_label = UIUtils.clickable_label(self.settings_win, f"VR Mod by Gistix - {self.settings.saved_mod_version if self.settings.saved_mod_version else 'unknown'}", "https://github.com/Gistix/portal2vr")
        self.mod_version_label.pack(pady=(0, 10))
        UIUtils.apply_theme(self.settings_win, self.settings.dark_mode)
        self.refresh_setting_buttons()

    def save_launch_args(self):
        self.settings.launch_options = self.launch_entry.get()
        self.settings.save()

    def reset_launch_args(self):
        self.settings.launch_options = DEFAULT_LAUNCH_OPTIONS
        self.launch_entry.delete(0, tk.END)
        self.launch_entry.insert(0, DEFAULT_LAUNCH_OPTIONS)
        self.settings.save()

    def toggle_dark_mode(self):
        self.settings.dark_mode = not self.settings.dark_mode
        self.settings.save()
        UIUtils.apply_theme(self.root, self.settings.dark_mode)
        if hasattr(self, "settings_win") and self.settings_win.winfo_exists():
            UIUtils.apply_theme(self.settings_win, self.settings.dark_mode)
        self.refresh_setting_buttons()

    def toggle_console(self):
        self.settings.show_console = not self.settings.show_console
        self.settings.save()
        if self.settings.show_console:
            self.console_text.pack(pady=5)
            self.root.geometry("380x360")
        else:
            self.console_text.pack_forget()
            self.root.geometry("380x190")
        self.refresh_setting_buttons()

    def refresh_setting_buttons(self):
        try:
            self.console_btn.config(text="Hide Console" if self.settings.show_console else "Show Console")
            self.dark_btn.config(text="Disable Dark Mode" if self.settings.dark_mode else "Enable Dark Mode")
        except Exception:
            pass

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
            self.mod_version_label.config(text="VR Mod by Gistix - " + (self.settings.saved_mod_version if self.settings.saved_mod_version else "unknown"))
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
