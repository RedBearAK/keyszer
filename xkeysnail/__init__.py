# -*- coding: utf-8 -*-


def eval_file(path):
    with open(path, "rb") as file:
        exec(compile(file.read(), path, 'exec'), globals())


def uinput_device_exists():
    from os.path import exists
    return exists('/dev/uinput')


def has_access_to_uinput():
    from evdev.uinput import UInputError
    try:
        from xkeysnail.output import _uinput  # noqa: F401
        return True
    except UInputError:
        return False


def cli_main():
    from .info import __logo__, __version__
    #print(__logo__.strip())
    print(f"xkeysnail v{__version__}")
    #print("                             v{}".format(__version__))

    # Parse args
    import argparse
    from appdirs import user_config_dir
    parser = argparse.ArgumentParser(description='Yet another keyboard remapping tool for X environment.')
#    parser.add_argument('config', metavar='config.py', type=str, default=user_config_dir('xkeysnail/config.py'), nargs='?',
#                        help='configuration file (See README.md for syntax)')
    parser.add_argument('-c', '--config', dest="config", metavar="config_file", type=str, 
                        default=user_config_dir('xkeysnail/config.py'),
                        help='configuration file (See README.md for syntax)')
    parser.add_argument('-d', '--devices', dest="devices", metavar='device', type=str, nargs='+',
                        help='keyboard devices to remap (if omitted, xkeysnail choose proper keyboard devices)')
    parser.add_argument('-w', '--watch', dest='watch', action='store_true',
                        help='watch keyboard devices plug in ')
    parser.add_argument('-q', '--quiet', dest='quiet', action='store_true',
                        help='suppress output of key events')
    parser.add_argument('--list-devices', dest='list_devices', action='store_true')
    parser.add_argument('--version', dest='show_version', action='store_true',
                        help='show version')
    args = parser.parse_args()

    if args.show_version:
        exit(0)

    if args.list_devices:
        from .input import get_devices_list, print_device_list
        print_device_list(get_devices_list())
        exit(0)


    # Make sure that the /dev/uinput device exists
    if not uinput_device_exists():
        print("""The '/dev/uinput' device does not exist.
Please check your kernel configuration.""")
        import sys
        sys.exit(1)

    # Make sure that user have root privilege
    if not has_access_to_uinput():
        print("""Failed to open `uinput` in write mode.
Please check your access permissions for /dev/uinput.""")
        import sys
        sys.exit(1)

    # Load configuration file
    eval_file(args.config)

    print(f"(--) CONFIG: {args.config}")

    if args.quiet:
        print("(--) QUIET: key output supressed.")

    if args.watch:
        print("(--) WATCH: Watching for new devices to hot-plug.")

    # Enter event loop
    from xkeysnail.input import main_loop
    main_loop(args.devices, args.watch, args.quiet)
