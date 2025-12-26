# Guia de Contribucion - PyCraft

Gracias por tu interes en contribuir a PyCraft! Este documento te guiara en el proceso.

## Tabla de Contenidos

- [Codigo de Conducta](#codigo-de-conducta)
- [Como Puedo Contribuir](#como-puedo-contribuir)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Configuracion del Entorno](#configuracion-del-entorno)
- [Proceso de Desarrollo](#proceso-de-desarrollo)
- [Estandares de Codigo](#estandares-de-codigo)
- [Proceso de Pull Request](#proceso-de-pull-request)

## Codigo de Conducta

Este proyecto se adhiere a un codigo de conducta. Al participar, se espera que mantengas un ambiente respetuoso y profesional.

### Nuestros Estandares

- Usa lenguaje acogedor e inclusivo
- Respeta diferentes puntos de vista
- Acepta criticas constructivas
- Enfocate en lo mejor para la comunidad

## Como Puedo Contribuir

### Reportar Bugs

Los bugs se rastrean como [issues de GitHub](https://github.com/OOMrConrado/PyCraft/issues).

**Antes de crear un issue:**
- Verifica que no exista un issue similar
- Asegurate de que sea realmente un bug

**Al reportar un bug incluye:**
- Titulo claro y descriptivo
- Pasos detallados para reproducir el problema
- Comportamiento esperado vs actual
- Screenshots si aplica
- Tu entorno (OS, version de Python, etc.)

### Sugerir Mejoras

Las sugerencias tambien se rastrean como issues.

**Incluye:**
- Descripcion clara de la mejora
- Por que seria util
- Ejemplos de uso

### Contribuir con Codigo

1. **Fork el repositorio**
2. **Crea una rama** para tu feature
3. **Desarrolla** siguiendo los estandares
4. **Prueba** tu codigo
5. **Envia** un Pull Request

## Estructura del Proyecto

```
src/
├── core/              # Logica de negocio
│   ├── api/          # Comunicacion con APIs externas
│   ├── download/     # Sistema de descargas
│   └── config/       # Configuracion
├── managers/         # Gestores de recursos
│   ├── java/         # Gestion de Java
│   ├── server/       # Gestion de servidores
│   ├── modpack/      # Gestion de modpacks
│   └── loader/       # Gestion de loaders (Forge/Fabric)
├── gui/              # Interfaz grafica (PySide6)
│   ├── tabs/         # Pestanas de la GUI
│   └── utils/        # Utilidades GUI
└── utils/            # Utilidades comunes
    ├── system_utils.py  # Utilidades del sistema
    └── updater.py       # Sistema de actualizaciones
```

Para mas detalles, ver [STRUCTURE.md](STRUCTURE.md).

### Principios de Arquitectura

1. **Separacion de Responsabilidades**: Cada modulo tiene un proposito claro
2. **Core**: Logica de negocio independiente de la GUI
3. **Managers**: Gestores especializados para recursos especificos
4. **GUI**: Interfaz grafica que usa los managers

## Configuracion del Entorno

### 1. Fork y Clona

```bash
git clone https://github.com/TU-USUARIO/PyCraft.git
cd PyCraft
```

### 2. Crea un Entorno Virtual

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS
```

### 3. Instala Dependencias

```bash
pip install -r requirements.txt
```

Las dependencias principales son:
- **PySide6**: Framework de interfaz grafica (Qt for Python)
- **qtawesome**: Iconos Font Awesome para Qt
- **requests**: Comunicacion HTTP con APIs
- **Pillow**: Procesamiento de imagenes
- **psutil**: Utilidades de sistema y procesos
- **packaging**: Parseo de versiones

### 4. Crea una Rama

```bash
git checkout -b feature/mi-nueva-feature
```

## Proceso de Desarrollo

### 1. Antes de Empezar

- Revisa los issues abiertos
- Comenta en el issue que trabajaras en el
- Asegurate de entender los requisitos

### 2. Durante el Desarrollo

- Escribe codigo limpio y documentado
- Sigue los estandares del proyecto
- Prueba tu codigo regularmente
- Haz commits pequenos y frecuentes

### 3. Mensajes de Commit

Usa el formato:

```
tipo(alcance): descripcion corta

Descripcion mas detallada si es necesario.
```

**Tipos:**
- `feat`: Nueva caracteristica
- `fix`: Correccion de bug
- `docs`: Cambios en documentacion
- `style`: Formato de codigo (no afecta funcionalidad)
- `refactor`: Refactorizacion
- `test`: Agregar tests
- `chore`: Tareas de mantenimiento

**Ejemplos:**
```
feat(modpack): agregar soporte para CurseForge

fix(server): corregir error al iniciar servidor Forge

docs(readme): actualizar instrucciones de instalacion
```

## Estandares de Codigo

### Python

- Sigue [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Usa type hints cuando sea posible
- Docstrings para funciones y clases
- Maximo 100 caracteres por linea

### Ejemplo:

```python
def install_modpack(
    self,
    modpack_id: str,
    version: str,
    destination: str,
    callback: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Instala un modpack en la ubicacion especificada.

    Args:
        modpack_id: ID del modpack
        version: Version a instalar
        destination: Ruta de destino
        callback: Funcion para reportar progreso

    Returns:
        True si la instalacion fue exitosa, False en caso contrario
    """
    # Implementacion...
```

### Nombres

- **Clases**: `PascalCase`
- **Funciones/Metodos**: `snake_case`
- **Constantes**: `UPPER_CASE`
- **Privado**: `_prefijo_underscore`

### Imports

```python
# Libreria estandar
import os
import json
from typing import Optional, Dict

# Librerias de terceros
import requests
from PySide6.QtWidgets import QWidget, QPushButton

# Imports locales
from ..core.api import MinecraftAPIHandler
from .utils import LoggerMixin
```

### Docstrings

Usa formato Google docstrings:

```python
def funcion_ejemplo(param1: str, param2: int) -> bool:
    """
    Descripcion breve de la funcion.

    Descripcion mas detallada si es necesario.

    Args:
        param1: Descripcion del primer parametro
        param2: Descripcion del segundo parametro

    Returns:
        Descripcion del valor de retorno

    Raises:
        ValueError: Si param2 es negativo
    """
    pass
```

## Proceso de Pull Request

### 1. Antes de Enviar

- [ ] El codigo sigue los estandares
- [ ] Has probado tu codigo
- [ ] Actualizaste la documentacion si es necesario
- [ ] No hay conflictos con `main`

### 2. Crear el PR

1. Ve a GitHub y crea un Pull Request
2. Usa un titulo descriptivo
3. Describe que cambios hiciste y por que
4. Referencia issues relacionados (`Closes #123`)

### 3. Template de PR

```markdown
## Descripcion
Breve descripcion de los cambios

## Tipo de Cambio
- [ ] Bug fix
- [ ] Nueva caracteristica
- [ ] Breaking change
- [ ] Documentacion

## Como se probo
Describe como probaste los cambios

## Checklist
- [ ] Mi codigo sigue los estandares del proyecto
- [ ] He probado mi codigo
- [ ] He actualizado la documentacion
- [ ] Mis cambios no generan warnings
```

### 4. Revision

- Responde a los comentarios de revision
- Haz los cambios solicitados
- Agradece el feedback

## Testing

### Pruebas Manuales

Antes de enviar tu PR, prueba:

1. **Servidor Vanilla**
   - Crear servidor nuevo
   - Abrir servidor existente
   - Iniciar/detener servidor
   - Enviar comandos

2. **Modpacks**
   - Buscar modpacks
   - Instalar modpack (servidor y cliente)
   - Iniciar servidor con modpack

3. **Java**
   - Deteccion de versiones instaladas
   - Descarga de nuevas versiones
   - Compatibilidad con diferentes versiones de Minecraft

4. **General**
   - No debe haber errores en consola
   - La GUI debe ser responsiva
   - Los logs deben ser claros
   - Verificar actualizaciones debe funcionar

### Tests Unitarios (Futuro)

El proyecto planea agregar tests unitarios. Contribuciones en esta area son bienvenidas.

## Areas de Contribucion

### Prioritarias

- Tests unitarios
- Soporte para mas loaders (Quilt, NeoForge)
- Internacionalizacion (i18n)
- Optimizacion de descargas
- Deteccion de errores mejorada

### Features Futuras

- Respaldo automatico de mundos
- Gestion de plugins (Spigot/Paper)
- Exportar configuraciones
- Soporte para Linux/macOS

## Necesitas Ayuda

- **Issues**: [GitHub Issues](https://github.com/OOMrConrado/PyCraft/issues)
- **Documentacion**: Ver [STRUCTURE.md](STRUCTURE.md)
- **Preguntas**: Abre un issue con la etiqueta `question`

## Recursos Utiles

- [Python PEP 8](https://www.python.org/dev/peps/pep-0008/)
- [PySide6 Docs](https://doc.qt.io/qtforpython-6/)
- [Minecraft Server API](https://wiki.vg/Main_Page)
- [Modrinth API](https://docs.modrinth.com/)

## Gracias

Gracias por contribuir a PyCraft! Cada contribucion, sin importar su tamano, es valiosa y apreciada.

---

**Ultima actualizacion**: Diciembre 2025
