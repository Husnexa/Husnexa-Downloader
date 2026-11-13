"""Builds the store upload zip. Stores assign their own ID, so the fixed 'key' is left out."""
import json
import os
import zipfile

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
EXTENSION_DIR = os.path.join(ROOT_DIR, "extension")
OUTPUT_DIR = os.path.join(ROOT_DIR, "installer_output")


def build():
    with open(os.path.join(EXTENSION_DIR, "manifest.json"), "r", encoding="utf-8") as f:
        manifest = json.load(f)
    manifest.pop("key", None)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"Husnexa_Extension_v{manifest['version']}.zip")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
        for folder, _, files in os.walk(EXTENSION_DIR):
            for name in files:
                full = os.path.join(folder, name)
                relative = os.path.relpath(full, EXTENSION_DIR)
                if relative != "manifest.json":
                    z.write(full, relative.replace(os.sep, "/"))
    return path


if __name__ == "__main__":
    print(build())
