"""Application update checker and downloader"""

import requests
import webbrowser
from typing import Optional, Dict, Any
from packaging import version


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
                # Find MSI asset
                download_url = None
                for asset in release_data.get('assets', []):
                    if asset['name'].endswith('.msi'):
                        download_url = asset['browser_download_url']
                        break

                # Fallback to release page if no MSI found
                if not download_url:
                    download_url = release_data.get('html_url')

                return {
                    'version': latest_version,
                    'download_url': download_url,
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
