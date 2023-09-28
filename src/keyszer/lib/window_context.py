import os
import abc
import dbus
import json
import time
import i3ipc
import shutil
import socket
import subprocess

from subprocess import PIPE
from i3ipc import Con
from typing import Dict, Optional

# For getting window info in more generic manner from 'wlroots' (ALPHA TESTING)
from pywayland.client import Display
from .wayland_protocols.wayland import WlDisplay, WlOutput, WlRegistry, wl_registry, WlSeat
from .wayland_protocols.wlr_foreign_toplevel_management_unstable_v1 import ZwlrForeignToplevelManagerV1, ZwlrForeignToplevelHandleV1


from .logger import error, debug

# Provider classes for window context info

# Place new provider classes above the generic class at the end to
# facilitate automatic inclusion in the list of supported environments
# and automatic redirection from the generic provider class to the
# matching specific provider class suitable for the environment.


NO_CONTEXT_WAS_ERROR = {"wm_class": "", "wm_name": "", "x_error": True}


class WindowContextProviderInterface(abc.ABC):
    """Abstract base class for all window context provider classes"""

    @classmethod
    @abc.abstractmethod
    def get_supported_environments(cls):
        """
        This method should return a list of environments that the subclass 
        supports.

        Each environment should be represented as a tuple. For example, if 
        a subclass supports the environments 'x11' and 'wayland', this method 
        should return [('x11', None), ('wayland', None)].

        If an environment is specific to a certain desktop environment, the 
        desktop environment should be included in the tuple. For example, if 
        a subclass supports the 'wayland' environment specifically on the 
        'gnome' desktop, this method should return [('wayland', 'gnome')].

        :returns: A list of tuples, each representing an environment supported 
        by the subclass.
        """

    @abc.abstractmethod
    def get_window_context(self):
        """
        This method should return the current window's context as a dictionary.

        The returned dictionary should contain the following keys:

        - "wm_class": The class of the window.
        - "wm_name": The name of the window.
        - "x_error": A boolean indicating whether there was an error 
            in obtaining the window's context.

        The "wm_class" and "wm_name" values are expected to be strings.
        The "x_error" value is expected to be a boolean, which should 
        be False if the window's context was successfully obtained, 
        and True otherwise.

        Example of a successful context:

        {
            "wm_class": "ExampleClass",
            "wm_name": "ExampleName",
            "x_error": False
        }

        In case of an error, the method should return NO_CONTEXT_WAS_ERROR, 
        which is a predefined global variable "constant":

        NO_CONTEXT_WAS_ERROR = {"wm_class": "", "wm_name": "", "x_error": True}

        :returns: A dictionary containing window context information.
        """


