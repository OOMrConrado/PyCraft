# Estructura del Proyecto PyCraft

Este documento describe la organizacion modular del proyecto PyCraft, disenada para mantener un codigo limpio, escalable y facil de mantener.

## Estructura de Carpetas

```
PyCraft/
├── main.py                    # Punto de entrada de la aplicacion
├── docs/                      # Documentacion del proyecto
│   ├── en/                    # Documentacion en ingles
│   └── es/                    # Documentacion en espanol
├── src/                       # Codigo fuente principal
│   ├── __version__.py         # Informacion de version de la aplicacion
│   ├── core/                  # Logica de negocio principal
│   │   ├── api/              # Manejo de APIs externas
│   │   │   ├── handlers.py   # MinecraftAPI, ModrinthAPI, CurseForgeAPI
│   │   │   └── __init__.py
│   │   ├── download/         # Sistema de descargas
│   │   │   ├── downloader.py # ServerDownloader
│   │   │   └── __init__.py
│   │   └── config/           # Configuracion de la aplicacion
│   │       └── __init__.py
│   │
│   ├── managers/             # Gestores de recursos
│   │   ├── java/            # Gestion de Java
│   │   │   ├── java_manager.py
│   │   │   └── __init__.py
│   │   ├── server/          # Gestion de servidores
│   │   │   ├── server_manager.py
│   │   │   └── __init__.py
│   │   ├── modpack/         # Gestion de modpacks
│   │   │   ├── modpack_manager.py
│   │   │   └── __init__.py
│   │   └── loader/          # Gestion de loaders (Forge/Fabric)
│   │       ├── loader_manager.py
│   │       └── __init__.py
│   │
│   ├── gui/                 # Interfaz grafica (PySide6)
│   │   ├── tabs/           # Pestanas de la GUI
│   │   │   ├── base_tab.py       # Clase base con utilidades comunes
│   │   │   ├── info_tab.py       # Pestana de informacion
│   │   │   └── __init__.py
│   │   ├── utils/          # Utilidades GUI
│   │   │   ├── logger.py         # LoggerMixin para logs
│   │   │   ├── widgets.py        # WidgetFactory para widgets
│   │   │   └── __init__.py
│   │   ├── main_window.py  # Ventana principal
│   │   └── __init__.py
│   │
│   └── utils/              # Utilidades comunes
│       ├── system_utils.py # Utilidades del sistema (RAM, puertos, permisos)
│       ├── updater.py      # Sistema de actualizaciones automaticas
│       └── __init__.py
```

## Principios de Diseno

### 1. Separacion de Responsabilidades
Cada carpeta tiene un proposito especifico y claro:

