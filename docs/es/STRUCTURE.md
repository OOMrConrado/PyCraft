# Estructura del Proyecto PyCraft

Este documento describe la organización modular del proyecto PyCraft, diseñada para mantener un código limpio, escalable y fácil de mantener.

## Estructura de Carpetas

```
PyCraft/
├── main.py                    # Punto de entrada de la aplicación
├── docs/                      # Documentación del proyecto
│   ├── en/                    # Documentación en inglés
│   └── es/                    # Documentación en español
├── src/                       # Código fuente principal
│   ├── core/                  # Lógica de negocio principal
│   │   ├── api/              # Manejo de APIs externas
│   │   │   ├── handlers.py   # MinecraftAPI, ModrinthAPI, CurseForgeAPI
│   │   │   └── __init__.py
│   │   ├── download/         # Sistema de descargas
│   │   │   ├── downloader.py # ServerDownloader
│   │   │   └── __init__.py
│   │   └── config/           # Configuración de la aplicación
│   │       └── __init__.py
│   │
│   ├── managers/             # Gestores de recursos
│   │   ├── java/            # Gestión de Java
│   │   │   ├── java_manager.py
│   │   │   └── __init__.py
│   │   ├── server/          # Gestión de servidores
│   │   │   ├── server_manager.py
│   │   │   └── __init__.py
│   │   ├── modpack/         # Gestión de modpacks
│   │   │   ├── modpack_manager.py
│   │   │   └── __init__.py
│   │   └── loader/          # Gestión de loaders (Forge/Fabric)
│   │       ├── loader_manager.py
│   │       └── __init__.py
│   │
│   ├── gui/                 # Interfaz gráfica
│   │   ├── tabs/           # Pestañas de la GUI
│   │   │   ├── base_tab.py       # Clase base con utilidades comunes
│   │   │   ├── info_tab.py       # Pestaña de información
│   │   │   └── __init__.py
│   │   ├── utils/          # Utilidades GUI
│   │   │   ├── logger.py         # LoggerMixin para logs
│   │   │   ├── widgets.py        # WidgetFactory para widgets
│   │   │   └── __init__.py
│   │   ├── main_window.py  # Ventana principal
│   │   └── __init__.py
│   │
│   └── utils/              # Utilidades comunes
│       └── __init__.py
```

## Principios de Diseño

### 1. Separación de Responsabilidades
Cada carpeta tiene un propósito específico y claro:

