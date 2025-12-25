"""Application update checker and downloader"""

import os
import sys
import subprocess
import tempfile
import requests
import webbrowser
from typing import Optional, Dict, Any, Callable
from packaging import version
from pathlib import Path


class UpdateChecker:
    """Checks for application updates from GitHub releases"""

    def __init__(self, current_version: str, repo_owner: str = "OOMrConrado", repo_name: str = "PyCraft"):
        self.current_version = current_version
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

    def check_for_updates(self) -> Optional[Dict[str, Any]]:
        """
        Check if a newer version is available

        Returns:
            Dict with update info if available, None otherwise
            {
                'version': str,
                'download_url': str,
                'release_notes': str,
                'published_at': str
            }
        """
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()

            release_data = response.json()
            latest_version = release_data.get('tag_name', '').lstrip('v')

            if not latest_version:
                return None

            # Compare versions
            if version.parse(latest_version) > version.parse(self.current_version):
                # Find installer .exe asset (Inno Setup)
                download_url = None
                asset_name = None
                file_size = 0

                for asset in release_data.get('assets', []):
                    if asset['name'].startswith('PyCraft-Setup') and asset['name'].endswith('.exe'):
                        download_url = asset['browser_download_url']
                        asset_name = asset['name']
                        file_size = asset.get('size', 0)
                        break

                # Fallback to release page if no installer found
                if not download_url:
                    download_url = release_data.get('html_url')

                return {
                    'version': latest_version,
                    'download_url': download_url,
                    'asset_name': asset_name,
                    'file_size': file_size,
                    'release_notes': release_data.get('body', 'No release notes available'),
                    'published_at': release_data.get('published_at', '')
                }

            return None

        except requests.exceptions.RequestException:
            # Network error or API error
            return None
        except Exception:
            # Any other error
            return None

    def open_download_page(self, url: str):
        """Open the download page in the default browser"""
        webbrowser.open(url)

    def download_update(self, download_url: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> Optional[str]:
        """
        Download the update installer to a temporary location

        Args:
            download_url: URL to download the installer from
            progress_callback: Optional callback function(downloaded_bytes, total_bytes)

        Returns:
            Path to downloaded installer file, or None if download failed
        """
        try:
            # Create temp directory for download
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, f"PyCraft-Update-{self.current_version}.exe")

            # Download with streaming to show progress
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(installer_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # Call progress callback
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded_size, total_size)

            return installer_path

        except Exception as e:
            print(f"Download failed: {e}")
            return None

    def install_update(self, installer_path: str, silent: bool = True) -> bool:
        """
        Install the downloaded update

        Args:
            installer_path: Path to the installer executable
            silent: If True, install silently without user interaction

        Returns:
            True if installation started successfully, False otherwise
        """
        try:
            if not os.path.exists(installer_path):
                return False

            # Build installer command
            # /SILENT = silent mode, no UI
            # /SUPPRESSMSGBOXES = suppress message boxes
            # /NORESTART = don't restart computer
            # /CLOSEAPPLICATIONS = close running PyCraft instance
            cmd = [installer_path]

            if silent:
                cmd.extend(['/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CLOSEAPPLICATIONS'])

            # Start installer in detached process
            # The installer will close this application and install the update
            subprocess.Popen(
                cmd,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True
            )

            # Give installer time to start
            import time
            time.sleep(1)

            # Exit the current application to allow update
            # The installer will handle closing the app if it's still running
            sys.exit(0)

        except Exception as e:
            print(f"Installation failed: {e}")
            return False

    def cleanup_temp_installers(self):
        """Clean up any old installer files from temp directory"""
        try:
            temp_dir = tempfile.gettempdir()
            for file in Path(temp_dir).glob("PyCraft-Update-*.exe"):
                try:
                    file.unlink()
                except Exception:
                    pass  # Ignore errors, file might be in use
        except Exception:
            pass
