"""
Módulo base con utilidades comunes para todas las pestañas
"""

import customtkinter as ctk


class BaseTab:
    """Clase base con utilidades comunes para todas las pestañas"""

    # Paleta de colores común
    COLORS = {
        "bg_primary": "gray10",
        "bg_secondary": "gray15",
        "bg_tertiary": "gray20",
        "accent": "#4CAF50",
        "accent_light": "#81C784",
        "warning": "#FFA726",
        "error": "#EF5350",
        "info": "#42A5F5",
        "border": "gray30",
        "text_primary": "white",
        "text_secondary": "gray",
    }

    def __init__(self, parent):
        """
        Inicializa la pestaña base

        Args:
            parent: El widget padre donde se creará esta pestaña
        """
        self.parent = parent

    @staticmethod
    def fix_textbox_scroll(textbox):
        """
        Arregla el scroll del textbox para hacerlo más smooth

        Args:
            textbox: El textbox a arreglar
        """
        def _on_mousewheel(event):
            textbox.yview_scroll(-1 * int(event.delta / 60), "units")

        # Bind mouse wheel para scroll más suave
        textbox._textbox.bind("<MouseWheel>", _on_mousewheel)
        textbox._textbox.bind("<Button-4>", lambda e: textbox.yview_scroll(-1, "units"))
        textbox._textbox.bind("<Button-5>", lambda e: textbox.yview_scroll(1, "units"))

    @staticmethod
    def fix_scrollable_frame_scroll(scrollable_frame):
        """
        Arregla el scroll del frame scrollable para hacerlo más smooth

        Args:
            scrollable_frame: El frame scrollable a arreglar
        """
        def _on_frame_scroll(event):
            if hasattr(scrollable_frame, "_parent_canvas"):
                scrollable_frame._parent_canvas.yview_scroll(
                    -1 * int(event.delta / 60), "units"
                )

        # Bind recursivo a todos los widgets del frame
        def bind_recursive(widget):
            widget.bind("<MouseWheel>", _on_frame_scroll)
            widget.bind("<Button-4>", lambda e: scrollable_frame._parent_canvas.yview_scroll(-1, "units") if hasattr(scrollable_frame, "_parent_canvas") else None)
            widget.bind("<Button-5>", lambda e: scrollable_frame._parent_canvas.yview_scroll(1, "units") if hasattr(scrollable_frame, "_parent_canvas") else None)
            for child in widget.winfo_children():
                bind_recursive(child)

        if hasattr(scrollable_frame, "_parent_canvas"):
            bind_recursive(scrollable_frame)

    def add_log(self, textbox, message: str, log_type: str = "normal"):
        """
        Agrega un mensaje al log con el color apropiado

        Args:
            textbox: El textbox donde agregar el log
            message: El mensaje a agregar
            log_type: Tipo de log (normal, info, success, warning, error)
        """
        # Configurar tags de colores si no existen
        if not hasattr(textbox, "_tags_configured"):
            textbox.tag_config("normal", foreground="white")
            textbox.tag_config("info", foreground="#42A5F5")
            textbox.tag_config("success", foreground="#4CAF50")
            textbox.tag_config("warning", foreground="#FFA726")
            textbox.tag_config("error", foreground="#EF5350")
            textbox._tags_configured = True

        # Insertar mensaje con el tag apropiado
        textbox.insert("end", message, log_type)
        textbox.see("end")

    @staticmethod
    def create_button(parent, text, command, width=200, height=35,
                      fg_color="blue", hover_color="darkblue", **kwargs):
        """
        Crea un botón estilizado

        Args:
            parent: Widget padre
            text: Texto del botón
            command: Comando a ejecutar
            width: Ancho del botón
            height: Alto del botón
            fg_color: Color de fondo
            hover_color: Color al pasar el mouse
            **kwargs: Argumentos adicionales para CTkButton

        Returns:
            El botón creado
        """
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=width,
            height=height,
            fg_color=fg_color,
            hover_color=hover_color,
            **kwargs
        )

    @staticmethod
    def create_label(parent, text, font_size=12, font_weight="normal",
                     text_color="white", **kwargs):
        """
        Crea una etiqueta estilizada

        Args:
            parent: Widget padre
            text: Texto de la etiqueta
            font_size: Tamaño de la fuente
            font_weight: Peso de la fuente (normal, bold)
            text_color: Color del texto
            **kwargs: Argumentos adicionales para CTkLabel

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
    def create_frame(parent, fg_color="gray15", **kwargs):
        """
        Crea un frame estilizado

        Args:
            parent: Widget padre
            fg_color: Color de fondo
            **kwargs: Argumentos adicionales para CTkFrame

        Returns:
            El frame creado
        """
        return ctk.CTkFrame(parent, fg_color=fg_color, **kwargs)

    @staticmethod
    def create_entry(parent, placeholder="", width=400, height=35, **kwargs):
        """
        Crea un campo de entrada estilizado

        Args:
            parent: Widget padre
            placeholder: Texto placeholder
            width: Ancho del campo
            height: Alto del campo
            **kwargs: Argumentos adicionales para CTkEntry

        Returns:
            El campo de entrada creado
        """
        return ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            width=width,
            height=height,
            **kwargs
        )

    @staticmethod
    def create_textbox(parent, width=800, height=200, **kwargs):
        """
        Crea un textbox estilizado

        Args:
            parent: Widget padre
            width: Ancho del textbox
            height: Alto del textbox
            **kwargs: Argumentos adicionales para CTkTextbox

        Returns:
            El textbox creado
        """
        return ctk.CTkTextbox(
            parent,
            width=width,
            height=height,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
            **kwargs
        )

    @staticmethod
    def create_scrollable_frame(parent, width=900, height=600, **kwargs):
        """
        Crea un frame scrollable estilizado

        Args:
            parent: Widget padre
            width: Ancho del frame
            height: Alto del frame
            **kwargs: Argumentos adicionales para CTkScrollableFrame

        Returns:
            El frame scrollable creado
        """
        return ctk.CTkScrollableFrame(
            parent,
            width=width,
            height=height,
            **kwargs
        )