class WlRoots_WindowContext_pywayland(WindowContextProviderInterface):
    """Window context provider object for Wayland+wlroots environments"""

    @classmethod
    def get_supported_environments(cls):
        # This class supports the wlroots compositor on Wayland via 'pywayland'
        return [
            ('wayland', 'wlroots'),
            ('wayland', 'sway')     # test using this in sway
        ]

    def __init__(self):
        debug(f"Initializing '{self.__class__.__name__}' provider instance...")
        self.display = Display()
        print("\t Display:", self.display)
        self.display.connect()

        self.registry           = self.display.get_registry() # appears generic due to redirects
        print("\t Registry:", self.registry)

        self.registry.dispatcher['global']              = self.handle_global
        self.registry.dispatcher['global_remove']       = self.handle_global_remove

        self.toplevel_manager   = None
        self.toplevel_windows   = []  # To keep track of toplevel windows

        # self.display.dispatcher   # I found "dispatcher: Dispatcher" here
        self.display.dispatch()
        self.display.roundtrip()

        self.wm_class           = None
        self.wm_name            = None

        # test out the context method:
        self.get_active_wdw_ctx()
        print(f"\t init: {self.wm_class = }")
        print(f"\t init: {self.wm_name = }")

    def handle_global(self, registry, name, interface, version):
        if interface == "zwlr_foreign_toplevel_manager_v1":
            self.toplevel_manager = self.registry.bind(name, ZwlrForeignToplevelManagerV1, version)
            self.toplevel_manager.dispatcher['toplevel'] = self.on_new_toplevel

    def handle_global_remove(self, registry, name):
        # Remove the top-level window from the list when it's no longer present
        for toplevel in self.toplevel_windows:
            if toplevel.name == name:  # Assuming the toplevel has a 'name' attribute. Adjust accordingly.
                self.toplevel_windows.remove(toplevel)
                break

    def on_new_toplevel(self, toplevel_manager, toplevel):
        print("\t on_new_toplevel() toplevel_manager:", toplevel_manager)
        print("\t on_new_toplevel() toplevel:", toplevel)
        print(f"{type(toplevel) = }")
        self.toplevel_windows.append(toplevel)
        print("\t on_new_toplevel() toplevel_windows:", self.toplevel_windows)
        toplevel.dispatcher['app_id'] = self.on_app_id
        toplevel.dispatcher['title'] = self.on_title

    def on_app_id(self, toplevel, app_id):
        print(f"\t on_app_id() {type(app_id) = }")
        print(f"\t on_app_id() {app_id = }")
        toplevel.app_id = app_id
        print(f"\t on_app_id() {type(toplevel.app_id) = }")
        print(f"\t on_app_id() {toplevel.app_id = }")

    def on_title(self, toplevel, title):
        print(f"\t on_title() {type(title) = }")
        print(f"\t on_title() {title = }")
        toplevel.title = title
        print(f"\t on_title() {type(toplevel.title) = }")
        print(f"\t on_title() {toplevel.title = }")

    def get_active_wdw_ctx(self):
        if not self.toplevel_windows:
            return NO_CONTEXT_WAS_ERROR
        # Assuming the last announced toplevel is the focused one
        focused_window = self.toplevel_windows[-1]
        print(f"\t get_active_wdw_ctx() {type(focused_window) = }")
        print(f"\t get_active_wdw_ctx() {focused_window = }")
        self.wm_class = getattr(focused_window, 'app_id', 'unknown')
        self.wm_name = getattr(focused_window, 'title', 'unknown')
        print(f"\t get_active_wdw_ctx() {type(self.wm_class) = }")
        print(f"\t get_active_wdw_ctx() {self.wm_class = }")
        print(f"\t get_active_wdw_ctx() {type(self.wm_name) = }")
        print(f"\t get_active_wdw_ctx() {self.wm_name = }")
        return {"wm_class": self.wm_class, "wm_name": self.wm_name, "x_error": False}

    def get_window_context(self):
        """Return window context to KeyContext"""
        print(f"\t get_window_context() was called...")
        return self.get_active_wdw_ctx()



# from wlroots.wlr_types import ForeignToplevelManagerV1
# from pywayland.client import Display


# class WlRoots_WindowContext_pywlroots(WindowContextProviderInterface):
#     """Window context provider object for Wayland+wlroots environments using the wlroots library."""

#     @classmethod
#     def get_supported_environments(cls):
#         # This class supports the wlroots compositor on Wayland via 'pywlroots'
#         return [
#             ('wayland', 'wlroots'),
#             ('wayland', 'sway')     # test using this in sway
#         ]

#     def __init__(self):
#         debug(f"Initializing '{self.__class__.__name__}' provider instance...")
        
#         # Initialize Wayland Display
#         self.display = Display()
        
#         # Create an instance of ForeignToplevelManagerV1
#         self.toplevel_manager = ForeignToplevelManagerV1.create(self.display)
        
#         # Placeholder for toplevel windows
#         self.toplevel_windows = []
        
#         # Setup event handlers (just placeholders for now)
#         self.setup_event_handlers()

#     def setup_event_handlers(self):
#         """Set up event handlers for the toplevel manager and windows."""
#         # Listen for new toplevels
#         self.toplevel_manager.on('toplevel', self.on_new_toplevel)

#         # For existing toplevel windows, set up their event handlers
#         for toplevel in self.toplevel_windows:
#             self._setup_toplevel_event_handlers(toplevel)

#     def _setup_toplevel_event_handlers(self, toplevel):
#         """Set up event handlers for a single toplevel window."""
#         toplevel.on('title', self.on_title_change)
#         toplevel.on('app_id', self.on_app_id_change)

#     def on_new_toplevel(self, toplevel):
#         """Handle when a new toplevel window is announced."""
#         pass

#     def on_app_id_change(self, toplevel, app_id):
#         """Handle when the app_id of a toplevel window changes."""
#         pass

