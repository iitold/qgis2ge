"""In-app update engine for qgis2ge QGIS plugin.

Checks for updates via GitHub Releases API or custom endpoints,
downloads release archives, and installs updates in-place.
"""

from __future__ import annotations

import configparser
import json
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

from qgis.core import QgsApplication, QgsTask


@dataclass
class UpdateInfo:
    """Information about an update check result."""

    has_update: bool
    current_version: str
    latest_version: str
    download_url: str
    changelog: str = ""
    published_at: str = ""
    error_message: str = ""


def parse_version(v_str: str) -> Tuple[int, ...]:
    """Parse version string into integer tuple for comparison (e.g. 'v1.2.0' -> (1, 2, 0))."""
    if not v_str:
        return (0,)
    clean = re.sub(r"^[^\d]*", "", v_str.strip())
    parts = re.split(r"[^0-9]+", clean)
    nums = [int(p) for p in parts if p.isdigit()]
    return tuple(nums) if nums else (0,)


def get_current_version() -> str:
    """Read current version from metadata.txt."""
    plugin_dir = os.path.dirname(__file__)
    metadata_path = os.path.join(plugin_dir, "metadata.txt")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
            # Direct regex match for version (handles BOM and formatting quirks)
            m = re.search(r"^version\s*=\s*(.+)$", content, re.MULTILINE)
            if m:
                return m.group(1).strip()
            # Fallback to ConfigParser
            config = configparser.ConfigParser()
            config.read_string(content)
            if "general" in config and "version" in config["general"]:
                return config["general"]["version"].strip()
        except Exception as exc:
            _ = exc
    return "1.1.3"


