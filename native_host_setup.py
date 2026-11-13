"""Registers the extension's native helper for the current Windows user.

Usage: python native_host_setup.py register | unregister
"""
import json
import os
import shutil
import sys
import winreg

import updater

HOST_NAME = "com.husnexa.host"
HOST_DESCRIPTION = "Husnexa browser helper"
HELPER_EXE_NAME = "Husnexa Helper.exe"
CHROMIUM_EXTENSION_ID = "ohmpahchleninhlecnlfonifnnplkkhj"
FIREFOX_EXTENSION_ID = "extension@husnexa"
CHROMIUM_REGISTRY_ROOTS = (
    r"Software\Google\Chrome\NativeMessagingHosts",
    r"Software\Microsoft\Edge\NativeMessagingHosts",
    r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts",
)
FIREFOX_REGISTRY_ROOT = r"Software\Mozilla\NativeMessagingHosts"


def setup_dir():
    return os.path.join(updater.get_local_appdata_dir(), "native_host")


def helper_path():
    """Returns the helper exe for an installed app, or a launcher script when running from source."""
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), HELPER_EXE_NAME)
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "native_host.py")
    launcher = os.path.join(setup_dir(), "native_host.bat")
    with open(launcher, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(f'@echo off\n"{sys.executable}" "{script}" %*\n')
    return launcher


def write_manifest(file_name, allowed):
    path = os.path.join(setup_dir(), file_name)
    manifest = {
        "name": HOST_NAME,
        "description": HOST_DESCRIPTION,
        "path": helper_path(),
        "type": "stdio",
        **allowed,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return path


def set_registry_value(root, manifest_path):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{root}\{HOST_NAME}") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, manifest_path)


def register():
    os.makedirs(setup_dir(), exist_ok=True)
    chromium = write_manifest(
        "chromium.json", {"allowed_origins": [f"chrome-extension://{CHROMIUM_EXTENSION_ID}/"]}
    )
    firefox = write_manifest("firefox.json", {"allowed_extensions": [FIREFOX_EXTENSION_ID]})
    for root in CHROMIUM_REGISTRY_ROOTS:
        set_registry_value(root, chromium)
    set_registry_value(FIREFOX_REGISTRY_ROOT, firefox)


def unregister():
    for root in CHROMIUM_REGISTRY_ROOTS + (FIREFOX_REGISTRY_ROOT,):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, rf"{root}\{HOST_NAME}")
        except FileNotFoundError:
            pass
    shutil.rmtree(setup_dir(), ignore_errors=True)


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "register":
        register()
    elif action == "unregister":
        unregister()
    else:
        sys.exit(__doc__)
