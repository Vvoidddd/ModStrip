import os
import re
import shutil
import threading
import customtkinter as ctk
import platform
import subprocess
import psutil
import time
import webbrowser
import requests
import sys
from tkinter import filedialog, messagebox

# --- Application Constants ---
CURRENT_VERSION = "1.0.2"
APP_ID = '4000'
GITHUB_REPO = "Vvoidddd/ModStrip"
BLACKLIST_FILE = "modstrip_blacklist.txt"
LOG_FILE = "modstrip_log.txt"
BACKUP_DIR_NAME = "ModStrip_Backup"
ICON_PATH = "ModStrip.ico" # If this isnt here then ur fucked lol

def handle_self_delete():
    """ If the app was started with '--delete-old', it deletes the specified file. """
    if len(sys.argv) > 2 and sys.argv[1] == '--delete-old':
        old_path = sys.argv[2]
        try:
            time.sleep(2)  # Wait for the old process to exit
            os.remove(old_path)
        except OSError as e:
            # Log the error if deletion fails, but don't stop the app
            log(f"Error deleting old version at {old_path}: {e}")

def get_steam_libraries():
    """ Finds all Steam library folders on the system. """
    libs = []
    try:
        base_path = os.path.expandvars(r'%ProgramFiles(x86)%\Steam')
        lib_vdf = os.path.join(base_path, 'steamapps', 'libraryfolders.vdf')
        if os.path.exists(lib_vdf):
            with open(lib_vdf, 'r', encoding='utf-8') as f:
                content = f.read()
            # Find all paths like "path" "C:\\Steam"
            matches = re.findall(r'"path"\s+"([^"]+)"', content)
            libs.extend([p.replace('\\\\', '\\') for p in matches])
        if os.path.exists(base_path) and base_path not in libs:
            libs.insert(0, base_path)
    except Exception as e:
        log(f"Error finding Steam libraries: {e}")
    return [p for p in libs if os.path.exists(p)]

def find_gmod_path():
    """ Automatically locates the Garry's Mod installation directory. """
    for lib in get_steam_libraries():
        try:
            manifest = os.path.join(lib, 'steamapps', f'appmanifest_{APP_ID}.acf')
            if os.path.exists(manifest):
                with open(manifest, 'r', encoding='utf-8') as f:
                    content = f.read()
                match = re.search(r'"installdir"\s+"([^"]+)"', content)
                if match:
                    path = os.path.join(lib, 'steamapps', 'common', match.group(1))
                    if os.path.exists(path):
                        return os.path.normpath(path)
        except Exception:
            continue
    return None

def is_broken_gma(filepath):
    """
    Checks if a .gma file is likely broken.
    A file is considered broken if it doesn't start with 'GMAD' or is smaller than 1KB.
    """
    try:
        with open(filepath, 'rb') as f:
            header = f.read(4)
            if header != b'GMAD':
                return True # Invalid header
        if os.path.getsize(filepath) < 1024: # Less than 1 KB
            return True
    except Exception:
        return True
    return False

def has_no_workshop_link(addon_path):
    """
    Checks if a legacy addon folder lacks a 'workshopid' in an 'addon.json'.
    This helps identify manually installed addons that might be outdated.
    """
    json_path = os.path.join(addon_path, 'addon.json')
    if not os.path.exists(json_path):
        return True # No addon.json, considered to have no link.

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            content = f.read().lower()
        # Simple string search is faster and safer than parsing potentially malformed JSON
        if '"workshopid"' in content:
            return False
    except Exception as e:
        log(f"Could not read {json_path}: {e}")
    return True

def load_blacklist():
    """ Loads Workshop IDs from the blacklist file. """
    if not os.path.exists(BLACKLIST_FILE):
        return set()
    try:
        with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip().isdigit())
    except Exception:
        return set()

def log(msg):
    """ Writes a message to the log file with a timestamp. """
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass # Don't crash the app if logging fails

