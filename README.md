<p align="center">
  <img src="assets/screenshots/logo.png" width="216" alt="MOBIHunter logo">
</p>

<h1 align="center">MOBIHunter</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-green" alt="Platform Windows and Linux">
  <img src="https://img.shields.io/badge/License-MIT-purple" alt="MIT License">
</p>

<p align="center">
  Fast, drag-and-drop MOBI → EPUB conversion powered by Calibre
</p>

<p align="center">
  <img src="assets/screenshots/main.png" width="500" alt="MOBIHunter main UI">
</p>

## Features

- Drag-and-drop files and folders
- File menu actions for Add MOBI, Clear List, Copy Errors, and About
- Large in-app file/folder picker with session directory memory
- Duplicate detection
- Batch conversion with progress tracking
- Existing output policy: skip / overwrite / rename
- Split-safe retry for common Calibre split errors
- Optional separate output folder toggle
- Bottom status bar (dependency status, current file, conversion result)
- Splash screen branding and About dialog dependency checks

## Linux Quick Start (Beginner)

1. Install Calibre: https://calibre-ebook.com/download
2. Download and run the latest portable app:

```bash
wget https://github.com/shammyfiveducks/MOBIHunter/releases/latest/download/MOBIHunter-linux-portable.tar.gz
tar -xzf MOBIHunter-linux-portable.tar.gz
cd MOBIHunter
chmod +x MOBIHunter
./MOBIHunter
```

If the app does not appear, start it from terminal in that folder with `./MOBIHunter` and check messages.

## Run From Source (Python)

### What is a virtual environment (`venv`)?

A virtual environment is a local Python environment inside this project folder. It keeps dependencies isolated so they do not affect other Python projects on your machine.

### Requirements

- Python 3.10+
- Calibre installed (`ebook-convert` available on `PATH`)
- Python packages: `tkinterdnd2`, `Pillow`

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Usage

1. Add MOBI files/folders using drag-and-drop or `File -> Add MOBI...`.
2. Optionally set output behavior and timeout.
3. Optionally set a separate output folder:
   - Use the bottom `Output` button, or
   - Toggle `File -> Use Separate Output Folder`.
4. Click `Convert All` (bottom-right).
5. Watch progress and bottom status bar updates.
6. If needed, copy conversion details from `File -> Copy Errors`.

## Troubleshooting

- `ebook-convert not found`: install Calibre and restart the app.
- Drag-and-drop unavailable: ensure `tkinterdnd2` is installed in the active environment.
- Dependencies missing: check the bottom status bar and open `File -> About` for details.

## Acknowledgements

- MOBI to EPUB conversion is performed by **Calibre** via `ebook-convert`.
  - Project: https://calibre-ebook.com/
  - Source: https://github.com/kovidgoyal/calibre
- Drag-and-drop support is provided by **tkinterdnd2**.
- Image loading/scaling support uses **Pillow**.

## Maintainers

Release packaging instructions are in [docs/RELEASING.md](docs/RELEASING.md).

## License

MIT. See [LICENSE](LICENSE).

If you find this useful, please consider starring the repo.
