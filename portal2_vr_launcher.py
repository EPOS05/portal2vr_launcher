import os
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import webbrowser

# Determine the base path of the application dynamically
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

# Paths dynamically based on the base directory
mod_dir = os.path.join(base_dir, "modfiles")
config_file = os.path.join(os.path.dirname(sys.argv[0]), "portal2_path.txt")

# Global variables
show_console = False
dark_mode = True

# Path to the icon file
icon_path = os.path.join(base_dir, "icon.ico")

# Function to read the Portal 2 installation path from the config file
def read_portal2_path():
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            return f.read().strip()
    return ""

# Function to write the Portal 2 installation path to the config file
def save_portal2_path(path):
    with open(config_file, "w") as f:
        f.write(path)

# Get the Portal 2 installation folder from the config file
portal2_path = read_portal2_path()
portal2_exe = os.path.join(portal2_path, "portal2.exe")
mod_installed_flag = os.path.join(portal2_path, "VR")

launch_options = "-insecure -window -novid +mat_motion_blur_percent_of_screen_max 0 +mat_queue_mode 0 +mat_vsync 0 +mat_antialias 0 +mat_grain_scale_override 0 -width 1280 -height 720"

# Function to check if the mod is installed
def is_mod_installed():
    return os.path.exists(mod_installed_flag)

# Function to log messages in the console
def log_console(message):
    if show_console:
        console_text.config(state=tk.NORMAL)
        console_text.insert(tk.END, f"{message}\n")
        console_text.config(state=tk.DISABLED)
        console_text.see(tk.END)

# Function to install the mod
def install_mod():
    if not portal2_path:
        messagebox.showerror("Error", "Portal 2 installation folder is not set. Please configure it in Settings.")
        return
    try:
        bin_dir = os.path.join(portal2_path, "bin")
        os.makedirs(bin_dir, exist_ok=True)

        for file in ["d3d9.dll", "openvr_api.dll"]:
            src = os.path.join(mod_dir, "bin", file)
            dest = os.path.join(bin_dir, file)
            shutil.copy2(src, dest)
            log_console(f"Copied {file} to: {dest}")

        for folder in ["portal2_dlc3", "VR"]:
            src = os.path.join(mod_dir, folder)
            dest = os.path.join(portal2_path, folder)
            if os.path.exists(src):
                shutil.copytree(src, dest, dirs_exist_ok=True)
                log_console(f"Copied {folder} to: {dest}")

        messagebox.showinfo("Install", "Portal 2 VR Mod has been installed.")
    except Exception as e:
        messagebox.showerror("Error", f"Installation failed: {e}")
        log_console(f"Installation failed: {e}")
    finally:
        update_status()

# Function to uninstall the mod
def uninstall_mod():
    if not portal2_path:
        messagebox.showerror("Error", "Portal 2 installation folder is not set. Please configure it in Settings.")
        return
    try:
        for path in ["bin/d3d9.dll", "bin/openvr_api.dll", "portal2_dlc3", "VR"]:
            full_path = os.path.join(portal2_path, path)
            if os.path.isdir(full_path):
                shutil.rmtree(full_path, ignore_errors=True)
                log_console(f"Removed directory: {full_path}")
            elif os.path.isfile(full_path):
                os.remove(full_path)
                log_console(f"Removed file: {full_path}")

        messagebox.showinfo("Uninstall", "Portal 2 VR Mod has been uninstalled.")
    except Exception as e:
        messagebox.showerror("Error", f"Uninstallation failed: {e}")
        log_console(f"Uninstallation failed: {e}")
    finally:
        update_status()

# Function to launch Portal 2 with the VR mod
def launch_portal2_vr():
    if not is_mod_installed():
        messagebox.showwarning("Launch Error", "The mod is not yet installed. Please install it first.")
        log_console("Launch failed: Mod is not installed.")
        return

    try:
        subprocess.Popen([portal2_exe] + launch_options.split())
        log_console("Launching Portal 2 VR...")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to launch Portal 2: {e}")
        log_console(f"Failed to launch Portal 2: {e}")

# Function to update the UI based on mod status
def update_status():
    if is_mod_installed():
        status_label.config(text="Mod Status: Installed")
        install_button.config(text="Uninstall", command=uninstall_mod)
        launch_button.config(state=tk.NORMAL)
    else:
        status_label.config(text="Mod Status: Uninstalled")
        install_button.config(text="Install", command=install_mod)
        launch_button.config(state=tk.DISABLED)

# Function to open the folder selection dialog
def select_folder():
    global portal2_path, portal2_exe, mod_installed_flag
    selected_folder = filedialog.askdirectory(title="Select Portal 2 Installation Folder")
    if selected_folder:
        portal2_path = selected_folder
        portal2_exe = os.path.join(portal2_path, "portal2.exe")
        mod_installed_flag = os.path.join(portal2_path, "VR")
        save_portal2_path(selected_folder)
        messagebox.showinfo("Success", f"Portal 2 installation folder set to:\n{selected_folder}")
        update_status()

