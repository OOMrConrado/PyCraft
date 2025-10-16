# PyCraft - Minecraft Server Manager

**Español** | [English](README.md)

**Una herramienta intuitiva para crear y gestionar servidores de Minecraft vanilla y con modpacks**

PyCraft simplifica la creación de servidores de Minecraft, permitiéndote descargar, configurar e iniciar servidores vanilla o con modpacks de forma automática. Con soporte para Forge, Fabric, y búsqueda integrada de modpacks de Modrinth.

---

## Características

- **Servidores Vanilla**: Crea servidores Minecraft vanilla con un solo clic
- **Modpacks**: Busca e instala modpacks directamente desde Modrinth
- **Configuración Automática**: EULA aceptado y server.properties configurado automáticamente
- **Loaders**: Soporte para Forge y Fabric
- **Java**: Verificación e instalación automática de Java
- **Gestión Completa**: Inicia, detiene y envía comandos a tus servidores
- **Interfaz Intuitiva**: GUI moderna con customtkinter

---

## Instalación

### Requisitos Previos
- **Python 3.8+** instalado
- **Java 17+** (o la versión será instalada automáticamente)
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
2. Ve a la pestaña **"Servidor Vanilla"**
3. Selecciona **"Crear Servidor Nuevo"**
4. Busca y selecciona una versión de Minecraft
5. Elige una carpeta de destino
6. Haz clic en **"Descargar e Instalar Servidor"**
7. Una vez completado, haz clic en **"Iniciar Servidor"**

### Instalar un Modpack

1. Ve a la pestaña **"Servidor con Mods"**
2. Selecciona **"Instalación de Modpack"**
3. Busca tu modpack favorito (ej: "Create", "ATM9")
4. Selecciona el modpack y la versión
5. Elige una carpeta de destino
6. Haz clic en **"Instalar Modpack"**
7. PyCraft descargará e instalará todo automáticamente

### Gestionar un Servidor con Modpack

1. En **"Servidor con Mods"**, selecciona **"Gestión de Servidor"**
2. Elige la carpeta del servidor
3. PyCraft detectará automáticamente el tipo (Forge/Fabric)
4. Haz clic en **"Iniciar Servidor"**

---

## Tecnologías

- **Python 3.x**
- **CustomTkinter** - Interfaz gráfica moderna
- **Requests** - Comunicación con APIs
- **Threading** - Ejecución asíncrona

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
│   │   ├── api/       # APIs (Minecraft, Modrinth)
│   │   └── download/  # Sistema de descargas
│   ├── managers/      # Gestores de recursos
│   │   ├── java/      # Gestión de Java
│   │   ├── server/    # Servidores Minecraft
│   │   ├── modpack/   # Instalación de modpacks
│   │   └── loader/    # Forge y Fabric
│   └── gui/           # Interfaz gráfica
│       ├── tabs/      # Pestañas modulares
│       └── utils/     # Utilidades GUI
```

Para información detallada de la arquitectura, ver [docs/es/STRUCTURE.md](docs/es/STRUCTURE.md)

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
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Por la biblioteca de GUI
