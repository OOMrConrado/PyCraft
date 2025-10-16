"""
Widget Factory - Fabrica de widgets comunes con estilos consistentes
Reduce código repetitivo y asegura consistencia visual
"""

import customtkinter as ctk
from typing import Optional, Callable


class WidgetFactory:
    """
    Factoría para crear widgets con estilos predefinidos y consistentes

    Uso:
        button = WidgetFactory.create_button(
            parent, "Click me", self.on_click, style="primary"
        )
    """

    # Estilos predefinidos para botones
    BUTTON_STYLES = {
        "primary": {"fg_color": "blue", "hover_color": "darkblue"},
        "success": {"fg_color": "green", "hover_color": "darkgreen"},
        "danger": {"fg_color": "red", "hover_color": "darkred"},
        "warning": {"fg_color": "#FFA726", "hover_color": "#b87d1d"},
        "secondary": {"fg_color": "gray25", "hover_color": "gray35"},
    }

    @staticmethod
    def create_button(
        parent,
        text: str,
        command: Optional[Callable] = None,
        style: str = "primary",
        width: int = 200,
        height: int = 35,
        **kwargs
    ) -> ctk.CTkButton:
        """
        Crea un botón estilizado

        Args:
            parent: Widget padre
            text: Texto del botón
            command: Comando a ejecutar al hacer clic
            style: Estilo predefinido (primary, success, danger, warning, secondary)
            width: Ancho del botón
            height: Alto del botón
            **kwargs: Argumentos adicionales para CTkButton

        Returns:
            El botón creado
        """
        style_config = WidgetFactory.BUTTON_STYLES.get(style, WidgetFactory.BUTTON_STYLES["primary"])

        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=width,
            height=height,
            **style_config,
            **kwargs
        )

    @staticmethod
    def create_label(
        parent,
        text: str,
        font_size: int = 12,
        font_weight: str = "normal",
        text_color: str = "white",
        **kwargs
    ) -> ctk.CTkLabel:
        """
        Crea una etiqueta estilizada

        Args:
            parent: Widget padre
            text: Texto de la etiqueta
            font_size: Tamaño de la fuente
            font_weight: Peso de la fuente (normal, bold)
            text_color: Color del texto
            **kwargs: Argumentos adicionales

        Returns:
            La etiqueta creada
        """
        return ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=font_size, weight=font_weight),
            text_color=text_color,
            **kwargs
        )

    @staticmethod
    def create_title(parent, text: str, **kwargs) -> ctk.CTkLabel:
        """
        Crea un título grande

        Args:
            parent: Widget padre
            text: Texto del título
            **kwargs: Argumentos adicionales

        Returns:
            La etiqueta de título
        """
        return WidgetFactory.create_label(
            parent, text, font_size=22, font_weight="bold", **kwargs
        )

    @staticmethod
    def create_section_title(parent, text: str, **kwargs) -> ctk.CTkLabel:
        """
        Crea un título de sección

        Args:
            parent: Widget padre
            text: Texto del título
            **kwargs: Argumentos adicionales

        Returns:
            La etiqueta de título de sección
        """
        return WidgetFactory.create_label(
            parent, text, font_size=18, font_weight="bold", **kwargs
        )

    @staticmethod
    def create_frame(
        parent,
        fg_color: str = "gray15",
        corner_radius: int = 10,
        **kwargs
    ) -> ctk.CTkFrame:
        """
        Crea un frame estilizado

        Args:
            parent: Widget padre
            fg_color: Color de fondo
            corner_radius: Radio de las esquinas
            **kwargs: Argumentos adicionales

        Returns:
            El frame creado
        """
        return ctk.CTkFrame(
            parent,
            fg_color=fg_color,
            corner_radius=corner_radius,
            **kwargs
        )

    @staticmethod
    def create_scrollable_frame(
        parent,
        width: int = 900,
        height: int = 600,
        **kwargs
    ) -> ctk.CTkScrollableFrame:
        """
        Crea un frame scrollable

        Args:
            parent: Widget padre
            width: Ancho del frame
            height: Alto del frame
            **kwargs: Argumentos adicionales

        Returns:
            El frame scrollable
        """
        return ctk.CTkScrollableFrame(
            parent,
            width=width,
            height=height,
            **kwargs
        )

    @staticmethod
    def create_entry(
        parent,
        placeholder: str = "",
        width: int = 400,
        height: int = 35,
        **kwargs
    ) -> ctk.CTkEntry:
        """
        Crea un campo de entrada

        Args:
            parent: Widget padre
            placeholder: Texto placeholder
            width: Ancho del campo
            height: Alto del campo
            **kwargs: Argumentos adicionales

        Returns:
            El campo de entrada
        """
        return ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            width=width,
            height=height,
            **kwargs
        )

    @staticmethod
    def create_textbox(
        parent,
        width: int = 800,
        height: int = 200,
        font_family: str = "Consolas",
        font_size: int = 11,
        **kwargs
    ) -> ctk.CTkTextbox:
        """
        Crea un textbox para logs/consola

        Args:
            parent: Widget padre
            width: Ancho del textbox
            height: Alto del textbox
            font_family: Familia de fuente
            font_size: Tamaño de fuente
            **kwargs: Argumentos adicionales

        Returns:
            El textbox creado
        """
        return ctk.CTkTextbox(
            parent,
            width=width,
            height=height,
            font=ctk.CTkFont(family=font_family, size=font_size),
            wrap="word",
            **kwargs
        )

    @staticmethod
    def create_progress_bar(
        parent,
        width: int = 400,
        height: int = 20,
        **kwargs
    ) -> ctk.CTkProgressBar:
        """
        Crea una barra de progreso

        Args:
            parent: Widget padre
            width: Ancho de la barra
            height: Alto de la barra
            **kwargs: Argumentos adicionales

        Returns:
            La barra de progreso
        """
        progress_bar = ctk.CTkProgressBar(
            parent,
            width=width,
            height=height,
            **kwargs
        )
        progress_bar.set(0)
        return progress_bar

    @staticmethod
    def create_separator(parent, **kwargs) -> ctk.CTkFrame:
        """
        Crea un separador horizontal

        Args:
            parent: Widget padre
            **kwargs: Argumentos adicionales

        Returns:
            El separador (frame delgado)
        """
        return ctk.CTkFrame(
            parent,
            height=2,
            fg_color="gray30",
            **kwargs
        )