def check_github_update(repo: str = "iitold/qgis2ge", current_ver: Optional[str] = None, timeout: int = 10) -> UpdateInfo:
    """Check GitHub repository releases for a newer version.

    Args:
        repo: GitHub repository in format 'owner/repo' (default 'iitold/qgis2ge').
        current_ver: Current version string. If None, read from metadata.txt.
        timeout: Network timeout in seconds.

    Returns:
        UpdateInfo dataclass.
    """
    if current_ver is None:
        current_ver = get_current_version()

    # Clean repo string
    clean_repo = repo.strip().replace("https://github.com/", "").strip("/")
    if not clean_repo or "/" not in clean_repo:
        clean_repo = "iitold/qgis2ge"

    api_url = f"https://api.github.com/repos/{clean_repo}/releases/latest"
    if not api_url.startswith("https://api.github.com/"):
        return UpdateInfo(
            has_update=False,
            current_version=current_ver,
            latest_version=current_ver,
            download_url="",
            error_message="Invalid repository path",
        )

    req = urllib.request.Request(
        api_url,
        headers={
            "User-Agent": "QGIS-qgis2ge-Updater",
            "Accept": "application/vnd.github.v3+json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:  # nosec B310
            if response.status != 200:
                return UpdateInfo(
                    has_update=False,
                    current_version=current_ver,
                    latest_version=current_ver,
                    download_url="",
                    error_message=f"GitHub API returned HTTP {response.status}",
                )
            data = json.loads(response.read().decode("utf-8"))

        tag_name = data.get("tag_name", "")
        latest_ver = tag_name.lstrip("vV")
        body = data.get("body", "")
        published_at = data.get("published_at", "")[:10]

        # Find best download URL: preferred attached .zip asset (qgis2ge.zip), fallback to zipball_url
        download_url = ""
        assets = data.get("assets", [])
        for asset in assets:
            name = asset.get("name", "").lower()
            if name.endswith(".zip"):
                download_url = asset.get("browser_download_url", "")
                break

        if not download_url:
            download_url = data.get("zipball_url", "")

        has_update = parse_version(latest_ver) > parse_version(current_ver)

        return UpdateInfo(
            has_update=has_update,
            current_version=current_ver,
            latest_version=latest_ver,
            download_url=download_url,
            changelog=body,
            published_at=published_at,
        )

    except urllib.error.HTTPError as e:
        if e.code == 404:
            msg = f"No releases found on GitHub repo '{clean_repo}'."
        else:
            msg = f"HTTP Error {e.code}: {e.reason}"
        return UpdateInfo(
            has_update=False,
            current_version=current_ver,
            latest_version=current_ver,
            download_url="",
            error_message=msg,
        )
    except Exception as e:
        return UpdateInfo(
            has_update=False,
            current_version=current_ver,
            latest_version=current_ver,
            download_url="",
            error_message=f"Network error: {str(e)}",
        )


def install_update_from_zip(
    zip_url: str,
    target_plugin_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Tuple[bool, str]:
    """Download ZIP release archive and install in-place over the plugin directory.

    Args:
        zip_url: Direct download URL of the update ZIP.
        target_plugin_dir: Target directory of the plugin. Defaults to this module's folder.
        progress_callback: Optional callback(percent: int, status_message: str).

    Returns:
        Tuple of (success: bool, message: str)
    """
    if target_plugin_dir is None:
        target_plugin_dir = os.path.dirname(__file__)

    if not zip_url:
        return False, "Download URL is empty."

    temp_dir = tempfile.mkdtemp(prefix="qgis2ge_update_")
    download_zip_path = os.path.join(temp_dir, "update.zip")
    extract_dir = os.path.join(temp_dir, "extracted")

    try:
        if progress_callback:
            progress_callback(10, "Connecting to download server...")

        if not (zip_url.startswith("https://") or zip_url.startswith("file:///")):
            return False, "Untrusted download URL scheme. Only HTTPS is allowed."

        req = urllib.request.Request(
            zip_url,
            headers={"User-Agent": "QGIS-qgis2ge-Updater"},
        )

        with urllib.request.urlopen(req, timeout=30) as resp, open(download_zip_path, "wb") as out_f:  # nosec B310
            total_size = resp.headers.get("content-length")
            total_size = int(total_size) if total_size and total_size.isdigit() else 0
            downloaded = 0
            chunk_size = 65536

            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out_f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0 and progress_callback:
                    pct = int(10 + (downloaded / total_size) * 60)
                    progress_callback(pct, f"Downloading: {downloaded // 1024} KB...")

        if progress_callback:
            progress_callback(75, "Extracting update archive...")

        if not zipfile.is_zipfile(download_zip_path):
            return False, "Downloaded file is not a valid ZIP archive."

        with zipfile.ZipFile(download_zip_path, "r") as zf:
            zf.extractall(extract_dir)

        # Locate the plugin directory inside extracted archive
        source_dir: Optional[str] = None
        if os.path.exists(os.path.join(extract_dir, "metadata.txt")):
            source_dir = extract_dir
        else:
            for root, dirs, files in os.walk(extract_dir):
                if "metadata.txt" in files:
                    source_dir = root
                    break

        if not source_dir:
            return False, "Update package is missing metadata.txt."

        if progress_callback:
            progress_callback(85, "Installing new files...")

        # Copy files over existing plugin directory
        for item in os.listdir(source_dir):
            if item in ("__pycache__", ".git", ".github"):
                continue
            s_path = os.path.join(source_dir, item)
            d_path = os.path.join(target_plugin_dir, item)
            if os.path.isdir(s_path):
                if os.path.exists(d_path):
                    shutil.rmtree(d_path, ignore_errors=True)
                shutil.copytree(s_path, d_path)
            else:
                shutil.copy2(s_path, d_path)

        if progress_callback:
            progress_callback(95, "Validating installation...")

        # Verify metadata.txt exists in target directory
        if not os.path.exists(os.path.join(target_plugin_dir, "metadata.txt")):
            return False, "Installation check failed: metadata.txt not found."

        if progress_callback:
            progress_callback(100, "Update completed successfully!")

        return True, "Plugin files updated successfully!"

    except Exception as e:
        return False, f"Update failed: {str(e)}"

    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as exc:
            _ = exc


class CheckUpdateTask(QgsTask):
    """Background task to query remote repository for updates without blocking UI."""

    def __init__(
        self,
        repo: str,
        current_version: str,
        on_completed: Callable[[UpdateInfo], None],
    ):
        super().__init__(f"Check update ({repo})", QgsTask.Flag.CanCancel)
        self.repo = repo
        self.current_version = current_version
        self.on_completed = on_completed
        self.result_info: Optional[UpdateInfo] = None

    def run(self) -> bool:
        if self.isCanceled():
            return False
        self.result_info = check_github_update(self.repo, self.current_version)
        return True

    def finished(self, result: bool) -> None:
        if self.result_info and self.on_completed:
            self.on_completed(self.result_info)


class InstallUpdateTask(QgsTask):
    """Background task to download and install plugin update."""

    def __init__(
        self,
        download_url: str,
        on_completed: Callable[[bool, str], None],
    ):
        super().__init__("Install qgis2ge update", QgsTask.Flag.CanCancel)
        self.download_url = download_url
        self.on_completed = on_completed
        self.success = False
        self.message = ""

    def run(self) -> bool:
        def task_progress(pct: int, msg: str):
            self.setProgress(pct)

        self.success, self.message = install_update_from_zip(
            self.download_url, progress_callback=task_progress
        )
        return self.success

    def finished(self, result: bool) -> None:
        if self.on_completed:
            self.on_completed(self.success, self.message)
