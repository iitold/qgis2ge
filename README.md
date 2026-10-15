# qgis2ge - QGIS to Google Earth

[![Release](https://img.shields.io/badge/release-v1.1.7-blue.svg)](https://github.com/iitold/qgis2ge/releases)
[![QGIS Version](https://img.shields.io/badge/QGIS-3.22+-brightgreen.svg)](https://qgis.org)
[![Author](https://img.shields.io/badge/Author-iitold-orange.svg)](https://github.com/iitold)
[![Email](https://img.shields.io/badge/Email-doancongthanh92%40gmail.com-red.svg)](mailto:doancongthanh92@gmail.com)
[![License: GPL v2+](https://img.shields.io/badge/License-GPL%20v2%2B-blue.svg)](LICENSE)

**qgis2ge** is a professional QGIS plugin designed to export vector polygon layers directly to Google Earth (`.kmz` / `.kml`) while **100% preserving styles, fill colors, outlines, opacity, categorized folders, attribute tables, and cell sector size scaling**.

---

## 👤 Author & Support
- **Developer:** [iitold](https://github.com/iitold)
- **Email:** [doancongthanh92@gmail.com](mailto:doancongthanh92@gmail.com)
- **GitHub Repository:** [https://github.com/iitold/qgis2ge](https://github.com/iitold/qgis2ge)
- **Bug Tracker:** [https://github.com/iitold/qgis2ge/issues](https://github.com/iitold/qgis2ge/issues)

---

## ⚡ Quick Start: Installation

### Method 1: Install from ZIP (Recommended)
1. Download **[qgis2ge.zip](https://github.com/iitold/qgis2ge/releases/latest)** from the latest GitHub Release.
2. In QGIS, navigate to the menu:  
   **Plugins ➔ Manage and Install Plugins...**
3. Select **Install from ZIP** on the left menu.
4. Click **Browse (...)**, select `qgis2ge.zip`, and click **Install Plugin**.
5. Launch the plugin from **Vector ➔ qgis2ge ➔ qgis2ge: Export to Google Earth...** or click the toolbar icon.

### Method 2: Manual Directory Copy
Extract or copy the `qgis2ge` directory directly into your QGIS plugins path:
```text
%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\
```
Then enable **qgis2ge** in **Plugins ➔ Installed**.

---

## 🔄 Updating to New Versions

### Option 1: 1-Click In-App Update (Easiest)
1. Open the **qgis2ge** dialog inside QGIS.
2. Click **Check for Updates** in the top-right header (next to the version badge).
3. When an update is detected, click **Update Now**:
   - The plugin automatically downloads the newest release package.
   - Replaces files and **hot-reloads live inside QGIS without restarting**.
4. *(Optional)* Check **Check for updates automatically when opening dialog** in *Advanced Options* for automated alerts.

### Option 2: Manual Re-installation
Download the newest `qgis2ge.zip` from [GitHub Releases](https://github.com/iitold/qgis2ge/releases/latest) and install via **Plugins ➔ Manage and Install Plugins ➔ Install from ZIP**.

---

## ✨ Features

- **True Style Fidelity:** Retains fill colors, border colors, stroke width, and opacity from all QGIS renderers (*Single, Categorized, Graduated, Rule-based, and Data-defined expressions*).
- **KMZ & KML Formats:** Direct export to compressed `.kmz` (85–90% smaller file size, ideal for large telecom layers) or plain `.kml`.
- **Telecom Cell Sector Scaling:** Custom size scaling (e.g. +50% = 1.5x) with **Site Origin Anchor** to keep the antenna tower base fixed while expanding beam coverage outward.
- **Categorized Google Earth Folders:** Groups polygons into toggleable `<Folder>` containers in Google Earth Pro.
- **ExtendedData Info Balloons:** Export selected layer attributes to viewable popup tables in Google Earth.
- **Background Execution:** Multi-threaded `QgsTask` processing with cancel support and progress updates.

---

## 🚀 For Developers: 1-Click Release Automation

To release a new version with automated checks and GitHub publishing:

```cmd
release.bat
```
Or with arguments:
```cmd
release.bat 1.2.0 "Release notes summary"
```

The script automatically:
1. Prompts for the new version and updates `qgis2ge/metadata.txt` and `README.md`.
2. Runs all 14 headless PyQGIS unit tests (`test_exporter.py`).
3. Packages a clean `qgis2ge.zip` and syncs to your local QGIS plugins directory.
4. Sets Git identity to `iitold` (`doancongthanh92@gmail.com`).
5. Commits, tags (`vX.Y.Z`), and pushes to GitHub.
6. Triggers GitHub Actions CI/CD to build and publish the release asset automatically.

---

## 🧪 Running Automated Tests

Run the headless PyQGIS test suite:
```cmd
cmd /c call "C:\Program Files\QGIS 3.40.12\bin\python-qgis-ltr.bat" -m unittest qgis2ge.tests.test_exporter
```

All 14 tests pass (`OK` in ~0.95s).

---

## 📄 License
GNU General Public License v2.0 or later (GPL-2.0-or-later).  
Created by **[iitold](https://github.com/iitold)** • [doancongthanh92@gmail.com](mailto:doancongthanh92@gmail.com).
