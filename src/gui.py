import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import threading
import os
from typing import Optional

from src.api_handler import MinecraftAPIHandler
from src.downloader import ServerDownloader
from src.server_manager import ServerManager


class PyCraftGUI:
    """Interfaz gráfica principal de PyCraft"""

    def __init__(self):
        # Configuración de customtkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Ventana principal
        self.root = ctk.CTk()
        self.root.title("PyCraft - Minecraft Server Manager")
        self.root.geometry("1000x800")
        self.root.resizable(False, False)

        # Componentes
        self.api_handler = MinecraftAPIHandler()
        self.downloader = ServerDownloader()
        self.server_manager: Optional[ServerManager] = None

        # Variables
        self.versions_list = []
        self.filtered_versions = []
        self.selected_version = None
        self.server_folder = None
        self.is_server_configured = False

        # Crear la interfaz
        self._create_widgets()

        # Cargar versiones al iniciar
        self._load_versions()

    def _create_widgets(self):
        """Crea todos los widgets de la interfaz"""

        # Header con logo y título
        header_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        header_frame.pack(pady=10, padx=20, fill="x")

        # Intentar cargar el logo
        try:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                    "PyCraft-Files", "logo.png")
            if os.path.exists(logo_path):
                logo_image = Image.open(logo_path)
                # Redimensionar el logo (más grande)
                logo_image = logo_image.resize((120, 120), Image.Resampling.LANCZOS)
                logo_photo = ctk.CTkImage(light_image=logo_image, dark_image=logo_image, size=(120, 120))

                logo_label = ctk.CTkLabel(header_frame, image=logo_photo, text="")
                logo_label.pack(side="left", padx=10)
        except Exception as e:
            print(f"No se pudo cargar el logo: {e}")

        # Título al lado del logo
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.pack(side="left", padx=10)

        ctk.CTkLabel(
            title_frame,
            text="PyCraft",
            font=ctk.CTkFont(size=32, weight="bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_frame,
            text="Minecraft Server Manager",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        ).pack(anchor="w")

        # Separador
        ctk.CTkFrame(self.root, height=2, fg_color="gray30").pack(fill="x", padx=20)

        # TabView para las 3 secciones
        self.tabview = ctk.CTkTabview(self.root, width=950, height=650)
        self.tabview.pack(pady=10, padx=20, fill="both", expand=True)

        # Crear las 3 tabs
        self.tabview.add("Servidor Vanilla")
        self.tabview.add("Servidor con Mods")
        self.tabview.add("Información y Ayuda")

        # Crear contenido de cada tab
        self._create_vanilla_tab()
        self._create_mods_tab()
        self._create_info_tab()

    def _create_vanilla_tab(self):
        """Crea la sección de servidor vanilla"""
        tab = self.tabview.tab("Servidor Vanilla")

        # Frame principal con scroll
        main_container = ctk.CTkScrollableFrame(tab, width=920, height=580)
        main_container.pack(pady=10, padx=10, fill="both", expand=True)

        # Selector de modo (Nuevo vs Existente)
        mode_frame = ctk.CTkFrame(main_container, fg_color="gray15")
        mode_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(
            mode_frame,
            text="¿Qué quieres hacer?",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(15, 10))

        # Segmented button para elegir modo
        self.mode_selector = ctk.CTkSegmentedButton(
            mode_frame,
            values=["Crear Servidor Nuevo", "Abrir Servidor Existente"],
            command=self._on_mode_change,
            width=700,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.mode_selector.pack(pady=(5, 15))
        self.mode_selector.set("Crear Servidor Nuevo")

        # Separador
        ctk.CTkFrame(main_container, height=2, fg_color="gray30").pack(pady=10, fill="x")

        # ===== FRAME PARA CREAR SERVIDOR NUEVO =====
        self.new_server_frame = ctk.CTkFrame(main_container)
        self.new_server_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(
            self.new_server_frame,
            text="Crear Servidor Nuevo",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)

        # Frame de selección de versión
        version_frame = ctk.CTkFrame(self.new_server_frame, fg_color="transparent")
        version_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(
            version_frame,
            text="Versión de Minecraft:",
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", pady=(0, 5))

        # Campo de búsqueda
        self.search_entry = ctk.CTkEntry(
            version_frame,
            placeholder_text="Buscar versión (ej: 1.20, 1.19.4)...",
            width=400,
            height=35
        )
        self.search_entry.pack(pady=5)
        self.search_entry.bind("<KeyRelease>", self._on_search_change)

        # Frame para el scrollable de versiones
        version_select_frame = ctk.CTkFrame(version_frame, fg_color="transparent")
        version_select_frame.pack(pady=5)

        ctk.CTkLabel(
            version_select_frame,
            text="Versiones disponibles:",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).pack(anchor="w")

        # ScrollableFrame para versiones (mejor UX que ComboBox largo)
        self.version_scrollable = ctk.CTkScrollableFrame(
            version_select_frame,
            width=400,
            height=150,
            label_text="Selecciona una versión"
        )
        self.version_scrollable.pack(pady=5)

        self.version_buttons = []

        # Label de versión seleccionada
        self.selected_version_label = ctk.CTkLabel(
            version_frame,
            text="Ninguna versión seleccionada",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="orange"
        )
        self.selected_version_label.pack(pady=10)

        # Botón para seleccionar carpeta (para servidor nuevo)
        folder_frame_new = ctk.CTkFrame(self.new_server_frame, fg_color="transparent")
        folder_frame_new.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(
            folder_frame_new,
            text="Carpeta de destino:",
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", pady=(0, 5))

        self.select_folder_new_btn = ctk.CTkButton(
            folder_frame_new,
            text="Seleccionar Carpeta de Destino",
            command=self._select_folder_new,
            width=400,
            height=35
        )
        self.select_folder_new_btn.pack(pady=5)

        # Label de carpeta seleccionada
        self.folder_label_new = ctk.CTkLabel(
            folder_frame_new,
            text="No se ha seleccionado carpeta",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        self.folder_label_new.pack(pady=5)

        # Botón de descarga
        self.download_btn = ctk.CTkButton(
            self.new_server_frame,
            text="Descargar e Instalar Servidor",
            command=self._download_and_setup,
            width=400,
            height=40,
            state="disabled",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.download_btn.pack(pady=15)

        # Barra de progreso
        self.progress_bar = ctk.CTkProgressBar(
            self.new_server_frame,
            width=400
        )
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            self.new_server_frame,
            text="",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        self.progress_label.pack()

        # ===== FRAME PARA ABRIR SERVIDOR EXISTENTE =====
        self.existing_server_frame = ctk.CTkFrame(main_container)
        # No hacemos pack() todavía, se mostrará al cambiar de modo

        ctk.CTkLabel(
            self.existing_server_frame,
            text="Abrir Servidor Existente",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)

        ctk.CTkLabel(
            self.existing_server_frame,
            text="Selecciona la carpeta donde tienes tu servidor de Minecraft",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        ).pack(pady=(0, 20))

        # Botón para seleccionar carpeta existente
        self.select_existing_btn = ctk.CTkButton(
            self.existing_server_frame,
            text="Seleccionar Carpeta del Servidor",
            command=self._select_existing_server,
            width=400,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.select_existing_btn.pack(pady=10)

        # Label de carpeta seleccionada
        self.folder_label_existing = ctk.CTkLabel(
            self.existing_server_frame,
            text="No se ha seleccionado carpeta",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        self.folder_label_existing.pack(pady=10)

        # Label de estado del servidor
        self.server_status_label = ctk.CTkLabel(
            self.existing_server_frame,
            text="",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.server_status_label.pack(pady=5)

        # Separador compartido
        ctk.CTkFrame(main_container, height=2, fg_color="gray30").pack(pady=10, fill="x")

        # ===== CONSOLA PARA CREAR SERVIDOR NUEVO =====
        self.new_server_console_frame = ctk.CTkFrame(main_container)
        self.new_server_console_frame.pack(pady=10, padx=10, fill="both", expand=True)

        ctk.CTkLabel(
            self.new_server_console_frame,
            text="Proceso de Creación",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)

        # TextBox para logs de creación
        self.new_log_text = ctk.CTkTextbox(
            self.new_server_console_frame,
            width=900,
            height=250,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word"
        )
        self.new_log_text.pack(pady=5, padx=10)

        # ===== CONSOLA Y CONTROLES PARA SERVIDOR EXISTENTE =====
        self.existing_server_console_frame = ctk.CTkFrame(main_container)
        # No hacer pack todavía, se mostrará al cambiar de modo

        ctk.CTkLabel(
            self.existing_server_console_frame,
            text="Consola del Servidor",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)

        # TextBox para logs del servidor
        self.existing_log_text = ctk.CTkTextbox(
            self.existing_server_console_frame,
            width=900,
            height=200,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word"
        )
        self.existing_log_text.pack(pady=5, padx=10)

        # Campo de input para comandos
        command_frame = ctk.CTkFrame(self.existing_server_console_frame, fg_color="transparent")
        command_frame.pack(pady=5, padx=10, fill="x")

        ctk.CTkLabel(
            command_frame,
            text="Enviar comando al servidor:",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).pack(side="left", padx=(0, 10))

        self.command_entry = ctk.CTkEntry(
            command_frame,
            placeholder_text="Ej: list, op jugador, stop, gamemode creative...",
            width=600,
            height=35
        )
        self.command_entry.pack(side="left", padx=5)
        self.command_entry.bind("<Return>", self._send_command)

        self.send_command_btn = ctk.CTkButton(
            command_frame,
            text="Enviar",
            command=lambda: self._send_command(None),
            width=100,
            height=35,
            state="disabled"
        )
        self.send_command_btn.pack(side="left", padx=5)

        # Botones de control del servidor
        control_frame = ctk.CTkFrame(self.existing_server_console_frame, fg_color="transparent")
        control_frame.pack(pady=10)

        self.start_server_btn = ctk.CTkButton(
            control_frame,
            text="Iniciar Servidor",
            command=self._start_server,
            width=200,
            height=35,
            state="disabled",
            fg_color="green",
            hover_color="darkgreen"
        )
        self.start_server_btn.pack(side="left", padx=5)

        self.stop_server_btn = ctk.CTkButton(
            control_frame,
            text="Detener Servidor",
            command=self._stop_server,
            width=200,
            height=35,
            state="disabled",
            fg_color="red",
            hover_color="darkred"
        )
        self.stop_server_btn.pack(side="left", padx=5)

        # Inicializar logs
        self._add_log_new("Bienvenido a PyCraft - Creador de Servidores\n", "info")
        self._add_log_new("Selecciona una versión y una carpeta para comenzar.\n", "info")

        self._add_log_existing("Consola del servidor\n", "info")
        self._add_log_existing("Selecciona la carpeta de tu servidor para comenzar.\n", "info")

        # Actualizar el estado inicial del botón
        self._update_download_button_state()

    def _create_mods_tab(self):
        """Crea la sección de servidor con mods (solo UI, sin funcionalidad)"""
        tab = self.tabview.tab("Servidor con Mods")

        # Frame principal
        main_frame = ctk.CTkFrame(tab)
        main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Título
        ctk.CTkLabel(
            main_frame,
            text="Servidor de Minecraft con Mods",
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=20)

        # Descripción
        description = ctk.CTkTextbox(
            main_frame,
            width=800,
            height=150,
            font=ctk.CTkFont(size=13)
        )
        description.pack(pady=20)
        description.insert("1.0",
            "Esta sección te permitirá crear servidores de Minecraft con mods (Forge/Fabric).\n\n"
            "PRÓXIMAMENTE:\n"
            "• Creación de servidor con Forge\n"
            "• Creación de servidor con Fabric\n"
            "• Instalación automática de mods\n"
            "• Gestión de configuraciones de mods\n\n"
            "IMPORTANTE: Para usar esta función, primero debes tener un servidor vanilla creado.\n\n"
            "Esta funcionalidad estará disponible en futuras versiones de PyCraft."
        )
        description.configure(state="disabled")

        # Botones (deshabilitados)
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=30)

        ctk.CTkButton(
            button_frame,
            text="Crear Servidor Completo con Mods",
            width=300,
            height=40,
            state="disabled",
            font=ctk.CTkFont(size=14)
        ).pack(pady=10)

        ctk.CTkButton(
            button_frame,
            text="Agregar Mods a Servidor Existente",
            width=300,
            height=40,
            state="disabled",
            font=ctk.CTkFont(size=14)
        ).pack(pady=10)

        # Label de estado
        ctk.CTkLabel(
            main_frame,
            text="En desarrollo - Próximamente disponible",
            font=ctk.CTkFont(size=12),
            text_color="orange"
        ).pack(pady=20)

    def _create_info_tab(self):
        """Crea la sección de información y ayuda"""
        tab = self.tabview.tab("Información y Ayuda")

        # Frame principal con scroll
        main_frame = ctk.CTkScrollableFrame(tab, width=900, height=600)
        main_frame.pack(pady=10, padx=10, fill="both", expand=True)

        # Título
        ctk.CTkLabel(
            main_frame,
            text="Guía Completa de PyCraft",
            font=ctk.CTkFont(size=26, weight="bold")
        ).pack(pady=20)

        # Sección: Requisitos
        self._create_info_section(
            main_frame,
            "Requisitos del Sistema",
            """
Para usar PyCraft y crear servidores de Minecraft necesitas:

• Java Development Kit (JDK) 17 o superior instalado
  Descarga: https://www.oracle.com/java/technologies/downloads/

• Espacio en disco: Mínimo 2 GB libres

• RAM: Mínimo 4 GB (se recomienda 8 GB o más)

• Sistema Operativo: Windows 10/11, Linux o macOS

• Conexión a Internet para descargar los archivos del servidor
            """
        )

        # Sección: Cómo usar
        self._create_info_section(
            main_frame,
            "Cómo Crear un Servidor Vanilla",
            """
Paso 1: Selecciona una Versión
   • Ve a la pestaña "Servidor Vanilla"
   • Busca la versión de Minecraft que deseas (ej: 1.20.1)
   • Haz clic en la versión para seleccionarla

Paso 2: Elige la Carpeta de Destino
   • Haz clic en "Seleccionar Carpeta de Destino"
   • Elige dónde quieres instalar el servidor

Paso 3: Descarga e Instala
   • Haz clic en "Descargar e Instalar Servidor"
   • Espera a que se complete la descarga y configuración
   • PyCraft configurará automáticamente el servidor por ti

Paso 4: Inicia el Servidor
   • Una vez completada la configuración, haz clic en "Iniciar Servidor"
   • El servidor comenzará a ejecutarse
   • Los logs aparecerán en la consola
            """
        )

        # Sección: Jugar con amigos (Hamachi)
        self._create_info_section(
            main_frame,
            "Jugar con Amigos usando Hamachi",
            """
Hamachi es una VPN que permite a tus amigos conectarse a tu servidor.

Paso 1: Descargar Hamachi
   • Descarga Hamachi desde: https://www.vpn.net/
   • Instala Hamachi en tu computadora

Paso 2: Crear una Red
   • Abre Hamachi
   • Haz clic en "Crear nueva red"
   • Elige un ID de red y una contraseña
   • Comparte el ID y contraseña con tus amigos

Paso 3: Tus Amigos se Unen
   • Tus amigos deben instalar Hamachi
   • Deben unirse a tu red usando el ID y contraseña

Paso 4: Obtener tu IP de Hamachi
   • En Hamachi, verás tu dirección IPv4 (ejemplo: 25.123.45.67)
   • Esta es la dirección que tus amigos usarán para conectarse

Paso 5: Conectarse en Minecraft
   • Tus amigos abren Minecraft
   • Van a "Multijugador" → "Agregar Servidor"
   • Usan tu IPv4 de Hamachi como dirección
   • Si cambiaste el puerto, agregan: 25.123.45.67:25565

IMPORTANTE:
   • Todos deben estar en la misma red de Hamachi
   • El servidor debe estar iniciado antes de que intenten conectarse
   • Windows Firewall puede pedir permiso - acéptalo
   • PyCraft ya configura automáticamente online-mode en false
            """
        )

        # Sección: Otras VPN
        self._create_info_section(
            main_frame,
            "Alternativas a Hamachi",
            """
También puedes usar otras VPN o métodos:

• Radmin VPN (Gratis, sin límite de usuarios)
  Descarga: https://www.radmin-vpn.com/

• ZeroTier (Gratis, más técnico pero muy potente)
  Descarga: https://www.zerotier.com/

• Port Forwarding (Avanzado)
  Requiere configurar tu router - más complejo pero más estable

• Playit.gg (Gratis, específico para gaming)
  Descarga: https://playit.gg/
            """
        )

        # Sección: Configuración del servidor
        self._create_info_section(
            main_frame,
            "Configuración del Servidor (server.properties)",
            """
PyCraft configura automáticamente:
   • online-mode=false (permite conexiones sin verificar con Mojang)
   • difficulty=normal (dificultad normal del juego)

Puedes editar manualmente el archivo server.properties para cambiar:
   • gamemode - Modo de juego (survival, creative, adventure, spectator)
   • max-players - Máximo de jugadores
   • pvp - Activar/desactivar PvP
   • spawn-protection - Protección del spawn
   • view-distance - Distancia de renderizado
   • motd - Mensaje del día (se ve en la lista de servidores)

El archivo server.properties está en la carpeta donde instalaste el servidor.
            """
        )

        # Sección: Solución de problemas
        self._create_info_section(
            main_frame,
            "Solución de Problemas Comunes",
            """
Problema: "Error al iniciar servidor"
   Solución: Verifica que Java esté instalado correctamente
   Comando para verificar: abre cmd y escribe: java -version

Problema: "Mis amigos no pueden conectarse"
   Solución:
   • Verifica que todos estén en la misma red de Hamachi
   • Verifica que el servidor esté iniciado
   • Revisa el firewall de Windows
   • Confirma que uses la IPv4 correcta de Hamachi

Problema: "El servidor se cierra inmediatamente"
   Solución:
   • Revisa los logs en la consola
   • Verifica que tengas suficiente RAM disponible
   • Asegúrate de que el puerto 25565 no esté en uso

Problema: "Java no se encuentra"
   Solución:
   • Descarga e instala Java desde oracle.com
   • Reinicia tu computadora después de instalar
   • Verifica la instalación con: java -version
            """
        )

        # Pie de página
        ctk.CTkLabel(
            main_frame,
            text="PyCraft - Simplificando la creación de servidores de Minecraft",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(pady=30)

    def _create_info_section(self, parent, title, content):
        """Crea una sección de información con título y contenido"""
        section_frame = ctk.CTkFrame(parent, fg_color="gray20")
        section_frame.pack(pady=10, padx=10, fill="x")

        # Título de la sección
        ctk.CTkLabel(
            section_frame,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#4CAF50"
        ).pack(pady=10, padx=10, anchor="w")

        # Contenido
        content_label = ctk.CTkLabel(
            section_frame,
            text=content.strip(),
            font=ctk.CTkFont(size=12),
            justify="left",
            anchor="w"
        )
        content_label.pack(pady=10, padx=20, anchor="w")

    def _load_versions(self):
        """Carga las versiones desde la API"""
        self._add_log_new("Cargando versiones de Minecraft desde la API...\n", "info")

        def load():
            versions = self.api_handler.get_version_names()
            if versions:
                self.versions_list = versions
                self.filtered_versions = versions.copy()
                self._populate_version_buttons(versions)
                self._add_log_new(f"✓ Se cargaron {len(versions)} versiones correctamente\n", "success")
            else:
                self._add_log_new("✗ Error al cargar versiones desde la API de Mojang\n", "error")
                messagebox.showerror("Error", "No se pudieron cargar las versiones de Minecraft")

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    def _populate_version_buttons(self, versions):
        """Crea botones para cada versión en el scrollable frame"""
        # Limpiar botones existentes
        for widget in self.version_scrollable.winfo_children():
            widget.destroy()
        self.version_buttons.clear()

        # Crear botones para cada versión
        for version in versions:
            btn = ctk.CTkButton(
                self.version_scrollable,
                text=version,
                width=380,
                height=30,
                command=lambda v=version: self._on_version_select(v),
                fg_color="gray25",
                hover_color="gray35"
            )
            btn.pack(pady=2, padx=5)
            self.version_buttons.append(btn)

    def _on_search_change(self, event):
        """Filtra las versiones según el texto de búsqueda"""
        search_text = self.search_entry.get().lower()

        if not search_text:
            self.filtered_versions = self.versions_list.copy()
        else:
            self.filtered_versions = [
                v for v in self.versions_list
                if search_text in v.lower()
            ]

        self._populate_version_buttons(self.filtered_versions)

    def _on_version_select(self, version):
        """Maneja la selección de una versión"""
        self.selected_version = version
        self.selected_version_label.configure(
            text=f"Versión seleccionada: {version}",
            text_color="green"
        )
        self._add_log_new(f"✓ Versión seleccionada: {version}\n", "info")
        self._update_download_button_state()

        # Destacar el botón seleccionado
        for btn in self.version_buttons:
            if btn.cget("text") == version:
                btn.configure(fg_color="blue", hover_color="darkblue")
            else:
                btn.configure(fg_color="gray25", hover_color="gray35")

    def _on_mode_change(self, value):
        """Cambia entre modo crear nuevo y abrir existente"""
        if value == "Crear Servidor Nuevo":
            # Mostrar frames de servidor nuevo
            self.existing_server_frame.pack_forget()
            self.existing_server_console_frame.pack_forget()
            self.new_server_frame.pack(pady=10, padx=10, fill="x", before=self.existing_server_frame.master.winfo_children()[-3])
            self.new_server_console_frame.pack(pady=10, padx=10, fill="both", expand=True)
            self._add_log_new("\n=== Modo: Crear Servidor Nuevo ===\n", "info")
        else:  # "Abrir Servidor Existente"
            # Mostrar frames de servidor existente
            self.new_server_frame.pack_forget()
            self.new_server_console_frame.pack_forget()
            self.existing_server_frame.pack(pady=10, padx=10, fill="x", before=self.new_server_frame.master.winfo_children()[-3])
            self.existing_server_console_frame.pack(pady=10, padx=10, fill="both", expand=True)
            self._add_log_existing("\n=== Modo: Abrir Servidor Existente ===\n", "info")

    def _select_folder_new(self):
        """Abre el diálogo para seleccionar carpeta para servidor nuevo"""
        folder = filedialog.askdirectory(title="Seleccionar carpeta para crear el servidor")
        if folder:
            self.server_folder = folder
            self.folder_label_new.configure(
                text=f"Carpeta: {folder}",
                text_color="white"
            )
            self._add_log_new(f"Carpeta seleccionada: {folder}\n", "info")
            self._update_download_button_state()

    def _select_existing_server(self):
        """Abre el diálogo para seleccionar carpeta con servidor existente"""
        folder = filedialog.askdirectory(title="Seleccionar carpeta del servidor existente")
        if folder:
            # Verificar que exista server.jar
            if self._detect_existing_server(folder):
                self.server_folder = folder
                self.folder_label_existing.configure(
                    text=f"Carpeta: {folder}",
                    text_color="white"
                )
                self.server_status_label.configure(
                    text="✓ Servidor encontrado - Listo para iniciar",
                    text_color="green"
                )

                # Limpiar consola y mostrar mensaje de bienvenida
                self.existing_log_text.configure(state="normal")
                self.existing_log_text.delete("1.0", "end")
                self.existing_log_text.configure(state="disabled")

                self._add_log_existing("╔═══════════════════════════════════════════════════════╗\n", "success")
                self._add_log_existing("║          ✓ SERVIDOR ENCONTRADO Y LISTO               ║\n", "success")
                self._add_log_existing("╚═══════════════════════════════════════════════════════╝\n", "success")
                self._add_log_existing(f"\nCarpeta: {folder}\n", "info")
                self._add_log_existing("\nEl servidor está listo para iniciar.\n", "info")
                self._add_log_existing("Haz clic en el botón 'Iniciar Servidor' para comenzar.\n\n", "info")

                # Configurar el server manager
                self.server_manager = ServerManager(folder)
                self.is_server_configured = True
                self.start_server_btn.configure(state="normal")
            else:
                self.server_status_label.configure(
                    text="✗ No se encontró server.jar en esta carpeta",
                    text_color="red"
                )
                self._add_log_existing(f"\n✗ Error: No se encontró server.jar en {folder}\n", "error")
                self._add_log_existing("Asegúrate de seleccionar la carpeta correcta donde está tu servidor\n", "warning")
                messagebox.showerror(
                    "Servidor no encontrado",
                    "No se encontró server.jar en la carpeta seleccionada.\n\n"
                    "Por favor, selecciona la carpeta donde tienes tu servidor de Minecraft."
                )

    def _update_download_button_state(self):
        """Actualiza el estado del botón de descarga"""
        if self.selected_version and self.server_folder:
            self.download_btn.configure(state="normal", fg_color=("#3B8ED0", "#1F6AA5"))
            self.progress_label.configure(text="¡Listo para descargar!", text_color="green")
        else:
            self.download_btn.configure(state="disabled")
            # Mostrar qué falta
            if not self.selected_version and not self.server_folder:
                self.progress_label.configure(text="Falta: seleccionar versión y carpeta", text_color="orange")
            elif not self.selected_version:
                self.progress_label.configure(text="Falta: seleccionar una versión", text_color="orange")
            elif not self.server_folder:
                self.progress_label.configure(text="Falta: seleccionar carpeta de destino", text_color="orange")

    def _download_and_setup(self):
        """Descarga el servidor y realiza la configuración inicial"""
        if not self.selected_version or not self.server_folder:
            messagebox.showwarning("Advertencia", "Selecciona una versión y una carpeta primero")
            return

        # Deshabilitar botones durante el proceso
        self.download_btn.configure(state="disabled")
        self.select_folder_new_btn.configure(state="disabled")
        self.search_entry.configure(state="disabled")

        def process():
            try:
                # Obtener URL del server.jar
                self._add_log_new(f"\nObteniendo información del servidor para Minecraft {self.selected_version}...\n", "info")
                url = self.api_handler.get_server_jar_url(self.selected_version)

                if not url:
                    self._add_log_new("Error: No se pudo obtener la URL del servidor desde la API de Mojang\n", "error")
                    messagebox.showerror("Error", "No se pudo obtener la URL del servidor")
                    return

                self._add_log_new(f"URL del servidor obtenida correctamente\n", "success")

                # Descargar servidor
                self._add_log_new("\nIniciando descarga del servidor...\n", "info")
                self.progress_label.configure(text="Descargando servidor...")

                server_path = self.downloader.download_server(
                    url,
                    self.server_folder,
                    self.selected_version,
                    progress_callback=self._update_progress
                )

                if not server_path:
                    self._add_log_new("Error: La descarga del servidor falló\n", "error")
                    messagebox.showerror("Error", "No se pudo descargar el servidor")
                    return

                self._add_log_new("Descarga completada exitosamente\n", "success")
                self.progress_label.configure(text="Descarga completada")

                # Configurar servidor
                self._add_log_new("\nConfigurando servidor (primera ejecución)...\n", "info")
                self._add_log_new("Esto puede tomar un momento...\n", "warning")
                self.progress_label.configure(text="Configurando servidor...")

                self.server_manager = ServerManager(self.server_folder)
                success = self.server_manager.run_server_first_time(log_callback=self._add_log_new_simple)

                if success:
                    self._add_log_new("\n¡Configuración completada!\n", "success")
                    self.progress_label.configure(text="¡Servidor creado exitosamente!")

                    # Mensaje grande de éxito
                    self._add_log_new("\n\n", "normal")
                    self._add_log_new("╔═══════════════════════════════════════════════════════╗\n", "success")
                    self._add_log_new("║                                                       ║\n", "success")
                    self._add_log_new("║        ✓ SERVIDOR CREADO EXITOSAMENTE               ║\n", "success")
                    self._add_log_new("║                                                       ║\n", "success")
                    self._add_log_new("╚═══════════════════════════════════════════════════════╝\n", "success")
                    self._add_log_new("\n", "normal")
                    self._add_log_new("Configuración aplicada:\n", "info")
                    self._add_log_new("  • EULA aceptado automáticamente\n", "info")
                    self._add_log_new("  • online-mode: false (para jugar con amigos)\n", "info")
                    self._add_log_new("  • difficulty: normal\n\n", "info")
                    self._add_log_new("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n", "warning")
                    self._add_log_new("          PRÓXIMO PASO:\n\n", "warning")
                    self._add_log_new("  Ve a la pestaña 'Abrir Servidor Existente'\n", "info")
                    self._add_log_new("  para iniciar y controlar tu servidor.\n\n", "info")
                    self._add_log_new("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n", "warning")

                    self.is_server_configured = False  # No permitir iniciar desde aquí

                    messagebox.showinfo(
                        "¡Servidor Creado!",
                        "¡Servidor creado exitosamente!\n\n"
                        "Configuración aplicada:\n"
                        "• EULA aceptado\n"
                        "• online-mode: false\n"
                        "• difficulty: normal\n\n"
                        "Ve a la pestaña 'Abrir Servidor Existente'\n"
                        "para iniciar tu servidor."
                    )
                else:
                    self._add_log_new("\nError durante la configuración del servidor\n", "error")
                    messagebox.showerror("Error", "Hubo un error durante la configuración del servidor")

            except Exception as e:
                self._add_log_new(f"\nError inesperado: {str(e)}\n", "error")
                messagebox.showerror("Error", f"Error durante el proceso: {str(e)}")

            finally:
                # Re-habilitar botones
                self.download_btn.configure(state="normal")
                self.select_folder_new_btn.configure(state="normal")
                self.search_entry.configure(state="normal")
                self.progress_bar.set(0)

        thread = threading.Thread(target=process, daemon=True)
        thread.start()

    def _update_progress(self, progress: int):
        """Actualiza la barra de progreso"""
        self.progress_bar.set(progress / 100)
        self.progress_label.configure(text=f"Descargando... {progress}%")

    def _start_server(self):
        """Inicia el servidor de Minecraft"""
        if not self.server_manager or not self.is_server_configured:
            messagebox.showwarning("Advertencia", "Primero debes seleccionar una carpeta con un servidor")
            return

        self._add_log_existing("\n=== INICIANDO SERVIDOR ===\n", "info")
        self._add_log_existing("El servidor está arrancando...\n", "info")
        self.start_server_btn.configure(state="disabled")
        self.stop_server_btn.configure(state="normal")

        def start():
            success = self.server_manager.start_server(
                log_callback=self._add_log_existing_simple,
                detached=True
            )
            if not success:
                self._add_log_existing("\n✗ Error al iniciar el servidor\n", "error")
                self.start_server_btn.configure(state="normal")
                self.stop_server_btn.configure(state="disabled")
                self.send_command_btn.configure(state="disabled")
            else:
                # El mensaje de "servidor listo" se mostrará automáticamente
                # cuando se detecte el "Done" en los logs
                # Habilitar el botón de comandos
                self.send_command_btn.configure(state="normal")

        thread = threading.Thread(target=start, daemon=True)
        thread.start()

    def _stop_server(self):
        """Detiene el servidor de Minecraft"""
        if not self.server_manager:
            return

        self._add_log_existing("\n=== DETENIENDO SERVIDOR ===\n", "warning")
        success = self.server_manager.stop_server()

        if success:
            self._add_log_existing("✓ Servidor detenido correctamente\n\n", "info")
        else:
            self._add_log_existing("✗ Error al detener el servidor o el servidor no estaba en ejecución\n", "error")

        self.start_server_btn.configure(state="normal")
        self.stop_server_btn.configure(state="disabled")
        self.send_command_btn.configure(state="disabled")

    def _add_log_new(self, message: str, log_type: str = "normal"):
        """
        Añade un mensaje a la consola de CREAR SERVIDOR NUEVO

        log_type puede ser: 'normal', 'info', 'success', 'warning', 'error'
        """
        self.new_log_text.configure(state="normal")

        # Configurar tags de colores si no existen
        self.new_log_text.tag_config("info", foreground="#2196F3")  # Azul
        self.new_log_text.tag_config("success", foreground="#4CAF50")  # Verde
        self.new_log_text.tag_config("warning", foreground="#FF9800")  # Naranja
        self.new_log_text.tag_config("error", foreground="#F44336")  # Rojo
        self.new_log_text.tag_config("normal", foreground="white")  # Blanco

        # Insertar el mensaje con el tag apropiado
        self.new_log_text.insert("end", message, log_type)
        self.new_log_text.see("end")
        self.new_log_text.configure(state="disabled")

    def _add_log_new_simple(self, message: str):
        """Añade un log simple a consola nueva (para callbacks)"""
        self._add_log_new(message, "normal")

    def _add_log_existing(self, message: str, log_type: str = "normal"):
        """
        Añade un mensaje a la consola de ABRIR SERVIDOR EXISTENTE

        log_type puede ser: 'normal', 'info', 'success', 'warning', 'error'
        """
        self.existing_log_text.configure(state="normal")

        # Configurar tags de colores si no existen
        self.existing_log_text.tag_config("info", foreground="#2196F3")  # Azul
        self.existing_log_text.tag_config("success", foreground="#4CAF50")  # Verde
        self.existing_log_text.tag_config("warning", foreground="#FF9800")  # Naranja
        self.existing_log_text.tag_config("error", foreground="#F44336")  # Rojo
        self.existing_log_text.tag_config("normal", foreground="white")  # Blanco

        # Insertar el mensaje con el tag apropiado
        self.existing_log_text.insert("end", message, log_type)
        self.existing_log_text.see("end")
        self.existing_log_text.configure(state="disabled")

    def _add_log_existing_simple(self, message: str):
        """Añade un log simple a consola existente (para callbacks)"""
        self._add_log_existing(message, "normal")

        # Detectar cuando el servidor está listo
        if "Done" in message and "For help, type" in message:
            self._add_log_existing("\n", "normal")
            self._add_log_existing("╔═══════════════════════════════════════════════════════╗\n", "success")
            self._add_log_existing("║                                                       ║\n", "success")
            self._add_log_existing("║      ✓ ¡SERVIDOR LISTO Y FUNCIONANDO!               ║\n", "success")
            self._add_log_existing("║                                                       ║\n", "success")
            self._add_log_existing("╚═══════════════════════════════════════════════════════╝\n", "success")
            self._add_log_existing("\nLos jugadores ya pueden conectarse al servidor.\n", "info")
            self._add_log_existing("Puedes enviar comandos usando el campo de abajo.\n\n", "info")

    def _send_command(self, event):
        """Envía un comando al servidor en ejecución"""
        command = self.command_entry.get().strip()
        if not command:
            return

        if not self.server_manager or not self.server_manager.is_server_running():
            self._add_log_existing("✗ Error: El servidor no está en ejecución\n", "error")
            return

        # Mostrar el comando en la consola
        self._add_log_existing(f"> {command}\n", "info")

        # Enviar el comando
        success = self.server_manager.send_command(command)
        if not success:
            self._add_log_existing("✗ Error al enviar comando\n", "error")

        # Limpiar el campo
        self.command_entry.delete(0, 'end')

    def _detect_existing_server(self, folder: str) -> bool:
        """
        Detecta si ya existe un servidor en la carpeta seleccionada

        Returns:
            True si existe un server.jar, False en caso contrario
        """
        server_jar_path = os.path.join(folder, "server.jar")
        return os.path.exists(server_jar_path)

    def _on_closing(self):
        """Maneja el cierre de la aplicación"""
        if self.server_manager and self.server_manager.is_server_running():
            response = messagebox.askyesno(
                "Servidor en ejecución",
                "El servidor está en ejecución. ¿Deseas detenerlo y cerrar PyCraft?"
            )
            if response:
                self._add_log_existing("\nCerrando PyCraft y deteniendo servidor...\n", "warning")
                self.server_manager.stop_server()
                # Dar tiempo para que el servidor se detenga
                self.root.after(500, self._force_close)
            # Si el usuario cancela, no hacer nada
        else:
            self._force_close()

    def _force_close(self):
        """Fuerza el cierre de la aplicación"""
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass

    def run(self):
        """Inicia la aplicación"""
        # Configurar el protocolo de cierre
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.mainloop()
