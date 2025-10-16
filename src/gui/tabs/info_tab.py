"""
Info and Help Tab Module
Contains all documentation and guides for using PyCraft
"""

import customtkinter as ctk
import webbrowser
from .base_tab import BaseTab


class InfoTab(BaseTab):
    """Class that handles the Info and Help tab"""

    def __init__(self, parent):
        """
        Initializes the info tab

        Args:
            parent: The parent widget where this tab will be created
        """
        super().__init__(parent)
        self.expanded_sections = {}  # Track which sections are expanded
        self.section_buttons = {}  # Store button references for accordion
        self.section_frames = {}  # Store content frame references
        self._create_content()

    def _create_content(self):
        """Creates the info tab content"""
        # Main frame with scroll
        main_frame = ctk.CTkScrollableFrame(self.parent, width=900, height=600)
        main_frame.pack(pady=10, padx=10, fill="both", expand=True)

        # Title
        ctk.CTkLabel(
            main_frame,
            text="Guía Completa de PyCraft",
            font=ctk.CTkFont(size=26, weight="bold")
        ).pack(pady=20)

        # Subtitle
        ctk.CTkLabel(
            main_frame,
            text="Haz clic en cada categoría para ver más información",
            font=ctk.CTkFont(size=13),
            text_color="gray70"
        ).pack(pady=(0, 20))

        # ===== SECCIÓN: INICIO RÁPIDO =====
        self._create_collapsible_section(
            main_frame,
            "Inicio Rápido",
            """
EMPEZAR CON PYCRAFT:

PyCraft te permite crear dos tipos de servidores:

1️⃣ SERVIDOR VANILLA (Minecraft puro):
   • Ve a la pestaña "Servidor Vanilla"
   • Sigue las instrucciones paso a paso en pantalla
   • PyCraft se encarga de todo automáticamente

2️⃣ SERVIDOR CON MODS:
   • Ve a la pestaña "Servidor con Mods"
   • Busca un modpack de Modrinth
   • Sigue las instrucciones de instalación

Después de crear tu servidor, visita las otras secciones de esta guía
para aprender a configurar la red y permitir que tus amigos se conecten.
            """,
            default_expanded=False
        )

        # ===== SECCIÓN: PROBLEMAS DE CONEXIÓN =====
        self._create_collapsible_section(
            main_frame,
            "Problemas de Conexión (Firewall/Antivirus)",
            """
Si otros jugadores no pueden conectarse a tu servidor:

1️⃣ FIREWALL DE WINDOWS - Opción Recomendada:
   • Ve a: Panel de Control > Firewall de Windows > Configuración avanzada
   • Crea una regla de ENTRADA para puerto TCP 25565
   • Aplica a perfiles: Dominio, Privado y Público

1️⃣ FIREWALL DE WINDOWS - Solución Rápida (Menos Seguro):
   ⚠️ IMPORTANTE: Solo mientras juegas, reactívalo después

   PARA EL HOST (quien tiene el servidor):
   • Ve a: Configuración > Red e Internet > Firewall de Windows Defender
   • Desactiva el firewall para redes Privadas y Públicas
   • Después de jugar, VUELVE A ACTIVARLO por seguridad

   PARA LOS JUGADORES:
   • Tus amigos también deben desactivar su firewall temporalmente
   • Esto ayuda a evitar bloqueos de conexión
   • Que reactiven el firewall después de jugar

2️⃣ ANTIVIRUS:
   • Algunos antivirus bloquean servidores de Minecraft
   • Agrega PyCraft y Java a las excepciones
   • Si el servidor no funciona, desactiva temporalmente el antivirus

3️⃣ PERFIL DE RED:
   • Asegúrate de que tu red esté configurada como 'Privada'
   • No uses 'Red pública' (bloquea conexiones entrantes)
   • Para cambiar: Configuración > Red e Internet > Estado

4️⃣ VERIFICAR PUERTO:
   • Asegúrate de que el puerto 25565 no esté en uso por otro programa
   • Si tienes otro servidor corriendo, ciérralo primero
            """,
            default_expanded=True  # Esta expandida por defecto porque es importante
        )

        # ===== SECCIÓN: CONFIGURACIÓN DE RED =====
        self._create_collapsible_section(
            main_frame,
            "Configuración de Red (Router/IP/Puertos)",
            """
CÓMO CONECTARSE AL SERVIDOR:

IP PARA CONEXIÓN:
   • Jugadores en tu red local: Usa tu IP local (192.168.x.x)
     Para encontrarla: abre cmd y escribe: ipconfig
     Busca "Dirección IPv4"

   • Jugadores externos (fuera de tu casa): Usa tu IP pública
     Para encontrarla: busca en Google "mi ip"

   • En Minecraft, conecta a: <TU_IP>:25565

ROUTER - PORT FORWARDING (Para jugar fuera de tu red local):
   • Necesitas configurar 'Port Forwarding' en tu router
   • Redirige el puerto 25565 (TCP) a la IP local de tu PC
   • Busca guías específicas para tu modelo de router
   • ALTERNATIVA MÁS FÁCIL: Usa una VPN como Hamachi (ver abajo)

CAMBIAR PUERTO (Avanzado):
   • Edita server.properties en la carpeta del servidor
   • Cambia: server-port=25565 al puerto que quieras
   • Recuerda configurar el firewall y router con el nuevo puerto
            """,
            default_expanded=False
        )

        # ===== SECCIÓN: USO DE VPNs =====
        self._create_collapsible_section(
            main_frame,
            "Uso de VPNs (Hamachi y Alternativas)",
            """
JUGAR CON AMIGOS USANDO HAMACHI:

Hamachi es una VPN que permite a tus amigos conectarse sin configurar el router.

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ALTERNATIVAS A HAMACHI:

• Radmin VPN (Gratis, sin límite de usuarios)
  Descarga: https://www.radmin-vpn.com/

• ZeroTier (Gratis, más técnico pero muy potente)
  Descarga: https://www.zerotier.com/

• Playit.gg (Gratis, específico para gaming)
  Descarga: https://playit.gg/

• Port Forwarding (Avanzado)
  Requiere configurar tu router - más complejo pero más estable
            """,
            default_expanded=False
        )

        # ===== SECCIÓN: CONFIGURACIÓN DEL SERVIDOR =====
        self._create_collapsible_section(
            main_frame,
            "Configuración del Servidor",
            """
CONFIGURACIÓN AUTOMÁTICA DE PYCRAFT:

PyCraft configura automáticamente:
   • online-mode=false (permite conexiones sin verificar con Mojang)
   • difficulty=normal (dificultad normal del juego)
   • EULA aceptado automáticamente

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EDITAR CONFIGURACIÓN MANUALMENTE:

Puedes editar el archivo server.properties para cambiar:

   • gamemode - Modo de juego
     Opciones: survival, creative, adventure, spectator

   • max-players - Máximo de jugadores permitidos
     Ejemplo: max-players=20

   • pvp - Activar/desactivar PvP
     Opciones: true, false

   • difficulty - Dificultad del juego
     Opciones: peaceful, easy, normal, hard

   • spawn-protection - Radio de protección del spawn
     Ejemplo: spawn-protection=16

   • view-distance - Distancia de renderizado en chunks
     Ejemplo: view-distance=10

   • motd - Mensaje del día (se ve en la lista de servidores)
     Ejemplo: motd=Mi Servidor de Minecraft

   • server-port - Puerto del servidor
     Ejemplo: server-port=25565

El archivo server.properties está en la carpeta donde instalaste el servidor.
IMPORTANTE: Reinicia el servidor después de hacer cambios.
            """,
            default_expanded=False
        )

        # ===== SECCIÓN: SOLUCIÓN DE PROBLEMAS =====
        self._create_collapsible_section(
            main_frame,
            "Solución de Problemas",
            """
PROBLEMA: "Error al iniciar servidor"
   Solución:
   • Verifica que Java esté instalado correctamente
   • Abre cmd y escribe: java -version
   • Si no está instalado, descarga desde: https://www.oracle.com/java/technologies/downloads/
   • Reinicia tu computadora después de instalar Java

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEMA: "Mis amigos no pueden conectarse"
   Solución:
   • Verifica que el servidor esté iniciado y corriendo
   • Si usas Hamachi, confirma que todos estén en la misma red
   • Revisa el firewall de Windows (ver sección Firewall arriba)
   • Confirma que uses la IP correcta:
     - IP de Hamachi si usas VPN
     - IP pública si configuraste Port Forwarding
     - IP local (192.168.x.x) si están en la misma red WiFi

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEMA: "El servidor se cierra inmediatamente"
   Solución:
   • Revisa los logs en la consola para ver el error exacto
   • Verifica que tengas suficiente RAM disponible
   • Asegúrate de que el puerto 25565 no esté en uso
   • Verifica que no haya otro servidor corriendo

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEMA: "Java no se encuentra"
   Solución:
   • Descarga e instala Java desde: https://www.oracle.com/java/technologies/downloads/
   • Reinicia tu computadora después de instalar
   • Verifica la instalación: abre cmd y escribe: java -version

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEMA: "Puerto 25565 en uso"
   Solución:
   • Cierra cualquier otro servidor de Minecraft
   • Reinicia tu computadora
   • O cambia el puerto en server.properties

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEMA: "Lag o rendimiento bajo"
   Solución:
   • Aumenta la RAM asignada al servidor
   • Reduce el view-distance en server.properties
   • Cierra otros programas para liberar recursos
   • Usa una versión optimizada como Paper o Spigot
            """,
            default_expanded=False
        )

        # ===== SECCIÓN: REQUISITOS =====
        self._create_collapsible_section(
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
            """,
            default_expanded=False
        )

        # Pie de página
        ctk.CTkLabel(
            main_frame,
            text="PyCraft - Simplificando la creación de servidores de Minecraft",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(pady=30)

    def _create_collapsible_section(self, parent, title, content, default_expanded=False):
        """
        Creates a collapsible section with a button to expand/collapse

        Args:
            parent: The parent widget
            title: Section title
            content: Section text content
            default_expanded: Whether the section should be expanded by default
        """
        # Section container frame
        section_container = ctk.CTkFrame(parent, fg_color="transparent")
        section_container.pack(pady=5, padx=10, fill="x")

        # Header button frame
        header_frame = ctk.CTkFrame(section_container, fg_color="gray20", corner_radius=10)
        header_frame.pack(fill="x", pady=2)

        # Variable to track state
        section_id = title
        self.expanded_sections[section_id] = default_expanded

        # Content frame (initially hidden or visible)
        content_frame = ctk.CTkFrame(section_container, fg_color="gray25", corner_radius=10)
        if default_expanded:
            content_frame.pack(fill="x", pady=(0, 5), padx=10)

        def toggle_section():
            """Toggles section visibility (accordion behavior)"""
            if self.expanded_sections[section_id]:
                # Collapse this section
                content_frame.pack_forget()
                toggle_button.configure(text=f"▶  {title}")
                self.expanded_sections[section_id] = False
            else:
                # CLOSE ALL OTHER SECTIONS (accordion)
                for other_id, other_frame in self.section_frames.items():
                    if other_id != section_id and self.expanded_sections.get(other_id, False):
                        other_frame.pack_forget()
                        self.expanded_sections[other_id] = False
                        # Update the other section's button
                        if other_id in self.section_buttons:
                            self.section_buttons[other_id].configure(text=f"▶  {other_id}")

                # Expand this section
                content_frame.pack(fill="x", pady=(0, 5), padx=10)
                toggle_button.configure(text=f"▼  {title}")
                self.expanded_sections[section_id] = True

        # Expand/collapse button - Light blue color #87CEEB
        arrow = "▼" if default_expanded else "▶"
        toggle_button = ctk.CTkButton(
            header_frame,
            text=f"{arrow}  {title}",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="transparent",
            text_color="#87CEEB",  # Light blue/cream color
            hover_color="gray30",
            anchor="w",
            command=toggle_section,
            height=40
        )
        toggle_button.pack(fill="x", padx=10, pady=5)

        # Save references for accordion
        self.section_buttons[section_id] = toggle_button
        self.section_frames[section_id] = content_frame

        # Process content and find URLs
        lines = content.strip().split('\n')
        inner_content_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        inner_content_frame.pack(pady=10, padx=20, anchor="w", fill="x")

        for line in lines:
            # Look for URLs in the line
            if 'https://' in line or 'http://' in line:
                self._create_line_with_link(inner_content_frame, line)
            else:
                # Normal line without links
                ctk.CTkLabel(
                    inner_content_frame,
                    text=line,
                    font=ctk.CTkFont(size=12),
                    justify="left",
                    anchor="w"
                ).pack(anchor="w")

    def _create_info_section(self, parent, title, content):
        """
        Crea una sección de información con título y contenido (sin colapsar)

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

        # Procesar contenido y buscar URLs
        lines = content.strip().split('\n')
        content_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        content_frame.pack(pady=10, padx=20, anchor="w", fill="x")

        for line in lines:
            # Buscar URLs en la línea
            if 'https://' in line or 'http://' in line:
                self._create_line_with_link(content_frame, line)
            else:
                # Línea normal sin enlaces
                ctk.CTkLabel(
                    content_frame,
                    text=line,
                    font=ctk.CTkFont(size=12),
                    justify="left",
                    anchor="w"
                ).pack(anchor="w")

    def _create_line_with_link(self, parent, line):
        """
        Creates a text line with a clickable link

        Args:
            parent: The parent widget
            line: Text line containing a URL
        """
        line_frame = ctk.CTkFrame(parent, fg_color="transparent")
        line_frame.pack(anchor="w", fill="x")

        # Split the line into text before and after the link
        parts = line.split('https://')
        if len(parts) < 2:
            parts = line.split('http://')
            protocol = 'http://'
        else:
            protocol = 'https://'

        # Text before the link
        if parts[0].strip():
            ctk.CTkLabel(
                line_frame,
                text=parts[0],
                font=ctk.CTkFont(size=12),
                justify="left",
                anchor="w"
            ).pack(side="left")

        # Extract the full URL
        url_part = parts[1].split()[0] if parts[1] else ""
        url = protocol + url_part

        # Create link button
        link_button = ctk.CTkButton(
            line_frame,
            text=url,
            font=ctk.CTkFont(size=12, underline=True),
            fg_color="transparent",
            text_color="#42A5F5",
            hover_color="gray25",
            cursor="hand2",
            command=lambda u=url: webbrowser.open(u),
            anchor="w",
            width=len(url) * 7
        )
        link_button.pack(side="left")

        # Text after the link (if any)
        remaining = ' '.join(parts[1].split()[1:]) if len(parts[1].split()) > 1 else ""
        if remaining:
            ctk.CTkLabel(
                line_frame,
                text=" " + remaining,
                font=ctk.CTkFont(size=12),
                justify="left",
                anchor="w"
            ).pack(side="left")
