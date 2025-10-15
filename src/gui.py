import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import threading
import os
import shutil
import json
from typing import Optional, Dict, List

from src.api_handler import MinecraftAPIHandler, ModrinthAPI, CurseForgeAPI, APIConfig
from src.downloader import ServerDownloader
from src.server_manager import ServerManager
from src.modpack_manager import ModpackManager


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
        self.modpack_manager = ModpackManager()
        self.api_config = APIConfig()

        # Cargar API key de CurseForge si existe
        cf_key = self.api_config.get_curseforge_key()
        if cf_key:
            self.modpack_manager.set_curseforge_api_key(cf_key)

        # Variables
        self.versions_list = []
        self.filtered_versions = []
        self.selected_version = None
        self.server_folder = None
        self.is_server_configured = False

        # Variables para modpacks
        self.modpack_search_results = []
        self.selected_modpack = None
        self.selected_modpack_version = None
        self.modpack_server_folder = None

        # Variables para servidor con modpack
        self.modpack_server_manager: Optional[ServerManager] = None
        self.modpack_server_path = None
        self.is_modpack_server_configured = False

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
                # Redimensionar el logo (mucho más grande y visible)
                logo_image = logo_image.resize((180, 180), Image.Resampling.LANCZOS)
                logo_photo = ctk.CTkImage(light_image=logo_image, dark_image=logo_image, size=(180, 180))

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

        # Crear las 4 tabs
        self.tabview.add("Servidor Vanilla")
        self.tabview.add("Servidor con Mods")
        self.tabview.add("Información y Ayuda")
        self.tabview.add("Configuración")

        # Crear contenido de cada tab
        self._create_vanilla_tab()
        self._create_mods_tab()
        self._create_info_tab()
        self._create_settings_tab()

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
        """Crea la sección de servidor con mods/modpacks"""
        tab = self.tabview.tab("Servidor con Mods")

        # Frame principal con scroll
        main_container = ctk.CTkScrollableFrame(tab, width=920, height=580)
        main_container.pack(pady=10, padx=10, fill="both", expand=True)

        # Título
        ctk.CTkLabel(
            main_container,
            text="Crear Servidor con Modpack",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(pady=15)

        ctk.CTkLabel(
            main_container,
            text="Descarga e instala modpacks completos desde Modrinth o CurseForge",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        ).pack(pady=(0, 15))

        # Selector de plataforma
        platform_frame = ctk.CTkFrame(main_container, fg_color="gray15")
        platform_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(
            platform_frame,
            text="Plataforma de Modpacks",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(15, 10))

        self.platform_selector = ctk.CTkSegmentedButton(
            platform_frame,
            values=["Modrinth (Recomendado)", "CurseForge (Requiere API Key)"],
            command=self._on_platform_change,
            width=700,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.platform_selector.pack(pady=(5, 15))
        self.platform_selector.set("Modrinth (Recomendado)")

        # Indicador de estado de CurseForge
        self.cf_status_label = ctk.CTkLabel(
            platform_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.cf_status_label.pack(pady=(0, 10))
        self._update_cf_status()

        # Separador
        ctk.CTkFrame(main_container, height=2, fg_color="gray30").pack(pady=10, fill="x")

        # Búsqueda de modpacks
        search_frame = ctk.CTkFrame(main_container)
        search_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(
            search_frame,
            text="Buscar Modpacks",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)

        search_input_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_input_frame.pack(pady=5)

        self.modpack_search_entry = ctk.CTkEntry(
            search_input_frame,
            placeholder_text="Ej: Create, ATM9, RLCraft, Vault Hunters...",
            width=500,
            height=35
        )
        self.modpack_search_entry.pack(side="left", padx=(0, 10))
        self.modpack_search_entry.bind("<Return>", lambda e: self._search_modpacks())

        self.search_modpacks_btn = ctk.CTkButton(
            search_input_frame,
            text="Buscar",
            command=self._search_modpacks,
            width=120,
            height=35
        )
        self.search_modpacks_btn.pack(side="left")

        # Resultados de búsqueda
        ctk.CTkLabel(
            search_frame,
            text="Resultados:",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).pack(anchor="w", padx=20, pady=(15, 5))

        self.modpack_results_frame = ctk.CTkScrollableFrame(
            search_frame,
            width=860,
            height=180
        )
        self.modpack_results_frame.pack(pady=5, padx=10)

        # Label inicial
        self.no_results_label = ctk.CTkLabel(
            self.modpack_results_frame,
            text="Usa la búsqueda para encontrar modpacks",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.no_results_label.pack(pady=20)

        # Modpack seleccionado
        self.selected_modpack_label = ctk.CTkLabel(
            search_frame,
            text="Ningún modpack seleccionado",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="orange"
        )
        self.selected_modpack_label.pack(pady=10)

        # Separador
        ctk.CTkFrame(main_container, height=2, fg_color="gray30").pack(pady=10, fill="x")

        # Carpeta de destino
        folder_frame = ctk.CTkFrame(main_container)
        folder_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(
            folder_frame,
            text="Carpeta de destino:",
            font=ctk.CTkFont(size=14)
        ).pack(anchor="w", pady=(10, 5), padx=20)

        self.select_modpack_folder_btn = ctk.CTkButton(
            folder_frame,
            text="Seleccionar Carpeta para el Servidor",
            command=self._select_modpack_folder,
            width=400,
            height=35
        )
        self.select_modpack_folder_btn.pack(pady=5)

        self.modpack_folder_label = ctk.CTkLabel(
            folder_frame,
            text="No se ha seleccionado carpeta",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        self.modpack_folder_label.pack(pady=(5, 15), padx=20)

        # Botón de instalación
        self.install_modpack_btn = ctk.CTkButton(
            main_container,
            text="Descargar e Instalar Modpack",
            command=self._install_modpack,
            width=400,
            height=45,
            state="disabled",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="green",
            hover_color="darkgreen"
        )
        self.install_modpack_btn.pack(pady=15)

        self.modpack_status_label = ctk.CTkLabel(
            main_container,
            text="",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        self.modpack_status_label.pack()

        # Separador
        ctk.CTkFrame(main_container, height=2, fg_color="gray30").pack(pady=10, fill="x")

        # Consola de instalación
        ctk.CTkLabel(
            main_container,
            text="Proceso de Instalación",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)

        self.modpack_log_text = ctk.CTkTextbox(
            main_container,
            width=900,
            height=200,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word"
        )
        self.modpack_log_text.pack(pady=5, padx=10)

        # Log inicial
        self._add_log_modpack("Bienvenido al instalador de Modpacks de PyCraft\n", "info")
        self._add_log_modpack("Busca un modpack, selecciónalo y elige una carpeta para comenzar.\n\n", "info")
        self._add_log_modpack("NOTA: La instalación automática incluye:\n", "info")
        self._add_log_modpack("  • Descarga del modpack y todos sus mods\n", "normal")
        self._add_log_modpack("  • Instalación automática de Forge o Fabric\n", "normal")
        self._add_log_modpack("  • Verificación e instalación de Java si es necesario\n", "normal")
        self._add_log_modpack("  • Configuración automática del servidor\n\n", "normal")

        # Separador grande
        ctk.CTkFrame(main_container, height=3, fg_color="gray30").pack(pady=20, fill="x")

        # ===== SECCIÓN PARA GESTIONAR SERVIDOR CON MODPACK =====
        ctk.CTkLabel(
            main_container,
            text="Gestionar Servidor con Modpack",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(pady=15)

        ctk.CTkLabel(
            main_container,
            text="Abre y controla tu servidor con modpack ya instalado",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        ).pack(pady=(0, 15))

        # Botón para seleccionar servidor con modpack
        modpack_server_frame = ctk.CTkFrame(main_container)
        modpack_server_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(
            modpack_server_frame,
            text="Selecciona la carpeta de tu servidor con modpack:",
            font=ctk.CTkFont(size=14)
        ).pack(anchor="w", pady=(10, 5), padx=20)

        self.select_modpack_server_btn = ctk.CTkButton(
            modpack_server_frame,
            text="Seleccionar Carpeta del Servidor con Modpack",
            command=self._select_modpack_server,
            width=400,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.select_modpack_server_btn.pack(pady=10)

        # Label de carpeta seleccionada
        self.modpack_server_status_label = ctk.CTkLabel(
            modpack_server_frame,
            text="No se ha seleccionado servidor",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        self.modpack_server_status_label.pack(pady=(5, 10), padx=20)

        # Botón para instalar modpack para el cliente
        self.install_client_btn = ctk.CTkButton(
            modpack_server_frame,
            text="📦 Instalar Modpack para el Cliente",
            command=self._install_client_modpack,
            width=350,
            height=40,
            state="disabled",
            fg_color="#FF6B35",
            hover_color="#E55A2B",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.install_client_btn.pack(pady=10)

        # Label informativo
        ctk.CTkLabel(
            modpack_server_frame,
            text="Instala el modpack en C:/Users/[tu-nombre]/Modrinth/ para poder jugar",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(pady=(0, 15), padx=20)

        # Separador
        ctk.CTkFrame(main_container, height=2, fg_color="gray30").pack(pady=10, fill="x")

        # Consola y controles para servidor con modpack
        ctk.CTkLabel(
            main_container,
            text="Consola del Servidor con Modpack",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)

        # TextBox para logs del servidor con modpack
        self.modpack_server_log_text = ctk.CTkTextbox(
            main_container,
            width=900,
            height=200,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word"
        )
        self.modpack_server_log_text.pack(pady=5, padx=10)

        # Campo de input para comandos
        modpack_command_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        modpack_command_frame.pack(pady=5, padx=10, fill="x")

        ctk.CTkLabel(
            modpack_command_frame,
            text="Enviar comando:",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).pack(side="left", padx=(0, 10))

        self.modpack_command_entry = ctk.CTkEntry(
            modpack_command_frame,
            placeholder_text="Ej: list, op jugador, stop...",
            width=600,
            height=35
        )
        self.modpack_command_entry.pack(side="left", padx=5)
        self.modpack_command_entry.bind("<Return>", self._send_modpack_command)

        self.send_modpack_command_btn = ctk.CTkButton(
            modpack_command_frame,
            text="Enviar",
            command=lambda: self._send_modpack_command(None),
            width=100,
            height=35,
            state="disabled"
        )
        self.send_modpack_command_btn.pack(side="left", padx=5)

        # Botones de control del servidor con modpack
        modpack_control_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        modpack_control_frame.pack(pady=10)

        self.start_modpack_server_btn = ctk.CTkButton(
            modpack_control_frame,
            text="Iniciar Servidor",
            command=self._start_modpack_server,
            width=200,
            height=35,
            state="disabled",
            fg_color="green",
            hover_color="darkgreen"
        )
        self.start_modpack_server_btn.pack(side="left", padx=5)

        self.stop_modpack_server_btn = ctk.CTkButton(
            modpack_control_frame,
            text="Detener Servidor",
            command=self._stop_modpack_server,
            width=200,
            height=35,
            state="disabled",
            fg_color="red",
            hover_color="darkred"
        )
        self.stop_modpack_server_btn.pack(side="left", padx=5)

        # Inicializar logs
        self._add_log_modpack_server("Consola del servidor con modpack\n", "info")
        self._add_log_modpack_server("Selecciona la carpeta de tu servidor para comenzar.\n", "info")

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
        servers_running = []

        if self.server_manager and self.server_manager.is_server_running():
            servers_running.append(("vanilla", self.server_manager))

        if self.modpack_server_manager and self.modpack_server_manager.is_server_running():
            servers_running.append(("modpack", self.modpack_server_manager))

        if servers_running:
            server_types = ", ".join([s[0] for s in servers_running])
            response = messagebox.askyesno(
                "Servidores en ejecución",
                f"Hay servidores en ejecución ({server_types}).\n\n¿Deseas detenerlos y cerrar PyCraft?"
            )
            if response:
                for server_type, manager in servers_running:
                    manager.stop_server()
                # Dar tiempo para que los servidores se detengan
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

    # ==================== MÉTODOS PARA MODPACKS ====================

    def _on_platform_change(self, value):
        """Maneja el cambio de plataforma de modpacks"""
        self._add_log_modpack(f"\nPlataforma cambiada a: {value}\n", "info")

        # Limpiar resultados
        for widget in self.modpack_results_frame.winfo_children():
            widget.destroy()

        self.no_results_label = ctk.CTkLabel(
            self.modpack_results_frame,
            text="Usa la búsqueda para encontrar modpacks",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.no_results_label.pack(pady=20)

        self.selected_modpack = None
        self.selected_modpack_label.configure(text="Ningún modpack seleccionado", text_color="orange")
        self._update_install_modpack_button()

    def _update_cf_status(self):
        """Actualiza el indicador de estado de CurseForge API"""
        if self.modpack_manager.curseforge_api and self.modpack_manager.curseforge_api.is_configured():
            self.cf_status_label.configure(
                text="✓ CurseForge API Key configurada",
                text_color="green"
            )
        else:
            self.cf_status_label.configure(
                text="⚠ CurseForge requiere API Key - Configúrala en la pestaña Configuración",
                text_color="orange"
            )

    def _search_modpacks(self):
        """Busca modpacks en la plataforma seleccionada"""
        query = self.modpack_search_entry.get().strip()

        if not query:
            messagebox.showwarning("Advertencia", "Ingresa un término de búsqueda")
            return

        platform_value = self.platform_selector.get()
        platform = "modrinth" if "Modrinth" in platform_value else "curseforge"

        if platform == "curseforge":
            if not self.modpack_manager.curseforge_api or not self.modpack_manager.curseforge_api.is_configured():
                messagebox.showerror(
                    "Error",
                    "Para usar CurseForge necesitas configurar una API Key.\n\n"
                    "Ve a la pestaña 'Configuración' para agregarla."
                )
                return

        self._add_log_modpack(f"\n🔍 Buscando '{query}' en {platform.capitalize()}...\n", "info")

        # Deshabilitar botón de búsqueda
        self.search_modpacks_btn.configure(state="disabled", text="Buscando...")

        def search():
            results = self.modpack_manager.search_modpacks(query, platform, limit=10)

            self.modpack_search_results = results if results else []
            self._populate_modpack_results(platform)

            self.search_modpacks_btn.configure(state="normal", text="Buscar")

        thread = threading.Thread(target=search, daemon=True)
        thread.start()

    def _populate_modpack_results(self, platform: str):
        """Muestra los resultados de búsqueda de modpacks"""
        # Limpiar resultados anteriores
        for widget in self.modpack_results_frame.winfo_children():
            widget.destroy()

        if not self.modpack_search_results or len(self.modpack_search_results) == 0:
            self._add_log_modpack("No se encontraron resultados\n", "warning")
            no_results = ctk.CTkLabel(
                self.modpack_results_frame,
                text="No se encontraron modpacks con ese nombre",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            )
            no_results.pack(pady=20)
            return

        self._add_log_modpack(f"✓ Encontrados {len(self.modpack_search_results)} modpacks\n", "success")

        # Mostrar resultados
        for modpack in self.modpack_search_results:
            self._create_modpack_result_card(modpack, platform)

    def _create_modpack_result_card(self, modpack: Dict, platform: str):
        """Crea una tarjeta visual para un modpack en los resultados"""
        card = ctk.CTkFrame(self.modpack_results_frame, fg_color="gray20")
        card.pack(pady=5, padx=10, fill="x")

        # Información del modpack
        if platform == "modrinth":
            name = modpack.get("title", "Sin nombre")
            description = modpack.get("description", "Sin descripción")
            author = modpack.get("author", "Desconocido")
            downloads = modpack.get("downloads", 0)
            project_id = modpack.get("project_id", "")
        else:  # curseforge
            name = modpack.get("name", "Sin nombre")
            description = modpack.get("summary", "Sin descripción")
            authors = modpack.get("authors", [])
            author = authors[0].get("name", "Desconocido") if authors else "Desconocido"
            downloads = modpack.get("downloadCount", 0)
            project_id = modpack.get("id", 0)

        # Título del modpack
        ctk.CTkLabel(
            card,
            text=name,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(pady=(10, 5), padx=15, anchor="w")

        # Descripción truncada
        desc_text = description[:100] + "..." if len(description) > 100 else description
        ctk.CTkLabel(
            card,
            text=desc_text,
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w"
        ).pack(pady=2, padx=15, anchor="w")

        # Info adicional
        info_text = f"Por {author} • {downloads:,} descargas"
        ctk.CTkLabel(
            card,
            text=info_text,
            font=ctk.CTkFont(size=10),
            text_color="gray70",
            anchor="w"
        ).pack(pady=2, padx=15, anchor="w")

        # Botón para seleccionar
        select_btn = ctk.CTkButton(
            card,
            text="Seleccionar",
            command=lambda: self._on_modpack_select(modpack, platform),
            width=120,
            height=28
        )
        select_btn.pack(pady=10, padx=15, anchor="e")

    def _on_modpack_select(self, modpack: Dict, platform: str):
        """Maneja la selección de un modpack"""
        self.selected_modpack = {
            "data": modpack,
            "platform": platform
        }

        if platform == "modrinth":
            name = modpack.get("title", "Sin nombre")
            project_id = modpack.get("project_id", "")

            self.selected_modpack["project_id"] = project_id

            # Obtener versiones del modpack
            versions = self.modpack_manager.modrinth_api.get_modpack_versions(project_id)
            if versions and len(versions) > 0:
                # Usar la primera versión (más reciente)
                self.selected_modpack_version = versions[0].get("id")
                version_name = versions[0].get("version_number", "última")
            else:
                version_name = "desconocida"
                self.selected_modpack_version = None

        else:  # curseforge
            name = modpack.get("name", "Sin nombre")
            modpack_id = modpack.get("id", 0)

            self.selected_modpack["modpack_id"] = modpack_id

            # Obtener archivos del modpack
            files = self.modpack_manager.curseforge_api.get_modpack_files(modpack_id)
            if files and len(files) > 0:
                # Usar el primer archivo (más reciente)
                self.selected_modpack_version = files[0].get("id")
                version_name = files[0].get("displayName", "última")
            else:
                version_name = "desconocida"
                self.selected_modpack_version = None

        self.selected_modpack_label.configure(
            text=f"✓ Modpack seleccionado: {name} (versión: {version_name})",
            text_color="green"
        )

        self._add_log_modpack(f"\n✓ Modpack seleccionado: {name}\n", "success")
        self._add_log_modpack(f"  Plataforma: {platform.capitalize()}\n", "info")
        self._add_log_modpack(f"  Versión: {version_name}\n\n", "info")

        self._update_install_modpack_button()

    def _select_modpack_folder(self):
        """Selecciona la carpeta para el servidor de modpack"""
        folder = filedialog.askdirectory(title="Seleccionar carpeta para el servidor con modpack")
        if folder:
            self.modpack_server_folder = folder
            self.modpack_folder_label.configure(
                text=f"Carpeta: {folder}",
                text_color="white"
            )
            self._add_log_modpack(f"Carpeta seleccionada: {folder}\n", "info")
            self._update_install_modpack_button()

    def _update_install_modpack_button(self):
        """Actualiza el estado del botón de instalación de modpack"""
        if self.selected_modpack and self.modpack_server_folder and self.selected_modpack_version:
            self.install_modpack_btn.configure(state="normal")
            self.modpack_status_label.configure(text="¡Listo para instalar!", text_color="green")
        else:
            self.install_modpack_btn.configure(state="disabled")
            # Mostrar qué falta
            missing = []
            if not self.selected_modpack:
                missing.append("seleccionar modpack")
            if not self.modpack_server_folder:
                missing.append("seleccionar carpeta")
            if not self.selected_modpack_version:
                missing.append("versión válida")

            if missing:
                self.modpack_status_label.configure(
                    text=f"Falta: {', '.join(missing)}",
                    text_color="orange"
                )

    def _install_modpack(self):
        """Instala el modpack seleccionado"""
        if not self.selected_modpack or not self.modpack_server_folder or not self.selected_modpack_version:
            messagebox.showwarning("Advertencia", "Selecciona un modpack y una carpeta primero")
            return

        # Deshabilitar botones durante la instalación
        self.install_modpack_btn.configure(state="disabled")
        self.search_modpacks_btn.configure(state="disabled")
        self.select_modpack_folder_btn.configure(state="disabled")

        def install():
            try:
                platform = self.selected_modpack["platform"]

                if platform == "modrinth":
                    project_id = self.selected_modpack["project_id"]
                    version_id = self.selected_modpack_version

                    success = self.modpack_manager.install_modrinth_modpack(
                        project_id,
                        version_id,
                        self.modpack_server_folder,
                        log_callback=self._add_log_modpack_simple
                    )

                else:  # curseforge
                    modpack_id = self.selected_modpack["modpack_id"]
                    file_id = self.selected_modpack_version

                    success = self.modpack_manager.install_curseforge_modpack(
                        modpack_id,
                        file_id,
                        self.modpack_server_folder,
                        log_callback=self._add_log_modpack_simple
                    )

                if success:
                    self._add_log_modpack("\n¡Todo listo! El servidor está configurado.\n", "success")

                    self._add_log_modpack("\n═══════════════════════════════════════════════════\n", "success")
                    self._add_log_modpack("SIGUIENTE PASO: INSTALAR PARA EL CLIENTE\n", "info")
                    self._add_log_modpack("═══════════════════════════════════════════════════\n\n", "success")
                    self._add_log_modpack("El servidor está listo, pero necesitas instalar el modpack\n", "info")
                    self._add_log_modpack("para el cliente también.\n\n", "info")
                    self._add_log_modpack("Baja a 'Gestionar Servidor con Modpack' y:\n", "info")
                    self._add_log_modpack("1. Selecciona la carpeta del servidor que acabas de instalar\n", "normal")
                    self._add_log_modpack("2. Haz clic en 'Instalar Modpack para Cliente'\n", "normal")
                    self._add_log_modpack("3. Luego podrás iniciar el servidor\n\n", "normal")

                    messagebox.showinfo(
                        "¡Servidor Instalado!",
                        f"El modpack del SERVIDOR se instaló correctamente en:\n{self.modpack_server_folder}\n\n"
                        "IMPORTANTE: Ahora debes instalarlo también para el CLIENTE.\n\n"
                        "Baja a 'Gestionar Servidor con Modpack' en esta pestaña\n"
                        "y sigue las instrucciones."
                    )
                else:
                    self._add_log_modpack("\n✗ La instalación falló. Revisa los logs anteriores.\n", "error")
                    messagebox.showerror("Error", "Hubo un error durante la instalación del modpack")

            except Exception as e:
                self._add_log_modpack(f"\n✗ Error inesperado: {str(e)}\n", "error")
                messagebox.showerror("Error", f"Error durante la instalación: {str(e)}")

            finally:
                # Re-habilitar botones
                self.install_modpack_btn.configure(state="normal")
                self.search_modpacks_btn.configure(state="normal")
                self.select_modpack_folder_btn.configure(state="normal")

        thread = threading.Thread(target=install, daemon=True)
        thread.start()

    def _add_log_modpack(self, message: str, log_type: str = "normal"):
        """
        Añade un mensaje a la consola de modpacks

        log_type puede ser: 'normal', 'info', 'success', 'warning', 'error'
        """
        self.modpack_log_text.configure(state="normal")

        # Configurar tags de colores
        self.modpack_log_text.tag_config("info", foreground="#2196F3")
        self.modpack_log_text.tag_config("success", foreground="#4CAF50")
        self.modpack_log_text.tag_config("warning", foreground="#FF9800")
        self.modpack_log_text.tag_config("error", foreground="#F44336")
        self.modpack_log_text.tag_config("normal", foreground="white")

        self.modpack_log_text.insert("end", message, log_type)
        self.modpack_log_text.see("end")
        self.modpack_log_text.configure(state="disabled")

    def _add_log_modpack_simple(self, message: str):
        """Añade un log simple a consola de modpack (para callbacks)"""
        self._add_log_modpack(message, "normal")

    # ==================== GESTIÓN DE SERVIDOR CON MODPACK ====================

    def _select_modpack_server(self):
        """Selecciona un servidor existente con modpack"""
        folder = filedialog.askdirectory(title="Seleccionar carpeta del servidor con modpack")
        if folder:
            # Detectar tipo de servidor
            temp_manager = ServerManager(folder)
            server_type = temp_manager.detect_server_type()

            if server_type in ["forge", "fabric"]:
                self.modpack_server_path = folder
                self.modpack_server_manager = temp_manager
                self.is_modpack_server_configured = True

                self.modpack_server_status_label.configure(
                    text=f"✓ Servidor {server_type.upper()} encontrado: {folder}",
                    text_color="green"
                )

                self.start_modpack_server_btn.configure(state="normal")
                self.install_client_btn.configure(state="normal")

                # Detectar versiones
                mc_version, loader_version = self._detect_server_versions(folder, server_type)

                self._add_log_modpack_server("\n╔═══════════════════════════════════════════════════════╗\n", "success")
                self._add_log_modpack_server("║     ✓ SERVIDOR CON MODPACK ENCONTRADO               ║\n", "success")
                self._add_log_modpack_server("╚═══════════════════════════════════════════════════════╝\n", "success")
                self._add_log_modpack_server(f"\nCarpeta: {folder}\n", "info")
                self._add_log_modpack_server(f"Tipo de servidor: {server_type.upper()}\n\n", "info")

                # Mostrar versiones detectadas
                self._add_log_modpack_server("═══════════════════════════════════════════════════════\n", "info")
                self._add_log_modpack_server("INFORMACIÓN DEL MODPACK:\n", "warning")
                self._add_log_modpack_server("═══════════════════════════════════════════════════════\n", "info")

                if mc_version:
                    self._add_log_modpack_server(f"  Minecraft: {mc_version}\n", "success")
                else:
                    self._add_log_modpack_server(f"  Minecraft: No detectada\n", "warning")

                if loader_version:
                    self._add_log_modpack_server(f"  {server_type.capitalize()}: {loader_version}\n", "success")
                else:
                    self._add_log_modpack_server(f"  {server_type.capitalize()}: No detectada\n", "warning")

                self._add_log_modpack_server("\n⚠ IMPORTANTE: Usa estas versiones en tu launcher!\n", "warning")
                self._add_log_modpack_server("═══════════════════════════════════════════════════════\n\n", "info")

                self._add_log_modpack_server("Acciones disponibles:\n", "info")
                self._add_log_modpack_server("1. Instalar Modpack para Cliente (botón naranja arriba)\n", "normal")
                self._add_log_modpack_server("2. Iniciar Servidor (botón verde abajo)\n\n", "normal")

            elif server_type == "vanilla":
                self.modpack_server_status_label.configure(
                    text="✗ Este es un servidor vanilla, no un servidor con modpack",
                    text_color="orange"
                )
                messagebox.showwarning(
                    "Servidor Vanilla",
                    "Este es un servidor vanilla (sin mods).\n\n"
                    "Para servidores vanilla, usa la pestaña 'Servidor Vanilla'."
                )
            else:
                self.modpack_server_status_label.configure(
                    text="✗ No se encontró un servidor válido en esta carpeta",
                    text_color="red"
                )
                self._add_log_modpack_server(f"\n✗ No se encontró servidor con modpack en: {folder}\n", "error")
                self._add_log_modpack_server("Asegúrate de seleccionar la carpeta donde instalaste el modpack.\n", "warning")
                messagebox.showerror(
                    "Servidor no encontrado",
                    "No se encontró un servidor con modpack en esta carpeta.\n\n"
                    "Asegúrate de que sea la carpeta donde instalaste el modpack\n"
                    "(debe contener fabric-server-launch.jar o archivos de Forge)."
                )

    def _start_modpack_server(self):
        """Inicia el servidor con modpack"""
        if not self.modpack_server_manager or not self.is_modpack_server_configured:
            messagebox.showwarning("Advertencia", "Primero debes seleccionar un servidor con modpack")
            return

        # Detectar tipo
        server_type = self.modpack_server_manager.detect_server_type()

        # Detectar RAM recomendada (buscar mods folder)
        mods_folder = os.path.join(self.modpack_server_path, "mods")
        ram_mb = 4096  # Default

        if os.path.exists(mods_folder):
            num_mods = len([f for f in os.listdir(mods_folder) if f.endswith('.jar')])
            ram_mb = self.modpack_server_manager.get_recommended_ram_for_modpack(num_mods)

        self._add_log_modpack_server(f"\n=== INICIANDO SERVIDOR {server_type.upper()} ===\n", "info")
        self._add_log_modpack_server(f"RAM asignada: {ram_mb} MB ({ram_mb // 1024} GB)\n", "info")
        self._add_log_modpack_server("El servidor está arrancando...\n\n", "info")

        self.start_modpack_server_btn.configure(state="disabled")
        self.stop_modpack_server_btn.configure(state="normal")

        def start():
            success = self.modpack_server_manager.start_modded_server(
                server_type,
                ram_mb=ram_mb,
                log_callback=self._add_log_modpack_server_simple,
                detached=True
            )

            if not success:
                self._add_log_modpack_server("\n✗ Error al iniciar el servidor\n", "error")
                self.start_modpack_server_btn.configure(state="normal")
                self.stop_modpack_server_btn.configure(state="disabled")
                self.send_modpack_command_btn.configure(state="disabled")
            else:
                self.send_modpack_command_btn.configure(state="normal")

        thread = threading.Thread(target=start, daemon=True)
        thread.start()

    def _stop_modpack_server(self):
        """Detiene el servidor con modpack"""
        if not self.modpack_server_manager:
            return

        self._add_log_modpack_server("\n=== DETENIENDO SERVIDOR ===\n", "warning")
        success = self.modpack_server_manager.stop_server()

        if success:
            self._add_log_modpack_server("✓ Servidor detenido correctamente\n\n", "info")
        else:
            self._add_log_modpack_server("✗ Error al detener el servidor o el servidor no estaba en ejecución\n", "error")

        self.start_modpack_server_btn.configure(state="normal")
        self.stop_modpack_server_btn.configure(state="disabled")
        self.send_modpack_command_btn.configure(state="disabled")

    def _send_modpack_command(self, event):
        """Envía un comando al servidor con modpack"""
        command = self.modpack_command_entry.get().strip()
        if not command:
            return

        if not self.modpack_server_manager or not self.modpack_server_manager.is_server_running():
            self._add_log_modpack_server("✗ Error: El servidor no está en ejecución\n", "error")
            return

        self._add_log_modpack_server(f"> {command}\n", "info")

        success = self.modpack_server_manager.send_command(command)
        if not success:
            self._add_log_modpack_server("✗ Error al enviar comando\n", "error")

        self.modpack_command_entry.delete(0, 'end')

    def _install_client_modpack(self):
        """Instala el modpack para el cliente"""
        if not self.modpack_server_path:
            messagebox.showwarning("Advertencia", "Primero debes seleccionar un servidor con modpack")
            return

        # Intentar detectar el nombre del modpack desde el manifest
        modpack_name = self._detect_modpack_name(self.modpack_server_path)

        if not modpack_name:
            # Si no se pudo detectar, pedir al usuario
            modpack_name = self._ask_modpack_name()
            if not modpack_name:
                return

        response = messagebox.askyesno(
            "Confirmar Instalación",
            f"¿Instalar el modpack para el cliente?\n\n"
            f"El modpack se instalará en:\n"
            f"C:\\Users\\{os.getenv('USERNAME')}\\Modrinth\\{modpack_name}\n\n"
            f"Luego podrás configurar tu launcher para usar esa carpeta."
        )

        if not response:
            return

        self._add_log_modpack_server("\n═══════════════════════════════════════════════════\n", "info")
        self._add_log_modpack_server("INSTALANDO MODPACK PARA EL CLIENTE\n", "info")
        self._add_log_modpack_server("═══════════════════════════════════════════════════\n\n", "info")

        self.install_client_btn.configure(state="disabled", text="Instalando...")

        def install():
            try:
                success = self.install_modpack_for_client(modpack_name, self.modpack_server_path)

                if success:
                    user_folder = os.path.expanduser('~')
                    final_path = os.path.join(user_folder, 'Modrinth', modpack_name)

                    messagebox.showinfo(
                        "¡Instalación Completada!",
                        f"El modpack se instaló correctamente para el cliente en:\n\n"
                        f"{final_path}\n\n"
                        f"Ahora puedes:\n"
                        f"1. Abrir SKLauncher (o tu launcher)\n"
                        f"2. Configurar el 'Directorio del juego' a la ruta de arriba\n"
                        f"3. ¡Iniciar el juego y conectarte al servidor!"
                    )
                else:
                    messagebox.showerror("Error", "Hubo un error al instalar el modpack para el cliente")

            except Exception as e:
                self._add_log_modpack_server(f"\n✗ Error: {str(e)}\n", "error")
                messagebox.showerror("Error", f"Error al instalar: {str(e)}")

            finally:
                self.install_client_btn.configure(state="normal", text="📦 Instalar Modpack para el Cliente")

        thread = threading.Thread(target=install, daemon=True)
        thread.start()

    def _detect_server_versions(self, server_folder: str, server_type: str) -> tuple[Optional[str], Optional[str]]:
        """
        Detecta las versiones de Minecraft y del loader del servidor

        Args:
            server_folder: Carpeta del servidor
            server_type: Tipo de servidor (forge o fabric)

        Returns:
            Tupla (minecraft_version, loader_version)
        """
        mc_version = None
        loader_version = None

        try:
            # Intentar desde manifest primero
            modrinth_manifest = os.path.join(server_folder, "modrinth.index.json")
            cf_manifest = os.path.join(server_folder, "manifest.json")

            if os.path.exists(modrinth_manifest):
                with open(modrinth_manifest, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    deps = data.get("dependencies", {})
                    mc_version = deps.get("minecraft")
                    if server_type == "forge":
                        loader_version = deps.get("forge")
                    elif server_type == "fabric":
                        loader_version = deps.get("fabric-loader")

            elif os.path.exists(cf_manifest):
                with open(cf_manifest, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    minecraft_info = data.get("minecraft", {})
                    mc_version = minecraft_info.get("version")

                    mod_loaders = minecraft_info.get("modLoaders", [])
                    if mod_loaders:
                        loader_id = mod_loaders[0].get("id", "")
                        # Formato: "forge-47.2.0"
                        if "-" in loader_id:
                            loader_version = loader_id.split("-", 1)[1]

            # Si no encontramos en manifests, buscar en la estructura de libraries
            if not mc_version or not loader_version:
                if server_type == "forge":
                    # Buscar en libraries/net/minecraftforge/forge/
                    forge_path = os.path.join(server_folder, "libraries", "net", "minecraftforge", "forge")
                    if os.path.exists(forge_path):
                        # Listar carpetas de versiones (ejemplo: 1.20.1-47.4.0)
                        for version_folder in os.listdir(forge_path):
                            if os.path.isdir(os.path.join(forge_path, version_folder)):
                                # Formato: 1.20.1-47.4.0
                                # Necesitamos separar la versión de Minecraft de la versión de Forge
                                # La versión de Minecraft tiene el formato X.Y.Z
                                # Buscamos el último guion que separa MC de Forge
                                parts = version_folder.split("-")
                                if len(parts) >= 2:
                                    # Reunir las partes de Minecraft (todo excepto la última parte)
                                    mc_parts = []
                                    forge_part = parts[-1]  # Última parte es la versión de Forge

                                    # Reconstruir versión de Minecraft
                                    for i, part in enumerate(parts[:-1]):
                                        if i == 0:
                                            mc_parts.append(part)
                                        else:
                                            # Si la parte parece ser parte de la versión de MC (números)
                                            mc_parts.append(part)

                                    if not mc_version:
                                        mc_version = ".".join(mc_parts)  # 1.20.1
                                    if not loader_version:
                                        loader_version = forge_part  # 47.4.0
                                break

                elif server_type == "fabric":
                    # Buscar en libraries/net/fabricmc/fabric-loader/
                    fabric_path = os.path.join(server_folder, "libraries", "net", "fabricmc", "fabric-loader")
                    if os.path.exists(fabric_path):
                        # Listar carpetas de versiones del loader
                        for loader_folder in os.listdir(fabric_path):
                            if os.path.isdir(os.path.join(fabric_path, loader_folder)):
                                loader_version = loader_folder
                                break

                    # Para Minecraft version, buscar en fabric-server-launch.jar o archivos de config
                    if not mc_version:
                        # Intentar desde .fabric/server.properties
                        fabric_server_properties = os.path.join(server_folder, ".fabric", "server.properties")
                        if os.path.exists(fabric_server_properties):
                            with open(fabric_server_properties, 'r') as f:
                                for line in f:
                                    if line.startswith("game-version="):
                                        mc_version = line.split("=", 1)[1].strip()
                                        break

            return mc_version, loader_version

        except Exception as e:
            self._add_log_modpack_server(f"⚠ Error al detectar versiones: {str(e)}\n", "warning")
            return None, None

    def _detect_modpack_name(self, server_folder: str) -> Optional[str]:
        """
        Intenta detectar el nombre del modpack desde el manifest

        Args:
            server_folder: Carpeta del servidor

        Returns:
            Nombre del modpack o None si no se pudo detectar
        """
        try:
            # Intentar leer modrinth.index.json (Modrinth)
            modrinth_manifest = os.path.join(server_folder, "modrinth.index.json")
            if os.path.exists(modrinth_manifest):
                with open(modrinth_manifest, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    name = data.get("name")
                    if name:
                        # Limpiar nombre de caracteres no válidos
                        name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
                        self._add_log_modpack_server(f"✓ Nombre del modpack detectado: {name}\n", "success")
                        return name

            # Intentar leer manifest.json (CurseForge)
            cf_manifest = os.path.join(server_folder, "manifest.json")
            if os.path.exists(cf_manifest):
                with open(cf_manifest, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    name = data.get("name")
                    if name:
                        # Limpiar nombre
                        name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
                        self._add_log_modpack_server(f"✓ Nombre del modpack detectado: {name}\n", "success")
                        return name

            self._add_log_modpack_server("⚠ No se pudo detectar el nombre del modpack automáticamente\n", "warning")
            return None

        except Exception as e:
            self._add_log_modpack_server(f"⚠ Error al detectar nombre: {str(e)}\n", "warning")
            return None

    def _ask_modpack_name(self) -> Optional[str]:
        """
        Pide al usuario el nombre del modpack

        Returns:
            Nombre ingresado por el usuario o None si canceló
        """
        # Crear ventana de diálogo personalizada
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Nombre del Modpack")
        dialog.geometry("500x250")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Centrar ventana
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (250 // 2)
        dialog.geometry(f"+{x}+{y}")

        result = {"name": None}

        # Contenido
        ctk.CTkLabel(
            dialog,
            text="Ingresa el nombre del modpack",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=20)

        ctk.CTkLabel(
            dialog,
            text="Este nombre se usará para crear la carpeta en:\nC:\\Users\\[tu-usuario]\\Modrinth\\[nombre]",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(pady=5)

        # Entry para el nombre
        name_entry = ctk.CTkEntry(
            dialog,
            placeholder_text="Ej: Prehistoric Nature, Create Above and Beyond...",
            width=400,
            height=40,
            font=ctk.CTkFont(size=13)
        )
        name_entry.pack(pady=20)
        name_entry.focus()

        def on_accept():
            name = name_entry.get().strip()
            if name:
                # Limpiar caracteres no válidos
                name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
                if name:
                    result["name"] = name
                    dialog.destroy()
                else:
                    messagebox.showwarning("Advertencia", "El nombre no puede estar vacío", parent=dialog)
            else:
                messagebox.showwarning("Advertencia", "Por favor ingresa un nombre", parent=dialog)

        def on_cancel():
            dialog.destroy()

        # Bind Enter key
        name_entry.bind("<Return>", lambda e: on_accept())

        # Botones
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=10)

        ctk.CTkButton(
            button_frame,
            text="Aceptar",
            command=on_accept,
            width=120,
            height=35,
            fg_color="green",
            hover_color="darkgreen"
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            button_frame,
            text="Cancelar",
            command=on_cancel,
            width=120,
            height=35,
            fg_color="red",
            hover_color="darkred"
        ).pack(side="left", padx=10)

        # Esperar a que se cierre la ventana
        self.root.wait_window(dialog)

        return result["name"]

    def _add_log_modpack_server(self, message: str, log_type: str = "normal"):
        """Añade un mensaje a la consola del servidor con modpack"""
        self.modpack_server_log_text.configure(state="normal")

        # Configurar tags de colores
        self.modpack_server_log_text.tag_config("info", foreground="#2196F3")
        self.modpack_server_log_text.tag_config("success", foreground="#4CAF50")
        self.modpack_server_log_text.tag_config("warning", foreground="#FF9800")
        self.modpack_server_log_text.tag_config("error", foreground="#F44336")
        self.modpack_server_log_text.tag_config("normal", foreground="white")

        self.modpack_server_log_text.insert("end", message, log_type)
        self.modpack_server_log_text.see("end")
        self.modpack_server_log_text.configure(state="disabled")

    def _add_log_modpack_server_simple(self, message: str):
        """Añade un log simple (para callbacks)"""
        self._add_log_modpack_server(message, "normal")

        # Detectar cuando el servidor está listo
        if "Done" in message and "For help, type" in message:
            self._add_log_modpack_server("\n", "normal")
            self._add_log_modpack_server("╔═══════════════════════════════════════════════════════╗\n", "success")
            self._add_log_modpack_server("║                                                       ║\n", "success")
            self._add_log_modpack_server("║      ✓ ¡SERVIDOR LISTO Y FUNCIONANDO!               ║\n", "success")
            self._add_log_modpack_server("║                                                       ║\n", "success")
            self._add_log_modpack_server("╚═══════════════════════════════════════════════════════╝\n", "success")
            self._add_log_modpack_server("\nLos jugadores ya pueden conectarse al servidor.\n", "info")
            self._add_log_modpack_server("Puedes enviar comandos usando el campo de abajo.\n\n", "info")

    # ==================== INSTALACIÓN PARA EL CLIENTE ====================

    def install_modpack_for_client(self, modpack_name: str, modpack_folder: str):
        """
        Instala el modpack para el cliente en C:/Users/[user]/Modrinth/[nombre]/

        Args:
            modpack_name: Nombre del modpack
            modpack_folder: Carpeta del servidor con el modpack
        """
        try:
            # Ruta a C:\Users\[nombre]\Modrinth\
            user_folder = os.path.expanduser('~')  # C:\Users\[nombre]
            modrinth_folder = os.path.join(user_folder, 'Modrinth')
            client_modpack_folder = os.path.join(modrinth_folder, modpack_name)

            self._add_log_modpack_server(f"Destino: {client_modpack_folder}\n", "info")

            # Crear carpetas
            os.makedirs(client_modpack_folder, exist_ok=True)

            # Copiar mods
            server_mods = os.path.join(modpack_folder, "mods")
            client_mods = os.path.join(client_modpack_folder, "mods")

            if os.path.exists(server_mods):
                self._add_log_modpack_server("Copiando mods al cliente...\n", "info")

                if os.path.exists(client_mods):
                    shutil.rmtree(client_mods)

                shutil.copytree(server_mods, client_mods)

                num_mods = len([f for f in os.listdir(client_mods) if f.endswith('.jar')])
                self._add_log_modpack_server(f"✓ {num_mods} mods copiados\n", "success")

            # Copiar config
            server_config = os.path.join(modpack_folder, "config")
            client_config = os.path.join(client_modpack_folder, "config")

            if os.path.exists(server_config):
                self._add_log_modpack_server("Copiando configuraciones...\n", "info")

                if os.path.exists(client_config):
                    shutil.rmtree(client_config)

                shutil.copytree(server_config, client_config)
                self._add_log_modpack_server("✓ Configuraciones copiadas\n", "success")

            # Copiar otros archivos importantes
            for folder in ["scripts", "resourcepacks", "shaderpacks"]:
                server_folder_path = os.path.join(modpack_folder, folder)
                client_folder_path = os.path.join(client_modpack_folder, folder)

                if os.path.exists(server_folder_path):
                    if os.path.exists(client_folder_path):
                        shutil.rmtree(client_folder_path)
                    shutil.copytree(server_folder_path, client_folder_path)

            self._add_log_modpack_server("\n✓ ¡Modpack instalado para el cliente!\n", "success")
            self._add_log_modpack_server(f"Ubicación: {client_modpack_folder}\n\n", "info")
            self._add_log_modpack_server("═══════════════════════════════════════════════════\n", "success")
            self._add_log_modpack_server("CÓMO CONFIGURAR TU LAUNCHER:\n", "info")
            self._add_log_modpack_server("═══════════════════════════════════════════════════\n\n", "success")
            self._add_log_modpack_server("Para SKLauncher:\n", "info")
            self._add_log_modpack_server("1. Abre SKLauncher\n", "normal")
            self._add_log_modpack_server("2. Ve a 'Configuración' o 'Settings'\n", "normal")
            self._add_log_modpack_server("3. En 'Directorio del juego' o 'Game Directory' pega:\n", "normal")
            self._add_log_modpack_server(f"   {client_modpack_folder}\n\n", "warning")
            self._add_log_modpack_server("Para MultiMC/PolyMC/Prism:\n", "info")
            self._add_log_modpack_server("1. Crea una nueva instancia\n", "normal")
            self._add_log_modpack_server("2. Edita la instancia > Settings > Minecraft\n", "normal")
            self._add_log_modpack_server("3. Marca 'Use custom Minecraft directory'\n", "normal")
            self._add_log_modpack_server(f"4. Pega: {client_modpack_folder}\n\n", "warning")
            self._add_log_modpack_server("IMPORTANTE: Selecciona la misma versión de Minecraft y loader\n", "warning")
            self._add_log_modpack_server("que usa el servidor (checa los logs del servidor).\n\n", "warning")

            return True

        except Exception as e:
            self._add_log_modpack_server(f"\n✗ Error al instalar para el cliente: {str(e)}\n", "error")
            return False

    # ==================== CONFIGURACIÓN / SETTINGS ====================

    def _create_settings_tab(self):
        """Crea la pestaña de configuración"""
        tab = self.tabview.tab("Configuración")

        # Frame principal
        main_frame = ctk.CTkScrollableFrame(tab, width=900, height=600)
        main_frame.pack(pady=10, padx=10, fill="both", expand=True)

        # Título
        ctk.CTkLabel(
            main_frame,
            text="Configuración de PyCraft",
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=20)

        # Sección: CurseForge API Key
        cf_frame = ctk.CTkFrame(main_frame, fg_color="gray20")
        cf_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(
            cf_frame,
            text="API Key de CurseForge",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#4CAF50"
        ).pack(pady=15, padx=20, anchor="w")

        ctk.CTkLabel(
            cf_frame,
            text="Para usar modpacks de CurseForge necesitas una API Key gratuita.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w"
        ).pack(pady=(0, 5), padx=20, anchor="w")

        # Instrucciones
        instructions_text = (
            "Cómo obtener tu API Key:\n\n"
            "1. Ve a: https://console.curseforge.com\n"
            "2. Inicia sesión o crea una cuenta\n"
            "3. Ve a 'API Keys' en el menú lateral\n"
            "4. Crea una nueva API key con nombre 'PyCraft'\n"
            "5. Copia la API key y pégala abajo\n\n"
            "NOTA: La API key se guarda localmente en tu computadora\n"
            "y solo se usa para descargar modpacks de CurseForge."
        )

        instructions_label = ctk.CTkLabel(
            cf_frame,
            text=instructions_text,
            font=ctk.CTkFont(size=11),
            justify="left",
            anchor="w"
        )
        instructions_label.pack(pady=10, padx=20, anchor="w")

        # Campo para API Key
        api_key_frame = ctk.CTkFrame(cf_frame, fg_color="transparent")
        api_key_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(
            api_key_frame,
            text="API Key:",
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=(0, 10))

        self.cf_api_key_entry = ctk.CTkEntry(
            api_key_frame,
            placeholder_text="Pega tu API key aquí...",
            width=500,
            height=35,
            show="*"
        )
        self.cf_api_key_entry.pack(side="left", padx=5)

        # Cargar API key existente si la hay
        existing_key = self.api_config.get_curseforge_key()
        if existing_key:
            self.cf_api_key_entry.insert(0, existing_key)

        # Botones
        button_frame = ctk.CTkFrame(cf_frame, fg_color="transparent")
        button_frame.pack(pady=15, padx=20)

        save_btn = ctk.CTkButton(
            button_frame,
            text="Guardar API Key",
            command=self._save_curseforge_key,
            width=150,
            height=35,
            fg_color="green",
            hover_color="darkgreen"
        )
        save_btn.pack(side="left", padx=5)

        clear_btn = ctk.CTkButton(
            button_frame,
            text="Limpiar",
            command=self._clear_curseforge_key,
            width=150,
            height=35,
            fg_color="red",
            hover_color="darkred"
        )
        clear_btn.pack(side="left", padx=5)

        # Estado
        self.cf_key_status_label = ctk.CTkLabel(
            cf_frame,
            text="",
            font=ctk.CTkFont(size=11)
        )
        self.cf_key_status_label.pack(pady=(0, 15), padx=20)

        self._update_cf_key_status()

        # Separador
        ctk.CTkFrame(main_frame, height=2, fg_color="gray30").pack(pady=20, fill="x", padx=20)

        # Información adicional
        info_frame = ctk.CTkFrame(main_frame, fg_color="gray20")
        info_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(
            info_frame,
            text="Información de PyCraft",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#4CAF50"
        ).pack(pady=15, padx=20, anchor="w")

        info_text = (
            "PyCraft - Minecraft Server Manager\n"
            "Versión: 1.0\n\n"
            "Desarrollado para simplificar la creación y gestión\n"
            "de servidores de Minecraft vanilla y con modpacks.\n\n"
            "Características:\n"
            "• Creación automática de servidores vanilla\n"
            "• Instalación de modpacks desde Modrinth y CurseForge\n"
            "• Instalación automática de Java\n"
            "• Soporte para Forge y Fabric\n"
            "• Configuración automática de servidores\n\n"
            "GitHub: github.com/ConradoGomez/PyCraft"
        )

        ctk.CTkLabel(
            info_frame,
            text=info_text,
            font=ctk.CTkFont(size=11),
            justify="left",
            anchor="w"
        ).pack(pady=(10, 20), padx=20, anchor="w")

    def _save_curseforge_key(self):
        """Guarda la API key de CurseForge"""
        api_key = self.cf_api_key_entry.get().strip()

        if not api_key:
            messagebox.showwarning("Advertencia", "Ingresa una API key primero")
            return

        success = self.api_config.save_curseforge_key(api_key)

        if success:
            self.modpack_manager.set_curseforge_api_key(api_key)
            self._update_cf_key_status()
            self._update_cf_status()
            messagebox.showinfo("Éxito", "API Key guardada correctamente")
        else:
            messagebox.showerror("Error", "No se pudo guardar la API Key")

    def _clear_curseforge_key(self):
        """Limpia la API key de CurseForge"""
        response = messagebox.askyesno(
            "Confirmar",
            "¿Estás seguro de que quieres eliminar la API Key de CurseForge?"
        )

        if response:
            self.api_config.clear_config()
            self.cf_api_key_entry.delete(0, 'end')
            self.modpack_manager.curseforge_api = None
            self._update_cf_key_status()
            self._update_cf_status()
            messagebox.showinfo("Éxito", "API Key eliminada")

    def _update_cf_key_status(self):
        """Actualiza el estado de la API key en settings"""
        if self.api_config.get_curseforge_key():
            self.cf_key_status_label.configure(
                text="✓ API Key configurada y lista para usar",
                text_color="green"
            )
        else:
            self.cf_key_status_label.configure(
                text="⚠ No hay API Key configurada",
                text_color="orange"
            )

    def run(self):
        """Inicia la aplicación"""
        # Configurar el protocolo de cierre
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.mainloop()