- **core/**: Lógica de negocio independiente de la UI
- **managers/**: Gestores especializados para recursos específicos
- **gui/**: Todo lo relacionado con la interfaz gráfica
- **utils/**: Funciones y clases utilitarias reutilizables

### 2. Módulos Explícitos
Los nombres de carpetas y archivos son descriptivos:
- `core/api/handlers.py` → Maneja APIs externas
- `managers/server/server_manager.py` → Gestiona servidores
- `gui/tabs/info_tab.py` → Pestaña de información

### 3. Imports Limpios
Gracias a los archivos `__init__.py`, los imports son concisos:

```python
# Antes
from src.api_handler import MinecraftAPIHandler

# Ahora
from src.core.api import MinecraftAPIHandler
```

### 4. Reutilización de Código
- `base_tab.py` contiene utilidades comunes para todas las pestañas
- `LoggerMixin` centraliza el manejo de logs
- `WidgetFactory` estandariza la creación de widgets
- Paleta de colores centralizada

## Componentes Principales

### Core (src/core/)

**API Handlers** (`core/api/handlers.py`)
- `MinecraftAPIHandler`: Comunicación con APIs de Mojang
- `ModrinthAPI`: Búsqueda e instalación de modpacks de Modrinth
- `CurseForgeAPI`: Reservado para implementación futura
- `APIConfig`: Gestión de configuración de API keys

**Downloader** (`core/download/downloader.py`)
- `ServerDownloader`: Sistema de descarga de archivos con progreso

### Managers (src/managers/)

**JavaManager** (`managers/java/`)
- Detección de instalaciones de Java
- Descarga automática de versiones necesarias
- Validación de versiones
- Gestión del PATH de Windows (agregar/quitar Java)
- Listado de instalaciones gestionadas por PyCraft
- Eliminación de instalaciones de Java

**ServerManager** (`managers/server/`)
- Creación y configuración de servidores
- Inicio y detención de procesos
- Envío de comandos al servidor

**ModpackManager** (`managers/modpack/`)
- Instalación de modpacks desde .mrpack
- Configuración automática de loaders
- Descarga de mods y dependencias
- Guardado de manifests para detección de versión
- Soporte para instalación de clientes de modpack

**LoaderManager** (`managers/loader/`)
- Detección de tipo de loader (Forge/Fabric)
- Instalación de loaders
- Configuración específica por tipo

### GUI (src/gui/)

**MainWindow** (`gui/main_window.py`)
- Ventana principal de la aplicación
- Gestión de pestañas (Vanilla, Mods, Info, Configuración)
- Orquestación de todos los componentes
- Soporte para iconos de ventana personalizados
- Diálogos personalizados con branding de PyCraft

**Tabs** (`gui/tabs/`)
- `BaseTab`: Clase base con utilidades comunes
- `InfoTab`: Información y ayuda enfocada en jugar con amigos

**Utils** (`gui/utils/`)
- `LoggerMixin`: Manejo unificado de logs con colores
- `WidgetFactory`: Creación estandarizada de widgets

## Mejoras Implementadas

### Modularización
- **Antes**: 1 archivo de 2768 líneas (`gui.py`)
- **Ahora**: Código distribuido en módulos especializados
- Archivo principal optimizado y mantenible

### Organización Clara
- Carpetas con nombres explicativos
- Fácil localizar funcionalidad específica
- Estructura escalable para futuras features

### Mantenibilidad
- Código más fácil de entender
- Cambios aislados a módulos específicos
- Reducción de acoplamiento

### Estándares de Calidad
- Documentación de módulos en cada `__init__.py`
- Imports relativos consistentes
- Estructura profesional tipo enterprise
- Type hints y docstrings
- Conformidad con PEP 8

## Guía de Uso

### Agregar Nueva Funcionalidad

**Para agregar un nuevo manager:**
1. Crear carpeta en `src/managers/nuevo_manager/`
2. Crear `nuevo_manager.py` con la clase
3. Exportar en `__init__.py`

```python
# src/managers/nuevo_manager/__init__.py
"""Nuevo Manager - Descripción breve."""

from .nuevo_manager import NuevoManager

__all__ = ["NuevoManager"]
```

**Para agregar una nueva pestaña:**
1. Crear archivo en `src/gui/tabs/nueva_tab.py`
2. Heredar de `BaseTab`
3. Importar en `main_window.py`

```python
from .tabs.base_tab import BaseTab

class NuevaTab(BaseTab):
    """Nueva pestaña con funcionalidad específica."""

    def __init__(self, parent):
        super().__init__(parent)
        self.create_widgets()
```

### Importar Módulos

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

## Patrones de Diseño Utilizados

### Mixin Pattern
`LoggerMixin` proporciona funcionalidad de logging reutilizable:

```python
class MiClase(LoggerMixin):
    def mi_metodo(self):
        self.add_log(self.log_textbox, "Mensaje", "info")
```

### Factory Pattern
`WidgetFactory` estandariza la creación de widgets:

```python
button = WidgetFactory.create_button(
    parent=self,
    text="Click",
    style="primary"
)
```

### Manager Pattern
Cada recurso tiene su manager dedicado que encapsula toda su lógica.

## Beneficios

1. **Escalabilidad**: Fácil agregar nuevas features sin afectar código existente
2. **Debugging**: Más sencillo localizar y corregir errores
3. **Testing**: Posibilidad de hacer unit tests por módulo
4. **Colaboración**: Múltiples desarrolladores pueden trabajar simultáneamente
5. **Documentación**: La estructura misma documenta la arquitectura

## Próximos Pasos Sugeridos

- Extraer pestañas individuales de `main_window.py`
- Crear módulo `utils/validators.py` para validaciones comunes
- Agregar tests unitarios por módulo
- Documentar API pública de cada manager
- Implementar logging estructurado
- Agregar internacionalización (i18n)

## Documentación Adicional

- **Contribuir**: Ver [CONTRIBUTING.md](CONTRIBUTING.md)
- **Licencia**: Ver [LICENSE](../../LICENSE)
- **README**: Ver [README](../../README.md)

---

**Versión**: 2.0
**Fecha**: Octubre 2025
**Estado**: Estructura modular implementada y funcional
