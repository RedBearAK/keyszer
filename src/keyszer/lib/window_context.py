import abc
import json
from .logger import error, debug

# Provider classes for window context info

NO_CONTEXT_WAS_ERROR = {"wm_class": "", "wm_name": "", "x_error": True}



class WindowContextProviderInterface(abc.ABC):

    @abc.abstractmethod
    def get_window_context(self):
        pass


class WindowContextProvider(WindowContextProviderInterface):
    """generic object to provide correct window context to KeyContext"""

    def __init__(self, session_type, wl_desktop_env) -> None:
        if session_type == 'x11':
            self._provider = Xorg_WindowContext()
        if session_type == 'wayland' and wl_desktop_env == 'gnome':
            self._provider = Wl_GNOME_WindowContext()
        # TODO: Add more compatible providers here in future
        # Next up: Wayland + KDE Plasma

    def get_window_context(self):
        return self._provider.get_window_context()


class Wl_GNOME_WindowContext(WindowContextProviderInterface):
    """Window context provider object for Wayland+GNOME environments"""

    def __init__(self):
        import dbus
        from dbus.exceptions import DBusException

        self.DBusException      = DBusException
        self.session_bus        = dbus.SessionBus()

        self.proxy_xremap       = self.session_bus.get_object(
                                                        "org.gnome.Shell",
                                                        "/com/k0kubun/Xremap")
        self.iface_xremap       = dbus.Interface(
                                            self.proxy_xremap,
                                            "com.k0kubun.Xremap")
        self.proxy_windowsext   = self.session_bus.get_object(
                                                        "org.gnome.Shell",
                                                        "/org/gnome/Shell/Extensions/WindowsExt")
        self.iface_windowsext   = dbus.Interface(
                                            self.proxy_windowsext,
                                            "org.gnome.Shell.Extensions.WindowsExt")

        self.last_shell_ext_uuid    = None
        self.ext_uuid_windowsext    = 'window-calls-extended@hseliger.eu'
        self.ext_uuid_xremap        = 'xremap@k0kubun.com'

        self.GNOME_SHELL_EXTENSIONS = {
            self.ext_uuid_windowsext:   self.get_wl_gnome_dbus_windowsext_context,
            self.ext_uuid_xremap:       self.get_wl_gnome_dbus_xremap_context,
        }

    def get_window_context(self):
        """
        This function gets the window context from one of the two compatible 
        GNOME Shell extensions, via D-Bus.
        
        It attempts to get the window context from the shell extension that 
        was successfully used last time.
        
        If it fails, it tries the other one. If both fail, it returns an error.
        """

        # Order of the extensions
        extension_order = [self.ext_uuid_windowsext, self.ext_uuid_xremap]

        # If we don't have a successful previous extension or it was the last in the order
        if (self.last_shell_ext_uuid not in extension_order
            or extension_order.index(self.last_shell_ext_uuid) == len(extension_order) - 1):
            starting_index  = 0  # We start from the first extension
        else:
            # We start from the next extension
            starting_index  = extension_order.index(self.last_shell_ext_uuid) + 1

        for i in range(starting_index, len(extension_order)):
            extension_uuid  = extension_order[i]
            try:
                # Call the function associated with the extension
                context     = self.GNOME_SHELL_EXTENSIONS[extension_uuid]()
            except self.DBusException as e:
                self.last_shell_ext_uuid = None
                error(f'Error returned from GNOME Shell extension {extension_uuid}\n\t {e}')
            else:
                self.last_shell_ext_uuid = extension_uuid
                debug(f"SHELL_EXT: Using '{self.last_shell_ext_uuid}' for window context")
                return context

        # If we reach here, it means all extensions have failed
        print()
        error(  f'############################################################################'
                f'\nSHELL_EXT: No compatible GNOME Shell extension responding via D-Bus.')
        error(  f'These extensions are compatible with keyszer:'
                f'\n       {self.ext_uuid_windowsext}:'
                f'\n\t\t(https://extensions.gnome.org/extension/4974/window-calls-extended/)'
                f'\n       {self.ext_uuid_xremap}:'
                f'\n\t\t(https://extensions.gnome.org/extension/5060/xremap/)'  )
        error(f'Install "Extension Manager" from Flathub to manage GNOME Shell extensions')
        error(f'############################################################################')
        print()
        return NO_CONTEXT_WAS_ERROR


    def get_wl_gnome_dbus_xremap_context(self):
        active_window_dbus  = ""
        active_window_dct   = ""
        wm_class            = ""
        wm_name             = ""

        active_window_dbus  = self.iface_xremap.ActiveWindow()
        active_window_dct   = json.loads(active_window_dbus)
        wm_class            = active_window_dct['wm_class']
        wm_name             = active_window_dct['title']

        return {"wm_class": wm_class, "wm_name": wm_name, "context_error": False}

    def get_wl_gnome_dbus_windowsext_context(self):
        wm_class            = ""
        wm_name             = ""

        wm_class            = str(self.iface_windowsext.FocusClass())
        wm_name             = str(self.iface_windowsext.FocusTitle())

        return {"wm_class": wm_class, "wm_name": wm_name, "context_error": False}


class Xorg_WindowContext(WindowContextProviderInterface):
    """Window context provider object for X11/Xorg environments"""

    def __init__(self):
        self._display = None

        # Import Xlib modules here
        from Xlib.xobject.drawable import Window
        from Xlib.display import Display
        from Xlib.error import (ConnectionClosedError, DisplayConnectionError, DisplayNameError)
        self.Window                 = Window
        self.Display                = Display
        self.ConnectionClosedError  = ConnectionClosedError
        self.DisplayConnectionError = DisplayConnectionError
        self.DisplayNameError       = DisplayNameError

    def get_window_context(self):
        """
        Get window context from Xorg, window name, class,
        whether there is an X error or not
        """
        try:
            self._display = self._display or self.Display()
            wm_class    = ""
            wm_name     = ""

            input_focus = self._display.get_input_focus().focus
            window      = self.get_actual_window(input_focus)
            if window:
                # use _NET_WM_NAME string instead of WM_NAME to 
                # bypass (COMPOUND_TEXT) encoding problems
                wm_name = window.get_full_text_property(self._display.get_atom("_NET_WM_NAME"))
                pair    = window.get_wm_class()
                if pair:
                    wm_class = str(pair[1])

            return {"wm_class": wm_class, "wm_name": wm_name, "x_error": False}

        except self.ConnectionClosedError as xerror:
            error(xerror)
            self._display = None
            return NO_CONTEXT_WAS_ERROR
        # most likely DISPLAY env isn't even set
        except self.DisplayNameError as xerror:
            error(xerror)
            self._display = None
            return NO_CONTEXT_WAS_ERROR
        # seen when we don't have permission to the X display
        except self.DisplayConnectionError as xerror:
            error(xerror)
            self._display = None
            return NO_CONTEXT_WAS_ERROR

    def get_actual_window(self, window):
        if not isinstance(window, self.Window):
            return None

        # use _NET_WM_NAME string instead of WM_NAME to bypass (COMPOUND_TEXT) encoding problems
        wmname = window.get_full_text_property(self._display.get_atom("_NET_WM_NAME"))
        wmclass = window.get_wm_class()
        # workaround for Java app
        # https://github.com/JetBrains/jdk8u_jdk/blob/master/src/solaris/classes/sun/awt/X11/XFocusProxyWindow.java#L35
        if (wmclass is None and wmname is None) or "FocusProxy" in (wmclass or ""):
            parent_window = window.query_tree().parent
            if parent_window:
                return self.get_actual_window(parent_window)
            return None

        return window
