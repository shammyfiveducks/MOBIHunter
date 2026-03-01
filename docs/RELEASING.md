# Releasing MOBIHunter

This guide is for maintainers who publish Linux portable builds to GitHub Releases.

## 1. Build the portable folder

From repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller

python -m PyInstaller \
  --noconfirm \
  --windowed \
  --name MOBIHunter \
  --add-data "assets:assets" \
  --collect-all tkinterdnd2 \
  main.py
```

Build output is in `dist/MOBIHunter/`.

## 2. Package tarball

```bash
tar -czf MOBIHunter-linux-portable.tar.gz -C dist MOBIHunter
```

## 3. Publish release

Create a new release and upload `MOBIHunter-linux-portable.tar.gz`:

- https://github.com/shammyfiveducks/MOBIHunter/releases/new

Keep the asset name exactly:

- `MOBIHunter-linux-portable.tar.gz`

That keeps this user download URL stable:

- `https://github.com/shammyfiveducks/MOBIHunter/releases/latest/download/MOBIHunter-linux-portable.tar.gz`

## 4. Quick verification

After publishing, verify redirect points to your new tag:

```bash
curl -sI https://github.com/shammyfiveducks/MOBIHunter/releases/latest/download/MOBIHunter-linux-portable.tar.gz | head
```