def close_gmod_if_running():
    """ Checks for and closes Garry's Mod processes. """
    procs_to_check = ['hl2.exe', 'gmod.exe']
    running_procs = []
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'].lower() in procs_to_check:
                running_procs.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if running_procs:
        if not messagebox.askyesno("GMod Running", "Garry's Mod is running and must be closed to continue.\nClose it now?"):
            return False
        for proc in running_procs:
            try:
                proc.terminate()
            except psutil.Error:
                pass # Process may have already closed
        # Wait for processes to terminate
        gone, alive = psutil.wait_procs(running_procs, timeout=5)
        for p in alive:
            p.kill() # Force kill any that remain
        time.sleep(1)
    return True

# --- Main Application ---
class ModStripApp(ctk.CTk):
    def __init__(self, gmod_dir):
        super().__init__()

        self.title(f"ModStrip v{CURRENT_VERSION}")
        self.geometry("900x650")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        try:
            if os.path.exists(ICON_PATH):
                self.iconbitmap(ICON_PATH)
        except Exception as e:
            print(f"Failed to set icon: {e}")

        # --- Variables ---
        self.gmod_dir = gmod_dir
        self.dry_run = ctk.BooleanVar(value=False)
        self.safe_mode = ctk.BooleanVar(value=True)
        self.show_full_path = ctk.BooleanVar(value=False)
        self.blacklist = load_blacklist()
        self._cleanup_active = False

        # --- Paths ---
        steamapps_dir = os.path.dirname(os.path.dirname(self.gmod_dir))
        self.workshop_content = os.path.normpath(os.path.join(steamapps_dir, 'workshop', 'content', APP_ID))
        self.addons_dir = os.path.normpath(os.path.join(self.gmod_dir, 'garrysmod', 'addons'))
        self.backup_dir = os.path.join(self.gmod_dir, BACKUP_DIR_NAME)

        self._setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        threading.Thread(target=self.check_for_updates, daemon=True).start()

    def _setup_ui(self):
        """ Creates and places all the widgets in the window. """
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Console Textbox ---
        self.console = ctk.CTkTextbox(self, state='disabled', corner_radius=6)
        self.console.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nsew")

        # --- Main Control Frame ---
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        control_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Buttons
        self.run_button = ctk.CTkButton(control_frame, text="Run Cleanup", command=self.run_cleanup)
        self.run_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(control_frame, text="Open Log", command=self.open_log).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(control_frame, text="Edit Blacklist", command=self.edit_blacklist).grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(control_frame, text="Developer Info", command=self.open_dev_info).grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        # Options
        ctk.CTkCheckBox(control_frame, text="Dry Run (Simulate)", variable=self.dry_run).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkCheckBox(control_frame, text="Safe Mode (Backup)", variable=self.safe_mode).grid(row=1, column=1, padx=10, pady=5, sticky="w")
        ctk.CTkCheckBox(control_frame, text="Show Full Path", variable=self.show_full_path).grid(row=1, column=2, padx=10, pady=5, sticky="w")

        # --- Path Information ---
        path_info_text = f"GMod: {self.gmod_dir}\nWorkshop: {self.workshop_content}"
        ctk.CTkLabel(self, text=path_info_text, anchor='w', justify='left').grid(row=2, column=0, padx=20, pady=(5, 10), sticky="ew")

    def append_console(self, text):
        """ Safely appends text to the console from any thread. """
        def update():
            if not self.winfo_exists(): return
            self.console.configure(state='normal')
            self.console.insert('end', text + '\n')
            self.console.see('end')
            self.console.configure(state='disabled')
            log(text)
        self.after(0, update)

    def check_for_updates(self):
        """ Checks GitHub for a new release. """
        self.append_console(f"ModStrip v{CURRENT_VERSION} | Checking for updates...")
        try:
            api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            latest_release = response.json()
            latest_version = latest_release.get("tag_name", "").lstrip('v')

            if not latest_version:
                self.append_console("Could not determine latest version.")
                return

            # Simple version comparison
            if tuple(map(int, latest_version.split('.'))) > tuple(map(int, CURRENT_VERSION.split('.'))):
                self.append_console(f"Update available: v{latest_version}")
                if messagebox.askyesno("Update Available", f"A new version (v{latest_version}) is available. Would you like to download and install it?"):
                    self._perform_update(latest_release)
            else:
                self.append_console("You are running the latest version.")

        except requests.exceptions.RequestException as e:
            self.append_console(f"Update check failed: {e}")
        except Exception as e:
            self.append_console(f"An error occurred during update check: {e}")

    def _perform_update(self, release_data):
        """ Downloads the new executable and restarts the application. """
        assets = release_data.get('assets', [])
        exe_asset = next((asset for asset in assets if asset['name'].lower().endswith('.exe')), None)

        if not exe_asset:
            messagebox.showerror("Update Error", "Could not find a .exe file in the latest release.")
            return

        download_url = exe_asset['browser_download_url']
        new_exe_path = os.path.join(os.path.dirname(sys.executable), f"ModStrip_v{release_data['tag_name']}.exe")
        old_exe_path = sys.executable

        try:
            self.append_console(f"Downloading from: {download_url}")
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(new_exe_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            self.append_console("Download complete.")

            # Launch the new exe with an argument to delete the old one
            subprocess.Popen([new_exe_path, '--delete-old', old_exe_path])
            self.after(100, self.destroy) # Close the current application

        except Exception as e:
            self.append_console(f"Failed to perform update: {e}")
            messagebox.showerror("Update Error", f"Failed to download or run the new version:\n{e}")

    def run_cleanup(self):
        """ Starts the cleanup process in a new thread. """
        if self._cleanup_active:
            self.append_console("Cleanup is already running.")
            return
        self._cleanup_active = True
        self.run_button.configure(state="disabled", text="Running...")
        threading.Thread(target=self._cleanup_task, daemon=True).start()

    def _move_or_delete(self, path, display_name):
        """ Moves file/folder to backup (if safe mode) or deletes it. """
        if self.dry_run.get():
            return
        try:
            if self.safe_mode.get():
                # Create a relative path to replicate the folder structure in the backup
                rel_path = os.path.relpath(path, os.path.dirname(self.addons_dir))
                dest = os.path.join(self.backup_dir, rel_path)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.move(path, dest)
                self.append_console(f"  -> Moved to backup: {display_name}")
            else:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                self.append_console(f"  -> Deleted: {display_name}")
        except Exception as e:
            self.append_console(f"  -> FAILED to process {display_name}: {e}")

    def _cleanup_task(self):
        """ The main logic for finding and processing broken/unwanted addons. """
        if not close_gmod_if_running():
            self.append_console("Cleanup aborted: Garry's Mod is running.")
            self._cleanup_active = False
            self.run_button.configure(state="normal", text="Run Cleanup")
            return

        count = 0
        self.append_console("\n" + "="*20 + " Starting Cleanup " + "="*20)
        action = "Simulating" if self.dry_run.get() else "Processing"

        # 1. Scan Workshop Content for broken .gma files
        self.append_console(f"\n[{action}] Broken Workshop Addons (.gma)...")
        if os.path.exists(self.workshop_content):
            for item in os.listdir(self.workshop_content):
                workshop_id = item
                if workshop_id in self.blacklist:
                    continue
                item_path = os.path.join(self.workshop_content, item)
                if os.path.isdir(item_path):
                    for gma_file in os.listdir(item_path):
                        if gma_file.endswith('.gma'):
                            full_path = os.path.join(item_path, gma_file)
                            if is_broken_gma(full_path):
                                display = full_path if self.show_full_path.get() else f"{workshop_id}.gma"
                                self.append_console(f"Found broken addon: {display}")
                                self._move_or_delete(full_path, display)
                                count += 1

        # 2. Scan legacy addons folder for addons without a workshop link
        self.append_console(f"\n[{action}] Legacy Addons without Workshop Link...")
        if os.path.exists(self.addons_dir):
            for entry in os.listdir(self.addons_dir):
                full_path = os.path.join(self.addons_dir, entry)
                if os.path.isdir(full_path) and has_no_workshop_link(full_path):
                    display = full_path if self.show_full_path.get() else entry
                    self.append_console(f"Found legacy addon: {display}")
                    self._move_or_delete(full_path, display)
                    count += 1

        self.append_console(f"\nCleanup finished. {action.replace('ing', 'ed')} {count} items.")
        self.append_console("="*58 + "\n")
        self._cleanup_active = False
        self.run_button.configure(state="normal", text="Run Cleanup")

    def open_log(self):
        """ Opens the log file with the default system application. """
        if not os.path.exists(LOG_FILE):
            self.append_console("Log file not created yet.")
            return
        try:
            os.startfile(LOG_FILE)
        except AttributeError: # For non-Windows
            subprocess.call(['open', LOG_FILE] if sys.platform == 'darwin' else ['xdg-open', LOG_FILE])
        except Exception as e:
            self.append_console(f"Failed to open log file: {e}")

    def edit_blacklist(self):
        """ Opens the blacklist file for editing. """
        try:
            if not os.path.exists(BLACKLIST_FILE):
                with open(BLACKLIST_FILE, 'w') as f:
                    f.write("# Enter one Workshop ID per line to exclude it from cleanup.\n")
            os.startfile(BLACKLIST_FILE)
        except AttributeError:
            subprocess.call(['open', BLACKLIST_FILE] if sys.platform == 'darwin' else ['xdg-open', BLACKLIST_FILE])
        except Exception as e:
            self.append_console(f"Failed to open blacklist file: {e}")

    def open_dev_info(self):
        """ Displays a small window with developer and tool information. """
        win = ctk.CTkToplevel(self)
        win.title("Developer Info")
        win.geometry("450x180")
        win.resizable(False, False)
        win.transient(self) # Keep on top of main window

        ctk.CTkLabel(win, text=f"ModStrip v{CURRENT_VERSION}", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10,5))
        ctk.CTkLabel(win, text="Developed by Void").pack()

        def create_link(parent, text, url):
            lbl = ctk.CTkLabel(parent, text=text, text_color="#6AABFF", cursor="hand2")
            lbl.pack(pady=2)
            lbl.bind("<Button-1>", lambda e: webbrowser.open(url))

        create_link(win, "ModStrip GitHub (Vvoidddd)", "https://github.com/Vvoidddd/ModStrip")
        create_link(win, "UI by CustomTkinter (TomSchimansky)", "https://github.com/TomSchimansky/CustomTkinter")

    def on_close(self):
        """ Handles the window close event. """
        if self._cleanup_active:
            if messagebox.askyesno("Exit", "Cleanup is still running. Are you sure you want to exit?"):
                self.destroy()
        else:
            self.destroy()

