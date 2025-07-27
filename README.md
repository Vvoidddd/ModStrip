# ModStrip

![ModStrip](ModStrip.png)

ModStrip is a powerful Garry's Mod addon cleaner and repair tool designed to detect and remove broken or invalid addons safely. It features an optional **Safe Mode** that moves problematic addons to a backup folder instead of deleting them, minimizing risk of data loss.

---

## Features

- **Safe Mode (Optional)**  
  Automatically moves broken addons to `ModStrip_Backup` instead of deleting them.

- **Addon Validation**  
  - Validates `.gma` headers and minimum size.
  - Checks addon folders for required structure.
  - Detects duplicate paths (e.g., `lua/`, `materials/`, `models/`, `sound/`).
  - Flags partial workshop downloads (`.part` files).
  - Cleans empty addon folders.

- **Blacklist Support**  
  Protects specified workshop addons listed in `modstrip_blacklist.txt`.

- **Modern GUI**  
  Uses `customtkinter` for a clean dark-themed interface.

- **Live Logging**  
  Logs all activity to `modstrip_log.txt` and shows real-time output in-app.

---

## Requirements

- Python 3.8+  
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter)  
- `psutil`

Install dependencies:

```bash
pip install customtkinter psutil
````

---

## Usage

1. Run the script:

   ```bash
   python modstrip.py
   ```

2. If your Garry's Mod folder isn't auto-detected, manually select it.

3. Options:

   * **Dry Run**: Simulate without deleting/moving files.
   * **Show Full Path**: Expand log paths.
   * **Safe Mode**: Enable backup instead of delete.

4. Click **Run Cleanup**.

5. Optional tools:

   * View/edit blacklist
   * Open log file
   * Developer info

---

## Safe Mode Behavior

When enabled:

* Broken or invalid addons are moved to `ModStrip_Backup` inside your `addons/` folder.
* Review or restore them later manually.

---

## Blacklist

* Add folder names of addons you want to exclude from removal into `modstrip_blacklist.txt`.
* One line per addon ID or folder name.

---

## ⚠️ Distribution Notice

This is the **only valid source** for ModStrip:

**GitHub Repository**: [https://github.com/Vvoidddd/ModStrip](https://github.com/Vvoidddd/ModStrip)

If you do not wish to build it yourself, the prebuilt `.exe` is located in the [Releases](https://github.com/Vvoidddd/ModStrip/releases) section.

Do **not** trust ModStrip binaries from unofficial sources.

---

## License

### Custom License

You are permitted to **use** and **modify** this project **only with direct permission from the creator**.

You may **not** redistribute modified versions or derivative works without explicit approval. Any modification that introduces **malicious, misleading, or poor-quality code** is strictly prohibited.

---

## Developer Info

* Created by Void
* GitHub: [https://github.com/Vvoidddd](https://github.com/Vvoidddd)
* UI: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)

---

## Troubleshooting

* Ensure Python and all dependencies are installed.
* Close Garry's Mod before scanning.
* Run the script with permission to access your addons folder.

---

## Contact

Open a GitHub issue or reach out directly via the profile link above.


