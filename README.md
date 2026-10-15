# qgis2ge - QGIS to Google Earth Plugin

[![GitHub Release](https://img.shields.io/badge/release-v1.1.0-blue.svg)](https://github.com/iitold/qgis2ge/releases)
[![QGIS Minimum Version](https://img.shields.io/badge/QGIS-3.22+-brightgreen.svg)](https://qgis.org)
[![License](https://img.shields.io/badge/license-GPLv2%2B-orange.svg)](LICENSE)

*Professional QGIS plugin to export vector polygon layers to Google Earth (`.kmz` / `.kml`) preserving 100% styles, categorized fill colors, borders, opacity, attribute tables, and cell sector size scaling.*

---

## 1. Key Features

- **True Color & Style Fidelity:**
  - Preserves fill colors, border/outline colors, border thickness, and opacity exactly as styled in QGIS.
  - Full support for all QGIS renderers: **Single Symbol**, **Categorized**, **Graduated**, **Rule-based**, and **Data-defined overrides** (`PropertyFillColor`, `PropertyStrokeColor`, `PropertyStrokeWidth`).
- **Direct KMZ & KML Support:**
  - Exports directly to compressed `.kmz` (ZIP containing `doc.kml`) or plain `.kml`.
  - KMZ reduces file size by **85–90%**, ideal for massive telecom layers with tens of thousands of sectors.
- **RF / Telecom Cell Sector Scaling:**
  - Allows expanding or shrinking sector petals (e.g. +50% = 1.5x) for optimal Google Earth visibility.
  - **Site Origin / First Vertex Anchor (Recommended for RF/RAN):** Keeps the antenna tower base coordinate strictly locked in place, extending only the outer beam boundary into the coverage azimuth.
  - **Centroid Anchor:** Scales polygons uniformly around their center of mass.
- **Hierarchical Category Folders:**
  - Features grouped automatically into toggleable `<Folder>` containers in Google Earth Pro based on category values.
- **ExtendedData Attributes:**
  - Selectable attributes exported to `<ExtendedData>` tags, viewable in Google Earth feature information balloons on click.
- **Memory-Safe Streaming:**
  - Handles 100,000+ features effortlessly via temporary-file streaming and style deduplication. Does not exhaust RAM or freeze QGIS.
- **Background Execution (QgsTask):**
  - Runs asynchronously with progress updates, cancel support, and completion notifications with "Open Folder" action.
- **In-App Updater & Self-Reloading:**
  - Integrated one-click update check against GitHub Releases (`iitold/qgis2ge`).
  - Downloads, verifies, installs, and reloads the plugin live inside QGIS without requiring an application restart.
- **One-Click Release Automation:**
  - Includes `release.bat` / `release.ps1` and GitHub Actions CI/CD to set versions, run tests, commit as `iitold`, tag, push, build, and publish releases automatically.

---

## 2. Directory Structure

```
qgis2ge/
├── __init__.py            # Plugin entrypoint classFactory(iface)
├── metadata.txt           # QGIS Plugin Manager metadata (version=1.1.0)
├── plugin.py              # Registers action in Vector Menu (&qgis2ge) & Toolbar
├── dialog.py              # Modern English dialog (responsive cards, swatches, controls)
├── exporter.py            # Core engine (KMZ/KML streaming, style deduplication, scaling)
├── updater.py             # In-app background updater & hot reload engine
├── task.py                # Asynchronous background execution (QgsTask)
├── styles.qss             # Unified light/dark theme stylesheet
├── icon.svg               # Plugin vector icon
└── tests/
    └── test_exporter.py   # Headless PyQGIS automated test suite (14 tests)
```

---

## 3. Installation

### Method 1: Install from ZIP (Recommended)
1. Download or locate [qgis2ge.zip](file:///c:/code/qgis_plugin/qgis-export-kml/qgis2ge.zip).
2. Open **QGIS** (3.22 up to 3.40+ LTR).
3. Go to menu: **Plugins -> Manage and Install Plugins...**
4. Select **Install from ZIP** on the left navigation panel.
5. Browse to `qgis2ge.zip` and click **Install Plugin**.
6. The plugin is ready to use! Access it via:
   - Menu: **Vector -> qgis2ge -> qgis2ge: Export to Google Earth...**
   - Toolbar: Click the **qgis2ge** icon on the Vector toolbar.

### Method 2: Manual Directory Copy
On Windows:
Copy the `qgis2ge` directory directly into:
```
%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\
```
Then restart QGIS or enable `qgis2ge` in **Plugins -> Installed**.

---

## 4. In-App Updates

### For End-Users
1. Open the **qgis2ge** dialog in QGIS.
2. In the top-right header, click **Check for Updates**.
3. If a newer release is published on GitHub:
   - A banner appears: `★ New version vX.Y.Z available! [Update Now] [Notes]`
   - Click **Update Now**: The plugin downloads `qgis2ge.zip` from GitHub Releases, extracts it in-place, and reloads itself immediately.
   - You can also check **Check for updates automatically when opening dialog** in the *Advanced Options* card.

---

## 5. Developer & Release Automation (`release.bat`)

To publish a new version of the plugin with full automated testing, Git tagging, and GitHub Actions building:

### Option A: Double-Click or Run `release.bat`
```cmd
release.bat
```
The script will interactively:
1. Show the current version (e.g. `1.1.0`) and ask for the new version (e.g. `1.2.0`).
2. Ask for release notes / changelog summary.
3. Automatically update `qgis2ge/metadata.txt` and `README.md`.
4. Run the PyQGIS test suite (`test_exporter.py`). If any test fails, it halts immediately to protect release integrity.
5. Package a clean `qgis2ge.zip` and sync to your local QGIS plugins folder for local verification.
6. Configure Git identity to `iitold` (`iitold@users.noreply.github.com`).
7. Set remote origin to `https://github.com/iitold/qgis2ge.git`.
8. Commit changes, create annotated tag `v1.2.0`.
9. Prompt for confirmation and push branch & tags to GitHub.

### Option B: Command-Line Arguments
```cmd
release.bat 1.2.0 "Added custom cell beam width and 5G band presets"
```
Or via PowerShell:
```powershell
.\release.ps1 -NewVersion 1.2.0 -ReleaseNotes "Added 5G band presets"
```

### GitHub Actions CI/CD
Once pushed, the GitHub Action workflow (`.github/workflows/release.yml`) automatically:
1. Checks out the tagged commit.
2. Builds `qgis2ge.zip` (clean without `__pycache__` or test files).
3. Creates a new GitHub Release for tag `vX.Y.Z` and attaches `qgis2ge.zip`.
4. End users clicking **Check for Updates** in QGIS will immediately see the new version and can update with 1 click!

---

## 6. Running Automated Tests

Run the test suite headless using the QGIS Python runtime:

```cmd
cmd /c call "C:\Program Files\QGIS 3.40.12\bin\python-qgis-ltr.bat" -m unittest qgis2ge.tests.test_exporter
```

Expected result:
```
..............
----------------------------------------------------------------------
Ran 14 tests in 0.951s

OK
```

All 14 test cases cover:
- KML hex color conversion (`aabbggrr`)
- Stroke modes (`same`, `same_opaque`, `original`, `none`)
- Categorized renderer deduplication & folder structure
- MultiPolygons & Polygons with internal holes
- Data-defined property overrides
- XML escaping and Vietnamese unicode strings
- Graduated renderer with ranges
- Rule-based renderer with nested rules
- Opacity and border width overrides
- Selected-features-only filtering
- Direct KMZ ZIP generation & `doc.kml` validation
- Geometry scaling & first-vertex origin anchoring
- In-app updater version comparison & ZIP replacement
- User cancellation and cleanup

---

## 7. License

GNU General Public License v2.0 or later (GPL-2.0-or-later).
Authored by **iitold** (`https://github.com/iitold/qgis2ge`).
