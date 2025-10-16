# PyCraft - Minecraft Server Manager

[Español](README.es.md) | **English**

**An intuitive tool to create and manage Minecraft vanilla and modded servers**

PyCraft simplifies the creation of Minecraft servers, allowing you to download, configure, and launch vanilla or modded servers automatically. With support for Forge, Fabric, and integrated Modrinth modpack search.

---

## Features

- **Vanilla Servers**: Create Minecraft vanilla servers with one click
- **Modpacks**: Search and install modpacks directly from Modrinth
- **Automatic Configuration**: EULA accepted and server.properties configured automatically
- **Loaders**: Support for Forge and Fabric
- **Java**: Automatic Java verification and installation
- **Complete Management**: Start, stop, and send commands to your servers
- **Intuitive Interface**: Modern GUI with customtkinter

---

## Installation

### Prerequisites
- **Python 3.8+** installed
- **Java 17+** (or the version will be installed automatically)
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
2. Go to the **"Vanilla Server"** tab
3. Select **"Create New Server"**
4. Search and select a Minecraft version
5. Choose a destination folder
6. Click **"Download and Install Server"**
7. Once completed, click **"Start Server"**

### Install a Modpack

1. Go to the **"Modded Server"** tab
2. Select **"Modpack Installation"**
3. Search for your favorite modpack (e.g., "Create", "ATM9")
4. Select the modpack and version
5. Choose a destination folder
6. Click **"Install Modpack"**
7. PyCraft will download and install everything automatically

### Manage a Modded Server

1. In **"Modded Server"**, select **"Server Management"**
2. Choose the server folder
3. PyCraft will automatically detect the type (Forge/Fabric)
4. Click **"Start Server"**

---

## Technologies

- **Python 3.x**
- **CustomTkinter** - Modern graphical interface
- **Requests** - API communication
- **Threading** - Asynchronous execution

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
│   │   ├── api/       # APIs (Minecraft, Modrinth)
│   │   └── download/  # Download system
│   ├── managers/      # Resource managers
│   │   ├── java/      # Java management
│   │   ├── server/    # Minecraft servers
│   │   ├── modpack/   # Modpack installation
│   │   └── loader/    # Forge and Fabric
│   └── gui/           # Graphical interface
│       ├── tabs/      # Modular tabs
│       └── utils/     # GUI utilities
```

For detailed architecture information, see [docs/en/STRUCTURE.md](docs/en/STRUCTURE.md)

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
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - For the GUI library
