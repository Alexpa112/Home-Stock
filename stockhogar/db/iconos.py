"""Migracion de los emojis antiguos de iconos a nombres de icono Lucide."""

# Mapeo de los emojis usados antes de la migración a iconos SVG (Lucide) a su
# nombre de icono equivalente. Debe coincidir con
# stockhogar/static/icons/mapeo-emoji-legacy.js (mismo propósito, lado JS).
MAPEO_EMOJI_A_ICONO_LUCIDE = {
    "🍎": "apple", "🍏": "apple", "🍌": "banana", "🍊": "citrus", "🍋": "citrus",
    "🍉": "cherry", "🍇": "grape", "🍓": "cherry", "🫐": "cherry", "🍒": "cherry",
    "🍑": "ice-cream", "🥭": "ice-cream", "🍍": "ice-cream", "🥝": "ice-cream",
    "🥑": "salad", "🍅": "carrot", "🥦": "salad", "🥬": "salad", "🥒": "salad",
    "🌶️": "carrot", "🫑": "carrot", "🌽": "carrot", "🥕": "carrot",
    "🧄": "sprout", "🧅": "sprout", "🥔": "sprout", "🍠": "sprout",
    "🥐": "croissant", "🥖": "wheat", "🍞": "wheat", "🧀": "wheat",
    "🥚": "egg", "🥩": "beef", "🍗": "drumstick", "🍖": "drumstick",
    "🥓": "sandwich", "🌭": "sandwich", "🍔": "sandwich", "🍕": "pizza",
    "🐟": "fish", "🦐": "fish-symbol", "🍱": "soup", "🍚": "soup", "🍜": "soup",
    "🥣": "container", "🥫": "container", "🫙": "package-2",
    "🍫": "candy-cane", "🍬": "candy", "🍩": "donut", "🍪": "cookie",
    "🎂": "cake", "🍯": "cake-slice", "🥜": "nut", "🧈": "wheat", "🧂": "container",
    "🫒": "droplet", "☕": "coffee", "🍵": "coffee", "🧃": "cup-soda",
    "🥤": "cup-soda", "🧋": "cup-soda", "🍶": "wine", "🍾": "wine",
    "🍷": "wine", "🍺": "beer", "🥛": "milk", "💧": "droplet",
    "🧴": "spray-can", "🧼": "spray-can", "🧽": "waves-ladder",
    "🪥": "shower-head", "🦷": "shower-head", "🧻": "toilet", "🧺": "waves-ladder",
    "🪣": "toilet", "🚽": "toilet", "🛁": "shower-head", "🚿": "shower-head",
    "🕯️": "flame", "🔥": "flame", "🧯": "flame-kindling",
    "💊": "pill", "🩹": "bandage", "🩺": "stethoscope", "🌡️": "thermometer",
    "👶": "baby", "🍼": "baby", "🧸": "toy-brick", "🐶": "dog", "🐱": "cat",
    "🐹": "paw-print", "🦴": "paw-print", "🐾": "paw-print",
    "👕": "shirt", "👖": "footprints", "🧦": "footprints", "🧣": "footprints",
    "🧤": "footprints", "👗": "shirt", "👟": "footprints", "🧥": "shirt",
    "🔧": "wrench", "🔩": "hammer", "🔨": "hammer", "🪛": "hammer", "🪜": "drill",
    "🖨️": "printer", "📱": "smartphone", "💻": "laptop", "🔌": "plug",
    "🔋": "battery", "💡": "lightbulb", "📷": "camera", "🎧": "headphones",
    "⌚": "watch", "🔦": "flashlight", "🗝️": "key", "📓": "notebook",
    "✏️": "pencil", "🖊️": "pencil", "📎": "paperclip", "✂️": "scissors",
    "📚": "book", "🌱": "sprout", "🪴": "flower", "🌻": "flower", "🍀": "clover",
    "🪵": "trees", "⚽": "volleyball", "🏀": "volleyball", "🚴": "bike",
    "🎮": "gamepad-2", "🎲": "dices", "🧩": "puzzle", "🚗": "car",
    "⛽": "fuel", "🎁": "gift", "🧳": "luggage", "🎈": "party-popper",
    "📦": "h-archive-box", "🛒": "h-shopping-cart", "🗂️": "h-folder",
    "🏠": "h-home", "📋": "h-clipboard-document-list",
    # Emojis adicionales usados en config.py (CATEGORIAS_DEFECTO/CATALOGO_DEFECTO)
    # que no estaban en el selector original de 144 iconos.
    "🍄": "salad", "🍆": "salad", "🍐": "apple", "🍈": "cherry", "🎃": "carrot",
    "🌰": "nut", "🫛": "salad", "🧁": "cake-slice", "🍮": "cake-slice",
    "🦃": "drumstick", "🦑": "fish-symbol", "🦪": "fish-symbol", "🐙": "fish-symbol",
    "🧊": "container", "🍦": "ice-cream", "🍟": "sandwich", "🥟": "soup",
    "🍰": "cake-slice", "🌾": "wheat", "🌿": "sprout", "🍿": "candy",
    "🍘": "cookie", "🥃": "wine", "🪒": "spray-can", "🍝": "soup",
    "🥞": "wheat", "🫓": "wheat", "🗑️": "h-trash", "😷": "stethoscope",
    # Emojis de las categorías Bazar y Ferretería.
    "🪚": "hammer", "⚙️": "settings", "🧱": "package-2", "🪝": "anchor",
    "🧰": "wrench", "🪓": "axe", "🔗": "link", "🚰": "droplet",
    "🪤": "target", "🎨": "palette", "🖌️": "paintbrush", "🧵": "scissors",
    "🪡": "scissors", "🧷": "pin", "📏": "ruler", "🪟": "app-window",
    "🖼️": "image", "🎀": "gift", "🔑": "key", "🧲": "magnet",
    "🪒": "spray-can", "🕸️": "waves-ladder", "🧨": "flame",
    "🍽️": "utensils", "☂️": "umbrella", "🔪": "utensils-crossed", "🥽": "glasses",
    "🥥": "nut",
}


