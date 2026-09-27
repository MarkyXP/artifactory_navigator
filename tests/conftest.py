"""
Shared test setup.

Two things the unit tests need that the import-time code in app/ assumes:

1. app.core.config reads CONFIG_PATH when it is first imported, and there is no
   .env in the repo, so it is pointed at the checked in config unless the
   environment already set one.
2. wx is a Windows GUI toolkit. app.gui.* and app.services.login import it at
   module level, so those modules cannot be imported on a headless machine.
   Importing wx at all is the problem, not using it - the login and directory
   loading tests drive pure Python objects, so a placeholder is enough to get
   past the import.
"""

import importlib
import os
import sys
import types
import unittest.mock

from cryptography.fernet import Fernet

# Get the parent directory of the current file
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

os.environ["CONFIG_PATH"] = os.environ.get(
    "CONFIG_PATH", os.path.join(parent_dir, "app", "core", "config.json")
)

# app.core.credentials builds a Fernet cipher at import time from APP_SECRET, so
# a valid key has to exist before that module is imported. This is a throwaway
# generated for the test process only - it decrypts nothing real, and the real
# key is supplied from the environment (or the .env) in normal use. tests
# replace the store accessors, so nothing is ever written with it.
os.environ.setdefault("APP_SECRET", Fernet.generate_key().decode())


class _PlaceholderBase:
    """
    Base for the generated attribute classes.

    Subclassable and tolerant of any method call, so app/gui classes that do
    "class Frame(wx.Frame)" and "def __init__: super().__init__(...)" can be
    declared and instantiated as usual. The class body itself only executes
    against this in test runs, so it is allowed to be permissive.
    """

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return _PlaceholderMethod(name)


class _PlaceholderMethod:
    """Callable, chainable stand-in for anything called on a wx object."""

    def __init__(self, name):
        self._name = name

    def __call__(self, *args, **kwargs):
        return self

    def __getattr__(self, name):
        return _PlaceholderMethod(f"{self._name}.{name}")

    def __iter__(self):
        return iter(())

    def __bool__(self):
        return False


def _make_placeholder_attr(module_name, attr):
    return type(attr, (_PlaceholderBase,), {"__module__": module_name})


def _install_placeholder(name):
    """
    Put a placeholder module in sys.modules if the real one isn't importable.

    Returns the stub, or None when the real module is available and nothing
    needed stubbing. Attributes resolve to real, subclassable classes rather
    than mocks, because app/gui declares classes inheriting from them.
    """
    # Already resolved to a placeholder by an earlier call (e.g. the parent
    # installed first) - don't probe for the real module again.
    if name in sys.modules:
        return sys.modules[name]
    try:
        importlib.import_module(name)
        return None
    except ImportError:
        pass
    stub = types.ModuleType(name)
    stub.__getattr__ = lambda attr: _make_placeholder_attr(name, attr)
    # A stub standing in for a package needs a __path__. Without one the import
    # machinery falls back to __getattr__, gets back a class instead of a
    # sequence, and dies iterating it when resolving a submodule. An empty
    # tuple means "a package with no submodules on disk", which is correct -
    # anything imported from it is stubbed explicitly.
    if "." not in name:
        stub.__path__ = []
    sys.modules[name] = stub
    # Register as an attribute of the parent too, so "import win32com.client"
    # resolves once win32com is itself a stub. Written into the parent's
    # __dict__ directly: the parent may be a stub whose __getattr__ synthesises
    # classes, which is not something setattr's internals can work with.
    parent, _, child = name.rpartition(".")
    if parent and parent in sys.modules:
        sys.modules[parent].__dict__[child] = stub
    return stub


_install_placeholder("wx")
# app.services.email sends DST mail through COM, which is Windows only.
_install_placeholder("win32com")
_install_placeholder("win32com.client")
