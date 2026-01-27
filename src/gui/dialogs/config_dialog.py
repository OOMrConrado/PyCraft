"""
Server Configuration Dialog.
"""

from typing import Dict, Optional, Callable

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QComboBox, QSpinBox, QFrame, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

from ...utils import system_utils


class ServerConfigDialog(QDialog):
    """
    Dialog for configuring server settings.

    Supports:
    - RAM allocation
    - Gamemode
    - Difficulty
    - Max players
    - Online mode
    - Pause when empty (vanilla only)
    """

    def __init__(
        self,
        colors: Dict[str, str],
        server_type: str,
        server_manager,
        current_ram: int,
        on_save: Optional[Callable] = None,
        mc_version: str = "",
        loader_info: str = "",
        parent=None
    ):
        super().__init__(parent)

        self.colors = colors
        self.server_type = server_type
        self.server_manager = server_manager
        self.current_ram = current_ram
        self._on_save = on_save
        self.mc_version = mc_version
        self.loader_info = loader_info

        self._setup_ui()

    def _setup_ui(self):
        """Build the dialog UI"""
        self.setWindowTitle("Server Configuration")
        dialog_height = 720 if self.server_type == "vanilla" else 620
        self.setFixedSize(420, dialog_height)
        self.setStyleSheet(f"background-color: {self.colors['bg_card']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Get total system RAM
        total_ram = system_utils.get_total_ram()
        if total_ram == -1:
            total_ram = 8192

        # Styles
        combo_style = self._combo_style()
        slider_style = self._slider_style()

        # === RAM Section ===
        layout.addWidget(self._section_label("RAM Allocation"))

        self.ram_value_label = QLabel(f"{self.current_ram} MB ({self.current_ram / 1024:.1f} GB)")
        self.ram_value_label.setStyleSheet(
            f"color: {self.colors['accent']}; font-size: 13px; font-weight: 500;"
        )
        layout.addWidget(self.ram_value_label)

        min_ram = 1024 if self.server_type == "vanilla" else 2048
        max_ram = min(total_ram - 1024, 32768)
        max_ram = max(max_ram, min_ram + 1024)

        self.ram_slider = QSlider(Qt.Orientation.Horizontal)
        self.ram_slider.setMinimum(min_ram)
        self.ram_slider.setMaximum(max_ram)
        self.ram_slider.setSingleStep(512)
        self.ram_slider.setValue(self.current_ram)
        self.ram_slider.setStyleSheet(slider_style)
        self.ram_slider.valueChanged.connect(
            lambda v: self.ram_value_label.setText(f"{v} MB ({v / 1024:.1f} GB)")
        )
        layout.addWidget(self.ram_slider)

        ram_info = QLabel(f"System: {total_ram / 1024:.1f} GB | Max: {max_ram / 1024:.1f} GB")
        ram_info.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px;")
        layout.addWidget(ram_info)

        layout.addSpacing(4)

        # === Gamemode Section ===
        layout.addWidget(self._section_label("Gamemode"))
        current_gamemode = self._get_property("gamemode", "survival")
        self.gamemode_container, self.gamemode_combo = self._create_combo(
            ["survival", "creative", "adventure", "spectator"],
            current_gamemode, combo_style
        )
        layout.addWidget(self.gamemode_container)

        layout.addSpacing(4)

        # === Difficulty Section ===
        layout.addWidget(self._section_label("Difficulty"))
        current_difficulty = self._get_property("difficulty", "normal")
        self.diff_container, self.diff_combo = self._create_combo(
            ["peaceful", "easy", "normal", "hard"],
            current_difficulty, combo_style
        )
        layout.addWidget(self.diff_container)

        layout.addSpacing(4)

        # === Max Players Section ===
        layout.addWidget(self._section_label("Max Players"))
        current_max_players = int(self._get_property("max-players", "20"))

        self.players_label = QLabel(f"{current_max_players} players")
        self.players_label.setStyleSheet(
            f"color: {self.colors['accent']}; font-size: 13px; font-weight: 500;"
        )
        layout.addWidget(self.players_label)

        self.players_slider = QSlider(Qt.Orientation.Horizontal)
        self.players_slider.setMinimum(1)
        self.players_slider.setMaximum(100)
        self.players_slider.setValue(current_max_players)
        self.players_slider.setStyleSheet(slider_style)
        self.players_slider.valueChanged.connect(
            lambda v: self.players_label.setText(f"{v} players")
        )
        layout.addWidget(self.players_slider)

        layout.addSpacing(4)

        # === Online Mode Section ===
        layout.addWidget(self._section_label("Online Mode"))

        online_hint = QLabel("Set to OFF to allow non-premium players (LAN/Hamachi)")
        online_hint.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px;")
        online_hint.setWordWrap(True)
        layout.addWidget(online_hint)

        current_online_raw = self._get_property("online-mode", "false").lower().strip()
        current_online_display = "ON" if current_online_raw == "true" else "OFF"
        self.online_container, self.online_combo = self._create_combo(
            ["OFF", "ON"], current_online_display, combo_style
        )
        layout.addWidget(self.online_container)

        layout.addSpacing(4)

        # === Pause When Empty Section (vanilla only) ===
        self.pause_spinbox = None
        if self.server_type == "vanilla":
            layout.addWidget(self._section_label("Pause When Empty"))

            pause_hint = QLabel("Server pauses when no players connected (saves resources)")
            pause_hint.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px;")
            pause_hint.setWordWrap(True)
            layout.addWidget(pause_hint)

            current_pause = int(self._get_property("pause-when-empty-seconds", "0"))
            layout.addWidget(self._build_pause_section(current_pause))

        layout.addStretch()

        # === Save Button ===
        save_btn = QPushButton("Save")
        save_btn.setFixedSize(120, 42)
        save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['accent']};
                color: #000000;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {self.colors.get('accent_hover', self.colors['accent'])};
            }}
        """)
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # === Footer ===
        layout.addSpacing(12)
        footer_line = QFrame()
        footer_line.setFrameShape(QFrame.Shape.HLine)
        footer_line.setStyleSheet(f"background-color: {self.colors['border']}; max-height: 1px;")
        layout.addWidget(footer_line)

        version_text = ""
        if self.mc_version:
            version_text = f"Minecraft {self.mc_version}"
        if self.loader_info:
            if version_text:
                version_text += f" | {self.loader_info}"
            else:
                version_text = self.loader_info

        if version_text:
            footer_label = QLabel(version_text)
            footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            footer_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px;")
            layout.addWidget(footer_label)

    def _section_label(self, text: str) -> QLabel:
        """Create a section label"""
        label = QLabel(text)
        label.setStyleSheet(f"color: {self.colors['text']}; font-size: 14px; font-weight: 600;")
        return label

    def _combo_style(self) -> str:
        """Generate combo box style"""
        return f"""
            QComboBox {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding: 10px 14px;
                padding-right: 35px;
                font-size: 13px;
            }}
            QComboBox:hover {{
                border: 1px solid {self.colors['accent']};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 30px;
                border: none;
            }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
                image: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text']};
                selection-background-color: {self.colors['accent']};
                selection-color: #000000;
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                border-radius: 4px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: rgba(74, 222, 128, 0.2);
            }}
        """

    def _slider_style(self) -> str:
        """Generate slider style"""
        return f"""
            QSlider::groove:horizontal {{
                background: {self.colors['bg_input']};
                height: 8px;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {self.colors['accent']};
                width: 18px;
                height: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }}
            QSlider::sub-page:horizontal {{
                background: {self.colors['accent']};
                border-radius: 4px;
            }}
        """

    def _create_combo(self, items: list, current: str, style: str):
        """Create combo with arrow indicator"""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        combo = QComboBox()
        combo.addItems(items)

        # Try to find and set current value (case-insensitive)
        current_lower = current.lower().strip()
        found_index = -1
        for i, item in enumerate(items):
            if item.lower() == current_lower:
                found_index = i
                break

        if found_index >= 0:
            combo.setCurrentIndex(found_index)
        else:
            combo.setCurrentIndex(0)  # Default to first item

        combo.setStyleSheet(style)
        combo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        arrow = QLabel("▼")
        arrow.setFixedWidth(30)
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow.setStyleSheet(f"""
            color: {self.colors['text_secondary']};
            font-size: 10px;
            background: transparent;
            margin-right: 10px;
        """)

        def on_show():
            arrow.setText("▲")
            arrow.setStyleSheet(
                f"color: {self.colors['accent']}; font-size: 10px; "
                f"background: transparent; margin-right: 10px;"
            )

        def on_hide():
            arrow.setText("▼")
            arrow.setStyleSheet(
                f"color: {self.colors['text_secondary']}; font-size: 10px; "
                f"background: transparent; margin-right: 10px;"
            )

        combo.showPopup = lambda orig=combo.showPopup: (on_show(), orig())[-1]
        combo.hidePopup = lambda orig=combo.hidePopup: (on_hide(), orig())[-1]

        layout.addWidget(combo, 1)
        layout.addWidget(arrow)

        return container, combo

    def _build_pause_section(self, current_pause: int) -> QWidget:
        """Build pause when empty section"""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(8)

        self.pause_spinbox = QSpinBox()
        self.pause_spinbox.setMinimum(0)
        self.pause_spinbox.setMaximum(7200)
        self.pause_spinbox.setValue(current_pause)
        self.pause_spinbox.setSingleStep(60)
        self.pause_spinbox.setSpecialValueText("Disabled")
        self.pause_spinbox.setStyleSheet(f"""
            QSpinBox {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                min-width: 120px;
            }}
            QSpinBox:hover {{
                border: 1px solid {self.colors['accent']};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 24px;
                border: none;
                background: transparent;
            }}
        """)

        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 12px;")
        self.time_label.setMinimumWidth(80)

        def update_time_label_from_value(value):
            """Update time label based on spinbox value"""
            if value == 0:
                self.time_label.setText("")
            elif value < 60:
                self.time_label.setText(f"= {value} sec")
            elif value < 3600:
                mins = value // 60
                secs = value % 60
                if secs == 0:
                    self.time_label.setText(f"= {mins} min")
                else:
                    self.time_label.setText(f"= {mins}m {secs}s")
            else:
                hours = value // 3600
                mins = (value % 3600) // 60
                if mins == 0:
                    self.time_label.setText(f"= {hours}h")
                else:
                    self.time_label.setText(f"= {hours}h {mins}m")

        def update_time_label_from_text(text):
            """Update time label based on text input (real-time)"""
            try:
                # Handle special case when showing "Disabled"
                if text == "Disabled" or text == "" or text == "0":
                    self.time_label.setText("")
                    return
                value = int(text)
                if value <= 0:
                    self.time_label.setText("")
                elif value < 60:
                    self.time_label.setText(f"= {value} sec")
                elif value < 3600:
                    mins = value // 60
                    secs = value % 60
                    if secs == 0:
                        self.time_label.setText(f"= {mins} min")
                    else:
                        self.time_label.setText(f"= {mins}m {secs}s")
                else:
                    hours = value // 3600
                    mins = (value % 3600) // 60
                    if mins == 0:
                        self.time_label.setText(f"= {hours}h")
                    else:
                        self.time_label.setText(f"= {hours}h {mins}m")
            except ValueError:
                # Not a valid number yet, keep current label
                pass

        # Initial update
        update_time_label_from_value(current_pause)

        # Connect both valueChanged and textChanged for real-time updates
        self.pause_spinbox.valueChanged.connect(update_time_label_from_value)
        self.pause_spinbox.lineEdit().textChanged.connect(update_time_label_from_text)

        # Presets
        preset_style = f"""
            QPushButton {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text_secondary']};
                border: 1px solid {self.colors['border']};
                border-radius: 6px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['accent']};
                color: #000000;
            }}
        """

        preset_5m = QPushButton("5m")
        preset_5m.setFixedSize(40, 28)
        preset_5m.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        preset_5m.setStyleSheet(preset_style)
        preset_5m.clicked.connect(lambda: self.pause_spinbox.setValue(300))

        preset_30m = QPushButton("30m")
        preset_30m.setFixedSize(40, 28)
        preset_30m.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        preset_30m.setStyleSheet(preset_style)
        preset_30m.clicked.connect(lambda: self.pause_spinbox.setValue(1800))

        preset_1h = QPushButton("1h")
        preset_1h.setFixedSize(40, 28)
        preset_1h.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        preset_1h.setStyleSheet(preset_style)
        preset_1h.clicked.connect(lambda: self.pause_spinbox.setValue(3600))

        layout.addWidget(self.pause_spinbox)
        layout.addWidget(self.time_label)
        layout.addStretch()
        layout.addWidget(preset_5m)
        layout.addWidget(preset_30m)
        layout.addWidget(preset_1h)

        return container

    def _get_property(self, prop: str, default: str) -> str:
        """Get property from server manager"""
        if self.server_manager:
            value = self.server_manager.get_property(prop)
            if value:
                return value
        return default

    def _save(self):
        """Save configuration"""
        ram = self.ram_slider.value()
        difficulty = self.diff_combo.currentText()
        gamemode = self.gamemode_combo.currentText()
        max_players = self.players_slider.value()
        # Convert ON/OFF to true/false for server.properties
        online_mode = "true" if self.online_combo.currentText() == "ON" else "false"
        pause = self.pause_spinbox.value() if self.pause_spinbox else None

        if self._on_save:
            self._on_save(ram, difficulty, gamemode, max_players, online_mode, pause)

        self.accept()

    def get_values(self):
        """Get current values"""
        return {
            "ram": self.ram_slider.value(),
            "difficulty": self.diff_combo.currentText(),
            "gamemode": self.gamemode_combo.currentText(),
            "max_players": self.players_slider.value(),
            "online_mode": "true" if self.online_combo.currentText() == "ON" else "false",
            "pause_when_empty": self.pause_spinbox.value() if self.pause_spinbox else None
        }
