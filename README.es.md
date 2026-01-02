# PyCraft - Minecraft Server Manager

**Español** | [English](README.md)

**Una herramienta intuitiva para crear y gestionar servidores de Minecraft vanilla y con modpacks**

PyCraft simplifica la creación de servidores de Minecraft, permitiéndote descargar, configurar e iniciar servidores vanilla o con modpacks de forma automática. Con soporte para Forge, Fabric, NeoForge, Quilt, y búsqueda integrada de modpacks de Modrinth.

---

## Características

### Gestión de Servidores
- **Servidores Vanilla**: Crea servidores Minecraft vanilla con un solo clic
- **Servidores con Mods**: Instala y gestiona servidores con Forge, Fabric, NeoForge o Quilt
- **Instalación de Modpacks**: Busca e instala modpacks de servidor directamente desde Modrinth y CurseForge
- **Modpacks de Cliente**: Navega y encuentra modpacks para tu launcher de Minecraft
- **Configuración Automática**: EULA aceptado y server.properties configurado automáticamente
- **Reinicio Rápido**: Estado del servidor mantenido tras detener/crash para reinicio instantáneo

### Interfaz
- **UI Moderna**: Interfaz limpia construida con PySide6 (framework Qt)
- **Sidebar Organizado**: Navegación fácil con secciones dedicadas para:
  - Inicio
  - Servidor Vanilla
  - Servidor con Mods
  - Modpacks de Cliente
  - Gestión (Java y Modpacks)
  - Configuración
- **Consola en Tiempo Real**: Consola de 500 líneas con resaltado de sintaxis
- **Enlaces Rápidos**: Acceso directo a GitHub, Modrinth, CurseForge

### Características Avanzadas
- **Gestión de Java**: Detección e instalación automática de Java con compatibilidad de versiones
- **Detección de Crashes**: Detección automática de crashes con acceso directo a logs y reportes de crash
- **Editor de Config**: Editor integrado de server.properties (habilitado tras primera ejecución)
- **Feedback Visual**: Animaciones de botones e indicadores de estado
- **Operaciones Thread-safe**: Gestión confiable del servidor con threading apropiado

---

## Instalación

### Requisitos Previos
- **Python 3.8+** instalado
- **Java 17+** (o será instalado automáticamente)
- **Windows 10/11** (Linux y macOS compatibles)

### Pasos de Instalación

1. **Clona el repositorio:**
```bash
git clone https://github.com/OOMrConrado/PyCraft.git
cd PyCraft
```

2. **Crea un entorno virtual:**
```bash
python -m venv .venv
.venv\Scripts\activate  # En Windows
source .venv/bin/activate  # En Linux/macOS
```

3. **Instala las dependencias:**
```bash
pip install -r requirements.txt
```

4. **Ejecuta la aplicación:**
```bash
python main.py
```

---

## Uso Rápido

### Crear un Servidor Vanilla

1. Abre PyCraft
2. Ve a **"Servidor Vanilla"** en el sidebar
3. Selecciona **"Crear Servidor Nuevo"**
4. Busca y selecciona una versión de Minecraft
5. Elige una carpeta de destino
6. Haz clic en **"Descargar e Instalar Servidor"**
7. Una vez completado, haz clic en **"Iniciar Servidor"**
8. El servidor generará `server.properties` en la primera ejecución
9. Usa el botón **"Config"** para personalizar la configuración del servidor

### Instalar un Modpack de Servidor

1. Ve a **"Servidor con Mods"** en el sidebar
2. Selecciona **"Instalar Servidor"**
3. Busca tu modpack favorito (ej: "Create", "ATM9")
4. Selecciona el modpack y la versión
5. Elige una carpeta de destino
6. Haz clic en **"Instalar Modpack"**
7. PyCraft descargará y configurará todo automáticamente
8. Haz clic en **"Iniciar Servidor"** cuando esté listo

### Gestionar un Servidor Existente