#     def on_title_change(self, toplevel, title):
#         """Handle when the title of a toplevel window changes."""
#         pass

#     def get_active_wdw_ctx(self):
#         """Retrieve the current focused window's class and title."""
#         pass

#     def get_window_context(self):
#         """Return window context to KeyContext."""
#         return self.get_active_wdw_ctx



# class Wl_sway_WindowContext(WindowContextProviderInterface):
#     """Window context provider object for Wayland+sway environments"""

#     @classmethod
#     def get_supported_environments(cls):
#         # This class supports the sway window manager environment on Wayland
#         return [
#             ('wayland', 'sway'),
#             ('wayland', 'swaywm'),
#         ]

#     def __init__(self):

#         # Create the connection object
#         self.cnxn_obj           = None
#         self._establish_connection()

#         self.wm_class           = None
#         self.wm_name            = None

#     def _establish_connection(self):
#         """Establish a connection to sway IPC via i3ipc. Retry indefinitely if unsuccessful."""
#         while True:
#             try:
#                 self.cnxn_obj = i3ipc.Connection(auto_reconnect=True)
#                 debug(f'CTX_SWAY: Connection object created.')
#                 break
#             # i3ipc.Connection() class may return generic Exception, or ConnectionError
#             except (ConnectionError, Exception) as cnxn_err:
#                 error(f'ERROR: Problem connecting to sway IPC via i3ipc:\n\t{cnxn_err}')
#                 time.sleep(3)

#     def get_active_wdw_ctx_sway_ipc(self):
#         """Get sway window context via i3ipc Python module methods."""
#         try:
#             tree                    = self.cnxn_obj.get_tree()
#         except ConnectionResetError as cnxn_err:
#             debug(f"IPC connection was reset (sway).\t\n{cnxn_err}")
#             return NO_CONTEXT_WAS_ERROR
#         focused_wdw             = tree.find_focused()
#         if not focused_wdw:
#             debug("No window is currently focused.")
#             return NO_CONTEXT_WAS_ERROR
#         self.wm_class           = focused_wdw.app_id or 'sway-ctx-error'
#         self.wm_name            = focused_wdw.name or 'sway-ctx-error'
#         return {"wm_class": self.wm_class, "wm_name": self.wm_name, "x_error": False}

#     def get_window_context(self):
#         """Return window context to KeyContext"""
#         return self.get_active_wdw_ctx_sway_ipc()


