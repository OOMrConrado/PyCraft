"""
Logger Mixin - Utilidad para manejo unificado de logs en textboxes
Simplifica el código repetitivo de logging en la GUI
"""

import customtkinter as ctk


class LoggerMixin:
    """
    Mixin que proporciona funcionalidad de logging para componentes GUI

    Uso:
        class MiComponente(LoggerMixin):
            def __init__(self):
                self.log_textbox = ctk.CTkTextbox(...)
                self._configure_log_tags(self.log_textbox)
    """

    # Colores estándar para logs
    LOG_COLORS = {
        "normal": "white",
        "info": "#42A5F5",
        "success": "#4CAF50",
        "warning": "#FFA726",
        "error": "#EF5350"
    }

    @staticmethod
    def _configure_log_tags(textbox: ctk.CTkTextbox):
        """
        Configura los tags de color para un textbox

        Args:
            textbox: El textbox donde configurar los tags
        """
        if hasattr(textbox, "_tags_configured"):
            return

        for tag_name, color in LoggerMixin.LOG_COLORS.items():
            textbox.tag_config(tag_name, foreground=color)

        textbox._tags_configured = True

    @staticmethod
    def add_log(textbox: ctk.CTkTextbox, message: str, log_type: str = "normal"):
        """
        Agrega un mensaje al log con el color apropiado

        Args:
            textbox: El textbox donde agregar el log
            message: El mensaje a agregar
            log_type: Tipo de log (normal, info, success, warning, error)
        """
        # Configurar tags si no están configurados
        LoggerMixin._configure_log_tags(textbox)

        # Validar tipo de log
        if log_type not in LoggerMixin.LOG_COLORS:
            log_type = "normal"

        # Insertar mensaje con el tag apropiado
        textbox.insert("end", message, log_type)
        textbox.see("end")

    @staticmethod
    def clear_log(textbox: ctk.CTkTextbox):
        """
        Limpia todo el contenido del log

        Args:
            textbox: El textbox a limpiar
        """
        textbox.delete("1.0", "end")

    @staticmethod
    def add_separator(textbox: ctk.CTkTextbox):
        """
        Agrega un separador visual al log

        Args:
            textbox: El textbox donde agregar el separador
        """
        LoggerMixin.add_log(textbox, "\n" + "="*50 + "\n\n", "info")
