#!/usr/bin/env python3
"""Fase 2 — stubs de caras (OpenCV Haar) y movimiento.

No se usan en el MVP de volumen. opencv-python-headless ya está en el venv.
Cuando se active: cargar haarcascade_frontalface_default.xml y marcar timestamps
con muchas detecciones / frame-diff alto; fusionar con candidates de volumen.
"""
from __future__ import annotations

from pathlib import Path


def detect_faces_stub(video: Path) -> list[dict]:
    return []


def detect_motion_stub(video: Path) -> list[dict]:
    return []


if __name__ == "__main__":
    print("fase2 stubs — sin acción. Activa desde detect_volume.py --faces/--motion más adelante.")
