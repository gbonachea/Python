#!/usr/bin/env python3
"""
ccleaner_like.py - Prototipo de limpiador para Linux (modo seguro).
Uso:
  python3 clean.py --dry-run
  python3 clean.py --clean trash,thumbnails,apt --yes
"""

import os
import shutil
import argparse
import getpass
from pathlib import Path
import subprocess

# Opcional: psutil para detectar procesos. Si no está, continuamos sin detección.
try:
    import psutil
except Exception:
    psutil = None

# --- Utilidades ---
def human_size(n):
    # formato simple
    units = ["B","KB","MB","GB","TB"]
    i = 0
    while n >= 1024 and i < len(units)-1:
        n /= 1024.0
        i += 1
    return f"{n:.1f} {units[i]}"

def disk_usage_of_path(p: Path):
    total = 0
    if p.exists():
        if p.is_file():
            total = p.stat().st_size
        else:
            for root, dirs, files in os.walk(p, onerror=lambda e: None):
                for f in files:
                    try:
                        total += Path(root, f).stat().st_size
                    except Exception:
                        pass
    return total

def safe_rmtree(path: Path):
    """Eliminar recursivamente un directorio con manejo de errores."""
    try:
        shutil.rmtree(path)
        return True
    except Exception as e:
        print(f"  [ERROR] al eliminar {path}: {e}")
        return False

def safe_remove_file(path: Path):
    try:
        path.unlink()
        return True
    except Exception as e:
        print(f"  [ERROR] al eliminar {path}: {e}")
        return False

# --- Rutas comunes a limpiar (por defecto, sólo en home del usuario actual) ---
def get_candidates():
    home = Path.home()
    candidates = {
        "trash": [home / ".local" / "share" / "Trash" / "files"],
        "thumbnails": [home / ".cache" / "thumbnails"],
        "pip_cache": [home / ".cache" / "pip"],
        "app_cache": [home / ".cache"],
        "chrome_cache": [
            home / ".cache" / "google-chrome",
            home / ".cache" / "chromium",
            home / ".cache" / "brave",
            home / ".config" / "google-chrome" / "Default" / "Cache",
            home / ".config" / "chromium" / "Default" / "Cache",
        ],
        "firefox_cache": [home / ".cache" / "mozilla"],
        # agregar más perfiles si necesario
    }
    # Opciones de sistema que requieren root
    system_candidates = {
        "apt_cache": [Path("/var/cache/apt/archives")],
        "journal": [],  # tratado especial (usa journalctl)
        "snap_cache": [Path("/var/lib/snapd/cache")],
    }
    return candidates, system_candidates

# --- Detección de procesos ---
BROWSERS = ["firefox", "chrome", "chromium", "brave", "google-chrome"]

def detect_running_browsers():
    running = set()
    if psutil:
        for p in psutil.process_iter(['name']):
            name = p.info.get('name') or ""
            ln = name.lower()
            for b in BROWSERS:
                if b in ln:
                    running.add(b)
    else:
        # fallback simple usando pgrep si está disponible
        try:
            for b in BROWSERS:
                res = subprocess.run(["pgrep","-x",b], stdout=subprocess.DEVNULL)
                if res.returncode == 0:
                    running.add(b)
        except Exception:
            pass
    return running

# --- Acciones ---
def simulate_clean(targets, include_system=False):
    """Muestra lo que se eliminaría y el tamaño estimado."""
    candidates, system_candidates = get_candidates()
    total = 0
    to_show = []
    for t in targets:
        paths = candidates.get(t, []) if not include_system else (candidates.get(t, []) + system_candidates.get(t, []) )
        if not paths and include_system and t in system_candidates:
            paths = system_candidates[t]
        for p in paths:
            if p and p.exists():
                size = disk_usage_of_path(p)
                total += size
                to_show.append((t, p, size))
            else:
                to_show.append((t, p, 0))
    return to_show, total

def perform_clean(targets, include_system=False, force=False, vacuum_journal_size=None):
    candidates, system_candidates = get_candidates()
    results = []
    for t in targets:
        paths = candidates.get(t, []) if not include_system else (candidates.get(t, []) + system_candidates.get(t, []) if t in system_candidates else [])
        for p in paths:
            if p and p.exists():
                # seguridad: evitar rutas raíz por error
                if str(p) in ("/", ""):
                    results.append((t, p, False, "ruta inválida"))
                    continue
                if p.is_dir():
                    if force:
                        ok = safe_rmtree(p)
                        results.append((t, p, ok, None if ok else "error"))
                    else:
                        # solo vaciar el contenido de la carpeta
                        try:
                            for child in p.iterdir():
                                if child.is_dir():
                                    safe_rmtree(child)
                                else:
                                    safe_remove_file(child)
                            results.append((t, p, True, "vaciado (force=False)"))
                        except Exception as e:
                            results.append((t, p, False, str(e)))
                else:
                    if force:
                        ok = safe_remove_file(p)
                        results.append((t, p, ok, None if ok else "error"))
                    else:
                        results.append((t, p, False, "no eliminado (force=False)"))
            else:
                results.append((t, p, False, "no existe"))
    # journalctl vacuum (sistema)
    if include_system and vacuum_journal_size:
        try:
            cmd = ["journalctl", "--vacuum-size=" + vacuum_journal_size]
            res = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            results.append(("journal", "journalctl", True, res.stdout.decode('utf-8','ignore')[:200]))
        except Exception as e:
            results.append(("journal", "journalctl", False, str(e)))
    return results
