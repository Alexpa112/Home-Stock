"""Configuracion y constantes compartidas por toda la aplicacion."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "stock.db"

CATEGORIES = ["Alimentacion", "Limpieza", "Higiene", "Bebidas", "Otros"]
DIAS_AVISO_DEFECTO = 30