# Iconos que en un primer momento se asignaron a Lucide y luego se
# reasignaron a Heroicons (nombres "h-...") por preferencia visual.
RENOMBRES_ICONO = {
    "folder": "h-folder",
    "home": "h-home",
    "clipboard-list": "h-clipboard-document-list",
    "package": "h-archive-box",
    "shopping-cart": "h-shopping-cart",
    "trash-2": "h-trash",
}


def migrar_iconos_emoji_a_lucide(db):
    """Traduce los emojis guardados en columnas `icono` a su nombre de icono
    Lucide equivalente (ver MAPEO_EMOJI_A_ICONO_LUCIDE). Idempotente: tras la
    primera ejecución ya no quedan filas con emoji, por lo que reejecutarla en
    cada arranque es un no-op seguro."""
    tablas_con_icono = [
        "categorias", "productos", "listas",
        "historial_articulos", "articulos_lista",
    ]
    for tabla in tablas_con_icono:
        columnas = [f["name"] for f in db.execute(f"PRAGMA table_info({tabla})").fetchall()]
        if "icono" not in columnas:
            continue
        for emoji, nombre_lucide in MAPEO_EMOJI_A_ICONO_LUCIDE.items():
            db.execute(
                f"UPDATE {tabla} SET icono = ? WHERE icono = ?",  # nosec B608 - tabla viene de tablas_con_icono, literal fijo
                (nombre_lucide, emoji),
            )
        # Renombrados posteriores: algunos conceptos "hogar/UI" pasaron de
        # Lucide a Heroicons (ver catalogo-iconos.js), así que filas ya
        # migradas al nombre Lucide antiguo se reasignan al nuevo nombre.
        for nombre_viejo, nombre_nuevo in RENOMBRES_ICONO.items():
            db.execute(
                f"UPDATE {tabla} SET icono = ? WHERE icono = ?",  # nosec B608 - tabla viene de tablas_con_icono, literal fijo
                (nombre_nuevo, nombre_viejo),
            )
