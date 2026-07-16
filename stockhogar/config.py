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

# Directorio de logs de la aplicacion (montado como volumen en docker-compose.yml
# para que sobrevivan a la reconstruccion del contenedor). El Panel de Gestion
# del Servidor (proyecto independiente) lee de aqui para mostrar los logs en vivo.
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
LOG_FILE_PATH = LOGS_DIR / "stockhogar.log"

DIAS_AVISO_DEFECTO = 30

# Duracion de la sesion iniciada: al ser un dispositivo domestico compartido,
# el login es persistente para no tener que volver a autenticarse cada vez.
DIAS_SESION = 365

# La cookie de sesion solo se marca "Secure" (exigir HTTPS) si APP_URL usa https.
# En local (http://localhost) se deja sin marcar para poder seguir probando sin TLS.
USAR_COOKIE_SEGURA = os.getenv("APP_URL", "http://localhost:5000").startswith("https://")

# Categorias de partida (se insertan una sola vez; a partir de ahi son
# totalmente editables desde la app). "Otros" es el comodin de respaldo y
# no se puede borrar. Se mantienen las 5 originales (por compatibilidad con
# productos ya creados con ellas) y se añaden las secciones habituales de
# un supermercado español, para que el catálogo de productos quede bien
# organizado.
CATEGORIAS_DEFECTO = [
    ("Alimentación", "🍎"),
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
    ("Hogar", "🏠"),
    ("Farmacia y Botiquín", "💊"),
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
    ("Calabacín", "Frutas y Verduras", "🥒", "kg", None),
    ("Berenjena", "Frutas y Verduras", "🍆", "kg", None),
    ("Espinacas", "Frutas y Verduras", "🥬", "ud", None),
    ("Peras", "Frutas y Verduras", "🍐", "kg", None),
    ("Melocotones", "Frutas y Verduras", "🍑", "kg", None),
    ("Sandía", "Frutas y Verduras", "🍉", "ud", None),
    ("Melón", "Frutas y Verduras", "🍈", "ud", None),
    ("Piña", "Frutas y Verduras", "🍍", "ud", None),
    ("Kiwis", "Frutas y Verduras", "🥝", "kg", None),
    ("Coliflor", "Frutas y Verduras", "🥦", "ud", None),
    ("Calabaza", "Frutas y Verduras", "🎃", "kg", None),
    ("Puerros", "Frutas y Verduras", "🥬", "ud", None),
    ("Apio", "Frutas y Verduras", "🥬", "ud", None),
    ("Mandarinas", "Frutas y Verduras", "🍊", "kg", None),
    ("Cerezas", "Frutas y Verduras", "🍒", "kg", None),
    ("Ciruelas", "Frutas y Verduras", "🍑", "kg", None),
    ("Granada", "Frutas y Verduras", "🌰", "ud", None),
    ("Higos", "Frutas y Verduras", "🌰", "kg", None),
    ("Judías verdes", "Frutas y Verduras", "🫛", "kg", None),
    ("Espárragos", "Frutas y Verduras", "🌱", "ud", None),
    ("Alcachofas", "Frutas y Verduras", "🌱", "kg", None),
    ("Rábanos", "Frutas y Verduras", "🥕", "ud", None),
    ("Remolacha", "Frutas y Verduras", "🥕", "kg", None),
    # Panadería y Bollería
    ("Pan de barra", "Panadería y Bollería", "🥖", "ud", None),
    ("Pan de molde", "Panadería y Bollería", "🍞", "ud", None),
    ("Croissants", "Panadería y Bollería", "🥐", "ud", None),
    ("Magdalenas", "Panadería y Bollería", "🧁", "ud", None),
    ("Pan integral", "Panadería y Bollería", "🍞", "ud", None),
    ("Bollos de leche", "Panadería y Bollería", "🥐", "ud", None),
    ("Donuts", "Panadería y Bollería", "🍩", "ud", None),
    ("Tortitas", "Panadería y Bollería", "🥞", "pack", None),
    ("Empanadillas", "Panadería y Bollería", "🥟", "pack", None),
    ("Pan de hamburguesa", "Panadería y Bollería", "🍔", "pack", None),
    ("Pan de pita", "Panadería y Bollería", "🫓", "pack", None),
    ("Tortillas de trigo", "Panadería y Bollería", "🫓", "pack", None),
    ("Bizcocho", "Panadería y Bollería", "🍰", "ud", None),
    ("Ensaimada", "Panadería y Bollería", "🥐", "ud", None),
    ("Palmeras de chocolate", "Panadería y Bollería", "🥐", "ud", None),
    ("Colines", "Panadería y Bollería", "🥖", "pack", None),
    # Lácteos y Huevos
    ("Leche entera", "Lácteos y Huevos", "🥛", "l", "Brick 1L"),
    ("Leche desnatada", "Lácteos y Huevos", "🥛", "l", "Brick 1L"),
    ("Huevos", "Lácteos y Huevos", "🥚", "docena", None),
    ("Yogur natural", "Lácteos y Huevos", "🍮", "pack", None),
    ("Queso", "Lácteos y Huevos", "🧀", "ud", None),
    ("Mantequilla", "Lácteos y Huevos", "🧈", "ud", None),
    ("Nata para cocinar", "Lácteos y Huevos", "🥛", "ud", None),
    ("Leche semidesnatada", "Lácteos y Huevos", "🥛", "l", "Brick 1L"),
    ("Yogur de sabores", "Lácteos y Huevos", "🍮", "pack", None),
    ("Queso rallado", "Lácteos y Huevos", "🧀", "ud", None),
    ("Queso fresco", "Lácteos y Huevos", "🧀", "ud", None),
    ("Actimel", "Lácteos y Huevos", "🍮", "pack", None),
    ("Cuajada", "Lácteos y Huevos", "🍮", "ud", None),
    ("Leche sin lactosa", "Lácteos y Huevos", "🥛", "l", "Brick 1L"),
    ("Mozzarella", "Lácteos y Huevos", "🧀", "ud", None),
    ("Queso parmesano", "Lácteos y Huevos", "🧀", "ud", None),
    ("Requesón", "Lácteos y Huevos", "🧀", "ud", None),
    ("Flan", "Lácteos y Huevos", "🍮", "pack", None),
    ("Natillas", "Lácteos y Huevos", "🍮", "pack", None),
    ("Nata montada", "Lácteos y Huevos", "🥛", "ud", None),
    # Carnes y Embutidos
    ("Pechuga de pollo", "Carnes y Embutidos", "🍗", "kg", None),
    ("Carne picada", "Carnes y Embutidos", "🥩", "kg", None),
    ("Filetes de ternera", "Carnes y Embutidos", "🥩", "kg", None),
    ("Jamón cocido", "Carnes y Embutidos", "🥓", "ud", None),
    ("Jamón serrano", "Carnes y Embutidos", "🍖", "ud", None),
    ("Chorizo", "Carnes y Embutidos", "🌭", "ud", None),
    ("Salchichas", "Carnes y Embutidos", "🌭", "ud", None),
    ("Bacon", "Carnes y Embutidos", "🥓", "ud", None),
    ("Muslos de pollo", "Carnes y Embutidos", "🍗", "kg", None),
    ("Alitas de pollo", "Carnes y Embutidos", "🍗", "kg", None),
    ("Lomo de cerdo", "Carnes y Embutidos", "🥩", "kg", None),
    ("Costillas", "Carnes y Embutidos", "🍖", "kg", None),
    ("Salchichón", "Carnes y Embutidos", "🍖", "ud", None),
    ("Mortadela", "Carnes y Embutidos", "🍖", "ud", None),
    ("Pavo en lonchas", "Carnes y Embutidos", "🦃", "ud", None),
    ("Pollo entero", "Carnes y Embutidos", "🍗", "kg", None),
    ("Solomillo de cerdo", "Carnes y Embutidos", "🥩", "kg", None),
    ("Morcilla", "Carnes y Embutidos", "🍖", "ud", None),
    ("Sobrasada", "Carnes y Embutidos", "🍖", "ud", None),
    ("Panceta", "Carnes y Embutidos", "🥓", "kg", None),
    ("Salami", "Carnes y Embutidos", "🍖", "ud", None),
    # Pescados y Mariscos
    ("Salmón", "Pescados y Mariscos", "🐟", "kg", None),
    ("Merluza", "Pescados y Mariscos", "🐟", "kg", None),
    ("Atún en lata", "Pescados y Mariscos", "🥫", "pack", None),
    ("Gambas", "Pescados y Mariscos", "🦐", "kg", None),
    ("Bacalao", "Pescados y Mariscos", "🐟", "kg", None),
    ("Sardinas", "Pescados y Mariscos", "🐟", "kg", None),
    ("Boquerones", "Pescados y Mariscos", "🐟", "kg", None),
    ("Calamares", "Pescados y Mariscos", "🦑", "kg", None),
    ("Mejillones", "Pescados y Mariscos", "🦪", "kg", None),
    ("Pulpo", "Pescados y Mariscos", "🐙", "kg", None),
    ("Lenguado", "Pescados y Mariscos", "🐟", "kg", None),
    ("Dorada", "Pescados y Mariscos", "🐟", "kg", None),
    ("Sepia", "Pescados y Mariscos", "🦑", "kg", None),
    ("Almejas", "Pescados y Mariscos", "🦪", "kg", None),
    ("Berberechos en lata", "Pescados y Mariscos", "🥫", "ud", None),
    ("Mejillones en lata", "Pescados y Mariscos", "🥫", "ud", None),
    # Congelados
    ("Guisantes congelados", "Congelados", "🧊", "ud", None),
    ("Verdura congelada", "Congelados", "🧊", "ud", None),
    ("Pizza congelada", "Congelados", "🍕", "ud", None),
    ("Helado", "Congelados", "🍦", "ud", None),
    ("Croquetas congeladas", "Congelados", "🧊", "ud", None),
    ("Patatas fritas congeladas", "Congelados", "🍟", "ud", None),
    ("Palitos de pescado", "Congelados", "🐟", "ud", None),
    ("Rebozados congelados", "Congelados", "🧊", "ud", None),
    ("Empanadillas congeladas", "Congelados", "🥟", "ud", None),
    ("Gambas congeladas", "Congelados", "🦐", "kg", None),
    ("Masa de hojaldre", "Congelados", "🧊", "ud", None),
    ("Langostinos congelados", "Congelados", "🦐", "kg", None),
    ("Tarta helada", "Congelados", "🍰", "ud", None),
    ("Salteado de verduras congelado", "Congelados", "🧊", "ud", None),
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
    ("Aceite de girasol", "Despensa", "🫙", "ud", None),
    ("Alubias", "Despensa", "🥫", "ud", None),
    ("Caldo en pastillas", "Despensa", "🧂", "ud", None),
    ("Especias variadas", "Despensa", "🌿", "ud", None),
    ("Pimentón", "Despensa", "🌶️", "ud", None),
    ("Mayonesa", "Despensa", "🥫", "ud", None),
    ("Ketchup", "Despensa", "🥫", "ud", None),
    ("Mostaza", "Despensa", "🥫", "ud", None),
    ("Levadura", "Despensa", "🌾", "ud", None),
    ("Maíz en lata", "Despensa", "🌽", "ud", None),
    ("Aceitunas", "Despensa", "🫒", "ud", None),
    ("Pepinillos", "Despensa", "🥒", "ud", None),
    ("Salsa barbacoa", "Despensa", "🥫", "ud", None),
    ("Alioli", "Despensa", "🥫", "ud", None),
    ("Salsa de soja", "Despensa", "🥫", "ud", None),
    ("Cacao en polvo", "Despensa", "🍫", "ud", None),
    ("Gelatina", "Despensa", "🍮", "ud", None),
    ("Pasta de tomate", "Despensa", "🥫", "ud", None),
    # Cereales y Pasta
    ("Espaguetis", "Cereales y Pasta", "🍜", "ud", None),
    ("Macarrones", "Cereales y Pasta", "🍜", "ud", None),
    ("Cereales de desayuno", "Cereales y Pasta", "🥣", "ud", None),
    ("Copos de avena", "Cereales y Pasta", "🥣", "ud", None),
    ("Galletas", "Cereales y Pasta", "🍪", "ud", None),
    ("Fideos", "Cereales y Pasta", "🍜", "ud", None),
    ("Arroz integral", "Cereales y Pasta", "🍚", "kg", None),
    ("Quinoa", "Cereales y Pasta", "🍚", "ud", None),
    ("Muesli", "Cereales y Pasta", "🥣", "ud", None),
    ("Tostadas", "Cereales y Pasta", "🍞", "ud", None),
    ("Arroz bomba", "Cereales y Pasta", "🍚", "kg", None),
    ("Cuscús", "Cereales y Pasta", "🍚", "ud", None),
    ("Pasta integral", "Cereales y Pasta", "🍜", "ud", None),
    ("Lasaña (placas)", "Cereales y Pasta", "🍝", "ud", None),
    ("Canelones (placas)", "Cereales y Pasta", "🍝", "ud", None),
    # Snacks y Dulces
    ("Patatas fritas", "Snacks y Dulces", "🍟", "ud", None),
    ("Palomitas", "Snacks y Dulces", "🍿", "ud", None),
    ("Chocolate", "Snacks y Dulces", "🍫", "ud", None),
    ("Frutos secos", "Snacks y Dulces", "🥜", "ud", None),
    ("Caramelos", "Snacks y Dulces", "🍬", "ud", None),
    ("Gominolas", "Snacks y Dulces", "🍬", "ud", None),
    ("Barritas de cereales", "Snacks y Dulces", "🍫", "ud", None),
    ("Turrón", "Snacks y Dulces", "🍫", "ud", None),
    ("Nachos", "Snacks y Dulces", "🌽", "ud", None),
    ("Gusanitos", "Snacks y Dulces", "🍟", "ud", None),
    ("Aceitunas rellenas", "Snacks y Dulces", "🫒", "ud", None),
    ("Regaliz", "Snacks y Dulces", "🍬", "ud", None),
    ("Tortitas de arroz", "Snacks y Dulces", "🍘", "ud", None),
    ("Almendras", "Snacks y Dulces", "🥜", "ud", None),
    ("Pistachos", "Snacks y Dulces", "🥜", "ud", None),
    # Bebidas
    ("Agua mineral", "Bebidas", "💧", "pack", None),
    ("Refrescos de cola", "Bebidas", "🥤", "ud", None),
    ("Zumo de naranja", "Bebidas", "🧃", "ud", None),
    ("Cerveza", "Bebidas", "🍺", "pack", None),
    ("Vino", "Bebidas", "🍷", "ud", None),
    ("Café", "Bebidas", "☕", "ud", None),
    ("Té", "Bebidas", "🍵", "ud", None),
    ("Refresco de limón", "Bebidas", "🥤", "ud", None),
    ("Bebida isotónica", "Bebidas", "🥤", "ud", None),
    ("Cava", "Bebidas", "🍾", "ud", None),
    ("Zumo de piña", "Bebidas", "🧃", "ud", None),
    ("Batido de chocolate", "Bebidas", "🥤", "ud", None),
    ("Cola cao", "Bebidas", "🍫", "ud", None),
    ("Agua con gas", "Bebidas", "💧", "pack", None),
    ("Cápsulas de café", "Bebidas", "☕", "pack", None),
    ("Leche de avena", "Bebidas", "🥛", "l", None),
    ("Leche de almendra", "Bebidas", "🥛", "l", None),
    ("Horchata", "Bebidas", "🥤", "ud", None),
    ("Vermut", "Bebidas", "🍷", "ud", None),
    ("Sidra", "Bebidas", "🍾", "ud", None),
    ("Whisky", "Bebidas", "🥃", "ud", None),
    ("Ron", "Bebidas", "🥃", "ud", None),
    ("Ginebra", "Bebidas", "🥃", "ud", None),
    ("Infusiones", "Bebidas", "🍵", "pack", None),
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
    ("Guantes de goma", "Limpieza", "🧤", "ud", None),
    ("Ambientador", "Limpieza", "🧴", "ud", None),
    ("Quitagrasas", "Limpieza", "🧴", "ud", None),
    ("Papel film", "Limpieza", "🧻", "ud", None),
    ("Papel de aluminio", "Limpieza", "🧻", "ud", None),
    ("Bayetas", "Limpieza", "🧽", "pack", None),
    ("Insecticida", "Limpieza", "🧴", "ud", None),
    ("Desatascador líquido", "Limpieza", "🧴", "ud", None),
    ("Bolsas de congelación", "Limpieza", "🧊", "pack", None),
    ("Vinagre de limpieza", "Limpieza", "🧴", "ud", None),
    ("Pastillas lavavajillas", "Limpieza", "🧴", "pack", None),
    # Higiene
    ("Papel higiénico", "Higiene", "🧻", "pack", None),
    ("Gel de ducha", "Higiene", "🧴", "ud", None),
    ("Champú", "Higiene", "🧴", "ud", None),
    ("Pasta de dientes", "Higiene", "🪥", "ud", None),
    ("Desodorante", "Higiene", "🧴", "ud", None),
    ("Cepillo de dientes", "Higiene", "🪥", "ud", None),
    ("Enjuague bucal", "Higiene", "🧴", "ud", None),
    ("Crema hidratante", "Higiene", "🧴", "ud", None),
    ("Cuchillas de afeitar", "Higiene", "🪒", "ud", None),
    ("Compresas", "Higiene", "🧴", "pack", None),
    ("Tampones", "Higiene", "🧴", "pack", None),
    ("Toallitas desmaquillantes", "Higiene", "🧴", "pack", None),
    ("Colonia", "Higiene", "🧴", "ud", None),
    ("Protector solar", "Higiene", "🧴", "ud", None),
    ("Crema de manos", "Higiene", "🧴", "ud", None),
    ("Hilo dental", "Higiene", "🪥", "ud", None),
    ("Algodón", "Higiene", "🧴", "ud", None),
    ("Bastoncillos", "Higiene", "🧴", "pack", None),
    ("Gel antibacterial", "Higiene", "🧴", "ud", None),
    ("Maquinillas desechables", "Higiene", "🪒", "pack", None),
    # Bebé
    ("Pañales", "Bebé", "🍼", "pack", None),
    ("Toallitas húmedas", "Bebé", "🍼", "pack", None),
    ("Leche de fórmula", "Bebé", "🍼", "ud", None),
    ("Potitos", "Bebé", "🍼", "ud", None),
    ("Papilla de cereales", "Bebé", "🍼", "ud", None),
    ("Crema para el culito", "Bebé", "🍼", "ud", None),
    ("Toallitas de baño", "Bebé", "🍼", "pack", None),
    ("Biberones", "Bebé", "🍼", "ud", None),
    ("Chupetes", "Bebé", "🍼", "ud", None),
    ("Potitos de fruta", "Bebé", "🍼", "ud", None),
    ("Colonia para bebé", "Bebé", "🍼", "ud", None),
    # Mascotas
    ("Pienso para perro", "Mascotas", "🐶", "kg", None),
    ("Pienso para gato", "Mascotas", "🐱", "kg", None),
    ("Arena para gatos", "Mascotas", "🐱", "ud", None),
    ("Snacks para mascotas", "Mascotas", "🦴", "ud", None),
    ("Comida húmeda para gato", "Mascotas", "🐱", "ud", None),
    ("Comida húmeda para perro", "Mascotas", "🐶", "ud", None),
    ("Bolsas para excrementos", "Mascotas", "🐶", "pack", None),
    ("Snacks dentales para perro", "Mascotas", "🦴", "ud", None),
    ("Champú para mascotas", "Mascotas", "🐶", "ud", None),
    ("Arena aglomerante", "Mascotas", "🐱", "ud", None),
    # Hogar
    ("Bombillas", "Hogar", "💡", "ud", None),
    ("Pilas AA", "Hogar", "🔋", "pack", None),
    ("Pilas AAA", "Hogar", "🔋", "pack", None),
    ("Velas", "Hogar", "🕯️", "ud", None),
    ("Cerillas", "Hogar", "🔥", "ud", None),
    ("Mechero", "Hogar", "🔥", "ud", None),
    ("Pinzas de tender", "Hogar", "🧺", "pack", None),
    ("Bolsas de vacío", "Hogar", "🧺", "pack", None),
    ("Ambientador eléctrico (recambio)", "Hogar", "🏠", "ud", None),
    ("Cinta adhesiva", "Hogar", "🏠", "ud", None),
    # Farmacia y Botiquín
    ("Paracetamol", "Farmacia y Botiquín", "💊", "ud", None),
    ("Ibuprofeno", "Farmacia y Botiquín", "💊", "ud", None),
    ("Tiritas", "Farmacia y Botiquín", "🩹", "pack", None),
    ("Gasas estériles", "Farmacia y Botiquín", "🩹", "pack", None),
    ("Alcohol antiséptico", "Farmacia y Botiquín", "💊", "ud", None),
    ("Agua oxigenada", "Farmacia y Botiquín", "💊", "ud", None),
    ("Termómetro", "Farmacia y Botiquín", "🌡️", "ud", None),
    ("Suero fisiológico", "Farmacia y Botiquín", "💊", "ud", None),
    ("Mascarillas", "Farmacia y Botiquín", "😷", "pack", None),
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
