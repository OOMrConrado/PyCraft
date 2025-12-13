"""
Info and Help Tab Module
Contains all documentation and guides for using PyCraft
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QCursor
import re

from .base_tab import BaseTab


class InfoTab(BaseTab):
    """Class that handles the Info and Help tab"""

    def __init__(self, parent: QWidget):
        """
        Initializes the info tab

        Args:
            parent: The parent widget where this tab will be created
        """
        super().__init__(parent)
        self.expanded_sections = {}
        self.section_buttons = {}
        self.section_frames = {}
        self._create_content()

    def _create_content(self):
        """Creates the info tab content"""
        # Main layout
        layout = QVBoxLayout(self.parent)
        layout.setContentsMargins(10, 10, 10, 10)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #1a1a1a;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Content widget
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #1a1a1a;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("PyCraft Complete Guide")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 26px;
                font-weight: bold;
                background-color: transparent;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Click on each category to see more information")
        subtitle.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 13px;
                background-color: transparent;
            }
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(subtitle)

        content_layout.addSpacing(20)

        # Section: Play with Friends
        self._create_collapsible_section(
            content_layout,
            "Play with Friends",
            """
Once you finish installing your server, follow these steps
so your friends can play with you:

==================================================

STEP 1: INSTALL CLIENT MODPACK (If using modpacks)

IMPORTANT: If you installed a server with modpack (Fabric/Forge),
your friends also need to install the modpack on their client.

OPTION A - Your friend installs the modpack:
1. Your friend must have PyCraft installed
2. Go to the "Settings" tab in PyCraft
3. Scroll down to "Client Modpack Folder Management"
4. Press "Install Client Modpack (for friends)"
5. Search for the modpack you are using (e.g., Prominence II, ATM9, etc.)
6. Select the SAME version you use on the server
7. Wait for it to download and install
8. Configure their launcher with the shown path

OPTION B - Share the Modrinth link:
1. Go to https://modrinth.com/ and search for your modpack
2. Share the link with your friend
3. Your friend installs from their favorite launcher (Prism, etc.)

If it's a Vanilla server, skip this step

==================================================

STEP 2: DISABLE THE FIREWALL

Both YOU (the host) and YOUR FRIENDS must do this:

1. Search "firewall" in Windows start menu
2. Click on "Windows Defender Firewall"
3. On the left side, click "Turn Windows Defender Firewall on or off"
4. Disable the Firewall for BOTH:
   - Private network
   - Public network
5. Click "OK"

IMPORTANT: Re-enable the firewall after playing

==================================================

STEP 3: USE HAMACHI (Recommended)

Why use Hamachi?
- It's the EASIEST way to play with friends
- No need to configure the router (Port Forwarding)
- Creates a virtual private network between you and your friends
- It's FREE

How to use Hamachi:

1. Download Hamachi: https://www.vpn.net/
2. Install Hamachi on your PC
3. Open Hamachi and click "Create new network"
4. Choose a network name and password
5. Share the name and password with your friends

YOUR FRIENDS must:
1. Install Hamachi
2. Join your network with the name and password you gave them

CONNECT IN MINECRAFT:

1. In Hamachi, you'll see your IPv4 address (e.g., 25.123.45.67)
2. Your friends open Minecraft -> Multiplayer -> Add Server
3. In "Server Address" they put your Hamachi IPv4
4. If you DID NOT change the port, just use the IP: 25.123.45.67
5. If you DID change the port, add: 25.123.45.67:25565

PyCraft already automatically configures online-mode to false
You only need the Hamachi IPv4, no need to configure ports
Everyone must be on the same Hamachi network
The server must be started before connecting

==================================================

ALTERNATIVES TO HAMACHI:

- Radmin VPN (Free, no user limit)
- ZeroTier (Free, more technical)
- Playit.gg (Free, gaming specific)
            """,
            default_expanded=True
        )

        # Section: More Server Configuration
        self._create_collapsible_section(
            content_layout,
            "More Server Configuration",
            """
