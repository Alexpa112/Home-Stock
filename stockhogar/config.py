"""Configuracion y constantes compartidas por toda la aplicacion."""
from pathlib import Path
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "stock.db"
CLAVES_PATH = DATA_DIR / "secret.json"

DIAS_AVISO_DEFECTO = 30

# Duracion de la sesion iniciada: al ser un dispositivo domestico compartido,
# el login es persistente para no tener que volver a autenticarse cada vez.
DIAS_SESION = 365

# Categorias de partida (se insertan una sola vez; a partir de ahi son
# totalmente editables desde la app). "Otros" es el comodin de respaldo y
# no se puede borrar. Se mantienen las 5 originales (por compatibilidad con
# productos ya creados con ellas) y se añaden las secciones habituales de
# un supermercado español, para que el catálogo de productos quede bien
# organizado.
CATEGORIAS_DEFECTO = [
    ("Alimentacion", "🍎"),
    ("Limpieza", "🧴"),
    ("Higiene", "🧼"),
    ("Bebidas", "🥤"),
    ("Otros", "🗂️"),
    ("Frutas y Verduras", "🥕"),
    ("Panadería y Bollería", "🥖"),
    ("Lácteos y Huevos", "🥚"),
    ("Carnes y Embutidos", "🥩"),
    ("Pescados y Mariscos", "🐟"),
    ("Congelados", "🧊"),
    ("Despensa", "🥫"),
    ("Cereales y Pasta", "🍝"),
    ("Snacks y Dulces", "🍫"),
    ("Bebé", "🍼"),
    ("Mascotas", "🐶"),
]
CATEGORIA_DEFECTO = "Otros"

# Colores sugeridos para las tarjetas de "stock" (espacios). Cada uno nuevo
# toma el siguiente color de la lista por turnos, para que se distingan a
# simple vista sin que el usuario tenga que elegir uno la primera vez.
PALETA_ESPACIOS = [
    "#B5551A",  # terracota (color de acento por defecto de la app)
    "#3E7C8C",  # azul petroleo
    "#7B6B9E",  # morado
    "#5B8C5A",  # verde
    "#C77B9E",  # rosa
    "#C9A227",  # mostaza
    "#4A6FA5",  # azul
    "#B5473F",  # rojo teja
]