class Wl_Hyprland_WindowContext(WindowContextProviderInterface):
    """Window context provider object for Wayland+Hyprland environments"""

    @classmethod
    def get_supported_environments(cls):
        # This class supports the Hyprland window manager environment on Wayland
        return [
            ('wayland', 'hyprland'),
            ('wayland', 'hypr')
        ]

    def __init__(self):
        from hyprpy import Hyprland
        self.hypr_inst      = Hyprland()

        self.first_run      = True
        self.sock           = None
        self.hyprctl_cmd    = shutil.which('hyprctl')
        self.wm_class       = None
        self.wm_name        = None

    def get_active_wdw_ctx_hyprpy(self):
        try:
            window_info         = self.hypr_inst.get_active_window()
            debug(f'CTX_HYPR: Using "hyprpy" for windows context.')
            self.wm_class       = window_info.wm_class
            self.wm_name        = window_info.title
            return {"wm_class": self.wm_class, "wm_name": self.wm_name, "x_error": False}
        except Exception as e:
            error(f'ERROR: Problem getting active window context using "hyprpy".\n\t{e}')
            return self.get_active_wdw_ctx_hypr_ipc() # fall back to direct IPC method

    def _open_socket(self):
        """Utility function to open Hyprland IPC socket"""
        try:
            HIS = os.environ['HYPRLAND_INSTANCE_SIGNATURE']
        except KeyError as key_err:
            raise EnvironmentError('HYPRLAND_INSTANCE_SIGNATURE is not set. KeyError resulted.')
        if HIS is None:
            raise EnvironmentError('HYPRLAND_INSTANCE_SIGNATURE is not set.')
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(f"/tmp/hypr/{HIS}/.socket.sock")

    def get_active_wdw_ctx_hypr_ipc(self):
        """Get Hyprland window context using IPC socket (faster than shell commands)."""
        try:
            if self.first_run or self.sock is None:
                try:
                    self._open_socket()
                    debug(f'CTX_HYPR: Using IPC socket for window context.')
                except (socket.error, OSError, EnvironmentError) as conn_err:
                    error(f'ERROR: Problem opening Hyprland IPC socket.\n\t{conn_err}')
                    return self.get_active_wdw_ctx_hypr_shell() # Fallback to shell method
                self.first_run = False

            command = "-j activewindow"  # Replace with the actual command
            self.sock.sendall(command.encode("utf-8"))
            response: bytes     = self.sock.recv(1024)
            wdw_info_str        = response.decode('utf-8')
            window_info: dict   = json.loads(wdw_info_str) # Type hint for VSCode "get()" highlight
            self.wm_class       = window_info.get("class", "hypr-context-error")
            self.wm_name        = window_info.get("title", "hypr-context-error")
            return {"wm_class": self.wm_class, "wm_name": self.wm_name, "x_error": False}

        except (socket.error, OSError, json.JSONDecodeError) as ctx_err:
            error(f'ERROR: Problem getting window context via Hyprland IPC socket:\n\t{ctx_err}')
            # Close the socket
            if self.sock:
                self.sock.close()
                self.sock = None  # Mark it as None so it will be re-opened on the next run
            return NO_CONTEXT_WAS_ERROR

    def get_active_wdw_ctx_hypr_shell(self):
        """Get Hyprland window context using shell commands (will perform poorly)."""
        if not self.hyprctl_cmd:
            error(f'ERROR: Hyprland context fallback failed: "hyprctl" not found.')
            return NO_CONTEXT_WAS_ERROR
        try:
            cmd_lst = [self.hyprctl_cmd, '-j', 'activewindow']
            result = subprocess.run(cmd_lst, stdout=PIPE, stderr=PIPE, text=True, check=True)
            wdw_info_str        = result.stdout
            window_info: dict   = json.loads(wdw_info_str) # Type hint for VSCode "get()" highlight
            self.wm_class       = window_info.get("class", "hypr-context-error")
            self.wm_name        = window_info.get("title", "hypr-context-error")
            debug(f'CTX_HYPR: Using shell command (hyprctl) for window context (FALLBACK!).')
            return {"wm_class": self.wm_class, "wm_name": self.wm_name, "x_error": False}
        except subprocess.CalledProcessError as proc_err:
            error(f"ERROR: Problem getting window context with hyprctl:\n\t{proc_err}")
            return NO_CONTEXT_WAS_ERROR

    def get_window_context(self):
        """Return window context to KeyContext"""
        # return self.get_active_wdw_ctx_hypr_ipc()
        return self.get_active_wdw_ctx_hyprpy()


