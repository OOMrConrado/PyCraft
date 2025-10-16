"""
Módulo de la pestaña de Información y Ayuda
Contiene toda la documentación y guías para usar PyCraft
"""

import customtkinter as ctk
from .base_tab import BaseTab


class InfoTab(BaseTab):
    """Clase que maneja la pestaña de Información y Ayuda"""

    def __init__(self, parent):
        """
        Inicializa la pestaña de información

        Args:
            parent: El widget padre donde se creará esta pestaña
        """
        super().__init__(parent)
        self._create_content()

    def _create_content(self):
        """Crea el contenido de la pestaña de información"""
        # Frame principal con scroll
        main_frame = ctk.CTkScrollableFrame(self.parent, width=900, height=600)
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
        """
        Crea una sección de información con título y contenido

        Args:
            parent: El widget padre
            title: Título de la sección
            content: Contenido de texto de la sección
        """
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
