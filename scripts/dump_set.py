#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import csv
import requests
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime

# ---------- Config ----------
USER_AGENT = "mtg-set-dump/1.0 (+https://github.com/TU_USUARIO)"  # <-- cámbialo
BASE_URL = "https://api.scryfall.com/cards/search"
OUT_DIR = Path("output")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def build_session():
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    retry = Retry(
        total=5, backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

def descargar_coleccion(codigo_set: str, include_tokens: bool, unique: str = "prints"):
    """
    codigo_set: código del set (ej. 'otj', 'woe', 'mh3')
    include_tokens: si False, excluye tokens (añade -is:token)
    unique: 'prints' (todas impresiones) | 'cards' (una por carta) | 'art'
    """
    session = build_session()
    q = f"e:{codigo_set}" + ("" if include_tokens else " -is:token")
    params = {"q": q, "unique": unique}

    url = BASE_URL
    cartas, pagina = [], 1

    while url:
        print(f"Descargando página {pagina} del set '{codigo_set}'...")
        r = session.get(url, params=params, timeout=30) if pagina == 1 else session.get(url, timeout=30)
        if r.status_code != 200:
            print(f"Error {r.status_code}: {r.text[:200]}")
            break

        datos = r.json()
        for carta in datos.get("data", []):
            prices = carta.get("prices") or {}
            purchase = carta.get("purchase_uris") or {}
            cartas.append({
                "name": carta.get("name"),
                "reprint": carta.get("reprint"),
                "set_name": carta.get("set_name"),
                "set": carta.get("set"),
                "collector_number": carta.get("collector_number"),
                "rarity": carta.get("rarity"),
                "lang": carta.get("lang"),
                "eur": prices.get("eur"),
                "eur_foil": prices.get("eur_foil"),
                "cardmarket_url": purchase.get("cardmarket"),
                "scryfall_id": carta.get("id"),
            })

        if datos.get("has_more"):
            url = datos.get("next_page")
            pagina += 1
            time.sleep(0.11)  # cortesía
        else:
            url = None

    print(f"Total de cartas: {len(cartas)}")
    return cartas

def guardar_en_csv(cartas, ruta_csv: Path):
    campos = [
        "name", "reprint", "set_name", "set", "collector_number",
        "rarity", "lang", "eur", "eur_foil", "cardmarket_url", "scryfall_id"
    ]
    ruta_csv.parent.mkdir(parents=True, exist_ok=True)
    with ruta_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos, delimiter=';')
        writer.writeheader()
        writer.writerows(cartas)
    print(f"Guardado en {ruta_csv}")

if __name__ == "__main__":
    # Variables de entorno (Actions) o input local
    codigo_set = (os.environ.get("SET_CODE") or "").strip().lower()
    include_tokens = (os.environ.get("INCLUDE_TOKENS") or "false").lower() == "true"
    unique = (os.environ.get("UNIQUE") or "prints").strip().lower()
    if unique not in ("prints", "cards", "art"):
        unique = "prints"

    if not codigo_set:
        codigo_set = input("Introduce el código del set (ej: otj, woe, mh3): ").strip().lower()

    if not codigo_set:
        raise SystemExit("⚠️ No se ha introducido ningún código de set.")

    cartas = descargar_coleccion(codigo_set, include_tokens=include_tokens, unique=unique)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    guardar_en_csv(cartas, OUT_DIR / f"coleccion_{codigo_set}_{unique}_{ts}.csv")
