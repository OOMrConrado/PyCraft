import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import threading
import os
import shutil
import json
import webbrowser
from typing import Optional, Dict, List
from pathlib import Path

from ..core.api import MinecraftAPIHandler, ModrinthAPI, CurseForgeAPI, APIConfig
from ..core.download import ServerDownloader
from ..managers.server import ServerManager
from ..managers.modpack import ModpackManager
from ..managers.java import JavaManager
from .tabs.info_tab import InfoTab


class PyCraftGUI:
    """Interfaz gráfica principal de PyCraft"""

    def __init__(self):
        # Configuración de customtkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Paleta de colores profesional y monocromática
        self.colors = {
            # Backgrounds
            "bg_primary": "#0f1419",      # Fondo principal muy oscuro
            "bg_secondary": "#1a1f26",    # Fondo secundario
            "bg_tertiary": "#232a33",     # Fondo terciario (cards)
            "bg_hover": "#2a3440",        # Hover state

            # Borders y separadores
            "border": "#2d3540",
            "border_light": "#3a4452",

            # Texto
            "text_primary": "#e6edf3",    # Texto principal
            "text_secondary": "#8b949e",  # Texto secundario
            "text_muted": "#6e7681",      # Texto suave

            # Acentos principales (azul suave)
            "accent": "#58a6ff",          # Azul principal
            "accent_hover": "#4a8ed8",    # Azul hover
            "accent_light": "#79c0ff",    # Azul claro
            "accent_dark": "#1f6feb",     # Azul oscuro

            # Estados
            "success": "#3fb950",         # Verde éxito
            "warning": "#d29922",         # Naranja advertencia
            "error": "#f85149",           # Rojo error
            "info": "#58a6ff",            # Azul info
        }

        # Ventana principal
        self.root = ctk.CTk()
        self.root.title("PyCraft - Minecraft Server Manager")
        self.root.geometry("1000x800")
        self.root.resizable(False, False)

        # Set window icon
        self.icon_path = None
        try:
            self.icon_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "PyCraft-Files", "icon.ico"
            )
            print(f"Icon path: {self.icon_path}")
            print(f"Icon exists: {os.path.exists(self.icon_path)}")
            if os.path.exists(self.icon_path):
                self.root.iconbitmap(self.icon_path)
                print("Main window icon set successfully")
        except Exception as e:
            print(f"No se pudo cargar el icono: {e}")
            import traceback
            traceback.print_exc()

        # Componentes
        self.api_handler = MinecraftAPIHandler()
        self.downloader = ServerDownloader()
        self.server_manager: Optional[ServerManager] = None
        self.modpack_manager = ModpackManager()
        self.java_manager = JavaManager()
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
        # Modpack metadata for sharing
        self.modpack_name = None
        self.modpack_version = None
        self.modpack_minecraft_version = None
        self.modpack_loader_name = None
        self.modpack_slug = None

        # Crear la interfaz
        self._create_widgets()

        # Cargar versiones al iniciar
        self._load_versions()

    def _set_window_icon(self, window):
        """Sets the PyCraft icon for a window"""
        try:
            if self.icon_path and os.path.exists(self.icon_path):
                # For CTkToplevel, we need to access the underlying tk window
                # and set the icon after the window is created
                def set_icon():
                    try:
                        # Direct iconbitmap call
                        window.iconbitmap(self.icon_path)
                    except Exception as e:
                        print(f"Error setting icon: {e}")

                # Call immediately
                set_icon()
                # Also call after window is mapped
                window.after(100, set_icon)
                window.after(500, set_icon)
        except Exception as e:
            print(f"Error in _set_window_icon: {e}")

    def _custom_askyesno(self, title: str, message: str, parent=None) -> bool:
        """Custom yes/no dialog with PyCraft icon"""
        dialog = ctk.CTkToplevel(parent or self.root)
        self._set_window_icon(dialog)
        dialog.title(title)
        dialog.geometry("450x200")
        dialog.resizable(False, False)
        dialog.transient(parent or self.root)
        dialog.grab_set()

        result = [False]

        # Message
        ctk.CTkLabel(
            dialog,
            text=message,
            font=ctk.CTkFont(size=13),
            wraplength=400,
            justify="left"
        ).pack(pady=30, padx=20)

        # Buttons frame
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=10)

        def on_yes():
            result[0] = True
            dialog.destroy()

        def on_no():
            result[0] = False
            dialog.destroy()

        ctk.CTkButton(
            button_frame,
            text="Sí",
            command=on_yes,
            width=100,
            fg_color=self.colors["success"],
            hover_color="#2d8a3e"
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            button_frame,
            text="No",
            command=on_no,
            width=100,
            fg_color="#6c757d",
            hover_color="#5a6268"
        ).pack(side="left", padx=10)

        # Wait for dialog to close
        dialog.wait_window()
        return result[0]

    def _custom_askokcancel(self, title: str, message: str, parent=None) -> bool:
        """Custom ok/cancel dialog with PyCraft icon"""
        dialog = ctk.CTkToplevel(parent or self.root)
        self._set_window_icon(dialog)
        dialog.title(title)
        dialog.geometry("450x200")
        dialog.resizable(False, False)
        dialog.transient(parent or self.root)
        dialog.grab_set()

        result = [False]

        # Message
        ctk.CTkLabel(
            dialog,
            text=message,
            font=ctk.CTkFont(size=13),
            wraplength=400,
            justify="left"
        ).pack(pady=30, padx=20)

        # Buttons frame
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=10)

        def on_ok():
            result[0] = True
            dialog.destroy()

        def on_cancel():
            result[0] = False
            dialog.destroy()

        ctk.CTkButton(
            button_frame,
            text="Aceptar",
            command=on_ok,
            width=100,
            fg_color=self.colors["success"],
            hover_color="#2d8a3e"
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            button_frame,
            text="Cancelar",
            command=on_cancel,
            width=100,
            fg_color="#6c757d",
            hover_color="#5a6268"
        ).pack(side="left", padx=10)

        # Wait for dialog to close
        dialog.wait_window()
        return result[0]

    def _create_widgets(self):
        """Crea todos los widgets de la interfaz"""

        # Header con logo y título
        header_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        header_frame.pack(pady=10, padx=20, fill="x")

        # Intentar cargar el logo
        try:
            # Get project root directory (go up from src/gui/main_window.py to project root)
            logo_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "PyCraft-Files", "logo.png"
            )
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

        # Crear las tabs
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
        # Fix scroll anidado
        self._fix_scrollable_frame_scroll(self.version_scrollable)

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
        # Fix scroll anidado
        self._fix_textbox_scroll(self.new_log_text)

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
        # Fix scroll anidado
        self._fix_textbox_scroll(self.existing_log_text)

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
            width=180,
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
            width=180,
            height=35,
            state="disabled",
            fg_color="red",
            hover_color="darkred"
        )
        self.stop_server_btn.pack(side="left", padx=5)

        self.config_server_btn = ctk.CTkButton(
            control_frame,
            text="⚙ Configuración",
            command=self._open_server_config,
            width=180,
            height=35,
            state="disabled",
            fg_color=self.colors["warning"],
            hover_color="#b87d1d"
        )
        self.config_server_btn.pack(side="left", padx=5)

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

        # Selector de modo (Instalación vs Gestión)
        mode_frame = ctk.CTkFrame(main_container, fg_color="gray15")
        mode_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(
            mode_frame,
            text="¿Qué quieres hacer?",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(15, 10))

        # Segmented button para elegir modo
        self.mods_mode_selector = ctk.CTkSegmentedButton(
            mode_frame,
            values=["Instalación de Modpack", "Abrir Servidor con Mods Existente"],
            command=self._on_mods_mode_change,
            width=700,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.mods_mode_selector.pack(pady=(5, 15))
        self.mods_mode_selector.set("Instalación de Modpack")

        # Separador
        ctk.CTkFrame(main_container, height=2, fg_color="gray30").pack(pady=10, fill="x")

        # Contenedores para cada modo
        self.modpack_install_frame = ctk.CTkFrame(main_container)
        self.modpack_management_frame = ctk.CTkFrame(main_container)

        # Crear el contenido de cada pestaña
        self._create_modpack_install_tab()
        self._create_modpack_management_tab()

        # Mostrar instalación por defecto
        self.modpack_install_frame.pack(pady=10, padx=10, fill="both", expand=True)

    def _create_modpack_install_tab(self):
        """Crea la pestaña de instalación de modpacks"""
        # Frame principal SIN scroll (el scroll está en el nivel superior)
        main_container = ctk.CTkFrame(self.modpack_install_frame, fg_color="transparent")
        main_container.pack(pady=5, padx=5, fill="both", expand=True)

        # Encabezado compacto
        header_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        header_frame.pack(pady=(5, 10), fill="x")

        # Título e indicador en la misma línea
        ctk.CTkLabel(
            header_frame,
            text="📦 Instalación de Modpack",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(side="left", padx=(10, 20))

        # Botón clickeable de Modrinth
        modrinth_button = ctk.CTkButton(
            header_frame,
            text="Modrinth",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="green",
            hover_color="darkgreen",
            corner_radius=5,
            width=100,
            height=25,
            command=lambda: webbrowser.open("https://modrinth.com/modpacks")
        )
        modrinth_button.pack(side="left")

        # Subtítulo
        ctk.CTkLabel(
            main_container,
            text="Descarga e instala modpacks completos de Modrinth",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        ).pack(pady=(0, 10), padx=10, anchor="w")

        # Hidden platform selector for compatibility
        self.platform_selector = ctk.CTkSegmentedButton(
            main_container,
            values=["Modrinth (Recomendado)", "CurseForge (Requiere API Key)"],
            command=self._on_platform_change,
            width=1,
            height=1
        )
        self.platform_selector.set("Modrinth (Recomendado)")

        self.cf_status_label = ctk.CTkLabel(main_container, text="")

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

        # Resultados de búsqueda - Frame con scroll interno controlado
        results_container = ctk.CTkFrame(search_frame, fg_color="gray20", corner_radius=10)
        results_container.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(
            results_container,
            text="Resultados:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="gray70"
        ).pack(anchor="w", padx=15, pady=(10, 5))

        # ScrollableFrame con altura fija para los resultados (evita overflow con muchos modpacks)
        self.modpack_results_frame = ctk.CTkScrollableFrame(
            results_container,
            fg_color="transparent",
            width=850,
            height=200  # Altura fija para mostrar ~4-5 modpacks con scroll
        )
        self.modpack_results_frame.pack(pady=(5, 10), padx=10, fill="x")
        # Fix mouse wheel scrolling
        self._fix_scrollable_frame_scroll(self.modpack_results_frame)

        # Label inicial
        self.no_results_label = ctk.CTkLabel(
            self.modpack_results_frame,
            text="Usa la búsqueda para encontrar modpacks",
            font=ctk.CTkFont(size=12),
            text_color="gray50"
        )
        self.no_results_label.pack(pady=30)

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
            fg_color=self.colors["success"],
            hover_color="#2d8a3e"
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
        ctk.CTkFrame(main_container, height=2, fg_color="gray30").pack(pady=15, fill="x")

        # Consola de instalación - Más compacta
        console_container = ctk.CTkFrame(main_container, fg_color="gray20", corner_radius=10)
        console_container.pack(pady=10, padx=10, fill="both", expand=True)

        ctk.CTkLabel(
            console_container,
            text="Proceso de Instalación",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", pady=(10, 5), padx=15)

        self.modpack_log_text = ctk.CTkTextbox(
            console_container,
            width=880,
            height=280,  # Aumentado de 180 a 280
            font=ctk.CTkFont(family="Consolas", size=11),  # Aumentado de 10 a 11
            wrap="word"
        )
        self.modpack_log_text.pack(pady=(5, 10), padx=10)
        # Fix scroll anidado
        self._fix_textbox_scroll(self.modpack_log_text)

        # Log inicial
        self._add_log_modpack("Bienvenido al instalador de Modpacks de PyCraft\n", "info")
        self._add_log_modpack("Busca un modpack, selecciónalo y elige una carpeta para comenzar.\n\n", "info")
        self._add_log_modpack("NOTA: La instalación automática incluye:\n", "info")
        self._add_log_modpack("  • Descarga del modpack y todos sus mods\n", "normal")
        self._add_log_modpack("  • Instalación automática de Forge o Fabric\n", "normal")
        self._add_log_modpack("  • Verificación e instalación de Java si es necesario\n", "normal")
        self._add_log_modpack("  • Configuración automática del servidor\n\n", "normal")

    def _create_modpack_management_tab(self):
        """Crea la pestaña de gestión de servidor con modpack"""
        # Frame principal SIN scroll (el scroll está en el nivel superior)
        main_container = ctk.CTkFrame(self.modpack_management_frame, fg_color="transparent")
        main_container.pack(pady=5, padx=5, fill="both", expand=True)

        # Título
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
            fg_color=self.colors["accent_dark"],
            hover_color=self.colors["accent_hover"],
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.install_client_btn.pack(pady=10)

        # Label informativo
        ctk.CTkLabel(
            modpack_server_frame,
            text="Instala el modpack en C:/Users/[tu-nombre]/.pycraft/modpack-modrinth/ para poder jugar",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(pady=(0, 15), padx=20)

        # Separador
        ctk.CTkFrame(main_container, height=2, fg_color="gray30").pack(pady=15, fill="x")

        # Consola y controles para servidor con modpack - Más compacta
        console_container = ctk.CTkFrame(main_container, fg_color="gray20", corner_radius=10)
        console_container.pack(pady=10, padx=10, fill="both", expand=True)

        ctk.CTkLabel(
            console_container,
            text="Consola del Servidor",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", pady=(10, 5), padx=15)

        # TextBox para logs del servidor con modpack
        self.modpack_server_log_text = ctk.CTkTextbox(
            console_container,
            width=880,
            height=280,  # Aumentado de 180 a 280 (consistencia)
            font=ctk.CTkFont(family="Consolas", size=11),  # Aumentado de 10 a 11
            wrap="word"
        )
        self.modpack_server_log_text.pack(pady=(5, 10), padx=10)
        # Fix scroll anidado
        self._fix_textbox_scroll(self.modpack_server_log_text)

        # Campo de input para comandos - Dentro del console container
        modpack_command_frame = ctk.CTkFrame(console_container, fg_color="transparent")
        modpack_command_frame.pack(pady=(0, 10), padx=10, fill="x")

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
            width=180,
            height=35,
            state="disabled",
            fg_color="red",
            hover_color="darkred"
        )
        self.stop_modpack_server_btn.pack(side="left", padx=5)

        self.config_modpack_server_btn = ctk.CTkButton(
            modpack_control_frame,
            text="⚙ Configuración",
            command=self._open_modpack_server_config,
            width=180,
            height=35,
            state="disabled",
            fg_color=self.colors["warning"],
            hover_color="#b87d1d"
        )
        self.config_modpack_server_btn.pack(side="left", padx=5)

        # Inicializar logs
        self._add_log_modpack_server("Consola del servidor con modpack\n", "info")
        self._add_log_modpack_server("Selecciona la carpeta de tu servidor para comenzar.\n", "info")

    def _create_info_tab(self):
        """Crea la sección de información y ayuda usando el módulo InfoTab"""
        tab = self.tabview.tab("Información y Ayuda")
        InfoTab(tab)

    def _create_settings_tab(self):
        """Creates the Settings tab with Java management and other configuration options"""
        tab = self.tabview.tab("Configuración")

        # Main scrollable container
        main_container = ctk.CTkScrollableFrame(tab, width=920, height=580)
        main_container.pack(pady=10, padx=10, fill="both", expand=True)

        # Title
        ctk.CTkLabel(
            main_container,
            text="⚙️ Configuración de PyCraft",
            font=("Arial", 24, "bold")
        ).pack(pady=10)

        # ===== JAVA MANAGEMENT SECTION =====
        java_frame = ctk.CTkFrame(main_container, fg_color="gray15")
        java_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(
            java_frame,
            text="☕ Gestión de Java",
            font=("Arial", 18, "bold")
        ).pack(pady=10)

        # Java info display
        self.java_info_frame = ctk.CTkFrame(java_frame, fg_color="gray20")
        self.java_info_frame.pack(pady=10, padx=20, fill="x")

        # Buttons frame
        java_buttons_frame = ctk.CTkFrame(java_frame, fg_color="transparent")
        java_buttons_frame.pack(pady=10)

        ctk.CTkButton(
            java_buttons_frame,
            text="🔄 Verificar Java",
            command=self._verify_java_installations,
            width=200,
            height=40,
            font=("Arial", 14)
        ).pack(side="left", padx=5)

        # Initial Java verification
        self._verify_java_installations()

        # ===== LANGUAGE SETTINGS =====
        language_frame = ctk.CTkFrame(main_container, fg_color="gray15")
        language_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(
            language_frame,
            text="🌐 Idioma / Language",
            font=("Arial", 18, "bold")
        ).pack(pady=10)

        ctk.CTkLabel(
            language_frame,
            text="Selecciona el idioma de la interfaz:",
            font=("Arial", 12)
        ).pack(pady=5)

        language_selector_frame = ctk.CTkFrame(language_frame, fg_color="transparent")
        language_selector_frame.pack(pady=10)

        self.language_var = ctk.StringVar(value="Español")

        ctk.CTkRadioButton(
            language_selector_frame,
            text="Español 🇪🇸",
            variable=self.language_var,
            value="Español",
            command=self._change_language
        ).pack(side="left", padx=10)

        ctk.CTkRadioButton(
            language_selector_frame,
            text="English 🇺🇸",
            variable=self.language_var,
            value="English",
            command=self._change_language
        ).pack(side="left", padx=10)

        ctk.CTkLabel(
            language_frame,
            text="⚠ Nota: Camb iar el idioma reiniciará la aplicación",
            font=("Arial", 10),
            text_color="orange"
        ).pack(pady=5)

        # ===== MODPACK CLIENT FOLDER MANAGEMENT =====
        modpack_frame = ctk.CTkFrame(main_container, fg_color="gray15")
        modpack_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(
            modpack_frame,
            text="📦 Gestión de Carpetas de Modpack Cliente",
            font=("Arial", 18, "bold")
        ).pack(pady=10)

        ctk.CTkLabel(
            modpack_frame,
            text="Administra las carpetas de modpacks instalados para el cliente:",
            font=("Arial", 12)
        ).pack(pady=5)

        # Buttons frame to hold both buttons side by side
        buttons_frame = ctk.CTkFrame(modpack_frame, fg_color="transparent")
        buttons_frame.pack(pady=10)

        ctk.CTkButton(
            buttons_frame,
            text="📂 Ver y Eliminar Carpetas de Modpack",
            command=self._manage_modpack_folders,
            width=300,
            height=40,
            font=("Arial", 14)
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            buttons_frame,
            text="📥 Instalar Modpack Cliente (para amigos)",
            command=self._open_client_modpack_installer,
            width=300,
            height=40,
            font=("Arial", 14),
            fg_color=self.colors["accent_dark"],
            hover_color=self.colors["accent_hover"]
        ).pack(side="left", padx=5)

    def _verify_java_installations(self):
        """Verifies and displays Java installations"""
        # Clear previous content
        for widget in self.java_info_frame.winfo_children():
            widget.destroy()

        # Get installations
        installations = self.java_manager.get_java_installations()

        if not installations:
            # No Java found
            ctk.CTkLabel(
                self.java_info_frame,
                text="⚠ No se encontraron instalaciones de Java gestionadas por PyCraft",
                font=("Arial", 12),
                text_color="orange"
            ).pack(pady=10)

            ctk.CTkButton(
                self.java_info_frame,
                text="⬇ Instalar Java",
                command=self._install_java_from_settings,
                width=200,
                height=35,
                fg_color="green",
                hover_color="darkgreen"
            ).pack(pady=10)
        else:
            # Display each installation
            for version, path, is_in_path in installations:
                install_frame = ctk.CTkFrame(self.java_info_frame, fg_color="gray25")
                install_frame.pack(pady=5, padx=10, fill="x")

                # Info section
                info_frame = ctk.CTkFrame(install_frame, fg_color="transparent")
                info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=10)

                ctk.CTkLabel(
                    info_frame,
                    text=f"☕ Java {version}",
                    font=("Arial", 14, "bold")
                ).pack(anchor="w")

                ctk.CTkLabel(
                    info_frame,
                    text=f"Ruta: {path}",
                    font=("Arial", 10),
                    text_color="gray"
                ).pack(anchor="w")

                status_text = "✓ En PATH del sistema" if is_in_path else "⚠ No está en PATH"
                status_color = "green" if is_in_path else "orange"
                ctk.CTkLabel(
                    info_frame,
                    text=status_text,
                    font=("Arial", 10),
                    text_color=status_color
                ).pack(anchor="w")

                # Buttons section
                buttons_frame = ctk.CTkFrame(install_frame, fg_color="transparent")
                buttons_frame.pack(side="right", padx=10)

                if not is_in_path:
                    ctk.CTkButton(
                        buttons_frame,
                        text="➕ Agregar a PATH",
                        command=lambda p=path: self._add_java_to_path_ui(p),
                        width=140,
                        height=30,
                        font=("Arial", 11),
                        fg_color="blue",
                        hover_color="darkblue"
                    ).pack(pady=2)
                else:
                    ctk.CTkButton(
                        buttons_frame,
                        text="➖ Quitar de PATH",
                        command=lambda p=path: self._remove_java_from_path_ui(p),
                        width=140,
                        height=30,
                        font=("Arial", 11),
                        fg_color="orange",
                        hover_color="darkorange"
                    ).pack(pady=2)

                ctk.CTkButton(
                    buttons_frame,
                    text="🗑️ Eliminar",
                    command=lambda v=version: self._delete_java_ui(v),
                    width=140,
                    height=30,
                    font=("Arial", 11),
                    fg_color="red",
                    hover_color="darkred"
                ).pack(pady=2)

    def _install_java_from_settings(self):
        """Handles Java installation from Settings tab"""
        # Ask user which version to install
        dialog = ctk.CTkInputDialog(
            text="¿Qué versión de Java quieres instalar?\nVersiones comunes: 8, 17, 21",
            title="Instalar Java"
        )
        version_str = dialog.get_input()

        if version_str:
            try:
                version = int(version_str)
                if version < 8 or version > 21:
                    messagebox.showerror("Error", "Versión inválida. Usa 8, 17 o 21.")
                    return

                # Show progress window
                progress_window = ctk.CTkToplevel(self.root)
                self._set_window_icon(progress_window)
                progress_window.title("Instalando Java")
                progress_window.geometry("600x400")
                progress_window.transient(self.root)
                progress_window.grab_set()

                ctk.CTkLabel(
                    progress_window,
                    text=f"Instalando Java {version}...",
                    font=("Arial", 16, "bold")
                ).pack(pady=20)

                log_text = ctk.CTkTextbox(progress_window, width=550, height=300)
                log_text.pack(pady=10, padx=20)

                def log_callback(message):
                    log_text.insert("end", message)
                    log_text.see("end")

                def install():
                    result = self.java_manager.download_java(version, log_callback)
                    if result:
                        log_callback("\n✓ Instalación completada!\n")
                        self.root.after(2000, progress_window.destroy)
                        self.root.after(2100, self._verify_java_installations)
                    else:
                        log_callback("\n✗ Error en la instalación\n")

                thread = threading.Thread(target=install, daemon=True)
                thread.start()

            except ValueError:
                messagebox.showerror("Error", "Debes ingresar un número de versión válido.")

    def _add_java_to_path_ui(self, java_path):
        """Adds Java to PATH from UI"""
        # Find java.exe in this path
        java_exe = self.java_manager._find_java_executable(java_path)
        if java_exe:
            java_bin_dir = java_exe.parent
            if self.java_manager.add_java_to_path(java_bin_dir):
                messagebox.showinfo(
                    "Éxito",
                    f"Java agregado al PATH del sistema.\n\n"
                    f"Nota: Es posible que necesites reiniciar las aplicaciones abiertas "
                    f"para que detecten el cambio."
                )
                self._verify_java_installations()
            else:
                messagebox.showerror("Error", "No se pudo agregar Java al PATH")
        else:
            messagebox.showerror("Error", "No se encontró el ejecutable de Java")

    def _remove_java_from_path_ui(self, java_path):
        """Removes Java from PATH from UI"""
        java_exe = self.java_manager._find_java_executable(java_path)
        if java_exe:
            java_bin_dir = java_exe.parent
            if self.java_manager.remove_java_from_path(java_bin_dir):
                messagebox.showinfo(
                    "Éxito",
                    f"Java removido del PATH del sistema.\n\n"
                    f"Nota: Es posible que necesites reiniciar las aplicaciones abiertas "
                    f"para que detecten el cambio."
                )
                self._verify_java_installations()
            else:
                messagebox.showerror("Error", "No se pudo remover Java del PATH")
        else:
            messagebox.showerror("Error", "No se encontró el ejecutable de Java")

    def _delete_java_ui(self, java_version):
        """Deletes a Java installation from UI"""
        result = self._custom_askyesno(
            "Confirmar eliminación",
            f"¿Estás seguro de que quieres eliminar Java {java_version}?\n\n"
            f"Esta acción no se puede deshacer."
        )

        if result:
            if self.java_manager.delete_java_installation(java_version):
                messagebox.showinfo("Éxito", f"Java {java_version} eliminado correctamente")
                self._verify_java_installations()
            else:
                messagebox.showerror(
                    "Error",
                    f"No se pudo eliminar Java {java_version}.\n"
                    f"Asegúrate de que no haya procesos de Java en ejecución."
                )

    def _change_language(self):
        """Handles language change"""
        selected = self.language_var.get()
        if selected == "English":
            messagebox.showinfo(
                "Language Change",
                "English language support is not yet implemented.\n"
                "This feature will be available in a future update."
            )
            # Reset to Spanish
            self.language_var.set("Español")
        else:
            # Already in Spanish, no action needed
            pass

    def _manage_modpack_folders(self):
        """Opens a window to manage modpack client folders"""
        # Check if there are any modpack folders
        pycraft_dir = Path.home() / ".pycraft"
        modpack_clients_dir = pycraft_dir / "modpack-modrinth"

        if not modpack_clients_dir.exists():
            messagebox.showinfo(
                "Sin carpetas",
                "No hay carpetas de modpack cliente instaladas."
            )
            return

        # Get all modpack folders
        modpack_folders = [f for f in modpack_clients_dir.iterdir() if f.is_dir()]

        if not modpack_folders:
            messagebox.showinfo(
                "Sin carpetas",
                "No hay carpetas de modpack cliente instaladas."
            )
            return

        # Create management window
        mgmt_window = ctk.CTkToplevel(self.root)
        self._set_window_icon(mgmt_window)
        mgmt_window.title("Gestión de Carpetas de Modpack Cliente")
        mgmt_window.geometry("700x500")
        mgmt_window.transient(self.root)
        mgmt_window.grab_set()

        ctk.CTkLabel(
            mgmt_window,
            text="📦 Carpetas de Modpack Cliente",
            font=("Arial", 18, "bold")
        ).pack(pady=20)

        ctk.CTkLabel(
            mgmt_window,
            text="Selecciona una carpeta para eliminarla:",
            font=("Arial", 12)
        ).pack(pady=5)

        # Scrollable frame for folders
        folders_frame = ctk.CTkScrollableFrame(mgmt_window, width=650, height=350)
        folders_frame.pack(pady=10, padx=20, fill="both", expand=True)

        for folder in modpack_folders:
            folder_frame = ctk.CTkFrame(folders_frame, fg_color="gray20")
            folder_frame.pack(pady=5, padx=10, fill="x")

            # Folder info
            info_frame = ctk.CTkFrame(folder_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=10)

            ctk.CTkLabel(
                info_frame,
                text=f"📁 {folder.name}",
                font=("Arial", 13, "bold")
            ).pack(anchor="w")

            ctk.CTkLabel(
                info_frame,
                text=f"Ruta: {folder}",
                font=("Arial", 9),
                text_color="gray"
            ).pack(anchor="w")

            # Size info
            try:
                size_mb = sum(f.stat().st_size for f in folder.rglob('*') if f.is_file()) / (1024 * 1024)
                ctk.CTkLabel(
                    info_frame,
                    text=f"Tamaño: {size_mb:.1f} MB",
                    font=("Arial", 9),
                    text_color="gray"
                ).pack(anchor="w")
            except:
                pass

            # Delete button
            ctk.CTkButton(
                folder_frame,
                text="🗑️ Eliminar",
                command=lambda f=folder, w=mgmt_window: self._delete_modpack_folder(f, w),
                width=100,
                height=30,
                fg_color="red",
                hover_color="darkred"
            ).pack(side="right", padx=10)

    def _delete_modpack_folder(self, folder_path, parent_window):
        """Deletes a modpack client folder"""
        result = self._custom_askyesno(
            "Confirmar eliminación",
            f"¿Estás seguro de que quieres eliminar la carpeta:\n{folder_path.name}?\n\n"
            f"Esta acción no se puede deshacer.",
            parent=parent_window
        )

        if result:
            try:
                import shutil
                shutil.rmtree(folder_path)
                messagebox.showinfo(
                    "Éxito",
                    f"Carpeta eliminada correctamente:\n{folder_path.name}",
                    parent=parent_window
                )
                # Refresh the window
                parent_window.destroy()
                self._manage_modpack_folders()
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"No se pudo eliminar la carpeta:\n{str(e)}",
                    parent=parent_window
                )

    def _open_client_modpack_installer(self):
        """Opens a window to search and install client modpacks for friends"""
        # Create installer window
        installer_window = ctk.CTkToplevel(self.root)
        self._set_window_icon(installer_window)
        installer_window.title("Instalar Modpack Cliente")
        installer_window.geometry("900x700")
        installer_window.transient(self.root)
        installer_window.grab_set()

        # Main container
        main_container = ctk.CTkFrame(installer_window)
        main_container.pack(pady=10, padx=10, fill="both", expand=True)

        # Title
        ctk.CTkLabel(
            main_container,
            text="📥 Instalar Modpack Cliente (para amigos)",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=10)

        ctk.CTkLabel(
            main_container,
            text="Busca e instala modpacks para que tus amigos puedan jugar en tu servidor",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        ).pack(pady=(0, 10))

        # Search section
        search_frame = ctk.CTkFrame(main_container, fg_color="gray20")
        search_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(
            search_frame,
            text="Buscar Modpacks en Modrinth",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)

        search_input_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_input_frame.pack(pady=5)

        search_entry = ctk.CTkEntry(
            search_input_frame,
            placeholder_text="Ej: Create, ATM9, RLCraft, Prominence...",
            width=500,
            height=35
        )
        search_entry.pack(side="left", padx=(0, 10))

        # Search results frame
        results_container = ctk.CTkFrame(search_frame, fg_color="gray25", corner_radius=10)
        results_container.pack(pady=10, padx=10, fill="both", expand=True)

        ctk.CTkLabel(
            results_container,
            text="Resultados:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="gray70"
        ).pack(anchor="w", padx=15, pady=(10, 5))

        results_frame = ctk.CTkScrollableFrame(
            results_container,
            fg_color="transparent",
            width=850,
            height=250
        )
        results_frame.pack(pady=(5, 10), padx=10, fill="both", expand=True)

        no_results_label = ctk.CTkLabel(
            results_frame,
            text="Usa la búsqueda para encontrar modpacks",
            font=ctk.CTkFont(size=12),
            text_color="gray50"
        )
        no_results_label.pack(pady=20)

        # Installation console
        console_frame = ctk.CTkFrame(main_container, fg_color="gray20")
        console_frame.pack(pady=10, padx=10, fill="both", expand=True)

        ctk.CTkLabel(
            console_frame,
            text="Consola de Instalación",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=5)

        console_textbox = ctk.CTkTextbox(
            console_frame,
            width=850,
            height=150,
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled"
        )
        console_textbox.pack(pady=5, padx=10, fill="both", expand=True)

        def add_console_log(message: str):
            """Adds a message to the console"""
            console_textbox.configure(state="normal")
            console_textbox.insert("end", message)
            console_textbox.see("end")
            console_textbox.configure(state="disabled")

        def search_modpacks():
            """Searches for modpacks on Modrinth"""
            query = search_entry.get().strip()
            if not query:
                return

            # Clear previous results
            for widget in results_frame.winfo_children():
                widget.destroy()

            add_console_log(f"Buscando '{query}' en Modrinth...\n")

            def do_search():
                try:
                    results = self.modpack_manager.search_modpacks(query, platform="modrinth")

                    if results:
                        add_console_log(f"✓ Encontrados {len(results)} modpacks\n\n")

                        for modpack in results[:10]:  # Show max 10 results
                            self._create_client_modpack_result_card(
                                results_frame,
                                modpack,
                                installer_window,
                                add_console_log
                            )
                    else:
                        no_results_label.pack(pady=20)
                        add_console_log("No se encontraron modpacks\n")

                except Exception as e:
                    add_console_log(f"✗ Error: {str(e)}\n")

            threading.Thread(target=do_search, daemon=True).start()

        search_btn = ctk.CTkButton(
            search_input_frame,
            text="Buscar",
            command=search_modpacks,
            width=120,
            height=35
        )
        search_btn.pack(side="left")

        search_entry.bind("<Return>", lambda e: search_modpacks())

    def _create_client_modpack_result_card(self, parent_frame, modpack: Dict, installer_window, log_callback):
        """Creates a result card for client modpack installation"""
        card = ctk.CTkFrame(
            parent_frame,
            fg_color=self.colors["bg_tertiary"],
            corner_radius=12,
            border_width=1,
            border_color=self.colors["border_light"]
        )
        card.pack(pady=6, padx=10, fill="x")

        # Modpack info
        name = modpack.get("title", "Sin nombre")
        description = modpack.get("description", "Sin descripción")
        author = modpack.get("author", "Desconocido")
        downloads = modpack.get("downloads", 0)
        project_id = modpack.get("project_id", "")

        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=15, pady=10)

        # Title
        ctk.CTkLabel(
            info_frame,
            text=name,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors["text_primary"],
            anchor="w"
        ).pack(anchor="w")

        # Description (truncated)
        desc_truncated = description[:100] + "..." if len(description) > 100 else description
        ctk.CTkLabel(
            info_frame,
            text=desc_truncated,
            font=ctk.CTkFont(size=11),
            text_color=self.colors["text_secondary"],
            anchor="w",
            wraplength=500
        ).pack(anchor="w", pady=(3, 0))

        # Metadata
        meta_text = f"Por {author} • {downloads:,} descargas"
        ctk.CTkLabel(
            info_frame,
            text=meta_text,
            font=ctk.CTkFont(size=10),
            text_color=self.colors["text_muted"],
            anchor="w"
        ).pack(anchor="w", pady=(3, 0))

        # Install button
        install_btn = ctk.CTkButton(
            card,
            text="Seleccionar",
            command=lambda: self._select_client_modpack_version(
                project_id,
                name,
                installer_window,
                log_callback
            ),
            width=120,
            height=35,
            fg_color=self.colors["accent_dark"],
            hover_color=self.colors["accent_hover"],
            font=ctk.CTkFont(size=12, weight="bold")
        )
        install_btn.pack(side="right", padx=15, pady=10)

    def _select_client_modpack_version(self, project_id: str, modpack_name: str, parent_window, log_callback):
        """Opens a dialog to select modpack version for client installation"""
        log_callback(f"\nObteniendo versiones de '{modpack_name}'...\n")

        def fetch_versions():
            try:
                versions = self.modpack_manager.modrinth_api.get_modpack_versions(project_id)

                if not versions:
                    log_callback("✗ No se encontraron versiones\n")
                    return

                log_callback(f"✓ Encontradas {len(versions)} versiones\n\n")

                # Create version selection dialog
                self.root.after(0, lambda: self._show_client_version_dialog(
                    versions,
                    modpack_name,
                    parent_window,
                    log_callback
                ))

            except Exception as e:
                log_callback(f"✗ Error al obtener versiones: {str(e)}\n")

        threading.Thread(target=fetch_versions, daemon=True).start()

    def _show_client_version_dialog(self, versions: List, modpack_name: str, parent_window, log_callback):
        """Shows dialog to select a version for client installation"""
        version_dialog = ctk.CTkToplevel(parent_window)
        self._set_window_icon(version_dialog)
        version_dialog.title(f"Seleccionar Versión - {modpack_name}")
        version_dialog.geometry("500x600")
        version_dialog.transient(parent_window)
        version_dialog.grab_set()

        ctk.CTkLabel(
            version_dialog,
            text=f"Versiones de {modpack_name}",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=15)

        ctk.CTkLabel(
            version_dialog,
            text="Selecciona la versión que quieres instalar:",
            font=ctk.CTkFont(size=12)
        ).pack(pady=5)

        # Scrollable frame for versions
        versions_frame = ctk.CTkScrollableFrame(version_dialog, width=450, height=450)
        versions_frame.pack(pady=10, padx=20, fill="both", expand=True)

        for version in versions:
            version_name = version.get("name", "Sin nombre")
            version_number = version.get("version_number", "")
            game_versions = version.get("game_versions", [])
            mc_version = game_versions[0] if game_versions else "Desconocida"

            version_frame = ctk.CTkFrame(versions_frame, fg_color="gray20")
            version_frame.pack(pady=5, padx=10, fill="x")

            info_frame = ctk.CTkFrame(version_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=10)

            ctk.CTkLabel(
                info_frame,
                text=version_name,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w"
            ).pack(anchor="w")

            ctk.CTkLabel(
                info_frame,
                text=f"Minecraft {mc_version} • Versión {version_number}",
                font=ctk.CTkFont(size=10),
                text_color="gray",
                anchor="w"
            ).pack(anchor="w")

            ctk.CTkButton(
                version_frame,
                text="Instalar",
                command=lambda v=version: self._install_client_modpack_version(
                    v,
                    modpack_name,
                    version_dialog,
                    parent_window,
                    log_callback
                ),
                width=100,
                fg_color=self.colors["success"],
                hover_color="#2d8a3e"
            ).pack(side="right", padx=10, pady=10)

    def _install_client_modpack_version(self, version: Dict, modpack_name: str, version_dialog, parent_window, log_callback):
        """Installs the selected modpack version for client"""
        version_dialog.destroy()

        log_callback(f"\n{'='*50}\n")
        log_callback(f"Instalando {modpack_name} para cliente...\n")
        log_callback(f"{'='*50}\n\n")

        def install():
            try:
                import zipfile
                import tempfile
                import urllib.request

                # Get the download URL for the modpack
                files = version.get("files", [])
                if not files:
                    log_callback("✗ No se encontró archivo de descarga\n")
                    return

                download_url = files[0].get("url", "")
                if not download_url:
                    log_callback("✗ URL de descarga inválida\n")
                    return

                # Install to client folder
                user_folder = os.path.expanduser('~')
                client_path = os.path.join(user_folder, '.pycraft', 'modpack-modrinth', modpack_name)

                log_callback(f"Descargando modpack...\n")
                log_callback(f"Destino: {client_path}\n\n")

                # Create temp directory
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Download the modpack
                    modpack_file = os.path.join(temp_dir, "modpack.mrpack")
                    log_callback("Descargando archivo...\n")
                    urllib.request.urlretrieve(download_url, modpack_file)
                    log_callback("✓ Descarga completada\n\n")

                    # Extract the modpack
                    log_callback("Extrayendo archivos...\n")
                    extract_dir = os.path.join(temp_dir, "extracted")
                    os.makedirs(extract_dir, exist_ok=True)

                    with zipfile.ZipFile(modpack_file, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)

                    log_callback("✓ Extracción completada\n\n")

                    # Copy to client folder
                    log_callback("Copiando archivos a la carpeta de cliente...\n")
                    os.makedirs(client_path, exist_ok=True)

                    # Copy overrides folder (contains mods, configs, etc.)
                    overrides_path = os.path.join(extract_dir, "overrides")
                    if os.path.exists(overrides_path):
                        for item in os.listdir(overrides_path):
                            src = os.path.join(overrides_path, item)
                            dst = os.path.join(client_path, item)
                            if os.path.isdir(src):
                                shutil.copytree(src, dst, dirs_exist_ok=True)
                            else:
                                shutil.copy2(src, dst)

                    # Also copy the manifest for reference
                    manifest_src = os.path.join(extract_dir, "modrinth.index.json")
                    if os.path.exists(manifest_src):
                        shutil.copy2(manifest_src, os.path.join(client_path, "modrinth.index.json"))

                    log_callback("✓ Archivos copiados correctamente\n\n")

                log_callback(f"\n{'='*50}\n")
                log_callback("✓ INSTALACIÓN COMPLETADA\n")
                log_callback(f"{'='*50}\n\n")
                log_callback(f"Ruta de instalación:\n{client_path}\n\n")
                log_callback("Configura esta ruta en tu launcher para jugar!\n")

                # Show success message
                self.root.after(0, lambda: messagebox.showinfo(
                    "Instalación Completada",
                    f"Modpack instalado correctamente!\n\n"
                    f"Ruta: {client_path}\n\n"
                    f"Ponlo en el directorio de tu launcher para jugar.",
                    parent=parent_window
                ))

            except Exception as e:
                log_callback(f"\n✗ Error: {str(e)}\n")

        threading.Thread(target=install, daemon=True).start()

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

        # Destacar el botón seleccionado con un color verde suave
        for btn in self.version_buttons:
            if btn.cget("text") == version:
                btn.configure(fg_color="#2d5f2e", hover_color="#3d7f3e")  # Dark green
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

    def _on_mods_mode_change(self, value):
        """Cambia entre instalación de modpack y gestión de servidor"""
        if value == "Instalación de Modpack":
            self.modpack_management_frame.pack_forget()
            self.modpack_install_frame.pack(pady=10, padx=10, fill="both", expand=True)
        else:  # "Gestión de Servidor"
            self.modpack_install_frame.pack_forget()
            self.modpack_management_frame.pack(pady=10, padx=10, fill="both", expand=True)

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
                self.config_server_btn.configure(state="normal")
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

                # Verificar e instalar Java automáticamente
                self.progress_label.configure(text="Verificando Java...")
                java_executable = self.java_manager.ensure_java_installed(
                    self.selected_version,
                    log_callback=self._add_log_new_simple
                )

                if not java_executable:
                    self._add_log_new("\nError: No se pudo obtener una versión compatible de Java\n", "error")
                    messagebox.showerror(
                        "Error de Java",
                        "No se pudo instalar Java automáticamente.\n\n"
                        "Por favor, instala Java manualmente desde:\n"
                        "https://adoptium.net/temurin/releases/"
                    )
                    return

                # Configurar servidor
                self._add_log_new("\nConfigurando servidor (primera ejecución)...\n", "info")
                self._add_log_new("Esto puede tomar un momento...\n", "warning")
                self.progress_label.configure(text="Configurando servidor...")

                self.server_manager = ServerManager(self.server_folder, java_executable=java_executable)
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

                    # Warning message in orange
                    self._add_log_new("⚠️ IMPORTANTE: Para jugar con amigos, ve a 'Información y Ayuda' → 'Jugar con Amigos'\n\n", "warning")
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
        self.config_server_btn.configure(state="disabled")  # No configurar mientras corre
        self.stop_server_btn.configure(state="normal")

        def start():
            success = self.server_manager.start_server(
                log_callback=self._add_log_existing_simple,
                detached=True
            )
            if not success:
                self._add_log_existing("\n✗ Error al iniciar el servidor\n", "error")
                self.start_server_btn.configure(state="normal")
                self.config_server_btn.configure(state="normal")
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
        self.config_server_btn.configure(state="normal")  # Permitir configurar cuando está detenido
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
            self._add_log_existing("║      ✓ ¡SERVIDOR LISTO Y FUNCIONANDO!                ║\n", "success")
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

    def _open_server_config(self):
        """Abre el diálogo de configuración del servidor vanilla"""
        if not self.server_manager or not self.is_server_configured:
            messagebox.showwarning("Advertencia", "Primero debes seleccionar un servidor")
            return

        if self.server_manager.is_server_running():
            messagebox.showwarning("Advertencia", "Detén el servidor antes de configurarlo")
            return

        # Crear ventana de configuración
        config_window = ctk.CTkToplevel(self.root)
        self._set_window_icon(config_window)
        config_window.title("Configuración del Servidor")
        config_window.geometry("450x450")  # Aumentado para mostrar información de versión
        config_window.resizable(False, False)

        # Centrar ventana
        config_window.transient(self.root)
        config_window.grab_set()

        # Título
        title_label = ctk.CTkLabel(
            config_window,
            text="⚙️ Configuración del Servidor",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(20, 10))

        # Dificultad
        difficulty_frame = ctk.CTkFrame(config_window, fg_color="gray20")
        difficulty_frame.pack(pady=15, padx=20, fill="both", expand=True)

        ctk.CTkLabel(
            difficulty_frame,
            text="Dificultad del Servidor:",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(15, 10))

        difficulty_var = ctk.StringVar(value="normal")

        difficulties = [
            ("Pacífica (sin monstruos)", "peaceful"),
            ("Fácil", "easy"),
            ("Normal", "normal"),
            ("Difícil", "hard")
        ]

        for text, value in difficulties:
            radio = ctk.CTkRadioButton(
                difficulty_frame,
                text=text,
                variable=difficulty_var,
                value=value,
                font=ctk.CTkFont(size=13)
            )
            radio.pack(pady=8, padx=20, anchor="w")

        # Información de versión
        version_frame = ctk.CTkFrame(config_window, fg_color="gray20")
        version_frame.pack(pady=10, padx=20, fill="x")

        # Mostrar versión del servidor
        version_text = f"Versión del servidor: {self.selected_version or 'Desconocida'}"
        ctk.CTkLabel(
            version_frame,
            text=version_text,
            font=ctk.CTkFont(size=12),
            text_color="gray70"
        ).pack(pady=10, padx=10)

        # Botones
        button_frame = ctk.CTkFrame(config_window, fg_color="transparent")
        button_frame.pack(pady=20)

        def apply_config():
            difficulty = difficulty_var.get()
            success = self.server_manager.configure_server_properties(
                difficulty=difficulty,
                log_callback=self._add_log_existing_simple
            )

            if success:
                self._add_log_existing(f"\n✓ Configuración aplicada: Dificultad = {difficulty}\n", "success")
                messagebox.showinfo("Éxito", f"Configuración aplicada correctamente!\n\nDificultad: {difficulty}")
                config_window.destroy()
            else:
                self._add_log_existing("\n✗ Error al aplicar configuración. Ver detalles arriba.\n", "error")
                messagebox.showerror("Error", "No se pudo aplicar la configuración.\nRevisa los logs para más detalles.")

        ctk.CTkButton(
            button_frame,
            text="Aplicar",
            command=apply_config,
            width=120,
            fg_color=self.colors["success"],
            hover_color="#2d8a3e"
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            button_frame,
            text="Cancelar",
            command=config_window.destroy,
            width=120,
            fg_color=self.colors["bg_hover"],
            hover_color=self.colors["border_light"]
        ).pack(side="left", padx=10)

    def _open_modpack_server_config(self):
        """Abre el diálogo de configuración del servidor con modpack"""
        if not self.modpack_server_manager or not self.is_modpack_server_configured:
            messagebox.showwarning("Advertencia", "Primero debes seleccionar un servidor con modpack")
            return

        if self.modpack_server_manager.is_server_running():
            messagebox.showwarning("Advertencia", "Detén el servidor antes de configurarlo")
            return

        # Crear ventana de configuración
        config_window = ctk.CTkToplevel(self.root)
        self._set_window_icon(config_window)
        config_window.title("Configuración del Servidor con Modpack")
        config_window.geometry("450x500")  # Aumentado para mostrar información de versión y modpack
        config_window.resizable(False, False)

        # Centrar ventana
        config_window.transient(self.root)
        config_window.grab_set()

        # Título
        title_label = ctk.CTkLabel(
            config_window,
            text="⚙️ Configuración del Servidor",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(20, 10))

        # Dificultad
        difficulty_frame = ctk.CTkFrame(config_window, fg_color="gray20")
        difficulty_frame.pack(pady=15, padx=20, fill="both", expand=True)

        ctk.CTkLabel(
            difficulty_frame,
            text="Dificultad del Servidor:",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(15, 10))

        difficulty_var = ctk.StringVar(value="normal")

        difficulties = [
            ("Pacífica (sin monstruos)", "peaceful"),
            ("Fácil", "easy"),
            ("Normal", "normal"),
            ("Difícil", "hard")
        ]

        for text, value in difficulties:
            radio = ctk.CTkRadioButton(
                difficulty_frame,
                text=text,
                variable=difficulty_var,
                value=value,
                font=ctk.CTkFont(size=13)
            )
            radio.pack(pady=8, padx=20, anchor="w")

        # Información de versión y modpack
        version_frame = ctk.CTkFrame(config_window, fg_color="gray20")
        version_frame.pack(pady=10, padx=20, fill="x")

        # Mostrar información del servidor y modpack
        info_container = ctk.CTkFrame(version_frame, fg_color="transparent")
        info_container.pack(pady=10, padx=10, fill="x")

        # Nombre del modpack
        modpack_name_text = f"Modpack: {self.modpack_name or 'Desconocido'}"
        ctk.CTkLabel(
            info_container,
            text=modpack_name_text,
            font=ctk.CTkFont(size=12),
            text_color="gray70",
            anchor="w"
        ).pack(pady=2, anchor="w")

        # Versión del modpack
        modpack_version_text = f"Versión del modpack: {self.modpack_version or 'Desconocida'}"
        ctk.CTkLabel(
            info_container,
            text=modpack_version_text,
            font=ctk.CTkFont(size=12),
            text_color="gray70",
            anchor="w"
        ).pack(pady=2, anchor="w")

        # Versión de Minecraft
        mc_version_text = f"Versión del servidor: {self.modpack_minecraft_version or 'Desconocida'}"
        ctk.CTkLabel(
            info_container,
            text=mc_version_text,
            font=ctk.CTkFont(size=12),
            text_color="gray70",
            anchor="w"
        ).pack(pady=2, anchor="w")

        # Tipo de servidor (Forge/Fabric)
        loader_text = f"Tipo: {self.modpack_loader_name.capitalize() if self.modpack_loader_name else 'Desconocido'}"
        ctk.CTkLabel(
            info_container,
            text=loader_text,
            font=ctk.CTkFont(size=12),
            text_color="gray70",
            anchor="w"
        ).pack(pady=2, anchor="w")

        # Botones
        button_frame = ctk.CTkFrame(config_window, fg_color="transparent")
        button_frame.pack(pady=20)

        def apply_config():
            difficulty = difficulty_var.get()
            success = self.modpack_server_manager.configure_server_properties(
                difficulty=difficulty,
                log_callback=self._add_log_modpack_server_simple
            )

            if success:
                self._add_log_modpack_server(f"\n✓ Configuración aplicada: Dificultad = {difficulty}\n", "success")
                messagebox.showinfo("Éxito", f"Configuración aplicada correctamente!\n\nDificultad: {difficulty}")
                config_window.destroy()
            else:
                self._add_log_modpack_server("\n✗ Error al aplicar configuración. Ver detalles arriba.\n", "error")
                messagebox.showerror("Error", "No se pudo aplicar la configuración.\nRevisa los logs para más detalles.")

        ctk.CTkButton(
            button_frame,
            text="Aplicar",
            command=apply_config,
            width=120,
            fg_color=self.colors["success"],
            hover_color="#2d8a3e"
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            button_frame,
            text="Cancelar",
            command=config_window.destroy,
            width=120,
            fg_color=self.colors["bg_hover"],
            hover_color=self.colors["border_light"]
        ).pack(side="left", padx=10)

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
            response = self._custom_askyesno(
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

    def _fix_textbox_scroll(self, textbox):
        """
        Arregla el problema de scroll anidado en CTkTextbox.
        Cuando el mouse está sobre el textbox, SOLO scrollea el textbox, no el padre.
        """
        # Variable para saber si el mouse está dentro del textbox
        mouse_inside = [False]

        def on_enter(event):
            mouse_inside[0] = True

        def on_leave(event):
            mouse_inside[0] = False

        def on_mouse_wheel(event):
            if mouse_inside[0]:
                # Get the internal textbox widget
                text_widget = textbox._textbox

                # Scroll the textbox (delta is positive for scroll up, negative for scroll down)
                # On Windows, event.delta is usually 120 or -120
                if event.delta > 0:
                    text_widget.yview_scroll(-1, "units")
                elif event.delta < 0:
                    text_widget.yview_scroll(1, "units")

                # Prevent propagation to parent scrollable frame
                return "break"
            return None

        # Bindear eventos de entrada/salida del mouse
        textbox.bind("<Enter>", on_enter)
        textbox.bind("<Leave>", on_leave)

        # Bindear eventos de scroll (Windows/Linux usa MouseWheel)
        textbox.bind("<MouseWheel>", on_mouse_wheel)
        # Mac/Linux pueden usar Button-4 y Button-5
        textbox.bind("<Button-4>", lambda e: on_mouse_wheel(type('Event', (), {'delta': 120})()))
        textbox.bind("<Button-5>", lambda e: on_mouse_wheel(type('Event', (), {'delta': -120})()))

    def _fix_scrollable_frame_scroll(self, scrollable_frame):
        """
        Arregla el problema de scroll anidado en CTkScrollableFrame.
        Intercepta la ruedita del mouse cuando está sobre el frame.
        """
        def on_mouse_wheel(event):
            # Interceptar el evento y scrollear el canvas interno manualmente
            if hasattr(scrollable_frame, '_parent_canvas'):
                canvas = scrollable_frame._parent_canvas

                # Determinar dirección y magnitud del scroll
                if event.delta:
                    # Windows/MacOS - event.delta es positivo para arriba, negativo para abajo
                    # Invertir el signo y escalar para hacer scroll más rápido
                    # Dividir entre 120 es estándar en Windows, luego multiplicar por 10 para velocidad
                    delta = int(-event.delta / 120) * 10
                else:
                    # Linux (event.num)
                    # num=4 es scroll up, num=5 es scroll down
                    delta = -10 if event.num == 4 else 10

                # Scrollear el canvas
                canvas.yview_scroll(delta, "units")

            # SIEMPRE prevenir propagación al padre
            return "break"

        def bind_widget_tree(widget):
            """Bindea recursivamente a un widget y todos sus hijos"""
            try:
                # Bindear al widget actual
                widget.bind("<MouseWheel>", on_mouse_wheel)
                widget.bind("<Button-4>", on_mouse_wheel)  # Linux scroll up
                widget.bind("<Button-5>", on_mouse_wheel)  # Linux scroll down

                # Bindear recursivamente a todos los hijos
                for child in widget.winfo_children():
                    bind_widget_tree(child)
            except:
                pass

        try:
            # Bindear al frame principal
            bind_widget_tree(scrollable_frame)

            # Bindear al canvas interno
            if hasattr(scrollable_frame, '_parent_canvas'):
                canvas = scrollable_frame._parent_canvas
                canvas.bind("<MouseWheel>", on_mouse_wheel)
                canvas.bind("<Button-4>", on_mouse_wheel)
                canvas.bind("<Button-5>", on_mouse_wheel)

            # Bindear al frame interno que contiene el contenido
            if hasattr(scrollable_frame, '_parent_frame'):
                bind_widget_tree(scrollable_frame._parent_frame)

            # Crear un método para bindear widgets nuevos que se agreguen después
            original_pack = None
            if hasattr(scrollable_frame, '_parent_frame'):
                parent_frame = scrollable_frame._parent_frame

                # Guardar el método pack original
                def make_bind_on_pack(original_method):
                    def bind_on_pack(*args, **kwargs):
                        result = original_method(*args, **kwargs)
                        # Después de pack, bindear eventos de scroll
                        bind_widget_tree(parent_frame)
                        return result
                    return bind_on_pack

                # No modificamos pack ya que puede causar problemas
                # En su lugar, usaremos after para re-bindear periódicamente
                def rebind_children():
                    try:
                        bind_widget_tree(scrollable_frame)
                        if hasattr(scrollable_frame, '_parent_frame'):
                            bind_widget_tree(scrollable_frame._parent_frame)
                    except:
                        pass
                    # Re-ejecutar cada 500ms
                    scrollable_frame.after(500, rebind_children)

                # Iniciar el rebinding automático
                scrollable_frame.after(500, rebind_children)

        except Exception as e:
            print(f"Error al configurar scroll fix: {e}")

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
        """Crea una tarjeta visual mejorada para un modpack en los resultados"""
        # Card container con mejor diseño usando la paleta de colores
        card = ctk.CTkFrame(
            self.modpack_results_frame,
            fg_color=self.colors["bg_tertiary"],
            corner_radius=12,
            border_width=1,
            border_color=self.colors["border_light"]
        )
        card.pack(pady=6, padx=10, fill="x")

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

        # Contenedor interno con padding
        inner_frame = ctk.CTkFrame(card, fg_color="transparent")
        inner_frame.pack(fill="both", expand=True, padx=15, pady=12)

        # Header con título y botón en la misma línea
        header_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 8))

        # Título del modpack
        title_label = ctk.CTkLabel(
            header_frame,
            text=name,
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
            text_color=self.colors["text_primary"]
        )
        title_label.pack(side="left", fill="x", expand=True)

        # Botón para seleccionar
        select_btn = ctk.CTkButton(
            header_frame,
            text="Seleccionar",
            command=lambda: self._on_modpack_select(modpack, platform),
            width=100,
            height=30,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        select_btn.pack(side="right")

        # Descripción truncada
        desc_text = description[:120] + "..." if len(description) > 120 else description
        desc_label = ctk.CTkLabel(
            inner_frame,
            text=desc_text,
            font=ctk.CTkFont(size=11),
            text_color=self.colors["text_secondary"],
            anchor="w",
            justify="left",
            wraplength=700
        )
        desc_label.pack(fill="x", pady=(0, 8))

        # Info adicional con iconos
        info_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        info_frame.pack(fill="x")

        # Autor
        author_label = ctk.CTkLabel(
            info_frame,
            text=f"👤 {author}",
            font=ctk.CTkFont(size=10),
            text_color=self.colors["text_muted"],
            anchor="w"
        )
        author_label.pack(side="left", padx=(0, 15))

        # Descargas
        downloads_label = ctk.CTkLabel(
            info_frame,
            text=f"⬇ {downloads:,} descargas",
            font=ctk.CTkFont(size=10),
            text_color=self.colors["text_muted"],
            anchor="w"
        )
        downloads_label.pack(side="left")

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
                    self._add_log_modpack("Sube a 'Abrir Servidor con Mods Existente' y:\n", "info")
                    self._add_log_modpack("1. Selecciona la carpeta del servidor que acabas de instalar\n", "normal")
                    self._add_log_modpack("2. Haz clic en 'Instalar Modpack para Cliente'\n", "normal")
                    self._add_log_modpack("3. Luego podrás iniciar el servidor\n\n", "normal")

                    messagebox.showinfo(
                        "¡Servidor Instalado!",
                        f"El modpack del SERVIDOR se instaló correctamente en:\n{self.modpack_server_folder}\n\n"
                        "IMPORTANTE: Ahora debes instalarlo también para el CLIENTE.\n\n"
                        "Sube a 'Abrir Servidor con Mods Existente' en esta pestaña\n"
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

                # Detectar versiones y metadata
                mc_version, loader_version = self._detect_server_versions(folder, server_type)
                modpack_name = self._detect_modpack_name(folder)

                # Store metadata for sharing
                self.modpack_name = modpack_name
                self.modpack_minecraft_version = mc_version
                self.modpack_loader_name = server_type

                # Try to get version and slug from manifest
                modpack_version, modpack_slug = self._get_modpack_metadata(folder)
                self.modpack_version = modpack_version
                self.modpack_slug = modpack_slug

                # Check if client modpack is already installed
                if self._is_client_modpack_installed(modpack_name):
                    self.install_client_btn.configure(
                        state="disabled",
                        text="✓ Modpack Cliente Ya Instalado"
                    )
                else:
                    self.install_client_btn.configure(state="normal")

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
                self._add_log_modpack_server("1. Instalar Modpack para Cliente (botón azul arriba)\n", "normal")
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
                self.config_modpack_server_btn.configure(state="normal")
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

    def _is_client_modpack_installed(self, modpack_name: str) -> bool:
        """
        Checks if a client modpack is already installed

        Args:
            modpack_name: Name of the modpack

        Returns:
            True if installed, False otherwise
        """
        if not modpack_name:
            return False

        user_folder = os.path.expanduser('~')
        client_path = os.path.join(user_folder, '.pycraft', 'modpack-modrinth', modpack_name)

        # Check if the folder exists and has mods
        if os.path.exists(client_path):
            mods_path = os.path.join(client_path, 'mods')
            if os.path.exists(mods_path):
                # Check if there are any mod files
                mod_files = [f for f in os.listdir(mods_path) if f.endswith('.jar')]
                return len(mod_files) > 0

        return False

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

        response = self._custom_askyesno(
            "Confirmar Instalación",
            f"¿Instalar el modpack para el cliente?\n\n"
            f"El modpack se instalará en:\n"
            f"C:\\Users\\{os.getenv('USERNAME')}\\.pycraft\\modpack-modrinth\\{modpack_name}\n\n"
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
                    final_path = os.path.join(user_folder, '.pycraft', 'modpack-modrinth', modpack_name)

                    # Show success message
                    messagebox.showinfo(
                        "¡Instalación Completada!",
                        f"El modpack se instaló correctamente para el cliente en:\n\n"
                        f"{final_path}\n\n"
                        f"Ahora puedes:\n"
                        f"1. Abrir SKLauncher (o tu launcher)\n"
                        f"2. Configurar el 'Directorio del juego' a la ruta de arriba\n"
                        f"3. ¡Iniciar el juego y conectarte al servidor!\n\n"
                        f"Para compartir con amigos, revisa la pestaña 'Información y Ayuda'\n"
                        f"en la sección '🎮 Jugar con Amigos'."
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

            # Debug: Log manifest existence
            self._add_log_modpack_server(f"\n🔍 Buscando manifests...\n", "info")
            self._add_log_modpack_server(f"  modrinth.index.json: {'✓ Existe' if os.path.exists(modrinth_manifest) else '✗ No existe'}\n", "info")
            self._add_log_modpack_server(f"  manifest.json: {'✓ Existe' if os.path.exists(cf_manifest) else '✗ No existe'}\n\n", "info")

            if os.path.exists(modrinth_manifest):
                self._add_log_modpack_server("📖 Leyendo modrinth.index.json...\n", "info")
                with open(modrinth_manifest, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    deps = data.get("dependencies", {})
                    mc_version = deps.get("minecraft")
                    if server_type == "forge":
                        loader_version = deps.get("forge")
                    elif server_type == "fabric":
                        loader_version = deps.get("fabric-loader")

                    self._add_log_modpack_server(f"  Minecraft desde manifest: {mc_version or 'No encontrado'}\n", "info")
                    self._add_log_modpack_server(f"  Loader desde manifest: {loader_version or 'No encontrado'}\n\n", "info")

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
                self._add_log_modpack_server("🔍 Buscando en estructura de carpetas...\n", "info")
                if server_type == "forge":
                    # Buscar en libraries/net/minecraftforge/forge/
                    forge_path = os.path.join(server_folder, "libraries", "net", "minecraftforge", "forge")
                    self._add_log_modpack_server(f"  Verificando: {forge_path}\n", "info")
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
                    self._add_log_modpack_server(f"  Verificando: {fabric_path}\n", "info")
                    if os.path.exists(fabric_path):
                        self._add_log_modpack_server(f"    ✓ Carpeta existe, listando versiones...\n", "info")
                        # Listar carpetas de versiones del loader
                        for loader_folder in os.listdir(fabric_path):
                            if os.path.isdir(os.path.join(fabric_path, loader_folder)):
                                loader_version = loader_folder
                                self._add_log_modpack_server(f"    Fabric loader encontrado: {loader_version}\n", "success")
                                break
                    else:
                        self._add_log_modpack_server(f"    ✗ Carpeta no existe\n", "warning")

                    # Para Minecraft version, buscar en fabric-server-launch.jar o archivos de config
                    if not mc_version:
                        # Intentar desde .fabric/server.properties
                        fabric_server_properties = os.path.join(server_folder, ".fabric", "server.properties")
                        self._add_log_modpack_server(f"  Verificando: {fabric_server_properties}\n", "info")
                        if os.path.exists(fabric_server_properties):
                            self._add_log_modpack_server(f"    ✓ Archivo existe, leyendo...\n", "info")
                            with open(fabric_server_properties, 'r') as f:
                                for line in f:
                                    if line.startswith("game-version="):
                                        mc_version = line.split("=", 1)[1].strip()
                                        self._add_log_modpack_server(f"    Minecraft version encontrada: {mc_version}\n", "success")
                                        break
                        else:
                            self._add_log_modpack_server(f"    ✗ Archivo no existe\n", "warning")

            return mc_version, loader_version

        except Exception as e:
            self._add_log_modpack_server(f"⚠ Error al detectar versiones: {str(e)}\n", "warning")
            return None, None

    def _get_modpack_metadata(self, server_folder: str) -> tuple[Optional[str], Optional[str]]:
        """
        Gets modpack version and slug from manifest files

        Args:
            server_folder: Server folder path

        Returns:
            Tuple (modpack_version, modpack_slug)
        """
        try:
            # Try Modrinth manifest first
            modrinth_manifest = os.path.join(server_folder, "modrinth.index.json")
            if os.path.exists(modrinth_manifest):
                with open(modrinth_manifest, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    version = data.get("versionId", data.get("name"))

                    # Try to get slug from the manifest
                    # Modrinth manifests usually have the project name in "name" field
                    name = data.get("name", "")
                    # Convert name to slug (lowercase, replace spaces with dashes)
                    slug = name.lower().replace(" ", "-").replace("_", "-") if name else None

                    return version, slug

            # Try CurseForge manifest
            cf_manifest = os.path.join(server_folder, "manifest.json")
            if os.path.exists(cf_manifest):
                with open(cf_manifest, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    version = data.get("version", data.get("name"))
                    name = data.get("name", "")
                    slug = name.lower().replace(" ", "-").replace("_", "-") if name else None

                    return version, slug

            return None, None

        except Exception as e:
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
        self._set_window_icon(dialog)
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
            text="Este nombre se usará para crear la carpeta en:\nC:\\Users\\[tu-usuario]\\.pycraft\\modpack-modrinth\\[nombre]",
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
        Instala el modpack para el cliente en C:/Users/[user]/.pycraft/modpack-modrinth/[nombre]/

        Args:
            modpack_name: Nombre del modpack
            modpack_folder: Carpeta del servidor con el modpack
        """
        try:
            # Ruta a C:\Users\[nombre]\.pycraft\modpack-modrinth\
            user_folder = os.path.expanduser('~')  # C:\Users\[nombre]
            pycraft_folder = os.path.join(user_folder, '.pycraft', 'modpack-modrinth')
            client_modpack_folder = os.path.join(pycraft_folder, modpack_name)

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

    def run(self):
        """Inicia la aplicación"""
        # Configurar el protocolo de cierre
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.mainloop()
