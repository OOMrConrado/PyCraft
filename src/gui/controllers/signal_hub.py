"""
Centralized Signal Hub for PyCraft GUI.
Provides thread-safe signal communication between components.
"""

from PySide6.QtCore import QObject, Signal


class SignalHub(QObject):
    """
    Centralized hub for all application signals.

    This class provides thread-safe communication between GUI components,
    background threads, and managers. All signals emit from the main thread
    when connected properly.

    Usage:
        signal_hub = SignalHub()
        signal_hub.log_signal.connect(self._on_log)
        signal_hub.log_signal.emit("message", "info", "console_target")
    """

    # Logging and progress signals
    log_signal = Signal(str, str, str)  # message, level, target
    progress_signal = Signal(int)  # progress percentage
    status_signal = Signal(str, str)  # status message, color

    # Java management signals
    java_status_signal = Signal(str)  # status message
    java_progress_signal = Signal(int, int)  # value, maximum
    java_console_signal = Signal(str, str)  # text, color
    java_complete_signal = Signal(bool)  # success

    # Modpack search signals
    modpack_results_signal = Signal(object)  # search results list
    mp_icon_signal = Signal(str, object)  # project_id, QPixmap
    mp_pagination_signal = Signal(int)  # total results count

    # Client modpack signals
    client_mp_results_signal = Signal(object)  # search results list
    client_mp_pagination_signal = Signal(int)  # total results count

    # Version loading signal
    version_loaded_signal = Signal(object, object)  # versions list, callback

    # Server lifecycle signals
    server_crashed_signal = Signal(str)  # server path for crash modal
    vanilla_server_stopped_signal = Signal(bool)  # True = normal stop, False = crash
    modpack_server_stopped_signal = Signal(bool)  # True = normal stop, False = crash
    vanilla_server_started_signal = Signal(bool)  # success
    modpack_server_started_signal = Signal(bool)  # success

    # Installation success signals (for modal dialogs)
    vanilla_install_success_signal = Signal(str, str)  # version, folder
    server_modpack_install_success_signal = Signal(str, str, str)  # name, mc_version, loader
    mp_server_install_done_signal = Signal()  # triggered when missing server install completes

    # Update signals
    update_check_complete_signal = Signal(object)  # update_info dict or None
    update_download_progress_signal = Signal(int, float, float)  # progress%, downloaded_mb, total_mb
    update_download_complete_signal = Signal(str)  # installer_path or empty string
    startup_update_check_signal = Signal(object)  # update_info for startup check

    def __init__(self, parent=None):
        super().__init__(parent)
