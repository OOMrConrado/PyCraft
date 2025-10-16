# Contributing Guide - PyCraft

Thank you for your interest in contributing to PyCraft! This document will guide you through the process.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute](#how-can-i-contribute)
- [Project Structure](#project-structure)
- [Environment Setup](#environment-setup)
- [Development Process](#development-process)
- [Code Standards](#code-standards)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to maintain a respectful and professional environment.

### Our Standards

- Use welcoming and inclusive language
- Respect differing viewpoints
- Accept constructive criticism
- Focus on what is best for the community

## How Can I Contribute

### Reporting Bugs

Bugs are tracked as [GitHub issues](https://github.com/OOMrConrado/PyCraft/issues).

**Before creating an issue:**
- Verify that a similar issue doesn't exist
- Make sure it's actually a bug

**When reporting a bug include:**
- Clear and descriptive title
- Detailed steps to reproduce the problem
- Expected vs actual behavior
- Screenshots if applicable
- Your environment (OS, Python version, etc.)

### Suggesting Enhancements

Suggestions are also tracked as issues.

**Include:**
- Clear description of the enhancement
- Why it would be useful
- Usage examples

### Contributing Code

1. **Fork the repository**
2. **Create a branch** for your feature
3. **Develop** following the standards
4. **Test** your code
5. **Submit** a Pull Request

## Project Structure

```
src/
├── core/              # Business logic
│   ├── api/          # External API communication
│   ├── download/     # Download system
│   └── config/       # Configuration
├── managers/         # Resource managers
│   ├── java/         # Java management
│   ├── server/       # Server management
│   ├── modpack/      # Modpack management
│   └── loader/       # Loader management (Forge/Fabric)
└── gui/              # Graphical interface
    ├── tabs/         # GUI tabs
    └── utils/        # GUI utilities
```

For more details, see [STRUCTURE.md](STRUCTURE.md).

### Architecture Principles

1. **Separation of Concerns**: Each module has a clear purpose
2. **Core**: Business logic independent of the GUI
3. **Managers**: Specialized managers for specific resources
4. **GUI**: Graphical interface that uses the managers

## Environment Setup

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR-USERNAME/PyCraft.git
cd PyCraft
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create a Branch

```bash
git checkout -b feature/my-new-feature
```

## Development Process

### 1. Before Starting

- Review open issues
- Comment on the issue that you'll work on it
- Make sure you understand the requirements

### 2. During Development

- Write clean and documented code
- Follow project standards
- Test your code regularly
- Make small and frequent commits

### 3. Commit Messages

Use the format:

```
type(scope): short description

More detailed description if necessary.
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting (doesn't affect functionality)
- `refactor`: Refactoring
- `test`: Add tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(modpack): add CurseForge support

fix(server): fix error when starting Forge server

docs(readme): update installation instructions
```

## Code Standards

### Python

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints when possible
- Docstrings for functions and classes
- Maximum 100 characters per line

### Example:

```python
def install_modpack(
    self,
    modpack_id: str,
    version: str,
    destination: str,
    callback: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Install a modpack to the specified location.

    Args:
        modpack_id: Modpack ID
        version: Version to install
        destination: Destination path
        callback: Function to report progress

    Returns:
        True if installation was successful, False otherwise
    """
    # Implementation...
```

### Naming

- **Classes**: `PascalCase`
- **Functions/Methods**: `snake_case`
- **Constants**: `UPPER_CASE`
- **Private**: `_underscore_prefix`

### Imports

```python
# Standard library
import os
import json
from typing import Optional, Dict

# Third-party libraries
import requests
import customtkinter as ctk

# Local imports
from ..core.api import MinecraftAPIHandler
from .utils import LoggerMixin
```

### Docstrings

Use Google docstring format:

```python
def example_function(param1: str, param2: int) -> bool:
    """
    Brief description of the function.

    More detailed description if necessary.

    Args:
        param1: Description of first parameter
        param2: Description of second parameter

    Returns:
        Description of return value

    Raises:
        ValueError: If param2 is negative
    """
    pass
```

## Pull Request Process

### 1. Before Submitting

- [ ] Code follows the standards
- [ ] You have tested your code
- [ ] Updated documentation if necessary
- [ ] No conflicts with `main`

### 2. Creating the PR

1. Go to GitHub and create a Pull Request
2. Use a descriptive title
3. Describe what changes you made and why
4. Reference related issues (`Closes #123`)

### 3. PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation

## How Has This Been Tested
Describe how you tested the changes

## Checklist
- [ ] My code follows the project standards
- [ ] I have tested my code
- [ ] I have updated the documentation
- [ ] My changes don't generate warnings
```

### 4. Review

- Respond to review comments
- Make requested changes
- Thank for the feedback

## Testing

### Manual Testing

Before submitting your PR, test:

1. **Vanilla Server**
   - Create new server
   - Open existing server
   - Start/stop server
   - Send commands

2. **Modpacks**
   - Search modpacks
   - Install modpack
   - Start server with modpack

3. **General**
   - No errors in console
   - GUI should be responsive
   - Logs should be clear

### Unit Tests (Future)

The project plans to add unit tests. Contributions in this area are welcome.

## Contribution Areas

### Priority

- Unit tests
- Support for more loaders
- Internationalization (i18n)
- Download optimization
- Improved error detection

### Future Features

- Server auto-update
- Automatic world backup
- Plugin management (Spigot/Paper)
- Dark/light mode
- Export configurations

## Need Help

- **Issues**: [GitHub Issues](https://github.com/OOMrConrado/PyCraft/issues)
- **Documentation**: See [STRUCTURE.md](STRUCTURE.md)
- **Questions**: Open an issue with the `question` label

## Useful Resources

- [Python PEP 8](https://www.python.org/dev/peps/pep-0008/)
- [CustomTkinter Docs](https://customtkinter.tomschimansky.com/)
- [Minecraft Server API](https://wiki.vg/Main_Page)
- [Modrinth API](https://docs.modrinth.com/)

## Thank You

Thank you for contributing to PyCraft! Every contribution, regardless of size, is valuable and appreciated.

---

**Last updated**: October 2025