AUTOMATIC PYCRAFT CONFIGURATION:

PyCraft automatically configures:
   - online-mode=false (allows connections without Mojang verification)
   - difficulty=normal (normal game difficulty)
   - EULA automatically accepted

==================================================

MANUAL CONFIGURATION:

You can edit the server.properties file to change:

   - gamemode - Game mode
     Options: survival, creative, adventure, spectator

   - max-players - Maximum allowed players
     Example: max-players=20

   - pvp - Enable/disable PvP
     Options: true, false

   - difficulty - Game difficulty
     Options: peaceful, easy, normal, hard

   - spawn-protection - Spawn protection radius
     Example: spawn-protection=16

   - view-distance - Render distance in chunks
     Example: view-distance=10

   - motd - Message of the day (shown in server list)
     Example: motd=My Minecraft Server

   - server-port - Server port
     Example: server-port=25565

The server.properties file is in the folder where you installed the server.
IMPORTANT: Restart the server after making changes.
            """,
            default_expanded=False
        )

        # Section: Troubleshooting
        self._create_collapsible_section(
            content_layout,
            "Troubleshooting",
            """
PROBLEM: "Error starting server"
   Solution:
   - Verify that Java is installed correctly
   - Open cmd and type: java -version
   - If not installed, you have two options:
     -> OPTION 1 (Recommended): Go to the "Settings" tab in PyCraft
        and download Java automatically
     -> OPTION 2: Manual download from: https://www.oracle.com/java/technologies/downloads/
   - Restart your computer after installing Java

==================================================

PROBLEM: "My friends can't connect"
   Solution:
   - Verify that the server is started and running
   - If using Hamachi, confirm everyone is on the same network
   - Check Windows firewall (see Firewall section above)
   - Confirm you're using the correct IP:
     - Hamachi IP if using VPN
     - Public IP if you configured Port Forwarding
     - Local IP (192.168.x.x) if on the same WiFi network

==================================================

PROBLEM: "The server closes immediately"
   Solution:
   - Check the console logs to see the exact error
   - Verify you have enough available RAM
   - Make sure port 25565 is not in use
   - Verify no other server is running

==================================================

PROBLEM: "Java not found"
   Solution:
   - OPTION 1 (Recommended): Go to the "Settings" tab in PyCraft
     and download Java automatically
   - OPTION 2: Download and install Java manually: https://www.oracle.com/java/technologies/downloads/
   - Restart your computer after installing
   - Verify installation: open cmd and type: java -version

==================================================

PROBLEM: "Port 25565 in use"
   Solution:
   - Close any other Minecraft server
   - Restart your computer
   - Or change the port in server.properties

==================================================

PROBLEM: "Lag or low performance"
   Solution:
   - Increase RAM allocated to the server
   - Reduce view-distance in server.properties
   - Close other programs to free resources
            """,
            default_expanded=False
        )

        # Section: Requirements
        self._create_collapsible_section(
            content_layout,
            "System Requirements",
            """
To use PyCraft and create Minecraft servers you need:

- Java Development Kit (JDK) 17 or higher installed
  Download: https://www.oracle.com/java/technologies/downloads/

- Disk space: Minimum 2 GB free

- RAM: Minimum 4 GB (8 GB or more recommended)

- Operating System: Windows 10/11, Linux or macOS

