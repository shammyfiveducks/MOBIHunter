# Changelog

All notable changes to this project are documented here.

## [0.6.0] - 2026-02-26

### Added

- Rebrand to **MOBI Hunter**
- Custom app icon and About dialog branding
- Large in-app picker for files/folders with directory memory
- About dialog dependency status checks and install hints
- Conversion progress bar and status label
- Cancel conversion button
- Open output folder button
- Copy errors button
- Optional source deletion on successful conversion
- Timeout tooltip guidance

### Changed

- Thread-safe logging and UI update handling
- Improved drag/drop payload parsing
- Duplicate queue prevention
- Existing output conflict policy (skip/overwrite/rename)
- End-of-run summary and queue cleanup behavior
- Split-safe retry for Calibre split errors