# Function to apply the chosen theme (dark/light) to all relevant widgets
def apply_theme(target=None):
    bg_color = "#333" if dark_mode else "SystemButtonFace"
    fg_color = "white" if dark_mode else "black"
    button_color = "#444" if dark_mode else "SystemButtonFace"
    button_active_color = "#555" if dark_mode else "SystemButtonFace"
    text_bg_color = "#222" if dark_mode else "white"
    text_fg_color = "white" if dark_mode else "black"
    
    # Apply to the target window and recursively to child widgets
    target = target or root
    target.configure(bg=bg_color)

    for widget in target.winfo_children():
        try:
            # Configure common widget types
            if isinstance(widget, (tk.Frame, tk.LabelFrame)):
                widget.configure(bg=bg_color)
                apply_theme(widget)  # Recurse into child frames
            elif isinstance(widget, tk.Label):
                widget.configure(bg=bg_color, fg=fg_color)
            elif isinstance(widget, tk.Button):
                widget.configure(
                    bg=button_color,
                    fg=fg_color,
                    activebackground=button_active_color,
                    activeforeground=fg_color
                )
            elif isinstance(widget, tk.Checkbutton):
                widget.configure(
                    bg=bg_color,
                    fg=fg_color,
                    selectcolor=bg_color,
                    activebackground=bg_color,
                    activeforeground=fg_color
                )
            elif isinstance(widget, (tk.Text, scrolledtext.ScrolledText)):
                widget.configure(
                    bg=text_bg_color,
                    fg=text_fg_color,
                    insertbackground=fg_color
                )
            elif isinstance(widget, tk.Toplevel):
                apply_theme(widget)  # Apply theme to new windows
        except tk.TclError:
            # Handle unsupported widget types gracefully
            pass

# Function to toggle dark mode
def toggle_dark_mode():
    global dark_mode
    dark_mode = not dark_mode
    dark_mode_checkbox_var.set(dark_mode)
    apply_theme()  # Refresh the theme across the entire application

# Function to open the help window
def show_help():
    help_window = tk.Toplevel(root)
    help_window.title("Help")
    help_window.geometry("400x180")
    help_window.iconbitmap(icon_path)

    tk.Label(
        help_window,
        text="Installation Steps:\n"
             "1. Select your Portal 2 installation folder from the settings.\n"
             "2. Run this executable to launch or install/uninstall the mod.\n",
        wraplength=380,
        justify="left"
    ).pack(pady=2)

    tk.Label(
        help_window,
        text="Github:",
    ).pack(pady=2)

    tk.Button(
        help_window,
        text="Launcher by EPOS",
        command=lambda: webbrowser.open("https://github.com/EPOS05/portal2vr_launcher"),
    ).pack(pady=0)

    tk.Button(
        help_window,
        text="VR Mod by Gistix",
        command=lambda: webbrowser.open("https://github.com/Gistix/portal2vr"),
    ).pack(pady=5)
    
    tk.Label(
        help_window,
        text="Launcher - v1.0  |  VR Mod - v0.2.0-preview.1",
    ).pack(pady=0)

    apply_theme(help_window)

# Function to toggle the console visibility
def show_console_toggle():
    global show_console
    show_console = not show_console
    console_checkbox_var.set(show_console)
    if show_console:
        console_text.pack(pady=5)
        root.geometry("315x450")  # Adjust window height when console is shown
    else:
        console_text.pack_forget()
        root.geometry("315x180")  # Reset to original height

# Function to open the settings window
def open_settings():
    settings_window = tk.Toplevel(root)
    settings_window.title("Settings")
    settings_window.geometry("400x180")
    settings_window.iconbitmap(icon_path)
    
    def update_folder_label():
        folder_text = portal2_path if portal2_path else "Not Set"
        folder_label.config(text=f"{folder_text}")

    tk.Checkbutton(
        settings_window,
        text="Show Console",
        variable=console_checkbox_var,
        command=show_console_toggle,
    ).pack(pady=5)

    tk.Checkbutton(
        settings_window,
        text="Enable Dark Mode",
        variable=dark_mode_checkbox_var,
        command=toggle_dark_mode,
    ).pack(pady=5)

    tk.Button(
        settings_window,
        text="Help",
        command=show_help,
    ).pack(pady=5)

    tk.Button(
        settings_window,
        text="Select Portal 2 Folder",
        command=select_folder,
    ).pack(pady=5)

    # Display the current Portal 2 installation folder
    folder_label = tk.Label(settings_window, text="")
    folder_label.pack(pady=0)
    update_folder_label()

    apply_theme(settings_window)  # Apply dark mode to the settings window

# Main window
root = tk.Tk()
root.title("Portal 2 VR Launcher")
root.geometry("315x180")
root.iconbitmap(icon_path)

console_checkbox_var = tk.BooleanVar(value=show_console)
dark_mode_checkbox_var = tk.BooleanVar(value=dark_mode)

title_label = tk.Label(root, text="Portal 2 VR Launcher", font=("Arial", 14))
title_label.pack()

status_label = tk.Label(root, text="Mod Status: Unknown")
status_label.pack()

button_frame = tk.Frame(root)
button_frame.pack(pady=20)

launch_button = tk.Button(button_frame, text="Launch Portal 2 VR", height=2, command=launch_portal2_vr, state=tk.DISABLED)
install_button = tk.Button(button_frame, text="Install/Uninstall", height=2, command=install_mod)
settings_button = tk.Button(button_frame, text=u"\u2699", width=5, height=5, command=open_settings)

launch_button.grid(row=0, column=0, sticky="nsew")
install_button.grid(row=1, column=0, sticky="nsew")
settings_button.grid(row=0, column=1, rowspan=2, sticky="nsew")

console_text = scrolledtext.ScrolledText(root, wrap=tk.WORD)
if show_console:
    console_text.pack()

update_status()
apply_theme()
root.mainloop()
