"""
PyCraft - Minecraft Server Manager
Aplicación para descargar, configurar e iniciar servidores de Minecraft fácilmente
"""

from src.gui import PyCraftGUI


def main():
    """Punto de entrada de la aplicación"""
    app = PyCraftGUI()
    app.run()


if __name__ == "__main__":
    main()
