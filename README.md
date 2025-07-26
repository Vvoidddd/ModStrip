# ModStrip

![ModStrip](ModStrip.png)

ModStrip is a powerful Garry's Mod addon cleaner tool designed to detect and remove broken or invalid addons safely. It offers a **Safe Mode** feature that moves problematic addons to a backup folder instead of deleting them, ensuring no accidental loss.

---

## Features

- **Safe Mode (Optional)**  
  Enable backup mode to automatically move broken addons to a `ModStrip_Backup` folder instead of permanently deleting them.

- **Addon Validation**  
  - Checks `.gma` files for validity and minimum size.  
  - Parses addon directories for file structure integrity.  
  - Detects duplicate paths across addons (`lua/`, `materials/`, `models/`, `sound/`).  
  - Scans for partial workshop downloads (`.part` files).  
  - Removes empty addon folders.

- **Blacklist Support**  
  Prevents removal of specific workshop addons listed in `modstrip_blacklist.txt`.

- **User-Friendly GUI**  
  Built with `customtkinter` for a modern, dark-themed interface.

- **Live Logging**  
  Logs all operations to `modstrip_log.txt` and displays output in-app.

---

## Requirements

- Python 3.8+  
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter)  
- `psutil` (for process management)  

Install dependencies with:

```bash
pip install customtkinter psutil
````

---

## Usage

1. Run the script:

   ```bash
   python modstrip.py
   ```

2. If Garry's Mod installation is not detected automatically, select your GMod folder manually (folder containing the `garrysmod` directory).

3. Use the GUI options:

   * **Dry Run**: Simulate cleanup without deleting or moving files.
   * **Show Full Path**: Display full file paths in the log output.
   * **Safe Mode**: When enabled, broken addons are moved to `ModStrip_Backup` instead of deleted permanently.

4. Click **Run Cleanup** to start scanning and cleaning your addons.

5. Use buttons to open the log file, edit the blacklist, or view developer info.

---

## Safe Mode Behavior

When **Safe Mode** is enabled:

* Detected broken or invalid addons are moved to a `ModStrip_Backup` folder inside your Garry's Mod addons directory.
* This prevents permanent loss and allows manual review or restoration.

---

## Blacklist

* Add Steam Workshop addon IDs (folder names) you want to protect from removal in `modstrip_blacklist.txt`.
* One ID per line.

---

## Developer Info

* Created by Void
* GitHub: [https://github.com/Vvoidddd](https://github.com/Vvoidddd)
* UI powered by CustomTkinter: [https://github.com/TomSchimansky/CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)

---

## License

MIT License — feel free to use, modify, and redistribute.

---

## Troubleshooting

* Ensure `customtkinter` and `psutil` are installed.
* Run Python with sufficient permissions to access Garry's Mod folders.
* Close Garry's Mod before running the cleanup for accurate and safe operation.

---

## Contact

For issues or feature requests, please open an issue on the GitHub repository or contact the developer directly.