- Internet connection to download server files
            """,
            default_expanded=False
        )

        # Add stretch to push content to top
        content_layout.addStretch()

        # Footer
        footer = QLabel("PyCraft - Simplifying Minecraft server creation")
        footer.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 11px;
                background-color: transparent;
            }
        """)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(footer)

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

    def _create_collapsible_section(
        self,
        parent_layout: QVBoxLayout,
        title: str,
        content: str,
        default_expanded: bool = False
    ):
        """
        Creates a collapsible section with a button to expand/collapse

        Args:
            parent_layout: The parent layout
            title: Section title
            content: Section text content
            default_expanded: Whether the section should be expanded by default
        """
        # Section container
        section_container = QFrame()
        section_container.setStyleSheet("background-color: transparent;")
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(0, 5, 0, 5)
        section_layout.setSpacing(0)

        # Header button
        section_id = title
        self.expanded_sections[section_id] = default_expanded

        arrow = "v" if default_expanded else ">"
        header_button = QPushButton(f"  {arrow}  {title}")
        header_button.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #87CEEB;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                text-align: left;
                padding: 12px 15px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        header_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        section_layout.addWidget(header_button)

        # Content frame
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background-color: #353535;
                border-radius: 10px;
                margin-left: 10px;
            }
        """)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(20, 15, 20, 15)

        # Process content and add labels
        lines = content.strip().split('\n')
        for line in lines:
            if 'https://' in line or 'http://' in line:
                self._create_line_with_link(content_layout, line)
            else:
                label = QLabel(line)
                label.setStyleSheet("""
                    QLabel {
                        color: #ffffff;
                        font-size: 12px;
                        background-color: transparent;
                    }
                """)
                label.setWordWrap(True)
                content_layout.addWidget(label)

        # Set initial visibility
        content_frame.setVisible(default_expanded)

        section_layout.addWidget(content_frame)

        # Store references
        self.section_buttons[section_id] = header_button
        self.section_frames[section_id] = content_frame

        # Connect button click
        def toggle_section():
            if self.expanded_sections[section_id]:
                # Collapse this section
                content_frame.setVisible(False)
                header_button.setText(f"  >  {title}")
                self.expanded_sections[section_id] = False
            else:
                # Collapse all other sections (accordion behavior)
                for other_id, other_frame in self.section_frames.items():
                    if other_id != section_id and self.expanded_sections.get(other_id, False):
                        other_frame.setVisible(False)
                        self.expanded_sections[other_id] = False
                        if other_id in self.section_buttons:
                            self.section_buttons[other_id].setText(f"  >  {other_id}")

                # Expand this section
                content_frame.setVisible(True)
                header_button.setText(f"  v  {title}")
                self.expanded_sections[section_id] = True

        header_button.clicked.connect(toggle_section)

        parent_layout.addWidget(section_container)

    def _create_line_with_link(self, parent_layout: QVBoxLayout, line: str):
        """
        Creates a text line with a clickable link

        Args:
            parent_layout: The parent layout
            line: Text line containing a URL
        """
        # Find URL in the line
        url_pattern = r'https?://[^\s]+'
        match = re.search(url_pattern, line)

        if not match:
            # No URL found, just add as regular label
            label = QLabel(line)
            label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-size: 12px;
                    background-color: transparent;
                }
            """)
            label.setWordWrap(True)
            parent_layout.addWidget(label)
            return

        url = match.group(0)
        before_url = line[:match.start()]
        after_url = line[match.end():]

        # Create horizontal layout for the line
        line_widget = QWidget()
        line_widget.setStyleSheet("background-color: transparent;")
        line_layout = QHBoxLayout(line_widget)
        line_layout.setContentsMargins(0, 0, 0, 0)
        line_layout.setSpacing(0)

        # Text before URL
        if before_url.strip():
            before_label = QLabel(before_url)
            before_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-size: 12px;
                    background-color: transparent;
                }
            """)
            line_layout.addWidget(before_label)

        # URL as clickable button
        link_button = QPushButton(url)
        link_button.setStyleSheet("""
            QPushButton {
                color: #42A5F5;
                font-size: 12px;
                text-decoration: underline;
                background-color: transparent;
                border: none;
                padding: 0;
            }
            QPushButton:hover {
                color: #64B5F6;
            }
        """)
        link_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        link_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
        link_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        line_layout.addWidget(link_button)

        # Text after URL
        if after_url.strip():
            after_label = QLabel(after_url)
            after_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-size: 12px;
                    background-color: transparent;
                }
            """)
            line_layout.addWidget(after_label)

        line_layout.addStretch()
        parent_layout.addWidget(line_widget)
