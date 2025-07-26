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
from tkinter import filedialog, messagebox

APP_ID = '4000'
BLACKLIST_FILE = "modstrip_blacklist.txt"
LOG_FILE = "modstrip_log.txt"
BACKUP_DIR_NAME = "ModStrip_Backup"

def parse_vdf(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {k: v.replace('\\\\', '\\') for k, v in re.findall(r'"(\d+)"\s+"([^"]+)"', content)}
    except Exception:
        return {}

def get_steam_libraries():
    base_path = os.path.expandvars(r'%ProgramFiles(x86)%\Steam')
    lib_vdf = os.path.join(base_path, 'steamapps', 'libraryfolders.vdf')
    libs = []
    if os.path.exists(lib_vdf):
        libs = list(parse_vdf(lib_vdf).values())
    if os.path.exists(base_path) and base_path not in libs:
        libs.insert(0, base_path)
    return [p for p in libs if os.path.exists(p)]

def find_gmod_path():
    for lib in get_steam_libraries():
        manifest = os.path.join(lib, 'steamapps', f'appmanifest_{APP_ID}.acf')
        if os.path.exists(manifest):
            try:
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
    try:
        with open(filepath, 'rb') as f:
            if f.read(4) != b'GMAD':
                return True
            f.seek(0, os.SEEK_END)
            return f.tell() < 50 * 1024
    except Exception:
        return True

def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return set()
    with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def log(msg):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def close_gmod_if_running():
    procs_to_check = ['hl2.exe', 'gmod.exe']
    running_procs = []
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() in procs_to_check:
                running_procs.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if running_procs:
        if not messagebox.askyesno("GMod Running", "Garry's Mod is running and must be closed to continue.\nClose now?"):
            return False
        for proc in running_procs:
            try: proc.terminate()
            except Exception: pass
        for proc in running_procs:
            try: proc.wait(timeout=10)
            except psutil.TimeoutExpired:
                try: proc.kill()
                except Exception: pass
        time.sleep(1)
    return True

class ModStripApp(ctk.CTk):
    def __init__(self, gmod_dir):
        super().__init__()
        self.title("ModStrip")
        self.geometry("900x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.dry_run = ctk.BooleanVar(value=False)
        self.safe_mode = ctk.BooleanVar(value=True)
        self.show_full_path = ctk.BooleanVar(value=False)
        self.blacklist = load_blacklist()

        self.gmod_dir = gmod_dir
        steamapps_dir = os.path.dirname(os.path.dirname(self.gmod_dir))
        self.workshop_content = os.path.normpath(os.path.join(steamapps_dir, 'workshop', 'content', APP_ID))
        self.workshop_downloads = os.path.normpath(os.path.join(steamapps_dir, 'workshop', 'downloads'))
        self.addons_dir = os.path.normpath(os.path.join(self.gmod_dir, 'garrysmod', 'addons'))
        self.backup_dir = os.path.join(self.gmod_dir, BACKUP_DIR_NAME)

        self._cleanup_active = False
        self._setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_ui(self):
        self.console = ctk.CTkTextbox(self, width=850, height=400, state='disabled')
        self.console.pack(padx=20, pady=15, fill='both', expand=True)

        options_frame = ctk.CTkFrame(self)
        options_frame.pack(fill='x', padx=20, pady=10)
        ctk.CTkCheckBox(options_frame, text="Dry Run (Don't Delete)", variable=self.dry_run).pack(side='left', padx=10)
        ctk.CTkCheckBox(options_frame, text="Safe Mode (Backup Broken Addons)", variable=self.safe_mode).pack(side='left', padx=10)
        ctk.CTkCheckBox(options_frame, text="Show Full Path", variable=self.show_full_path).pack(side='left', padx=10)

        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.pack(fill='x', padx=20, pady=(0, 20))
        ctk.CTkButton(buttons_frame, text="Run Cleanup", command=self.run_cleanup).pack(side='left', padx=15)
        ctk.CTkButton(buttons_frame, text="Open Log", command=self.open_log).pack(side='left', padx=15)
        ctk.CTkButton(buttons_frame, text="Edit Blacklist", command=self.edit_blacklist).pack(side='left', padx=15)
        ctk.CTkButton(buttons_frame, text="Developer Info", command=self.open_dev_info).pack(side='left', padx=15)

        path_info = (f"GMod Install: {self.gmod_dir}\n"
                     f"Workshop Content: {self.workshop_content}\n"
                     f"Workshop Downloads: {self.workshop_downloads}\n"
                     f"Addons Folder: {self.addons_dir}\n"
                     f"Backup Folder (Safe Mode): {self.backup_dir}")
        ctk.CTkLabel(self, text=path_info, anchor='w', justify='left').pack(fill='x', padx=20, pady=5)

    def append_console(self, text):
        def update():
            if not self.winfo_exists():
                return
            self.console.configure(state='normal')
            self.console.insert('end', text + '\n')
            self.console.see('end')
            self.console.configure(state='disabled')
            log(text)
        self.after(0, update)

    def run_cleanup(self):
        if self._cleanup_active:
            self.append_console("Cleanup already running.")
            return
        self._cleanup_active = True
        threading.Thread(target=self._cleanup_task, daemon=True).start()

    def _move_or_delete(self, path, display):
        if self.dry_run.get():
            return
        if self.safe_mode.get():
            rel_path = os.path.relpath(path, self.gmod_dir)
            dest = os.path.join(self.backup_dir, rel_path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.move(path, dest)
            self.append_console(f"Moved to backup: {display}")
        else:
            os.remove(path)
            self.append_console(f"Deleted: {display}")

    def _cleanup_task(self):
        if not close_gmod_if_running():
            self.append_console("Cleanup aborted: Garry's Mod is running.")
            self._cleanup_active = False
            return

        count = 0
        self.append_console("Starting ModStrip cleanup...\n")

        for root, _, files in os.walk(self.gmod_dir):
            for f in files:
                if f.endswith('.gma'):
                    full_path = os.path.join(root, f)
                    if self.workshop_content in full_path:
                        wid = os.path.basename(os.path.dirname(full_path))
                        if wid in self.blacklist:
                            continue
                    try:
                        if is_broken_gma(full_path):
                            display = full_path if self.show_full_path.get() else f
                            self.append_console(f"Broken addon found: {display}")
                            self._move_or_delete(full_path, display)
                            count += 1
                    except Exception as e:
                        self.append_console(f"Error checking {full_path}: {e}")

        if os.path.exists(self.workshop_downloads):
            for root, _, files in os.walk(self.workshop_downloads):
                for f in files:
                    if f.endswith('.part'):
                        full_path = os.path.join(root, f)
                        display = full_path if self.show_full_path.get() else f
                        self.append_console(f"Partial download found: {display}")
                        try:
                            self._move_or_delete(full_path, display)
                            count += 1
                        except Exception as e:
                            self.append_console(f"Failed to handle {display}: {e}")

        if os.path.exists(self.addons_dir):
            try:
                entries = os.listdir(self.addons_dir)
            except Exception as e:
                self.append_console(f"Failed to list addons folder: {e}")
                entries = []
            for entry in entries:
                full_path = os.path.join(self.addons_dir, entry)
                if os.path.isdir(full_path):
                    try:
                        if not os.listdir(full_path):
                            display = full_path if self.show_full_path.get() else entry
                            self.append_console(f"Empty addon folder: {display}")
                            shutil.rmtree(full_path)
                            count += 1
                    except Exception as e:
                        self.append_console(f"Failed to remove folder {full_path}: {e}")

        self.append_console(f"\nCleanup finished. {'Simulated' if self.dry_run.get() else 'Processed'} {count} entries.")
        self._cleanup_active = False

    def open_log(self):
        try:
            if platform.system() == 'Windows':
                os.startfile(LOG_FILE)
            elif platform.system() == 'Darwin':
                subprocess.call(('open', LOG_FILE))
            else:
                subprocess.call(('xdg-open', LOG_FILE))
        except Exception as e:
            self.append_console(f"Failed to open log file: {e}")

    def edit_blacklist(self):
        try:
            if not os.path.exists(BLACKLIST_FILE):
                open(BLACKLIST_FILE, 'w').close()
            if platform.system() == 'Windows':
                os.startfile(BLACKLIST_FILE)
            elif platform.system() == 'Darwin':
                subprocess.call(('open', BLACKLIST_FILE))
            else:
                subprocess.call(('xdg-open', BLACKLIST_FILE))
        except Exception as e:
            self.append_console(f"Failed to open blacklist file: {e}")

    def open_dev_info(self):
        win = ctk.CTkToplevel(self)
        win.title("Developer Info")
        win.geometry("400x180")
        win.resizable(False, False)

        info_lines = [
            "UI made with customtkinter.",
            "GitHub: https://github.com/TomSchimansky/CustomTkinter",
            "ModStrip developed by Void.",
            "GitHub: https://github.com/Vvoidddd"
        ]

        for line in info_lines:
            if line.startswith("http"):
                lbl = ctk.CTkLabel(win, text=line, text_color="blue", cursor="hand2")
                lbl.pack(anchor='w', padx=15)
                lbl.bind("<Button-1>", lambda e, url=line: webbrowser.open(url))
            else:
                ctk.CTkLabel(win, text=line).pack(anchor='w', padx=15)

    def on_close(self):
        if self._cleanup_active and not messagebox.askyesno("Exit", "Cleanup is running. Exit anyway?"):
            return
        self.destroy()

def select_gmod_dir():
    root = ctk.CTk()
    root.withdraw()
    messagebox.showwarning("Warning", "Could not auto-detect Garry's Mod installation.\nPlease select your GMod folder.")
    path = filedialog.askdirectory(title="Select Garry's Mod folder (must contain 'garrysmod')")
    root.destroy()
    if path and os.path.exists(os.path.join(path, 'garrysmod')):
        return os.path.normpath(path)
    return None

if __name__ == "__main__":
    gmod_dir = find_gmod_path()
    if not gmod_dir:
        gmod_dir = select_gmod_dir()
    if not gmod_dir:
        print("GMod not found. Exiting.")
        exit(1)

    app = ModStripApp(gmod_dir)
    app.mainloop()
