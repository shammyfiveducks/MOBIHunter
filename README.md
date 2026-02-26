<p align="center">
  <img src="assets/screenshots/logo.png" width="216">
</p>

<h1 align="center">MOBIHunter</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-green">
  <img src="https://img.shields.io/badge/License-MIT-purple">
</p>
<p align="center">
  Fast, drag-and-drop MOBI → EPUB conversion powered by Calibre
</p>

<p align="center">
  <img src="assets/screenshots/main.png" width="700">
</p>

<p align="center">
  Simple. Fast. No nonsense.
</p>

## Features

- Drag-and-drop files and folders
- Large in-app file/folder picker with session directory memory
- Duplicate detection
- Batch conversion with progress tracking
- Existing output policy: skip / overwrite / rename
- Split-safe retry for common Calibre split errors
- Cancel active conversion
- Optional delete-source-on-success toggle
- Output folder shortcut
- About dialog with dependency status checks
- 
<img width="623" height="566" alt="main" src="https://github.com/user-attachments/assets/4436b76a-8d89-4f4a-a087-c46747ab8be4" />

## Requirements


- Python 3.10+
- Calibre installed (`ebook-convert` available on `PATH`)
- Python package: `tkinterdnd2`
- Python package: `Pillow` (used for high-quality icon resizing)

## Install (Linux/macOS)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Install (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Calibre / ebook-convert

If `ebook-convert` is missing, install Calibre:

- https://calibre-ebook.com/download

After install, restart terminal and app so `ebook-convert` is on `PATH`.

## Run (Linux/macOS)

```bash
source .venv/bin/activate
python main.py
```

## Run (Windows PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

## Usage

1. Add MOBI files/folders via drag-drop or `Add MOBI...`.
2. Choose output behavior if EPUB already exists.
3. Optionally set timeout and source deletion behavior.
4. Click `Convert All`.
5. Review logs and copy errors if needed.
6. Open `About` to see live dependency status.

## Troubleshooting

- `ebook-convert not found`:
  Install Calibre and restart the app.
- Conversion split errors:
  App auto-retries with safer split settings.
- Drag-and-drop unavailable:
  Ensure `tkinterdnd2` is installed in the active environment.
- About button is red:
  One or more required dependencies are missing; open About for install hints.

## Beginner Friendly Instructions:

🚀 Quick Start (Windows – Recommended)

Follow these steps if you're new to Python.

1. Install Python

Download and install:

https://www.python.org/downloads/

During install, tick:

Add Python to PATH

Click Install Now

2. Install Calibre

Download and install:

https://calibre-ebook.com/download

3. Download MOBIHunter

Click the green Code button on this page → Download ZIP

Extract it somewhere convenient, for example:

Desktop\MOBIHunter

4. Open the folder in Terminal

Inside the MOBIHunter folder:

Right-click empty space → click:

Open in Terminal

5. Run MOBIHunter

Copy and paste:

py -m venv .venv
..venv\Scripts\activate
pip install -r requirements.txt
python main.py

MOBIHunter will open.

▶ Running Again Later

Next time, just run:

..venv\Scripts\activate
python main.py

✨ Features

Drag-and-drop files and folders

Large in-app file/folder picker with memory

Batch conversion

Duplicate detection

Progress tracking

Existing output options:

Skip

Overwrite

Rename

Automatic retry for common Calibre errors

Cancel active conversion

Optional delete-source-after-success

Output folder shortcut

Live dependency status checker

🖥 Requirements

Python 3.10+

Calibre installed (ebook-convert available on PATH)

Python packages:

tkinterdnd2

Pillow

🐧 Install (Linux / macOS)

Open terminal inside project folder:

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py

⚙ Calibre / ebook-convert

MOBIHunter uses Calibre's conversion engine.

If conversion fails with:

ebook-convert not found

Install Calibre:

https://calibre-ebook.com/download

Then restart terminal and MOBIHunter.

📖 Usage

Drag and drop MOBI files or folders
or click Add MOBI

Choose output behaviour if EPUB exists

Click Convert All

Watch progress

Open converted EPUB files

🧰 Troubleshooting
ebook-convert not found

Install Calibre and restart MOBIHunter.

Drag and drop not working

Run:

pip install tkinterdnd2

About button shows red

Open About

It will tell you exactly what is missing.

Conversion failed

Check log output inside MOBIHunter.

Retry usually works automatically.


## License

MIT. See [LICENSE](LICENSE).
