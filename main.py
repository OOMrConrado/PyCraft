"""
PyCraft - Minecraft Server Manager
Application to download, configure and start Minecraft servers easily
"""

from src.gui import PyCraftGUI


def main():
    """Application entry point"""
    app = PyCraftGUI()
    app.run()


if __name__ == "__main__":
    main()