# Catalogo de productos habituales de supermercado en España (investigado:
# leche, huevos, pan, aceite, pasta, arroz, frutas y verduras son los
# alimentos que compra la inmensa mayoria de hogares). Se siembra una vez en
# el historial de articulos como sugerencias listas para usar; el usuario
# puede editarlas, borrarlas o añadir las suyas sin límite.
# Formato: (nombre, categoria, icono, unidad, sub_descripcion)
CATALOGO_DEFECTO = [
    # Frutas y Verduras
    ("Plátanos", "Frutas y Verduras", "🍌", "kg", None),
    ("Manzanas", "Frutas y Verduras", "🍎", "kg", None),
    ("Naranjas", "Frutas y Verduras", "🍊", "kg", None),
    ("Limones", "Frutas y Verduras", "🍋", "kg", None),
    ("Fresas", "Frutas y Verduras", "🍓", "kg", None),
    ("Uvas", "Frutas y Verduras", "🍇", "kg", None),
    ("Aguacates", "Frutas y Verduras", "🥑", "ud", None),
    ("Tomates", "Frutas y Verduras", "🍅", "kg", None),
    ("Lechuga", "Frutas y Verduras", "🥬", "ud", None),
    ("Cebollas", "Frutas y Verduras", "🧅", "kg", None),
    ("Ajos", "Frutas y Verduras", "🧄", "ud", None),
    ("Patatas", "Frutas y Verduras", "🥔", "kg", None),
    ("Pimientos", "Frutas y Verduras", "🌶️", "kg", None),
    ("Zanahorias", "Frutas y Verduras", "🥕", "kg", None),
    ("Pepino", "Frutas y Verduras", "🥒", "ud", None),
    ("Brócoli", "Frutas y Verduras", "🥦", "ud", None),
    ("Champiñones", "Frutas y Verduras", "🍄", "kg", None),
    # Panadería y Bollería
    ("Pan de barra", "Panadería y Bollería", "🥖", "ud", None),
    ("Pan de molde", "Panadería y Bollería", "🍞", "ud", None),
    ("Croissants", "Panadería y Bollería", "🥐", "ud", None),
    ("Magdalenas", "Panadería y Bollería", "🧁", "ud", None),
    # Lácteos y Huevos
    ("Leche entera", "Lácteos y Huevos", "🥛", "l", "Brick 1L"),
    ("Leche desnatada", "Lácteos y Huevos", "🥛", "l", "Brick 1L"),
    ("Huevos", "Lácteos y Huevos", "🥚", "docena", None),
    ("Yogur natural", "Lácteos y Huevos", "🍮", "pack", None),
    ("Queso", "Lácteos y Huevos", "🧀", "ud", None),
    ("Mantequilla", "Lácteos y Huevos", "🧈", "ud", None),
    ("Nata para cocinar", "Lácteos y Huevos", "🥛", "ud", None),
    # Carnes y Embutidos
    ("Pechuga de pollo", "Carnes y Embutidos", "🍗", "kg", None),
    ("Carne picada", "Carnes y Embutidos", "🥩", "kg", None),
    ("Filetes de ternera", "Carnes y Embutidos", "🥩", "kg", None),
    ("Jamón cocido", "Carnes y Embutidos", "🥓", "ud", None),
    ("Jamón serrano", "Carnes y Embutidos", "🍖", "ud", None),
    ("Chorizo", "Carnes y Embutidos", "🌭", "ud", None),
    ("Salchichas", "Carnes y Embutidos", "🌭", "ud", None),
    ("Bacon", "Carnes y Embutidos", "🥓", "ud", None),
    # Pescados y Mariscos
    ("Salmón", "Pescados y Mariscos", "🐟", "kg", None),
    ("Merluza", "Pescados y Mariscos", "🐟", "kg", None),
    ("Atún en lata", "Pescados y Mariscos", "🥫", "pack", None),
    ("Gambas", "Pescados y Mariscos", "🦐", "kg", None),
    # Congelados
    ("Guisantes congelados", "Congelados", "🧊", "ud", None),
    ("Verdura congelada", "Congelados", "🧊", "ud", None),
    ("Pizza congelada", "Congelados", "🍕", "ud", None),
    ("Helado", "Congelados", "🍦", "ud", None),
    ("Croquetas congeladas", "Congelados", "🧊", "ud", None),
    # Despensa
    ("Aceite de oliva", "Despensa", "🫒", "ud", None),
    ("Arroz", "Despensa", "🍚", "kg", None),
    ("Lentejas", "Despensa", "🥫", "ud", None),
    ("Garbanzos", "Despensa", "🥫", "ud", None),
    ("Tomate frito", "Despensa", "🥫", "ud", None),
    ("Sal", "Despensa", "🧂", "ud", None),
    ("Azúcar", "Despensa", "🧂", "kg", None),
    ("Harina", "Despensa", "🌾", "kg", None),
    ("Miel", "Despensa", "🍯", "ud", None),
    ("Vinagre", "Despensa", "🍶", "ud", None),
    # Cereales y Pasta
    ("Espaguetis", "Cereales y Pasta", "🍜", "ud", None),
    ("Macarrones", "Cereales y Pasta", "🍜", "ud", None),
    ("Cereales de desayuno", "Cereales y Pasta", "🥣", "ud", None),
    ("Copos de avena", "Cereales y Pasta", "🥣", "ud", None),
    ("Galletas", "Cereales y Pasta", "🍪", "ud", None),
    # Snacks y Dulces
    ("Patatas fritas", "Snacks y Dulces", "🍟", "ud", None),
    ("Palomitas", "Snacks y Dulces", "🍿", "ud", None),
    ("Chocolate", "Snacks y Dulces", "🍫", "ud", None),
    ("Frutos secos", "Snacks y Dulces", "🥜", "ud", None),
    ("Caramelos", "Snacks y Dulces", "🍬", "ud", None),
    # Bebidas
    ("Agua mineral", "Bebidas", "💧", "pack", None),
    ("Refrescos de cola", "Bebidas", "🥤", "ud", None),
    ("Zumo de naranja", "Bebidas", "🧃", "ud", None),
    ("Cerveza", "Bebidas", "🍺", "pack", None),
    ("Vino", "Bebidas", "🍷", "ud", None),
    ("Café", "Bebidas", "☕", "ud", None),
    ("Té", "Bebidas", "🍵", "ud", None),
    # Limpieza
    ("Detergente lavadora", "Limpieza", "🧴", "ud", None),
    ("Suavizante", "Limpieza", "🧴", "ud", None),
    ("Lejía", "Limpieza", "🧴", "ud", None),
    ("Limpiacristales", "Limpieza", "🧴", "ud", None),
    ("Papel de cocina", "Limpieza", "🧻", "ud", None),
    ("Bolsas de basura", "Limpieza", "🗑️", "pack", None),
    ("Estropajo", "Limpieza", "🧽", "ud", None),
    ("Friegasuelos", "Limpieza", "🪣", "ud", None),
    ("Lavavajillas", "Limpieza", "🧴", "ud", None),
    # Higiene
    ("Papel higiénico", "Higiene", "🧻", "pack", None),
    ("Gel de ducha", "Higiene", "🧴", "ud", None),
    ("Champú", "Higiene", "🧴", "ud", None),
    ("Pasta de dientes", "Higiene", "🪥", "ud", None),
    ("Desodorante", "Higiene", "🧴", "ud", None),
    ("Cepillo de dientes", "Higiene", "🪥", "ud", None),
    # Bebé
    ("Pañales", "Bebé", "🍼", "pack", None),
    ("Toallitas húmedas", "Bebé", "🍼", "pack", None),
    ("Leche de fórmula", "Bebé", "🍼", "ud", None),
    ("Potitos", "Bebé", "🍼", "ud", None),
    # Mascotas
    ("Pienso para perro", "Mascotas", "🐶", "kg", None),
    ("Pienso para gato", "Mascotas", "🐱", "kg", None),
    ("Arena para gatos", "Mascotas", "🐱", "ud", None),
    ("Snacks para mascotas", "Mascotas", "🦴", "ud", None),
]

# Configuración OAuth para Google y Apple
# Obtén estas credenciales en:
# - Google: https://console.cloud.google.com/
# - Apple: https://developer.apple.com/
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID", "")
APPLE_CLIENT_SECRET = os.getenv("APPLE_CLIENT_SECRET", "")
APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID", "")

# Configuración de Email (para invitaciones a compartir listas)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@homestock.local")
APP_URL = os.getenv("APP_URL", "http://localhost:5000")