def select_gmod_dir_manually():
    """ Opens a dialog for the user to select their GMod directory. """
    root = ctk.CTk()
    root.withdraw() # Hide the empty root window
    messagebox.showwarning("GMod Not Found", "Could not auto-detect your Garry's Mod installation.\nPlease select your main 'GarrysMod' folder (the one containing 'hl2.exe').")
    path = filedialog.askdirectory(title="Select Garry's Mod Folder")
    root.destroy()
    # Check if the selected path looks correct
    if path and os.path.exists(os.path.join(path, 'garrysmod')) and os.path.exists(os.path.join(path, 'hl2.exe')):
        return os.path.normpath(path)
    return None

if __name__ == "__main__":
    handle_self_delete()

    gmod_directory = find_gmod_path()
    if not gmod_directory:
        gmod_directory = select_gmod_dir_manually()

    if not gmod_directory:
        # Use tkinter for final message if customtkinter fails
        try:
            root = ctk.CTk()
            root.withdraw()
            messagebox.showerror("Fatal Error", "Garry's Mod installation path not found or provided. The application cannot continue.")
            root.destroy()
        except Exception:
            print("Garry's Mod installation path not found. Exiting.")
        sys.exit(1)

    app = ModStripApp(gmod_dir=gmod_directory)
    app.mainloop()