# Guía de Contribución - PyCraft

¡Gracias por tu interés en contribuir a PyCraft! Este documento te guiará en el proceso.

## Tabla de Contenidos

- [Código de Conducta](#código-de-conducta)
- [Cómo Puedo Contribuir](#cómo-puedo-contribuir)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Configuración del Entorno](#configuración-del-entorno)
- [Proceso de Desarrollo](#proceso-de-desarrollo)
- [Estándares de Código](#estándares-de-código)
- [Proceso de Pull Request](#proceso-de-pull-request)

## Código de Conducta

Este proyecto se adhiere a un código de conducta. Al participar, se espera que mantengas un ambiente respetuoso y profesional.

### Nuestros Estándares

- Usa lenguaje acogedor e inclusivo
- Respeta diferentes puntos de vista
- Acepta críticas constructivas
- Enfócate en lo mejor para la comunidad

## Cómo Puedo Contribuir

### Reportar Bugs

Los bugs se rastrean como [issues de GitHub](https://github.com/OOMrConrado/PyCraft/issues).

**Antes de crear un issue:**
- Verifica que no exista un issue similar
- Asegúrate de que sea realmente un bug

**Al reportar un bug incluye:**
- Título claro y descriptivo
- Pasos detallados para reproducir el problema
- Comportamiento esperado vs actual
- Screenshots si aplica
- Tu entorno (OS, versión de Python, etc.)

### Sugerir Mejoras

Las sugerencias también se rastrean como issues.

**Incluye:**
- Descripción clara de la mejora
- Por qué sería útil
- Ejemplos de uso

### Contribuir con Código

1. **Fork el repositorio**
2. **Crea una rama** para tu feature
3. **Desarrolla** siguiendo los estándares
4. **Prueba** tu código
5. **Envía** un Pull Request

## Estructura del Proyecto

```
src/
├── core/              # Lógica de negocio
│   ├── api/          # Comunicación con APIs externas
│   ├── download/     # Sistema de descargas
│   └── config/       # Configuración
├── managers/         # Gestores de recursos
│   ├── java/         # Gestión de Java
│   ├── server/       # Gestión de servidores
│   ├── modpack/      # Gestión de modpacks
│   └── loader/       # Gestión de loaders (Forge/Fabric)
└── gui/              # Interfaz gráfica
    ├── tabs/         # Pestañas de la GUI
    └── utils/        # Utilidades GUI
```

Para más detalles, ver [STRUCTURE.md](STRUCTURE.md).

### Principios de Arquitectura

1. **Separación de Responsabilidades**: Cada módulo tiene un propósito claro
2. **Core**: Lógica de negocio independiente de la GUI
3. **Managers**: Gestores especializados para recursos específicos
4. **GUI**: Interfaz gráfica que usa los managers

## Configuración del Entorno

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

### 4. Crea una Rama

```bash
git checkout -b feature/mi-nueva-feature
```

## Proceso de Desarrollo

### 1. Antes de Empezar

- Revisa los issues abiertos
- Comenta en el issue que trabajarás en él
- Asegúrate de entender los requisitos

### 2. Durante el Desarrollo

- Escribe código limpio y documentado
- Sigue los estándares del proyecto
- Prueba tu código regularmente
- Haz commits pequeños y frecuentes

### 3. Mensajes de Commit

Usa el formato:

```
tipo(alcance): descripción corta

Descripción más detallada si es necesario.
```

**Tipos:**
- `feat`: Nueva característica
- `fix`: Corrección de bug
- `docs`: Cambios en documentación
- `style`: Formato de código (no afecta funcionalidad)
- `refactor`: Refactorización
- `test`: Agregar tests
- `chore`: Tareas de mantenimiento

**Ejemplos:**
```
feat(modpack): agregar soporte para CurseForge

fix(server): corregir error al iniciar servidor Forge

docs(readme): actualizar instrucciones de instalación
```

## Estándares de Código

### Python

- Sigue [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Usa type hints cuando sea posible
- Docstrings para funciones y clases
- Máximo 100 caracteres por línea

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
    Instala un modpack en la ubicación especificada.

    Args:
        modpack_id: ID del modpack
        version: Versión a instalar
        destination: Ruta de destino
        callback: Función para reportar progreso

    Returns:
        True si la instalación fue exitosa, False en caso contrario
    """
    # Implementación...
```

### Nombres

- **Clases**: `PascalCase`
- **Funciones/Métodos**: `snake_case`
- **Constantes**: `UPPER_CASE`
- **Privado**: `_prefijo_underscore`

### Imports

```python
# Librería estándar
import os
import json
from typing import Optional, Dict

# Librerías de terceros
import requests
import customtkinter as ctk

# Imports locales
from ..core.api import MinecraftAPIHandler
from .utils import LoggerMixin
```

### Docstrings

Usa formato Google docstrings:

```python
def funcion_ejemplo(param1: str, param2: int) -> bool:
    """
    Descripción breve de la función.

    Descripción más detallada si es necesario.

    Args:
        param1: Descripción del primer parámetro
        param2: Descripción del segundo parámetro

    Returns:
        Descripción del valor de retorno

    Raises:
        ValueError: Si param2 es negativo
    """
    pass
```

## Proceso de Pull Request

### 1. Antes de Enviar

- [ ] El código sigue los estándares
- [ ] Has probado tu código
- [ ] Actualizaste la documentación si es necesario
- [ ] No hay conflictos con `main`

### 2. Crear el PR

1. Ve a GitHub y crea un Pull Request
2. Usa un título descriptivo
3. Describe qué cambios hiciste y por qué
4. Referencia issues relacionados (`Closes #123`)

### 3. Template de PR

```markdown
## Descripción
Breve descripción de los cambios

## Tipo de Cambio
- [ ] Bug fix
- [ ] Nueva característica
- [ ] Breaking change
- [ ] Documentación

## Cómo se probó
Describe cómo probaste los cambios

## Checklist
- [ ] Mi código sigue los estándares del proyecto
- [ ] He probado mi código
- [ ] He actualizado la documentación
- [ ] Mis cambios no generan warnings
```

### 4. Revisión

- Responde a los comentarios de revisión
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
   - Instalar modpack
   - Iniciar servidor con modpack

3. **General**
   - No debe haber errores en consola
   - La GUI debe ser responsiva
   - Los logs deben ser claros

### Tests Unitarios (Futuro)

El proyecto planea agregar tests unitarios. Contribuciones en esta área son bienvenidas.

## Áreas de Contribución

### Prioritarias

- Tests unitarios
- Soporte para más loaders
- Internacionalización (i18n)
- Optimización de descargas
- Detección de errores mejorada

### Features Futuras

- Auto-actualización de servidores
- Respaldo automático de mundos
- Gestión de plugins (Spigot/Paper)
- Modo oscuro/claro
- Exportar configuraciones

## Necesitas Ayuda

- **Issues**: [GitHub Issues](https://github.com/OOMrConrado/PyCraft/issues)
- **Documentación**: Ver [STRUCTURE.md](STRUCTURE.md)
- **Preguntas**: Abre un issue con la etiqueta `question`

## Recursos Útiles

- [Python PEP 8](https://www.python.org/dev/peps/pep-0008/)
- [CustomTkinter Docs](https://customtkinter.tomschimansky.com/)
- [Minecraft Server API](https://wiki.vg/Main_Page)
- [Modrinth API](https://docs.modrinth.com/)

## Gracias

¡Gracias por contribuir a PyCraft! Cada contribución, sin importar su tamaño, es valiosa y apreciada.

---

**Última actualización**: Octubre 2025
