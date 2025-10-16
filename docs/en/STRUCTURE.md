# PyCraft Project Structure

This document describes the modular organization of the PyCraft project, designed to maintain clean, scalable, and maintainable code.

## Folder Structure

```
PyCraft/
├── main.py                    # Application entry point
├── docs/                      # Project documentation
│   ├── en/                    # English documentation
│   └── es/                    # Spanish documentation
├── src/                       # Main source code
│   ├── core/                  # Core business logic
│   │   ├── api/              # External API handling
│   │   │   ├── handlers.py   # MinecraftAPI, ModrinthAPI, CurseForgeAPI
│   │   │   └── __init__.py
│   │   ├── download/         # Download system
│   │   │   ├── downloader.py # ServerDownloader
│   │   │   └── __init__.py
│   │   └── config/           # Application configuration
│   │       └── __init__.py
│   │
│   ├── managers/             # Resource managers
│   │   ├── java/            # Java management
│   │   │   ├── java_manager.py
│   │   │   └── __init__.py
│   │   ├── server/          # Server management
│   │   │   ├── server_manager.py
│   │   │   └── __init__.py
│   │   ├── modpack/         # Modpack management
│   │   │   ├── modpack_manager.py
│   │   │   └── __init__.py
│   │   └── loader/          # Loader management (Forge/Fabric)
│   │       ├── loader_manager.py
│   │       └── __init__.py
│   │
│   ├── gui/                 # Graphical interface
│   │   ├── tabs/           # GUI tabs
│   │   │   ├── base_tab.py       # Base class with common utilities
│   │   │   ├── info_tab.py       # Information tab
│   │   │   └── __init__.py
│   │   ├── utils/          # GUI utilities
│   │   │   ├── logger.py         # LoggerMixin for logging
│   │   │   ├── widgets.py        # WidgetFactory for widgets
│   │   │   └── __init__.py
│   │   ├── main_window.py  # Main window
│   │   └── __init__.py
│   │
│   └── utils/              # Common utilities
│       └── __init__.py
```

## Design Principles

### 1. Separation of Concerns
Each folder has a specific and clear purpose:

- **core/**: Business logic independent of the UI
- **managers/**: Specialized managers for specific resources
- **gui/**: Everything related to the graphical interface
- **utils/**: Reusable utility functions and classes

### 2. Explicit Modules
Folder and file names are descriptive:
- `core/api/handlers.py` → Handles external APIs
- `managers/server/server_manager.py` → Manages servers
- `gui/tabs/info_tab.py` → Information tab

### 3. Clean Imports
Thanks to `__init__.py` files, imports are concise:

```python
# Before
from src.api_handler import MinecraftAPIHandler

# Now
from src.core.api import MinecraftAPIHandler
```

### 4. Code Reusability
- `base_tab.py` contains common utilities for all tabs
- `LoggerMixin` centralizes log handling
- `WidgetFactory` standardizes widget creation
- Centralized color palette

## Main Components

### Core (src/core/)

**API Handlers** (`core/api/handlers.py`)
- `MinecraftAPIHandler`: Communication with Mojang APIs
- `ModrinthAPI`: Search and install modpacks from Modrinth
- `CurseForgeAPI`: Reserved for future implementation
- `APIConfig`: API key configuration management

**Downloader** (`core/download/downloader.py`)
- `ServerDownloader`: File download system with progress tracking

### Managers (src/managers/)

**JavaManager** (`managers/java/`)
- Detection of Java installations
- Automatic download of required versions
- Version validation

**ServerManager** (`managers/server/`)
- Server creation and configuration
- Process start and stop
- Send commands to server

**ModpackManager** (`managers/modpack/`)
- Install modpacks from .mrpack files
- Automatic loader configuration
- Download mods and dependencies

**LoaderManager** (`managers/loader/`)
- Loader type detection (Forge/Fabric)
- Loader installation
- Type-specific configuration

### GUI (src/gui/)

**MainWindow** (`gui/main_window.py`)
- Main application window
- Tab management (Vanilla, Mods, Info)
- Orchestration of all components

**Tabs** (`gui/tabs/`)
- `BaseTab`: Base class with common utilities
- `InfoTab`: Information and help

**Utils** (`gui/utils/`)
- `LoggerMixin`: Unified log handling with colors
- `WidgetFactory`: Standardized widget creation

## Implemented Improvements

### Modularization
- **Before**: 1 file with 2768 lines (`gui.py`)
- **Now**: Code distributed across specialized modules
- Optimized and maintainable main file

### Clear Organization
- Folders with explanatory names
- Easy to locate specific functionality
- Scalable structure for future features

### Maintainability
- Easier to understand code
- Changes isolated to specific modules
- Reduced coupling

### Quality Standards
- Module documentation in each `__init__.py`
- Consistent relative imports
- Enterprise-level professional structure
- Type hints and docstrings
- PEP 8 compliance

## Usage Guide

### Adding New Functionality

**To add a new manager:**
1. Create folder in `src/managers/new_manager/`
2. Create `new_manager.py` with the class
3. Export in `__init__.py`

```python
# src/managers/new_manager/__init__.py
"""New Manager - Brief description."""

from .new_manager import NewManager

__all__ = ["NewManager"]
```

**To add a new tab:**
1. Create file in `src/gui/tabs/new_tab.py`
2. Inherit from `BaseTab`
3. Import in `main_window.py`

```python
from .tabs.base_tab import BaseTab

class NewTab(BaseTab):
    """New tab with specific functionality."""

    def __init__(self, parent):
        super().__init__(parent)
        self.create_widgets()
```

### Importing Modules

```python
# API handlers
from src.core.api import MinecraftAPIHandler, ModrinthAPI

# Managers
from src.managers.server import ServerManager
from src.managers.modpack import ModpackManager

# GUI components
from src.gui.tabs.info_tab import InfoTab
from src.gui.utils import LoggerMixin, WidgetFactory
```

## Design Patterns Used

### Mixin Pattern
`LoggerMixin` provides reusable logging functionality:

```python
class MyClass(LoggerMixin):
    def my_method(self):
        self.add_log(self.log_textbox, "Message", "info")
```

### Factory Pattern
`WidgetFactory` standardizes widget creation:

```python
button = WidgetFactory.create_button(
    parent=self,
    text="Click",
    style="primary"
)
```

### Manager Pattern
Each resource has its dedicated manager that encapsulates all its logic.

## Benefits

1. **Scalability**: Easy to add new features without affecting existing code
2. **Debugging**: Easier to locate and fix errors
3. **Testing**: Ability to create unit tests per module
4. **Collaboration**: Multiple developers can work simultaneously
5. **Documentation**: The structure itself documents the architecture

## Suggested Next Steps

- Extract individual tabs from `main_window.py`
- Create `utils/validators.py` module for common validations
- Add unit tests per module
- Document public API of each manager
- Implement structured logging
- Add internationalization (i18n)

## Additional Documentation

- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)
- **License**: See [LICENSE](../../LICENSE)
- **README**: See [README](../../README.md)

---

**Version**: 2.0
**Date**: October 2025
**Status**: Modular structure implemented and functional
