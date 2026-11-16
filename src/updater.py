"""Update OklyPlay from its GitHub releases.

Only the portable exe can replace itself. Running from source, the check still
reports a newer version, but installing is left to git.

The swap works around Windows refusing to overwrite a running exe: the running
file is renamed to OklyPlay.old.exe (allowed while it runs), the download takes
its name, the new exe is started and this one exits. The next start deletes the
.old file."""

import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import urllib.request

from version import __version__

logger = logging.getLogger(__name__)

REPO = "OlegTheSnowman/OklyPlay"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
ASSET_NAME = "OklyPlay.exe"
TIMEOUT = 15


class UpdateError(Exception):
    pass


def parse_version(text):
    """'v1.2.10' -> (1, 2, 10). Anything that is not numbers counts as 0."""
    parts = re.findall(r"\d+", text or "")[:3]
    return tuple(int(p) for p in parts) + (0,) * (3 - len(parts))


def is_newer(remote, local=__version__):
    return parse_version(remote) > parse_version(local)


def is_frozen():
    """True when running as the PyInstaller exe, the only form that can self-update."""
    return bool(getattr(sys, "frozen", False))


def _get(url, accept="application/vnd.github+json"):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": f"OklyPlay/{__version__}"})
    return urllib.request.urlopen(req, timeout=TIMEOUT)


def fetch_latest():
    """Ask GitHub for the latest release. Returns a dict with version, notes, page,
    and the exe's download url, size and sha256 (None when GitHub gives none)."""
    try:
        with _get(LATEST_URL) as resp:
            data = json.load(resp)
    except Exception as e:
        raise UpdateError(f"Could not reach GitHub: {e}") from e
    asset = next((a for a in data.get("assets", []) if a.get("name") == ASSET_NAME), None)
    digest = (asset or {}).get("digest") or ""
    return {
        "version": data.get("tag_name", "").lstrip("v"),
        # Release notes are Markdown; drop heading marks so "### Fixed" reads as "Fixed"
        "notes": re.sub(r"(?m)^#+\s*", "", data.get("body") or "").strip(),
        "page": data.get("html_url") or RELEASES_PAGE,
        "url": asset.get("browser_download_url") if asset else None,
        "size": asset.get("size") if asset else None,
        "sha256": digest.split(":", 1)[1].lower() if digest.startswith("sha256:") else None,
    }


def download(release, dest, progress=None):
    """Download the release exe to dest, checking size and SHA-256.

    progress(done_bytes, total_bytes) is called as data arrives; if it returns
    False the download stops and UpdateError is raised. A partial or bad file
    is deleted."""
    if not release.get("url"):
        raise UpdateError("This release has no OklyPlay.exe to download.")
    total = release.get("size") or 0
    sha = hashlib.sha256()
    done = 0
    try:
        with _get(release["url"], accept="application/octet-stream") as resp, open(dest, "wb") as f:
            total = total or int(resp.headers.get("Content-Length") or 0)
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                sha.update(chunk)
                done += len(chunk)
                if progress and progress(done, total) is False:
                    raise UpdateError("Download cancelled.")
        if total and done != total:
            raise UpdateError(f"Download incomplete: got {done} of {total} bytes.")
        if release.get("sha256") and sha.hexdigest() != release["sha256"]:
            raise UpdateError("The downloaded file is damaged (checksum mismatch).")
    except UpdateError:
        _remove(dest)
        raise
    except Exception as e:
        _remove(dest)
        raise UpdateError(f"Download failed: {e}") from e


def install_and_restart(new_exe):
    """Swap the running exe for new_exe and start it. The caller must exit right after."""
    current = sys.executable
    old = os.path.splitext(current)[0] + ".old.exe"
    _remove(old)
    os.replace(current, old)
    try:
        os.replace(new_exe, current)
    except Exception:
        os.replace(old, current)  # put the working exe back
        raise
    subprocess.Popen([current], close_fds=True)


def cleanup_old_exe():
    """Delete the .old.exe left behind by the previous update, if any."""
    if is_frozen():
        _remove(os.path.splitext(sys.executable)[0] + ".old.exe")


def download_path():
    """Where the new exe is downloaded: next to the running one, so the final
    rename stays on one drive."""
    return os.path.splitext(sys.executable)[0] + ".new.exe"


def _remove(path):
    try:
        os.remove(path)
    except OSError:
        pass