class Wl_KDE_Plasma_WindowContext(WindowContextProviderInterface):
    """Window context provider object for Wayland+KDE_Plasma environments"""

    @classmethod
    def get_supported_environments(cls):
        # This class supports the KDE Plasma environment on Wayland
        return [
            ('wayland', 'kde'),
            ('wayland', 'plasma')
        ]

    def __init__(self):
        # import time
        # import dbus
        from dbus.exceptions import DBusException

        self.DBusException      = DBusException
        self.session_bus        = dbus.SessionBus()

        self.wm_class           = None
        self.wm_name            = None
        self.res_name           = None

        self.toshy_dbus_obj     = 'org.toshy.Toshy'
        self.toshy_dbus_path    = '/org/toshy/Toshy'

        while True:
            try:
                self.proxy_toshy_svc = self.session_bus.get_object( self.toshy_dbus_obj,
                                                                    self.toshy_dbus_path)
                self.iface_toshy_svc = dbus.Interface(self.proxy_toshy_svc,
                                                        self.toshy_dbus_obj)
                break
            except self.DBusException as dbus_error:
                error(f'Error getting Toshy KDE D-Bus service interface.\n\t{dbus_error}')
            time.sleep(3)

    def get_window_context(self):
        """
        Return window context to KeyContext
        Gets window context info from D-Bus service fed by KWin script
        """
        try:
            # Convert to native Python dict type from 'dbus.Dictionary()' type
            window_info_dct     = dict(self.iface_toshy_svc.GetActiveWindow())
        except self.DBusException as dbus_error:
            error(f'Toshy KDE D-Bus service interface stale?:\n\t{dbus_error}')
            error(f'Trying to refresh Toshy KDE D-Bus service interface...')
            try:
                self.proxy_toshy_svc = self.session_bus.get_object( self.toshy_dbus_obj,
                                                                    self.toshy_dbus_path)
                self.iface_toshy_svc = dbus.Interface(  self.proxy_toshy_svc,
                                                        self.toshy_dbus_obj)
            except self.DBusException as dbus_error:
                error(f'Error refreshing Toshy KDE D-Bus service interface.\n\t{dbus_error}')
            try:
                # Convert to native Python dict type from 'dbus.Dictionary()' type
                window_info_dct     = dict(self.iface_toshy_svc.GetActiveWindow())
                debug(f'Toshy KDE D-Bus service interface restored!')
            except self.DBusException as dbus_error: 
                debug(f'Error returned from Toshy KDE D-Bus service:\n\t{dbus_error}')
                return NO_CONTEXT_WAS_ERROR

        # native_dict = {str(key): str(value) for key, value in dbus_dict.items()}
        new_wdw_info_dct    = {str(key): str(value) for key, value in window_info_dct.items()}
        # 'caption' is X11/Xorg WM_NAME equivalent
        self.wm_name        = new_wdw_info_dct.get('caption', '')
        # 'resourceClass' is X11/Xorg WM_CLASS equivalent
        self.wm_class       = new_wdw_info_dct.get('resource_class', '')
        # 'resourceName' has no X11/Xorg equivalent (tends to be process name?)
        self.res_name       = new_wdw_info_dct.get('resource_name', '')

        debug(f"KDE_DBUS_SVC: Using D-Bus interface '{self.toshy_dbus_obj}' for window context")

        return {"wm_class": self.wm_class, "wm_name": self.wm_name, "x_error": False}