- **core/**: Logica de negocio independiente de la UI
- **managers/**: Gestores especializados para recursos especificos
- **gui/**: Todo lo relacionado con la interfaz grafica
- **utils/**: Funciones y clases utilitarias reutilizables

### 2. Modulos Explicitos
Los nombres de carpetas y archivos son descriptivos:
- `core/api/handlers.py` -> Maneja APIs externas
- `managers/server/server_manager.py` -> Gestiona servidores
- `gui/tabs/info_tab.py` -> Pestana de informacion
- `utils/updater.py` -> Sistema de actualizaciones

### 3. Imports Limpios
Gracias a los archivos `__init__.py`, los imports son concisos:

```python
# Antes
from src.api_handler import MinecraftAPIHandler

# Ahora
from src.core.api import MinecraftAPIHandler
```

### 4. Reutilizacion de Codigo
- `base_tab.py` contiene utilidades comunes para todas las pestanas
- `LoggerMixin` centraliza el manejo de logs
- `WidgetFactory` estandariza la creacion de widgets
- Paleta de colores centralizada

## Componentes Principales

### Core (src/core/)

**API Handlers** (`core/api/handlers.py`)
- `MinecraftAPIHandler`: Comunicacion con APIs de Mojang
- `ModrinthAPI`: Busqueda e instalacion de modpacks de Modrinth
  - Soporte para paginacion en busquedas
  - Filtro por lado (servidor/cliente)
  - Obtencion de metadatos de proyectos en lote
- `CurseForgeAPI`: Reservado para implementacion futura
- `APIConfig`: Gestion de configuracion de API keys

**Downloader** (`core/download/downloader.py`)
- `ServerDownloader`: Sistema de descarga de archivos con progreso

### Managers (src/managers/)

**JavaManager** (`managers/java/`)
- Deteccion de instalaciones de Java
- Descarga automatica de versiones necesarias
- Validacion de versiones y compatibilidad
- Gestion del PATH de Windows (agregar/quitar Java)
- Listado de instalaciones gestionadas por PyCraft
- Eliminacion de instalaciones de Java
- Soporte para elevacion UAC en Windows

**ServerManager** (`managers/server/`)
- Creacion y configuracion de servidores
- Inicio y detencion de procesos
- Envio de comandos al servidor
- Deteccion automatica de version de Minecraft
  - Soporta: modrinth.index.json, Fabric, Forge, logs
- Inicializacion automatica de servidor
  - Aceptacion de EULA automatica
  - Generacion de server.properties
- Sistema Auto-Healer para deteccion de crashes
- Notificacion cuando el servidor esta listo

**ModpackManager** (`managers/modpack/`)
- Instalacion de modpacks desde archivos .mrpack
- Configuracion automatica de loaders (Fabric/Forge/NeoForge/Quilt)
- Descarga de mods y dependencias
- Guardado de manifests para deteccion de version
- Soporte para navegacion de modpacks de cliente (redirige a fuentes oficiales)
- Deteccion y exclusion de mods solo-cliente
- Sistema de known_issues para mods problematicos

**LoaderManager** (`managers/loader/`)
- Deteccion de tipo de loader (Forge/Fabric/NeoForge/Quilt)
- Instalacion de loaders
- Configuracion especifica por tipo

### GUI (src/gui/)

**MainWindow** (`gui/main_window.py`)
- Ventana principal de la aplicacion (PySide6)
- Gestion de pestanas (Vanilla, Mods, Info, Configuracion)
- Orquestacion de todos los componentes
- Soporte para iconos de ventana personalizados
- Dialogos personalizados con branding de PyCraft
- Verificacion de actualizaciones al inicio
- Sistema de auto-healing integrado

**Tabs** (`gui/tabs/`)
- `BaseTab`: Clase base con utilidades comunes
- `InfoTab`: Informacion y ayuda enfocada en jugar con amigos

**Utils** (`gui/utils/`)
- `LoggerMixin`: Manejo unificado de logs con colores
- `WidgetFactory`: Creacion estandarizada de widgets Qt

### Utils (src/utils/)

**System Utils** (`utils/system_utils.py`)
- `validate_eula_file()`: Valida archivos EULA
- `validate_properties_file()`: Valida server.properties
- `check_write_permissions()`: Verifica permisos de escritura
- `check_available_ram()`: Detecta RAM disponible del sistema
- `get_total_ram()`: Obtiene RAM total del sistema
- `can_allocate_ram()`: Verifica si hay RAM suficiente
- `is_port_in_use()`: Verifica si un puerto esta ocupado
- `check_minecraft_port()`: Verifica puerto 25565
- `cleanup_zombie_processes()`: Limpia procesos Java zombie

**Update Checker** (`utils/updater.py`)
- `UpdateChecker`: Verifica actualizaciones desde GitHub Releases
  - Compara versiones usando semver
  - Descarga instaladores automaticamente
  - Soporta instalacion silenciosa (Inno Setup)
  - Limpieza de instaladores temporales

## Mejoras Implementadas

### Framework de UI
- **Antes**: CustomTkinter
- **Ahora**: PySide6 (Qt for Python)
- Mayor rendimiento y apariencia nativa
- Soporte para iconos con QtAwesome

### Sistema de Actualizaciones
- Verificacion automatica al iniciar
- Descarga e instalacion de actualizaciones
- Soporte para instaladores Inno Setup

### Auto-Healer
- Deteccion automatica de mods solo-cliente
- Base de datos de mods problematicos
- Exclusion automatica durante instalacion

### Deteccion de Version
- Multiples fuentes de deteccion
- Cache de version detectada
- Verificacion de compatibilidad con Java

### Modularizacion
- **Antes**: 1 archivo de 2768 lineas (`gui.py`)
- **Ahora**: Codigo distribuido en modulos especializados
- Archivo principal optimizado y mantenible

### Organizacion Clara
- Carpetas con nombres explicativos
- Facil localizar funcionalidad especifica
- Estructura escalable para futuras features

### Mantenibilidad
- Codigo mas facil de entender
- Cambios aislados a modulos especificos
- Reduccion de acoplamiento

### Estandares de Calidad
- Documentacion de modulos en cada `__init__.py`
- Imports relativos consistentes
- Estructura profesional tipo enterprise
- Type hints y docstrings
- Conformidad con PEP 8

## Guia de Uso

### Agregar Nueva Funcionalidad

**Para agregar un nuevo manager:**
1. Crear carpeta en `src/managers/nuevo_manager/`
2. Crear `nuevo_manager.py` con la clase
3. Exportar en `__init__.py`

```python
# src/managers/nuevo_manager/__init__.py
"""Nuevo Manager - Descripcion breve."""

from .nuevo_manager import NuevoManager

__all__ = ["NuevoManager"]
```

**Para agregar una nueva pestana:**
1. Crear archivo en `src/gui/tabs/nueva_tab.py`
2. Heredar de `BaseTab`
3. Importar en `main_window.py`

```python
from .tabs.base_tab import BaseTab

class NuevaTab(BaseTab):
    """Nueva pestana con funcionalidad especifica."""

    def __init__(self, parent):
        super().__init__(parent)
        self.create_widgets()
```

### Importar Modulos

```python
# API handlers
from src.core.api import MinecraftAPIHandler, ModrinthAPI

# Managers
from src.managers.server import ServerManager
from src.managers.modpack import ModpackManager

# GUI components
from src.gui.tabs.info_tab import InfoTab
from src.gui.utils import LoggerMixin, WidgetFactory

# Utils
from src.utils import system_utils
from src.utils.updater import UpdateChecker
```

## Patrones de Diseno Utilizados

### Mixin Pattern
`LoggerMixin` proporciona funcionalidad de logging reutilizable:

```python
class MiClase(LoggerMixin):
    def mi_metodo(self):
        self.add_log(self.log_textbox, "Mensaje", "info")
```

### Factory Pattern
`WidgetFactory` estandariza la creacion de widgets:

```python
button = WidgetFactory.create_button(
    parent=self,
    text="Click",
    style="primary"
)
```

### Manager Pattern
Cada recurso tiene su manager dedicado que encapsula toda su logica.

### Singleton Pattern
`UpdateChecker` mantiene una unica instancia para verificaciones.

## Beneficios

1. **Escalabilidad**: Facil agregar nuevas features sin afectar codigo existente
2. **Debugging**: Mas sencillo localizar y corregir errores
3. **Testing**: Posibilidad de hacer unit tests por modulo
4. **Colaboracion**: Multiples desarrolladores pueden trabajar simultaneamente
5. **Documentacion**: La estructura misma documenta la arquitectura

## Proximos Pasos Sugeridos

- Agregar tests unitarios por modulo
- Documentar API publica de cada manager
- Implementar logging estructurado
- Agregar internacionalizacion (i18n)
- Soporte para mas loaders (Quilt, NeoForge)

## Documentacion Adicional

- **Contribuir**: Ver [CONTRIBUTING.md](CONTRIBUTING.md)
- **Licencia**: Ver [LICENSE](../../LICENSE)
- **README**: Ver [README](../../README.md)

---

**Version**: 1.0.0
**Fecha**: Diciembre 2025
**Estado**: Estructura modular implementada y funcional
