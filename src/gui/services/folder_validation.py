"""
Folder Validation Service.
Validates folder selections for server operations.
"""

import os
from pathlib import Path
from typing import Tuple


class FolderValidator:
    """Validates folder selections for server operations"""

    # Dangerous folder names (case-insensitive)
    DANGEROUS_NAMES = {
        "downloads": "Downloads folder",
        "descargas": "Downloads folder",
        "desktop": "Desktop",
        "escritorio": "Desktop",
        "documents": "Documents folder",
        "documentos": "Documents folder",
        "my documents": "Documents folder",
        "mis documentos": "Documents folder",
        "program files": "Program Files",
        "program files (x86)": "Program Files",
        "archivos de programa": "Program Files",
        "windows": "Windows system folder",
        "system32": "Windows system folder",
        "users": "Users folder",
        "appdata": "AppData folder",
    }

    # System folders that should not contain servers
    SYSTEM_FOLDERS = ["program files", "program files (x86)", "windows", "system32"]

    @staticmethod
    def is_dangerous_folder(folder_path: str) -> Tuple[bool, str]:
        """
        Check if a folder is a dangerous/important system location.

        Args:
            folder_path: Path to check

        Returns:
            Tuple of (is_dangerous, warning_message)
        """
        if not folder_path:
            return False, ""

        path = Path(folder_path).resolve()
        path_str = str(path).lower()
        path_name = path.name.lower()

        # Check if it's a drive root (C:\, D:\, etc.)
        if path.parent == path:  # Root of a drive
            return True, "You selected a drive root. This will create server files directly in your drive, which can cause clutter and issues."

        # Check folder name
        if path_name in FolderValidator.DANGEROUS_NAMES:
            location = FolderValidator.DANGEROUS_NAMES[path_name]
            return True, f"You selected your {location}. Creating a Minecraft server here is not recommended as it may cause data loss or clutter."

        # Check if path contains dangerous folders at top level
        for part in path.parts:
            part_lower = part.lower()
            if part_lower in FolderValidator.SYSTEM_FOLDERS:
                return True, f"You selected a folder inside '{part}'. This is a system location and is not recommended for Minecraft servers."

        return False, ""

    @staticmethod
    def is_existing_server(folder_path: str) -> bool:
        """
        Check if folder already contains a Minecraft server.

        Args:
            folder_path: Path to check

        Returns:
            True if server files are detected
        """
        path = Path(folder_path)

        # Check for exact files
        if (path / "server.jar").exists():
            return True
        if (path / "server.properties").exists():
            return True

        # Check for pattern-based files (forge, fabric, paper, spigot)
        for pattern in ["forge-*.jar", "fabric-server-*.jar", "paper-*.jar", "spigot-*.jar"]:
            if list(path.glob(pattern)):
                return True

        return False

    @staticmethod
    def has_server(folder: str) -> bool:
        """
        Check if folder contains a Minecraft server (vanilla or modded).

        More comprehensive check than is_existing_server, also looks for
        modded server structures.

        Args:
            folder: Path to check

        Returns:
            True if any server files are detected
        """
        import glob

        # Check for common server jar patterns
        jar_patterns = [
            "server.jar",
            "forge-*.jar",
            "neoforge-*.jar",
            "fabric-server-*.jar",
            "quilt-server-*.jar",
            "minecraft_server*.jar"
        ]

        for p in jar_patterns:
            if glob.glob(os.path.join(folder, p)):
                return True

        # Check for run scripts (common in modded servers)
        if os.path.exists(os.path.join(folder, "run.bat")) or os.path.exists(os.path.join(folder, "run.sh")):
            return True

        # Check for start scripts
        if os.path.exists(os.path.join(folder, "start.bat")) or os.path.exists(os.path.join(folder, "start.sh")):
            return True

        # Check for startserver scripts (ATM and similar modpacks)
        if os.path.exists(os.path.join(folder, "startserver.bat")) or os.path.exists(os.path.join(folder, "startserver.sh")):
            return True

        # Check for libraries folder with forge/neoforge (modern Forge structure)
        libraries_path = os.path.join(folder, "libraries", "net", "minecraftforge")
        if os.path.exists(libraries_path):
            return True

        neoforge_path = os.path.join(folder, "libraries", "net", "neoforged")
        if os.path.exists(neoforge_path):
            return True

        return False