class Wl_GNOME_WindowContext(WindowContextProviderInterface):
    """Window context provider object for Wayland+GNOME environments"""

    @classmethod
    def get_supported_environments(cls):
        # This class supports the GNOME environment on Wayland
        return [('wayland', 'gnome')]

    def __init__(self):
        # import dbus
        from dbus.exceptions import DBusException

        self.DBusException      = DBusException
        session_bus             = dbus.SessionBus()

        path_focused_wdw        = "/org/gnome/shell/extensions/FocusedWindow"
        obj_focused_wdw         = "org.gnome.shell.extensions.FocusedWindow"
        proxy_focused_wdw       = session_bus.get_object("org.gnome.Shell", path_focused_wdw)
        self.iface_focused_wdw  = dbus.Interface(proxy_focused_wdw, obj_focused_wdw)

        path_windowsext         = "/org/gnome/Shell/Extensions/WindowsExt"
        obj_windowsext          = "org.gnome.Shell.Extensions.WindowsExt"
        proxy_windowsext        = session_bus.get_object("org.gnome.Shell", path_windowsext)
        self.iface_windowsext   = dbus.Interface(proxy_windowsext,obj_windowsext)

        path_xremap             = "/com/k0kubun/Xremap"
        obj_xremap              = "com.k0kubun.Xremap"
        proxy_xremap            = session_bus.get_object("org.gnome.Shell", path_xremap)
        self.iface_xremap       = dbus.Interface(proxy_xremap, obj_xremap)

        self.last_good_ext_uuid     = None
        self.cycle_count            = 0

        self.ext_uuid_focused_wdw   = 'focused-window-dbus@flexagoon.com'
        self.ext_uuid_windowsext    = 'window-calls-extended@hseliger.eu'
        self.ext_uuid_xremap        = 'xremap@k0kubun.com'

        self.GNOME_SHELL_EXTENSIONS = {
            self.ext_uuid_xremap:       self.get_wl_gnome_dbus_xremap_context,
            self.ext_uuid_windowsext:   self.get_wl_gnome_dbus_windowsext_context,
            self.ext_uuid_focused_wdw:  self.get_wl_gnome_dbus_focused_wdw_context,
        }

    def get_window_context(self):
        """
        This function gets the window context from one of the compatible 
        GNOME Shell extensions, via D-Bus.
        
        It attempts to get the window context from the shell extension that 
        was successfully used last time.
        
        If it fails, it tries the others. If all fail, it returns an error.
        """

        # Order of the extensions
        extension_uuids = list(self.GNOME_SHELL_EXTENSIONS.keys())

        # If we have a last successful extension
        if self.last_good_ext_uuid in extension_uuids:
            starting_index = extension_uuids.index(self.last_good_ext_uuid)
        else:
            # We don't have a last successful extension, so start from the first
            starting_index = 0

        # Create a new list that starts with the last successful extension, followed by the others
        ordered_extensions = extension_uuids[starting_index:] + extension_uuids[:starting_index]

        for extension_uuid in ordered_extensions:
            try:
                # Call the function associated with the extension
                context = self.GNOME_SHELL_EXTENSIONS[extension_uuid]()
            except self.DBusException as e:
                error(f"Error returned from GNOME Shell extension '{extension_uuid}'\n\t {e}")
                # Continue to the next extension
                continue
            else:
                # No exceptions were thrown, so this extension is now the preferred one
                self.last_good_ext_uuid = extension_uuid
                debug(f"SHELL_EXT: Using UUID '{self.last_good_ext_uuid}' for window context")
                return context

        # If we reach here, it means all extensions have failed
        print()
        error(  f'############################################################################')
        error(  f'SHELL_EXT: No compatible GNOME Shell extension responding via D-Bus.'
                f'\n\tThese shell extensions are compatible with keyszer:'
                f'\n\t    {self.ext_uuid_xremap} (supports pre-GNOME 41.x):'
                f'\n\t\t(https://extensions.gnome.org/extension/5060/xremap/)'
                f'\n\t    {self.ext_uuid_windowsext}:'
                f'\n\t\t(https://extensions.gnome.org/extension/4974/window-calls-extended/)'
                f'\n\t    {self.ext_uuid_focused_wdw}:'
                f'\n\t\t(https://extensions.gnome.org/extension/5592/focused-window-d-bus/)'
        )
        error(f'Install "Extension Manager" from Flathub to manage GNOME Shell extensions')
        error(f'############################################################################')
        print()

        self.last_good_ext_uuid = None
        return NO_CONTEXT_WAS_ERROR

    def get_wl_gnome_dbus_focused_wdw_context(self):
        """utility function to actually talk to the 'Focused Window D-Bus' extension"""
        wm_class            = ''
        wm_name             = ''
        
        try:
            focused_wdw_dbus    = self.iface_focused_wdw.Get()
            # print(f'{focused_wdw_dbus = }')
            focused_wdw_dct     = json.loads(focused_wdw_dbus)
            # print(f'{focused_wdw_dct = }')

            wm_class            = focused_wdw_dct.get('wm_class', '')
            wm_name             = focused_wdw_dct.get('title', '')
        except self.DBusException as dbus_error:
            # This will be the error if no window info found (e.g., GNOME desktop):
            # org.gnome.gjs.JSError.Error: No window in focus
            if 'No window in focus' in str(dbus_error): pass
            else: raise   # pass on the original exception if not 'No window in focus'

        return {"wm_class": wm_class, "wm_name": wm_name, "x_error": False}

    def get_wl_gnome_dbus_windowsext_context(self):
        """utility function to actually talk to the 'Window Calls Extended' extension"""
        wm_class            = ''
        wm_name             = ''

        wm_class            = str(self.iface_windowsext.FocusClass())
        wm_name             = str(self.iface_windowsext.FocusTitle())

        return {"wm_class": wm_class, "wm_name": wm_name, "x_error": False}

    def get_wl_gnome_dbus_xremap_context(self):
        """utility function to actually talk to the 'Xremap' extension"""
        active_window_dbus  = ''
        active_window_dct   = ''
        wm_class            = ''
        wm_name             = ''

        active_window_dbus  = self.iface_xremap.ActiveWindow()
        active_window_dct   = json.loads(active_window_dbus)

        # use get() with default value to avoid KeyError for 
        # GNOME Shell/desktop lack of properties returned
        active_window_dct: Dict[str:str]
        wm_class            = active_window_dct.get('wm_class', '')
        wm_name             = active_window_dct.get('title', '')

        return {"wm_class": wm_class, "wm_name": wm_name, "x_error": False}