1. En **"Servidor con Mods"**, selecciona **"Ejecutar Servidor"**
2. Elige la carpeta del servidor
3. PyCraft detectará automáticamente el tipo (Forge/Fabric/NeoForge/Quilt)
4. Haz clic en **"Iniciar Servidor"**
5. Envía comandos a través de la consola
6. Usa **"Config"** para editar las propiedades del servidor (tras primera ejecución)

### Navegar Modpacks de Cliente

1. Ve a **"Modpacks de Cliente"** en el sidebar
2. Elige el proveedor (Modrinth o CurseForge)
3. Busca un modpack
4. Haz clic en **"Open"** para visitar la página del modpack
5. Descarga e instala a través del launcher oficial (CurseForge App o Modrinth)

---

## Tecnologías

- **Python 3.x**
- **PySide6** - Framework GUI moderno basado en Qt
- **QtAwesome** - Biblioteca de iconos para una interfaz hermosa
- **Requests** - Comunicación con APIs
- **Threading** - Operaciones asíncronas para UI fluida

---

## Estructura del Proyecto

```
PyCraft/
├── main.py              # Punto de entrada
├── docs/                # Documentación
│   ├── en/             # Documentación en inglés
│   └── es/             # Documentación en español
├── src/
│   ├── core/           # Lógica de negocio
│   │   ├── api.py      # Manejadores de API (Minecraft, Modrinth)
│   │   └── download.py # Sistema de descargas
│   ├── managers/       # Gestores de recursos
│   │   ├── java/       # Detección e instalación de Java
│   │   ├── server/     # Gestión de servidores
│   │   └── modpack/    # Instalación de modpacks
│   ├── gui/            # Interfaz gráfica
│   │   └── main_window.py  # UI principal
│   └── utils/          # Utilidades
└── PyCraft-Files/      # Assets (logo, iconos)
```

Para información detallada de la arquitectura, ver [docs/es/STRUCTURE.md](docs/es/STRUCTURE.md)

---

## Vista General de la Interfaz

### Navegación por Sidebar
- **Inicio**: Página de bienvenida con enlaces rápidos
- **Servidor Vanilla**: Crea y gestiona servidores vanilla
- **Servidor con Mods**: Instala y ejecuta servidores con mods
- **Modpacks de Cliente**: Instala modpacks para tu launcher
- **Sección de Gestión**:
  - **Java**: Gestiona instalaciones de Java
  - **Modpacks**: Visualiza y gestiona modpacks de cliente instalados
- **Configuración**: Ajustes de la aplicación e información

### Características de la Consola
- Salida del servidor en tiempo real
- Resaltado de sintaxis (errores, advertencias, info)
- Buffer de 500 líneas para logs completos
- Entrada de comandos con prefijo `/`
- Feedback visual al enviar comandos

### Manejo de Crashes
- Detección automática de crashes
- Diálogo modal con información del crash
- Enlaces directos a:
  - Carpeta de logs del servidor
  - Carpeta de reportes de crash
- Servidor listo para reiniciar inmediatamente

---

## Contribuir

Las contribuciones son bienvenidas. Por favor lee [docs/es/CONTRIBUTING.md](docs/es/CONTRIBUTING.md) para conocer los detalles del proceso y el código de conducta.

### Pasos para Contribuir

1. Fork el proyecto
2. Crea tu rama de feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## Licencia

Este proyecto está bajo la Licencia MIT. Ver [LICENSE](LICENSE) para más detalles.

---

## Autor

**Conrado Gómez**
- GitHub: [@OOMrConrado](https://github.com/OOMrConrado)
- Email: conradogomez556@gmail.com

---

## Agradecimientos

- [Mojang](https://www.minecraft.net/) - Por Minecraft
- [Modrinth](https://modrinth.com/) - Por su excelente API de modpacks
- [PySide6](https://www.qt.io/qt-for-python) - Por el framework Qt
- [QtAwesome](https://github.com/spyder-ide/qtawesome) - Por la biblioteca de iconos
