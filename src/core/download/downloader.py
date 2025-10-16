import requests
import os
from typing import Optional, Callable


class ServerDownloader:
    """Handles Minecraft server.jar download"""

    def __init__(self):
        self.download_progress = 0
        # Create persistent session for better performance
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PyCraft/1.0',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })

    def download_server(
        self,
        url: str,
        destination_folder: str,
        version_id: str,
        progress_callback: Optional[Callable[[int], None]] = None,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Downloads server.jar from the provided URL with automatic retries

        Args:
            url: server.jar URL
            destination_folder: Folder where the server will be saved
            version_id: Version ID to name the file
            progress_callback: Callback function to update progress (0-100)
            max_retries: Maximum number of retries (default 3)

        Returns:
            Full path of downloaded file or None if error
        """
        import time

        # Create folder if it doesn't exist
        try:
            os.makedirs(destination_folder, exist_ok=True)
        except PermissionError as e:
            print(f"Permission error creating folder: {e}")
            return None

        # File name
        file_name = "server.jar"
        file_path = os.path.join(destination_folder, file_name)

        # Attempt download with retries
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"\nRetrying download (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(2)  # Wait before retrying

                # Perform download with persistent session
                response = self.session.get(url, stream=True, timeout=60)
                response.raise_for_status()

                # Get total size
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                last_progress = 0

                # Use 1 MB chunk size for much faster download
                chunk_size = 1024 * 1024  # 1 MB

                # Write file in large blocks with optimized buffer
                with open(file_path, 'wb', buffering=chunk_size * 2) as file:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            file.write(chunk)
                            downloaded_size += len(chunk)

                            # Update progress only when it changes (reduces overhead)
                            if total_size > 0 and progress_callback:
                                progress = int((downloaded_size / total_size) * 100)
                                if progress != last_progress:
                                    self.download_progress = progress
                                    progress_callback(progress)
                                    last_progress = progress

                # Validate complete download
                if total_size > 0:
                    actual_size = os.path.getsize(file_path)
                    if actual_size < total_size * 0.95:  # Allow 5% margin
                        print(f"Incomplete download: {actual_size}/{total_size} bytes")
                        if attempt < max_retries - 1:
                            continue  # Retry
                        else:
                            print("Incomplete download after all retries")
                            return None

                # Ensure progress reaches 100%
                if progress_callback:
                    progress_callback(100)

                print(f"Download completed: {file_path}")
                return file_path

            except requests.Timeout:
                print(f"\nTimeout during download (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    continue
                else:
                    print("Retries exhausted due to timeout")
                    return None

            except requests.RequestException as e:
                print(f"\nNetwork error: {str(e)}")
                if attempt < max_retries - 1:
                    continue
                else:
                    print("Retries exhausted")
                    return None

            except PermissionError as e:
                print(f"\nPermission error writing file: {e}")
                return None  # Don't retry permission errors

            except Exception as e:
                print(f"\nUnexpected error downloading: {str(e)} ({type(e).__name__})")
                if attempt < max_retries - 1:
                    continue
                else:
                    return None

        return None

    def verify_file_exists(self, file_path: str) -> bool:
        """Verifies if the file exists"""
        return os.path.exists(file_path) and os.path.isfile(file_path)