class Xorg_WindowContext(WindowContextProviderInterface):
    """Window context provider object for X11/Xorg environments"""

    @classmethod
    def get_supported_environments(cls):
        # This class supports any desktop environment on X11
        return [('x11', None)]

    def __init__(self):
        self._display = None

        # Import Xlib modules here
        from Xlib.xobject.drawable import Window
        from Xlib.display import Display
        from Xlib.error import (
                            ConnectionClosedError,
                            DisplayConnectionError,
                            DisplayNameError,
                            BadWindow
                            )
        self.Window                 = Window
        self.Display                = Display
        self.ConnectionClosedError  = ConnectionClosedError
        self.DisplayConnectionError = DisplayConnectionError
        self.DisplayNameError       = DisplayNameError
        self.BadWindow              = BadWindow

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
                # We use _NET_WM_NAME string (UTF-8) here instead of WM_NAME to 
                # bypass (COMPOUND_TEXT) encoding problems when non-ASCII
                # characters are in the window name string.
                # Xlib cannot deal with COMPOUND_TEXT encoding and ends up
                # returning an empty "bytes object".
                
                # Older form: 
                # wm_name = window.get_full_text_property(self._display.get_atom("_NET_WM_NAME"))
                
                # Mitigation for '_NET_WM_NAME' not being set at all(!), but WM_NAME is good:
                # (this was observed in KDE 4.x application launcher/menu)
                wm_name = window.get_full_text_property(self._display.get_atom("_NET_WM_NAME"))
                if wm_name is None:
                    error(f'Xlib _NET_WM_NAME query returned NoneType, falling back to WM_NAME')
                    wm_name = window.get_wm_name()
                    if isinstance(wm_name, bytes):
                        error(f'Xlib WM_NAME query returned bytes object, falling back to error string')
                        wm_name = "ERR: Xorg_WindowContext: Bad _NET_WM_NAME and WM_NAME"
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

        # # use _NET_WM_NAME string instead of WM_NAME to bypass (COMPOUND_TEXT) encoding problems
        # wmname = window.get_full_text_property(self._display.get_atom("_NET_WM_NAME"))
        # wmclass = window.get_wm_class()

        try:
            # use _NET_WM_NAME string instead of WM_NAME to bypass (COMPOUND_TEXT) encoding problems
            wmname = window.get_full_text_property(self._display.get_atom("_NET_WM_NAME"))
            wmclass = window.get_wm_class()
        except self.BadWindow as xerror:  # Catch the BadWindow error here
            error(xerror)
            return None  # or do some appropriate handling here

        # workaround for Java app
        # https://github.com/JetBrains/jdk8u_jdk/blob/master/src/solaris/classes/sun/awt/X11/XFocusProxyWindow.java#L35
        if (wmclass is None and wmname is None) or "FocusProxy" in (wmclass or ""):
            parent_window = window.query_tree().parent
            if parent_window:
                return self.get_actual_window(parent_window)
            return None

        return window


###############################################################################################
# ALL SPECIFIC PROVIDER CLASSES MUST BE DEFINED BEFORE/ABOVE THIS GENERIC PROVIDER!!!
# This class is responsible for making a list of the environments supported
# by all the specific provider classes in this module, and redirecting the
# rest of the keymapper code to the correct specific provider. 

# Generic class for the rest of the code to interact with
class WindowContextProvider(WindowContextProviderInterface):
    """generic object to provide correct window context to KeyContext"""
    _instance = None

    # Mapping of environments to provider classes
    environment_class_map = {
        env: cls for cls in WindowContextProviderInterface.__subclasses__()
        for env in cls.get_supported_environments()
    }

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(WindowContextProvider, cls).__new__(cls)
        return cls._instance

    def __init__(self, session_type, wl_desktop_env) -> None:

        env = (session_type, wl_desktop_env)
        if env not in self.environment_class_map:
            raise ValueError(f"Unsupported environment: {env}")

        self._provider = self.environment_class_map[env]()

    def get_window_context(self):
        return self._provider.get_window_context()

    @classmethod
    def get_supported_environments(cls):
        # This generic class does not directly support any environments
        return []

# ALL SPECIFIC PROVIDER CLASSES MUST BE DEFINED BEFORE/ABOVE THIS GENERIC PROVIDER!!!
# This class is responsible for making a list of the environments supported
# by all the specific provider classes in this module, and redirecting the
# rest of the keymapper code to the correct specific provider. 
