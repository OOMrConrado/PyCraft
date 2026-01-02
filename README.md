# PyCraft - Minecraft Server Manager

[Español](README.es.md) | **English**

**An intuitive tool to create and manage Minecraft vanilla and modded servers**

PyCraft simplifies the creation of Minecraft servers, allowing you to download, configure, and launch vanilla or modded servers automatically. With support for Forge, Fabric, NeoForge, Quilt, and integrated Modrinth modpack search.

---

## Features

### Server Management
- **Vanilla Servers**: Create Minecraft vanilla servers with one click
- **Modded Servers**: Install and manage modded servers with Forge, Fabric, NeoForge, or Quilt
- **Modpack Installation**: Search and install server modpacks directly from Modrinth and CurseForge
- **Client Modpacks**: Browse and find modpacks for your Minecraft launcher
- **Automatic Configuration**: EULA accepted and server.properties configured automatically
- **Quick Restart**: Server state maintained after stop/crash for instant restart

### Interface
- **Modern UI**: Clean interface built with PySide6 (Qt framework)
- **Organized Sidebar**: Easy navigation with dedicated sections for:
  - Home
  - Vanilla Server
  - Modded Server
  - Client Modpacks
  - Management (Java & Modpacks)
  - Settings
- **Real-time Console**: 500-line console with syntax highlighting
- **Quick Links**: Direct access to GitHub, Modrinth, CurseForge

### Advanced Features
- **Java Management**: Automatic Java detection and installation with version compatibility
- **Crash Detection**: Automatic crash detection with direct access to logs and crash reports
- **Config Editor**: Built-in server.properties editor (enabled after first run)
- **Visual Feedback**: Button animations and status indicators
- **Thread-safe Operations**: Reliable server management with proper threading

---

## Installation

### Prerequisites
- **Python 3.8+** installed
- **Java 17+** (or will be installed automatically)
- **Windows 10/11** (Linux and macOS compatible)

### Installation Steps

1. **Clone the repository:**
```bash
git clone https://github.com/OOMrConrado/PyCraft.git
cd PyCraft
```

2. **Create a virtual environment:**
```bash
python -m venv .venv
.venv\Scripts\activate  # On Windows
source .venv/bin/activate  # On Linux/macOS
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the application:**
```bash
python main.py
```

---

## Quick Start

### Create a Vanilla Server

1. Open PyCraft
2. Go to **"Vanilla Server"** in the sidebar
3. Select **"Create New Server"**
4. Search and select a Minecraft version
5. Choose a destination folder
6. Click **"Download and Install Server"**
7. Once completed, click **"Start Server"**
8. Server will generate `server.properties` on first run
9. Use **"Config"** button to customize server settings

### Install a Server Modpack

1. Go to **"Modded Server"** in the sidebar
2. Select **"Install Server"**
3. Search for your favorite modpack (e.g., "Create", "ATM9")
4. Select the modpack and version
5. Choose a destination folder
6. Click **"Install Modpack"**
7. PyCraft will download and configure everything automatically
8. Click **"Start Server"** when ready

### Manage an Existing Server

1. In **"Modded Server"**, select **"Run Server"**
2. Choose the server folder
3. PyCraft will automatically detect the type (Forge/Fabric/NeoForge/Quilt)
4. Click **"Start Server"**
5. Send commands through the console
6. Use **"Config"** to edit server properties (after first run)

### Browse Client Modpacks

1. Go to **"Client Modpacks"** in the sidebar
2. Choose provider (Modrinth or CurseForge)
3. Search for a modpack
4. Click **"Open"** to visit the modpack page
5. Download and install through the official launcher (CurseForge App or Modrinth)

---

## Technologies

- **Python 3.x**
- **PySide6** - Modern Qt-based GUI framework
- **QtAwesome** - Icon library for beautiful interface
- **Requests** - API communication
- **Threading** - Asynchronous operations for smooth UI

---

## Project Structure

```
PyCraft/
├── main.py              # Entry point
├── docs/                # Documentation
│   ├── en/             # English docs
│   └── es/             # Spanish docs
├── src/
│   ├── core/           # Business logic
│   │   ├── api.py      # API handlers (Minecraft, Modrinth)
│   │   └── download.py # Download system
│   ├── managers/       # Resource managers
│   │   ├── java/       # Java detection & installation
│   │   ├── server/     # Server management
│   │   └── modpack/    # Modpack installation
│   ├── gui/            # Graphical interface
│   │   └── main_window.py  # Main UI
│   └── utils/          # Utilities
└── PyCraft-Files/      # Assets (logo, icons)
```

For detailed architecture information, see [docs/en/STRUCTURE.md](docs/en/STRUCTURE.md)

---

## Interface Overview

### Sidebar Navigation
- **Home**: Welcome page with quick links
- **Vanilla Server**: Create and manage vanilla servers
- **Modded Server**: Install and run modded servers
- **Client Modpacks**: Install modpacks for your launcher
- **Management Section**:
  - **Java**: Manage Java installations
  - **Modpacks**: View and manage installed client modpacks
- **Settings**: Application settings and information

### Console Features
- Real-time server output
- Syntax highlighting (errors, warnings, info)
- 500-line buffer for complete logs
- Command input with `/` prefix
- Visual feedback on command send

### Crash Handling
- Automatic crash detection
- Modal dialog with crash information
- Direct links to:
  - Server logs folder
  - Crash reports folder
- Server ready to restart immediately

---

## Contributing

Contributions are welcome! Please read [docs/en/CONTRIBUTING.md](docs/en/CONTRIBUTING.md) for details on the process and code of conduct.

### Steps to Contribute

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## License

This project is under the MIT License. See [LICENSE](LICENSE) for more details.

---

## Author

**Conrado Gómez**
- GitHub: [@OOMrConrado](https://github.com/OOMrConrado)
- Email: conradogomez556@gmail.com

---

## Acknowledgments

- [Mojang](https://www.minecraft.net/) - For Minecraft
- [Modrinth](https://modrinth.com/) - For their excellent modpack API
- [CurseForge](https://www.curseforge.com/) - For their modpack platform and API
- [PySide6](https://www.qt.io/qt-for-python) - For the Qt framework
- [QtAwesome](https://github.com/spyder-ide/qtawesome) - For the icon library
