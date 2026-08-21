#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fusiona las claves nuevas de traduccion (HTML modales, app.js, login, backend)
en stockhogar/translations.json para los 7 idiomas soportados."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
TRANSLATIONS_FILE = BASE / "stockhogar" / "translations.json"

# clave: {es, gl, en, pt, fr, it, de}
NUEVAS = {
    # --- Modal Ajustes ---
    "mi_perfil": {"es": "Mi Perfil", "gl": "O meu perfil", "en": "My Profile", "pt": "Meu Perfil", "fr": "Mon profil", "it": "Il mio profilo", "de": "Mein Profil"},
    "nueva_contrasena_opcional": {"es": "Nueva contraseña (dejar en blanco para no cambiar)", "gl": "Novo contrasinal (deixar en branco para non cambiar)", "en": "New password (leave blank to keep current)", "pt": "Nova senha (deixe em branco para não alterar)", "fr": "Nouveau mot de passe (laisser vide pour ne pas changer)", "it": "Nuova password (lascia vuoto per non cambiare)", "de": "Neues Passwort (leer lassen, um es nicht zu ändern)"},
    "minimo_4_caracteres": {"es": "Mínimo 4 caracteres", "gl": "Mínimo 4 caracteres", "en": "Minimum 4 characters", "pt": "Mínimo de 4 caracteres", "fr": "Minimum 4 caractères", "it": "Minimo 4 caratteri", "de": "Mindestens 4 Zeichen"},
    "ajustes": {"es": "Ajustes", "gl": "Axustes", "en": "Settings", "pt": "Configurações", "fr": "Paramètres", "it": "Impostazioni", "de": "Einstellungen"},
    "tema": {"es": "Tema", "gl": "Tema", "en": "Theme", "pt": "Tema", "fr": "Thème", "it": "Tema", "de": "Design"},
    "tema_sistema": {"es": "Como el dispositivo", "gl": "Como o dispositivo", "en": "Same as device", "pt": "Como o dispositivo", "fr": "Comme l'appareil", "it": "Come il dispositivo", "de": "Wie das Gerät"},
    "tema_claro": {"es": "Claro", "gl": "Claro", "en": "Light", "pt": "Claro", "fr": "Clair", "it": "Chiaro", "de": "Hell"},
    "tema_oscuro": {"es": "Oscuro", "gl": "Escuro", "en": "Dark", "pt": "Escuro", "fr": "Sombre", "it": "Scuro", "de": "Dunkel"},
    "instalar_app": {"es": "Instalar app", "gl": "Instalar app", "en": "Install app", "pt": "Instalar app", "fr": "Installer l'application", "it": "Installa app", "de": "App installieren"},
    "instalar_app_texto": {"es": "Instala esta app en tu dispositivo para acceder más rápido y usarla sin conexión.", "gl": "Instala esta app no teu dispositivo para acceder máis rápido e usala sen conexión.", "en": "Install this app on your device for quicker access and offline use.", "pt": "Instale este app no seu dispositivo para acesso mais rápido e uso offline.", "fr": "Installez cette application sur votre appareil pour un accès plus rapide et une utilisation hors ligne.", "it": "Installa questa app sul tuo dispositivo per un accesso più rapido e l'uso offline.", "de": "Installiere diese App auf deinem Gerät für schnelleren Zugriff und Offline-Nutzung."},

    # --- Modal Categorías ---
    "categorias": {"es": "Categorías", "gl": "Categorías", "en": "Categories", "pt": "Categorias", "fr": "Catégories", "it": "Categorie", "de": "Kategorien"},
    "nueva_categoria": {"es": "Nueva categoría", "gl": "Nova categoría", "en": "New category", "pt": "Nova categoria", "fr": "Nouvelle catégorie", "it": "Nuova categoria", "de": "Neue Kategorie"},
    "icono_dospuntos": {"es": "Icono:", "gl": "Icona:", "en": "Icon:", "pt": "Ícone:", "fr": "Icône :", "it": "Icona:", "de": "Symbol:"},
    "ayuda_borrar_categoria": {"es": "Toca la ✕ de una categoría para borrarla (solo si no la usa ningún producto).", "gl": "Toca a ✕ dunha categoría para borrala (só se non a usa ningún produto).", "en": "Tap the ✕ on a category to delete it (only if no product uses it).", "pt": "Toque no ✕ de uma categoria para excluí-la (somente se nenhum produto a usar).", "fr": "Touchez le ✕ d'une catégorie pour la supprimer (uniquement si aucun produit ne l'utilise).", "it": "Tocca la ✕ di una categoria per eliminarla (solo se nessun prodotto la utilizza).", "de": "Tippe auf das ✕ einer Kategorie, um sie zu löschen (nur wenn kein Produkt sie verwendet)."},
    "listo": {"es": "Listo", "gl": "Feito", "en": "Done", "pt": "Concluído", "fr": "Terminé", "it": "Fatto", "de": "Fertig"},

    # --- Selector de iconos ---
    "seleccionar_icono": {"es": "Seleccionar icono", "gl": "Seleccionar icona", "en": "Select icon", "pt": "Selecionar ícone", "fr": "Sélectionner une icône", "it": "Seleziona icona", "de": "Symbol auswählen"},
    "buscar_icono_simple": {"es": "Buscar icono...", "gl": "Buscar icona...", "en": "Search icon...", "pt": "Pesquisar ícone...", "fr": "Rechercher une icône...", "it": "Cerca icona...", "de": "Symbol suchen..."},
    "sin_iconos_coincidentes": {"es": "Ningún icono coincide con esa búsqueda.", "gl": "Ningunha icona coincide con esa busca.", "en": "No icons match that search.", "pt": "Nenhum ícone corresponde a essa pesquisa.", "fr": "Aucune icône ne correspond à cette recherche.", "it": "Nessuna icona corrisponde a questa ricerca.", "de": "Kein Symbol entspricht dieser Suche."},

    # --- Mis Listas ---
    "mis_listas": {"es": "Mis Listas", "gl": "As miñas listas", "en": "My Lists", "pt": "Minhas Listas", "fr": "Mes listes", "it": "Le mie liste", "de": "Meine Listen"},

    # --- Crear nueva lista ---
    "crear_nueva_lista_titulo": {"es": "Crear nueva lista", "gl": "Crear nova lista", "en": "Create new list", "pt": "Criar nova lista", "fr": "Créer une nouvelle liste", "it": "Crea nuova lista", "de": "Neue Liste erstellen"},
    "color_lista": {"es": "Color de la lista", "gl": "Cor da lista", "en": "List color", "pt": "Cor da lista", "fr": "Couleur de la liste", "it": "Colore della lista", "de": "Listenfarbe"},
    "ej_mi_inventario": {"es": "Ej. Mi inventario", "gl": "Ex. O meu inventario", "en": "E.g. My inventory", "pt": "Ex. Meu inventário", "fr": "Ex. Mon inventaire", "it": "Es. Il mio inventario", "de": "Z.B. Mein Inventar"},
    "cambiar_icono": {"es": "Cambiar icono", "gl": "Cambiar icona", "en": "Change icon", "pt": "Mudar ícone", "fr": "Changer d'icône", "it": "Cambia icona", "de": "Symbol ändern"},
    "crear_lista": {"es": "Crear lista", "gl": "Crear lista", "en": "Create list", "pt": "Criar lista", "fr": "Créer la liste", "it": "Crea lista", "de": "Liste erstellen"},

    # --- Editar/Ajustes de lista ---
    "ajustes_lista": {"es": "Ajustes de la lista", "gl": "Axustes da lista", "en": "List settings", "pt": "Configurações da lista", "fr": "Paramètres de la liste", "it": "Impostazioni della lista", "de": "Listeneinstellungen"},
    "personalizar_lista": {"es": "Personalizar lista", "gl": "Personalizar lista", "en": "Customize list", "pt": "Personalizar lista", "fr": "Personnaliser la liste", "it": "Personalizza lista", "de": "Liste anpassen"},
    "ordenando": {"es": "Ordenando", "gl": "Ordenando", "en": "Sorting", "pt": "Ordenando", "fr": "Tri", "it": "Ordinamento", "de": "Sortierung"},
    "region_e_idioma": {"es": "Región e idioma", "gl": "Rexión e idioma", "en": "Region & language", "pt": "Região e idioma", "fr": "Région et langue", "it": "Regione e lingua", "de": "Region & Sprache"},
    "miembros_lista": {"es": "Miembros de la lista", "gl": "Membros da lista", "en": "List members", "pt": "Membros da lista", "fr": "Membres de la liste", "it": "Membri della lista", "de": "Listenmitglieder"},
    "nombre_e_imagen": {"es": "Nombre e imagen", "gl": "Nome e imaxe", "en": "Name & image", "pt": "Nome e imagem", "fr": "Nom et image", "it": "Nome e immagine", "de": "Name & Bild"},
    "color": {"es": "Color", "gl": "Cor", "en": "Color", "pt": "Cor", "fr": "Couleur", "it": "Colore", "de": "Farbe"},
    "compartir_lista": {"es": "Compartir lista", "gl": "Compartir lista", "en": "Share list", "pt": "Compartilhar lista", "fr": "Partager la liste", "it": "Condividi lista", "de": "Liste teilen"},
    "enlace": {"es": "Enlace", "gl": "Ligazón", "en": "Link", "pt": "Link", "fr": "Lien", "it": "Link", "de": "Link"},
    "permiso": {"es": "Permiso", "gl": "Permiso", "en": "Permission", "pt": "Permissão", "fr": "Autorisation", "it": "Autorizzazione", "de": "Berechtigung"},
    "permiso_ver_solo_lectura": {"es": "👁️ Ver (solo lectura)", "gl": "👁️ Ver (só lectura)", "en": "👁️ View (read-only)", "pt": "👁️ Ver (somente leitura)", "fr": "👁️ Voir (lecture seule)", "it": "👁️ Visualizza (sola lettura)", "de": "👁️ Ansehen (nur lesen)"},
    "permiso_editar_lectura_escritura": {"es": "✏️ Editar (lectura y escritura)", "gl": "✏️ Editar (lectura e escritura)", "en": "✏️ Edit (read & write)", "pt": "✏️ Editar (leitura e escrita)", "fr": "✏️ Modifier (lecture et écriture)", "it": "✏️ Modifica (lettura e scrittura)", "de": "✏️ Bearbeiten (Lesen & Schreiben)"},
    "compartir_con_usuario": {"es": "Compartir con Usuario", "gl": "Compartir con Usuario", "en": "Share with user", "pt": "Compartilhar com Usuário", "fr": "Partager avec un utilisateur", "it": "Condividi con utente", "de": "Mit Benutzer teilen"},
    "email_destinatario": {"es": "Email del destinatario", "gl": "Email do destinatario", "en": "Recipient's email", "pt": "Email do destinatário", "fr": "Email du destinataire", "it": "Email del destinatario", "de": "E-Mail des Empfängers"},
    "placeholder_email_ejemplo": {"es": "usuario@example.com", "gl": "usuario@example.com", "en": "user@example.com", "pt": "usuario@example.com", "fr": "utilisateur@example.com", "it": "utente@example.com", "de": "benutzer@example.com"},
    "generar_enlace_invitacion": {"es": "Generar Enlace de Invitación", "gl": "Xerar Ligazón de Invitación", "en": "Generate Invitation Link", "pt": "Gerar Link de Convite", "fr": "Générer un lien d'invitation", "it": "Genera link di invito", "de": "Einladungslink erstellen"},
    "generar_enlace_compartible": {"es": "Generar Enlace Compartible", "gl": "Xerar Ligazón Compartible", "en": "Generate Shareable Link", "pt": "Gerar Link Compartilhável", "fr": "Générer un lien partageable", "it": "Genera link condivisibile", "de": "Teilbaren Link erstellen"},
    "compartir_whatsapp": {"es": "Compartir por WhatsApp", "gl": "Compartir por WhatsApp", "en": "Share via WhatsApp", "pt": "Compartilhar via WhatsApp", "fr": "Partager via WhatsApp", "it": "Condividi via WhatsApp", "de": "Über WhatsApp teilen"},
    "abrir_whatsapp": {"es": "Abrir WhatsApp", "gl": "Abrir WhatsApp", "en": "Open WhatsApp", "pt": "Abrir WhatsApp", "fr": "Ouvrir WhatsApp", "it": "Apri WhatsApp", "de": "WhatsApp öffnen"},
    "placeholder_telefono": {"es": "Teléfono (opcional, ej: +34 123 45 67 89)", "gl": "Teléfono (opcional, ex: +34 123 45 67 89)", "en": "Phone (optional, e.g. +1 555 123 4567)", "pt": "Telefone (opcional, ex: +55 11 91234-5678)", "fr": "Téléphone (facultatif, ex : +33 6 12 34 56 78)", "it": "Telefono (facoltativo, es: +39 333 123 4567)", "de": "Telefon (optional, z.B. +49 151 12345678)"},
    "ayuda_whatsapp": {"es": "Sin teléfono: abre WhatsApp Web. Con teléfono: envía un mensaje directo.", "gl": "Sen teléfono: abre WhatsApp Web. Con teléfono: envía unha mensaxe directa.", "en": "Without a phone: opens WhatsApp Web. With a phone: sends a direct message.", "pt": "Sem telefone: abre o WhatsApp Web. Com telefone: envia uma mensagem direta.", "fr": "Sans téléphone : ouvre WhatsApp Web. Avec téléphone : envoie un message direct.", "it": "Senza telefono: apre WhatsApp Web. Con telefono: invia un messaggio diretto.", "de": "Ohne Telefonnummer: öffnet WhatsApp Web. Mit Telefonnummer: sendet eine Direktnachricht."},
    "enlace_generado_titulo": {"es": "🔗 Enlace de invitación generado:", "gl": "🔗 Ligazón de invitación xerada:", "en": "🔗 Invitation link generated:", "pt": "🔗 Link de convite gerado:", "fr": "🔗 Lien d'invitation généré :", "it": "🔗 Link di invito generato:", "de": "🔗 Einladungslink erstellt:"},
    "copiar": {"es": "📋 Copiar", "gl": "📋 Copiar", "en": "📋 Copy", "pt": "📋 Copiar", "fr": "📋 Copier", "it": "📋 Copia", "de": "📋 Kopieren"},
    "enlace_valido_7_dias": {"es": "✓ Válido por 7 días. Comparte por WhatsApp, email, mensaje directo, etc.", "gl": "✓ Válido por 7 días. Comparte por WhatsApp, email, mensaxe directa, etc.", "en": "✓ Valid for 7 days. Share it via WhatsApp, email, direct message, etc.", "pt": "✓ Válido por 7 dias. Compartilhe via WhatsApp, email, mensagem direta, etc.", "fr": "✓ Valable 7 jours. Partagez-le via WhatsApp, email, message direct, etc.", "it": "✓ Valido per 7 giorni. Condividilo via WhatsApp, email, messaggio diretto, ecc.", "de": "✓ 7 Tage gültig. Teile ihn über WhatsApp, E-Mail, Direktnachricht usw."},
    "miembros_con_acceso": {"es": "👥 Miembros con acceso", "gl": "👥 Membros con acceso", "en": "👥 Members with access", "pt": "👥 Membros com acesso", "fr": "👥 Membres avec accès", "it": "👥 Membri con accesso", "de": "👥 Mitglieder mit Zugriff"},
    "cargando_miembros": {"es": "Cargando miembros...", "gl": "Cargando membros...", "en": "Loading members...", "pt": "Carregando membros...", "fr": "Chargement des membres...", "it": "Caricamento membri...", "de": "Mitglieder werden geladen..."},
    "salir_lista": {"es": "Salir de esta lista", "gl": "Saír desta lista", "en": "Leave this list", "pt": "Sair desta lista", "fr": "Quitter cette liste", "it": "Esci da questa lista", "de": "Diese Liste verlassen"},

    # --- Modal Ordenando ---
    "elegir_orden_articulos": {"es": "Elige cómo deseas ordenar los artículos:", "gl": "Escolle como queres ordenar os artigos:", "en": "Choose how to sort the items:", "pt": "Escolha como deseja ordenar os itens:", "fr": "Choisissez comment trier les articles :", "it": "Scegli come ordinare gli articoli:", "de": "Wähle, wie die Artikel sortiert werden sollen:"},
    "orden_manual": {"es": "Manual (arrastra para reordenar)", "gl": "Manual (arrastra para reordenar)", "en": "Manual (drag to reorder)", "pt": "Manual (arraste para reordenar)", "fr": "Manuel (glisser pour réorganiser)", "it": "Manuale (trascina per riordinare)", "de": "Manuell (zum Umsortieren ziehen)"},
    "orden_alfabetico": {"es": "Alfabético (A → Z)", "gl": "Alfabético (A → Z)", "en": "Alphabetical (A → Z)", "pt": "Alfabético (A → Z)", "fr": "Alphabétique (A → Z)", "it": "Alfabetico (A → Z)", "de": "Alphabetisch (A → Z)"},
    "orden_categoria": {"es": "Por categoría (agrupado)", "gl": "Por categoría (agrupado)", "en": "By category (grouped)", "pt": "Por categoria (agrupado)", "fr": "Par catégorie (groupé)", "it": "Per categoria (raggruppato)", "de": "Nach Kategorie (gruppiert)"},
    "orden_pendientes_primero": {"es": "Pendientes primero (sin tachar)", "gl": "Pendentes primeiro (sen riscar)", "en": "Pending first (unchecked)", "pt": "Pendentes primeiro (não marcados)", "fr": "En attente d'abord (non cochés)", "it": "In sospeso prima (non spuntati)", "de": "Ausstehende zuerst (nicht abgehakt)"},

    # --- Región e idioma ---
    "region": {"es": "Región", "gl": "Rexión", "en": "Region", "pt": "Região", "fr": "Région", "it": "Regione", "de": "Region"},
    "pais_espana": {"es": "España", "gl": "España", "en": "Spain", "pt": "Espanha", "fr": "Espagne", "it": "Spagna", "de": "Spanien"},
    "pais_mexico": {"es": "México", "gl": "México", "en": "Mexico", "pt": "México", "fr": "Mexique", "it": "Messico", "de": "Mexiko"},
    "pais_argentina": {"es": "Argentina", "gl": "Arxentina", "en": "Argentina", "pt": "Argentina", "fr": "Argentine", "it": "Argentina", "de": "Argentinien"},
    "pais_chile": {"es": "Chile", "gl": "Chile", "en": "Chile", "pt": "Chile", "fr": "Chili", "it": "Cile", "de": "Chile"},
    "pais_colombia": {"es": "Colombia", "gl": "Colombia", "en": "Colombia", "pt": "Colômbia", "fr": "Colombie", "it": "Colombia", "de": "Kolumbien"},
    "pais_peru": {"es": "Perú", "gl": "Perú", "en": "Peru", "pt": "Peru", "fr": "Pérou", "it": "Perù", "de": "Peru"},

    # --- Nombre e imagen ---
    "ej_mi_lista_compra": {"es": "Ej. Mi lista de compra", "gl": "Ex. A miña lista da compra", "en": "E.g. My shopping list", "pt": "Ex. Minha lista de compras", "fr": "Ex. Ma liste de courses", "it": "Es. La mia lista della spesa", "de": "Z.B. Meine Einkaufsliste"},

    # --- Cabecera / banner / ticket ---
    "consumo": {"es": "Consumo", "gl": "Consumo", "en": "Consumption", "pt": "Consumo", "fr": "Consommation", "it": "Consumo", "de": "Verbrauch"},
    "cambiar_lista": {"es": "Cambiar lista", "gl": "Cambiar lista", "en": "Change list", "pt": "Mudar lista", "fr": "Changer de liste", "it": "Cambia lista", "de": "Liste wechseln"},
    "banner_crear_lista_texto": {"es": "⚠️ Debes crear una lista para comenzar.", "gl": "⚠️ Debes crear unha lista para comezar.", "en": "⚠️ You need to create a list to get started.", "pt": "⚠️ Você precisa criar uma lista para começar.", "fr": "⚠️ Vous devez créer une liste pour commencer.", "it": "⚠️ Devi creare una lista per iniziare.", "de": "⚠️ Erstelle eine Liste, um zu starten."},
    "crear_lista_ahora": {"es": "Crear lista ahora", "gl": "Crear lista agora", "en": "Create list now", "pt": "Criar lista agora", "fr": "Créer la liste maintenant", "it": "Crea lista ora", "de": "Liste jetzt erstellen"},
    "escanear_ticket_simple": {"es": "Escanear ticket", "gl": "Escanear tíquet", "en": "Scan receipt", "pt": "Escanear recibo", "fr": "Numériser le reçu", "it": "Scansiona ricevuta", "de": "Beleg scannen"},
    "ocr_instrucciones": {"es": "Lectura local con OCR (sin conexión a internet). Es orientativa: revisa y corrige los artículos detectados antes de añadirlos al stock.", "gl": "Lectura local con OCR (sen conexión a internet). É orientativa: revisa e corrixe os artigos detectados antes de engadilos ao stock.", "en": "Local OCR reading (no internet connection). It's a guide only: review and correct the detected items before adding them to your stock.", "pt": "Leitura local com OCR (sem conexão à internet). É apenas orientativa: revise e corrija os itens detectados antes de adicioná-los ao estoque.", "fr": "Lecture locale par OCR (sans connexion internet). À titre indicatif : vérifiez et corrigez les articles détectés avant de les ajouter au stock.", "it": "Lettura locale con OCR (senza connessione a internet). È solo indicativa: controlla e correggi gli articoli rilevati prima di aggiungerli allo stock.", "de": "Lokale OCR-Erkennung (ohne Internetverbindung). Nur als Hinweis: Überprüfe und korrigiere die erkannten Artikel, bevor du sie zum Bestand hinzufügst."},
    "toca_para_foto": {"es": "Toca para hacer una foto o elegir una imagen del ticket.", "gl": "Toca para facer unha foto ou elixir unha imaxe do tíquet.", "en": "Tap to take a photo or choose an image of the receipt.", "pt": "Toque para tirar uma foto ou escolher uma imagem do recibo.", "fr": "Touchez pour prendre une photo ou choisir une image du reçu.", "it": "Tocca per scattare una foto o scegliere un'immagine della ricevuta.", "de": "Tippe, um ein Foto zu machen oder ein Bild des Belegs auszuwählen."},
    "cambiar_foto": {"es": "Cambiar foto", "gl": "Cambiar foto", "en": "Change photo", "pt": "Mudar foto", "fr": "Changer la photo", "it": "Cambia foto", "de": "Foto ändern"},
    "leyendo_ticket": {"es": "Leyendo el ticket, un momento...", "gl": "Lendo o tíquet, un momento...", "en": "Reading the receipt, one moment...", "pt": "Lendo o recibo, um momento...", "fr": "Lecture du reçu, un instant...", "it": "Lettura della ricevuta, un momento...", "de": "Beleg wird gelesen, einen Moment..."},
    "añadir_linea": {"es": "+ Añadir línea", "gl": "+ Engadir liña", "en": "+ Add line", "pt": "+ Adicionar linha", "fr": "+ Ajouter une ligne", "it": "+ Aggiungi riga", "de": "+ Zeile hinzufügen"},
    "volver": {"es": "← Volver", "gl": "← Volver", "en": "← Back", "pt": "← Voltar", "fr": "← Retour", "it": "← Indietro", "de": "← Zurück"},
    "analizar": {"es": "Analizar", "gl": "Analizar", "en": "Analyze", "pt": "Analisar", "fr": "Analyser", "it": "Analizza", "de": "Analysieren"},

    # --- app.js: confirmaciones y textos de modal dinámicos ---
    "añadir_al_stock": {"es": "Añadir al stock", "gl": "Engadir ao stock", "en": "Add to stock", "pt": "Adicionar ao estoque", "fr": "Ajouter au stock", "it": "Aggiungi allo stock", "de": "Zum Bestand hinzufügen"},
    "añadir_a_la_lista": {"es": "Añadir a la lista", "gl": "Engadir á lista", "en": "Add to list", "pt": "Adicionar à lista", "fr": "Ajouter à la liste", "it": "Aggiungi alla lista", "de": "Zur Liste hinzufügen"},
    "confirmar_borrar_categoria": {"es": "¿Borrar la categoría \"{nombre}\"?", "gl": "¿Borrar a categoría \"{nombre}\"?", "en": "Delete category \"{nombre}\"?", "pt": "Excluir a categoria \"{nombre}\"?", "fr": "Supprimer la catégorie « {nombre} » ?", "it": "Eliminare la categoria \"{nombre}\"?", "de": "Kategorie \"{nombre}\" löschen?"},
    "confirmar_eliminar_producto_stock": {"es": "¿Eliminar este producto del stock?", "gl": "¿Eliminar este produto do stock?", "en": "Remove this product from stock?", "pt": "Remover este produto do estoque?", "fr": "Supprimer ce produit du stock ?", "it": "Rimuovere questo prodotto dallo stock?", "de": "Dieses Produkt aus dem Bestand entfernen?"},
    "añadir_x_al_stock": {"es": "Añadir \"{nombre}\" al stock", "gl": "Engadir \"{nombre}\" ao stock", "en": "Add \"{nombre}\" to stock", "pt": "Adicionar \"{nombre}\" ao estoque", "fr": "Ajouter « {nombre} » au stock", "it": "Aggiungi \"{nombre}\" allo stock", "de": "\"{nombre}\" zum Bestand hinzufügen"},
    "confirmar_borrar_articulo_lista": {"es": "¿Borrar este artículo de la lista?", "gl": "¿Borrar este artigo da lista?", "en": "Delete this item from the list?", "pt": "Excluir este item da lista?", "fr": "Supprimer cet article de la liste ?", "it": "Eliminare questo articolo dalla lista?", "de": "Diesen Artikel von der Liste löschen?"},
    "edicion_avanzada_articulo": {"es": "Edición avanzada para artículo personalizado ID {id}. Esta funcionalidad puede extenderse en el futuro.", "gl": "Edición avanzada para artigo personalizado ID {id}. Esta funcionalidade pode ampliarse no futuro.", "en": "Advanced editing for custom item ID {id}. This feature may be expanded in the future.", "pt": "Edição avançada para item personalizado ID {id}. Esta funcionalidade pode ser expandida no futuro.", "fr": "Édition avancée pour l'article personnalisé ID {id}. Cette fonctionnalité pourra être étendue à l'avenir.", "it": "Modifica avanzata per l'articolo personalizzato ID {id}. Questa funzionalità potrà essere ampliata in futuro.", "de": "Erweiterte Bearbeitung für benutzerdefinierten Artikel ID {id}. Diese Funktion kann in Zukunft erweitert werden."},
    "ayuda_stock_catalogo": {"es": "Toca un producto para indicar su cantidad y añadirlo al stock.", "gl": "Toca un produto para indicar a súa cantidade e engadilo ao stock.", "en": "Tap a product to enter its quantity and add it to stock.", "pt": "Toque em um produto para indicar a quantidade e adicioná-lo ao estoque.", "fr": "Touchez un produit pour indiquer sa quantité et l'ajouter au stock.", "it": "Tocca un prodotto per indicare la quantità e aggiungerlo allo stock.", "de": "Tippe auf ein Produkt, um die Menge anzugeben und es zum Bestand hinzuzufügen."},
    "ayuda_lista_catalogo": {"es": "Toca un producto para añadirlo. Mantén pulsado para ajustar cantidad, unidad, sub-descripción o icono antes de añadirlo.", "gl": "Toca un produto para engadilo. Mantén premido para axustar cantidade, unidade, subdescrición ou icona antes de engadilo.", "en": "Tap a product to add it. Long-press to adjust quantity, unit, sub-description or icon before adding it.", "pt": "Toque em um produto para adicioná-lo. Mantenha pressionado para ajustar quantidade, unidade, subdescrição ou ícone antes de adicionar.", "fr": "Touchez un produit pour l'ajouter. Appuyez longuement pour ajuster la quantité, l'unité, la sous-description ou l'icône avant de l'ajouter.", "it": "Tocca un prodotto per aggiungerlo. Tieni premuto per regolare quantità, unità, sotto-descrizione o icona prima di aggiungerlo.", "de": "Tippe auf ein Produkt, um es hinzuzufügen. Lange drücken, um Menge, Einheit, Unterbeschreibung oder Symbol vor dem Hinzufügen anzupassen."},

    # --- Login / registro ---
    "login_subtitulo": {"es": "Inicia sesión para continuar.", "gl": "Inicia sesión para continuar.", "en": "Sign in to continue.", "pt": "Faça login para continuar.", "fr": "Connectez-vous pour continuer.", "it": "Accedi per continuare.", "de": "Melde dich an, um fortzufahren."},
    "registro_subtitulo": {"es": "Crea tu cuenta para empezar.", "gl": "Crea a túa conta para comezar.", "en": "Create your account to get started.", "pt": "Crie sua conta para começar.", "fr": "Créez votre compte pour commencer.", "it": "Crea il tuo account per iniziare.", "de": "Erstelle dein Konto, um loszulegen."},
    "nombre_completo": {"es": "Nombre completo", "gl": "Nome completo", "en": "Full name", "pt": "Nome completo", "fr": "Nom complet", "it": "Nome completo", "de": "Vollständiger Name"},
    "confirma_contrasena": {"es": "Confirma contraseña", "gl": "Confirma o contrasinal", "en": "Confirm password", "pt": "Confirme a senha", "fr": "Confirmez le mot de passe", "it": "Conferma password", "de": "Passwort bestätigen"},
    "placeholder_tu_usuario": {"es": "Tu usuario", "gl": "O teu usuario", "en": "Your username", "pt": "Seu usuário", "fr": "Votre identifiant", "it": "Il tuo nome utente", "de": "Dein Benutzername"},
    "placeholder_tu_contrasena": {"es": "Tu contraseña", "gl": "O teu contrasinal", "en": "Your password", "pt": "Sua senha", "fr": "Votre mot de passe", "it": "La tua password", "de": "Dein Passwort"},
    "placeholder_tu_nombre": {"es": "Tu nombre", "gl": "O teu nome", "en": "Your name", "pt": "Seu nome", "fr": "Votre nom", "it": "Il tuo nome", "de": "Dein Name"},
    "placeholder_tu_email": {"es": "tu@email.com", "gl": "o.teu@email.com", "en": "you@email.com", "pt": "seu@email.com", "fr": "vous@email.com", "it": "tu@email.com", "de": "du@email.com"},
    "minimo_8_caracteres": {"es": "Mínimo 8 caracteres", "gl": "Mínimo 8 caracteres", "en": "Minimum 8 characters", "pt": "Mínimo de 8 caracteres", "fr": "Minimum 8 caractères", "it": "Minimo 8 caratteri", "de": "Mindestens 8 Zeichen"},
    "placeholder_confirma_contrasena": {"es": "Confirma tu contraseña", "gl": "Confirma o teu contrasinal", "en": "Confirm your password", "pt": "Confirme sua senha", "fr": "Confirmez votre mot de passe", "it": "Conferma la tua password", "de": "Bestätige dein Passwort"},
    "entrar": {"es": "Entrar", "gl": "Entrar", "en": "Sign in", "pt": "Entrar", "fr": "Se connecter", "it": "Accedi", "de": "Anmelden"},
    "crear_cuenta": {"es": "Crear cuenta", "gl": "Crear conta", "en": "Create account", "pt": "Criar conta", "fr": "Créer un compte", "it": "Crea account", "de": "Konto erstellen"},
    "no_tienes_cuenta": {"es": "¿No tienes cuenta?", "gl": "¿Non tes conta?", "en": "Don't have an account?", "pt": "Não tem uma conta?", "fr": "Vous n'avez pas de compte ?", "it": "Non hai un account?", "de": "Noch kein Konto?"},
    "crea_una": {"es": "Crea una", "gl": "Crea unha", "en": "Create one", "pt": "Crie uma", "fr": "Créez-en un", "it": "Creane uno", "de": "Erstelle eins"},
    "ya_tienes_cuenta": {"es": "¿Ya tienes cuenta?", "gl": "¿Xa tes conta?", "en": "Already have an account?", "pt": "Já tem uma conta?", "fr": "Vous avez déjà un compte ?", "it": "Hai già un account?", "de": "Bereits ein Konto?"},
    "inicia_sesion_link": {"es": "Inicia sesión", "gl": "Inicia sesión", "en": "Sign in", "pt": "Entrar", "fr": "Connectez-vous", "it": "Accedi", "de": "Anmelden"},
    "continuar_google": {"es": "Continuar con Google", "gl": "Continuar con Google", "en": "Continue with Google", "pt": "Continuar com o Google", "fr": "Continuer avec Google", "it": "Continua con Google", "de": "Mit Google fortfahren"},
    "error_contrasenas_no_coinciden": {"es": "Las contraseñas no coinciden", "gl": "Os contrasinais non coinciden", "en": "Passwords don't match", "pt": "As senhas não coincidem", "fr": "Les mots de passe ne correspondent pas", "it": "Le password non coincidono", "de": "Die Passwörter stimmen nicht überein"},
    "error_no_se_pudo_crear_cuenta": {"es": "No se pudo crear la cuenta", "gl": "Non se puido crear a conta", "en": "Couldn't create the account", "pt": "Não foi possível criar a conta", "fr": "Impossible de créer le compte", "it": "Impossibile creare l'account", "de": "Konto konnte nicht erstellt werden"},
    "error_credenciales_incorrectas": {"es": "Usuario o contraseña incorrectos", "gl": "Usuario ou contrasinal incorrectos", "en": "Incorrect username or password", "pt": "Usuário ou senha incorretos", "fr": "Identifiant ou mot de passe incorrect", "it": "Nome utente o password errati", "de": "Benutzername oder Passwort falsch"},

    # --- Backend: nombres de recurso ---
    "recurso_articulo": {"es": "Artículo", "gl": "Artigo", "en": "Item", "pt": "Item", "fr": "Article", "it": "Articolo", "de": "Artikel"},
    "recurso_articulo_personalizado": {"es": "Artículo personalizado", "gl": "Artigo personalizado", "en": "Custom item", "pt": "Item personalizado", "fr": "Article personnalisé", "it": "Articolo personalizzato", "de": "Benutzerdefinierter Artikel"},
    "recurso_categoria": {"es": "Categoría", "gl": "Categoría", "en": "Category", "pt": "Categoria", "fr": "Catégorie", "it": "Categoria", "de": "Kategorie"},
    "recurso_lista": {"es": "Lista", "gl": "Lista", "en": "List", "pt": "Lista", "fr": "Liste", "it": "Lista", "de": "Liste"},
    "recurso_producto": {"es": "Producto", "gl": "Produto", "en": "Product", "pt": "Produto", "fr": "Produit", "it": "Prodotto", "de": "Produkt"},

    # --- Backend: mensajes genéricos ---
    "err_no_autenticado": {"es": "No has iniciado sesión", "gl": "Non iniciaches sesión", "en": "You are not signed in", "pt": "Você não fez login", "fr": "Vous n'êtes pas connecté", "it": "Non hai effettuato l'accesso", "de": "Du bist nicht angemeldet"},
    "err_no_permitido": {"es": "No tienes permiso para esta acción", "gl": "Non tes permiso para esta acción", "en": "You don't have permission for this action", "pt": "Você não tem permissão para esta ação", "fr": "Vous n'avez pas la permission pour cette action", "it": "Non hai il permesso per questa azione", "de": "Du hast keine Berechtigung für diese Aktion"},
    "err_recurso_no_encontrado": {"es": "{recurso} no encontrado", "gl": "{recurso} non atopado", "en": "{recurso} not found", "pt": "{recurso} não encontrado", "fr": "{recurso} introuvable", "it": "{recurso} non trovato", "de": "{recurso} nicht gefunden"},
    "err_interno_generico": {"es": "Ha ocurrido un error interno. Inténtalo de nuevo o contacta con soporte.", "gl": "Ocorreu un erro interno. Téntao de novo ou contacta con soporte.", "en": "An internal error occurred. Please try again or contact support.", "pt": "Ocorreu um erro interno. Tente novamente ou entre em contato com o suporte.", "fr": "Une erreur interne s'est produite. Réessayez ou contactez le support.", "it": "Si è verificato un errore interno. Riprova o contatta l'assistenza.", "de": "Ein interner Fehler ist aufgetreten. Bitte versuche es erneut oder kontaktiere den Support."},

    # --- Backend: articulos_lista / listas ---
    "err_no_hay_lista_activa": {"es": "No hay una lista activa", "gl": "Non hai unha lista activa", "en": "There is no active list", "pt": "Não há uma lista ativa", "fr": "Aucune liste active", "it": "Nessuna lista attiva", "de": "Keine aktive Liste vorhanden"},
    "err_nombre_obligatorio": {"es": "El nombre es obligatorio", "gl": "O nome é obrigatorio", "en": "The name is required", "pt": "O nome é obrigatório", "fr": "Le nom est obligatoire", "it": "Il nome è obbligatorio", "de": "Der Name ist erforderlich"},
    "err_sin_permiso_editar_lista": {"es": "No tienes permisos para editar esta lista", "gl": "Non tes permisos para editar esta lista", "en": "You don't have permission to edit this list", "pt": "Você não tem permissão para editar esta lista", "fr": "Vous n'avez pas l'autorisation de modifier cette liste", "it": "Non hai i permessi per modificare questa lista", "de": "Du hast keine Berechtigung, diese Liste zu bearbeiten"},
    "err_nada_que_actualizar": {"es": "No hay nada que actualizar", "gl": "Non hai nada que actualizar", "en": "There is nothing to update", "pt": "Não há nada para atualizar", "fr": "Rien à mettre à jour", "it": "Non c'è nulla da aggiornare", "de": "Es gibt nichts zu aktualisieren"},
    "err_no_salir_propia_lista": {"es": "No puedes salir de tu propia lista", "gl": "Non podes saír da túa propia lista", "en": "You can't leave your own list", "pt": "Você não pode sair da sua própria lista", "fr": "Vous ne pouvez pas quitter votre propre liste", "it": "Non puoi uscire dalla tua stessa lista", "de": "Du kannst deine eigene Liste nicht verlassen"},

    # --- Backend: auth ---
    "err_password_min_8": {"es": "La contraseña debe tener al menos 8 caracteres", "gl": "O contrasinal debe ter polo menos 8 caracteres", "en": "The password must be at least 8 characters long", "pt": "A senha deve ter no mínimo 8 caracteres", "fr": "Le mot de passe doit comporter au moins 8 caractères", "it": "La password deve contenere almeno 8 caratteri", "de": "Das Passwort muss mindestens 8 Zeichen lang sein"},
    "err_usuario_duplicado": {"es": "Ya existe un usuario con ese nombre", "gl": "Xa existe un usuario con ese nome", "en": "A user with that name already exists", "pt": "Já existe um usuário com esse nome", "fr": "Un utilisateur avec ce nom existe déjà", "it": "Esiste già un utente con questo nome", "de": "Ein Benutzer mit diesem Namen existiert bereits"},
    "err_nombre_max_80": {"es": "El nombre no puede exceder 80 caracteres", "gl": "O nome non pode exceder 80 caracteres", "en": "The name cannot exceed 80 characters", "pt": "O nome não pode exceder 80 caracteres", "fr": "Le nom ne peut pas dépasser 80 caractères", "it": "Il nome non può superare gli 80 caratteri", "de": "Der Name darf 80 Zeichen nicht überschreiten"},
    "err_password_min_4": {"es": "La contraseña debe tener mínimo 4 caracteres", "gl": "O contrasinal debe ter mínimo 4 caracteres", "en": "The password must be at least 4 characters long", "pt": "A senha deve ter no mínimo 4 caracteres", "fr": "Le mot de passe doit comporter au moins 4 caractères", "it": "La password deve contenere almeno 4 caratteri", "de": "Das Passwort muss mindestens 4 Zeichen lang sein"},
    "err_nueva_password_min_4": {"es": "La nueva contraseña debe tener al menos 4 caracteres", "gl": "O novo contrasinal debe ter polo menos 4 caracteres", "en": "The new password must be at least 4 characters long", "pt": "A nova senha deve ter no mínimo 4 caracteres", "fr": "Le nouveau mot de passe doit comporter au moins 4 caractères", "it": "La nuova password deve contenere almeno 4 caratteri", "de": "Das neue Passwort muss mindestens 4 Zeichen lang sein"},
    "err_password_actual_incorrecta": {"es": "La contraseña actual es incorrecta", "gl": "O contrasinal actual é incorrecto", "en": "The current password is incorrect", "pt": "A senha atual está incorreta", "fr": "Le mot de passe actuel est incorrect", "it": "La password attuale non è corretta", "de": "Das aktuelle Passwort ist falsch"},
    "err_ultimo_usuario": {"es": "No puedes borrar el único usuario que queda", "gl": "Non podes borrar o único usuario que queda", "en": "You can't delete the only remaining user", "pt": "Você não pode excluir o único usuário restante", "fr": "Vous ne pouvez pas supprimer le seul utilisateur restant", "it": "Non puoi eliminare l'unico utente rimasto", "de": "Du kannst den letzten verbleibenden Benutzer nicht löschen"},

    # --- Backend: categorias ---
    "err_categoria_duplicada": {"es": "Ya existe una categoría con ese nombre", "gl": "Xa existe unha categoría con ese nome", "en": "A category with that name already exists", "pt": "Já existe uma categoria com esse nome", "fr": "Une catégorie avec ce nom existe déjà", "it": "Esiste già una categoria con questo nome", "de": "Eine Kategorie mit diesem Namen existiert bereits"},
    "err_no_borrar_categoria_defecto": {"es": "No se puede borrar la categoría \"{nombre}\"", "gl": "Non se pode borrar a categoría \"{nombre}\"", "en": "The category \"{nombre}\" cannot be deleted", "pt": "Não é possível excluir a categoria \"{nombre}\"", "fr": "Impossible de supprimer la catégorie « {nombre} »", "it": "Impossibile eliminare la categoria \"{nombre}\"", "de": "Die Kategorie \"{nombre}\" kann nicht gelöscht werden"},

    # --- Backend: idiomas ---
    "err_claves_debe_ser_lista": {"es": "claves debe ser una lista", "gl": "claves debe ser unha lista", "en": "claves must be a list", "pt": "claves deve ser uma lista", "fr": "claves doit être une liste", "it": "claves deve essere un elenco", "de": "claves muss eine Liste sein"},

    # --- Backend: oauth ---
    "err_oauth_google_generico": {"es": "Error de Google: {error}", "gl": "Erro de Google: {error}", "en": "Google error: {error}", "pt": "Erro do Google: {error}", "fr": "Erreur Google : {error}", "it": "Errore di Google: {error}", "de": "Google-Fehler: {error}"},
    "err_oauth_solicitud_invalida": {"es": "Solicitud de autenticación inválida o expirada", "gl": "Solicitude de autenticación inválida ou caducada", "en": "Invalid or expired authentication request", "pt": "Solicitação de autenticação inválida ou expirada", "fr": "Demande d'authentification invalide ou expirée", "it": "Richiesta di autenticazione non valida o scaduta", "de": "Ungültige oder abgelaufene Authentifizierungsanfrage"},
    "err_oauth_sin_codigo": {"es": "No se recibió código de autorización", "gl": "Non se recibiu código de autorización", "en": "No authorization code was received", "pt": "Nenhum código de autorização foi recebido", "fr": "Aucun code d'autorisation reçu", "it": "Nessun codice di autorizzazione ricevuto", "de": "Kein Autorisierungscode erhalten"},
    "err_oauth_google_fallo": {"es": "No se pudo completar el inicio de sesión con Google. Inténtalo de nuevo.", "gl": "Non se puido completar o inicio de sesión con Google. Téntao de novo.", "en": "Couldn't complete sign-in with Google. Please try again.", "pt": "Não foi possível concluir o login com o Google. Tente novamente.", "fr": "Impossible de terminer la connexion avec Google. Réessayez.", "it": "Impossibile completare l'accesso con Google. Riprova.", "de": "Die Anmeldung mit Google konnte nicht abgeschlossen werden. Bitte versuche es erneut."},

    # --- Backend: permisos ---
    "err_min_2_caracteres": {"es": "Ingresa al menos 2 caracteres", "gl": "Ingresa polo menos 2 caracteres", "en": "Enter at least 2 characters", "pt": "Digite pelo menos 2 caracteres", "fr": "Saisissez au moins 2 caractères", "it": "Inserisci almeno 2 caratteri", "de": "Gib mindestens 2 Zeichen ein"},
    "err_nivel_invalido": {"es": "Nivel debe ser 'ver' o 'editar'", "gl": "O nivel debe ser 'ver' ou 'editar'", "en": "Level must be 'view' or 'edit'", "pt": "O nível deve ser 'ver' ou 'editar'", "fr": "Le niveau doit être « voir » ou « modifier »", "it": "Il livello deve essere 'visualizza' o 'modifica'", "de": "Die Stufe muss 'ansehen' oder 'bearbeiten' sein"},
    "err_usuario_no_encontrado": {"es": "Usuario no encontrado", "gl": "Usuario non atopado", "en": "User not found", "pt": "Usuário não encontrado", "fr": "Utilisateur introuvable", "it": "Utente non trovato", "de": "Benutzer nicht gefunden"},
    "err_falta_email_o_usuario": {"es": "Debe proporcionar email o nombre de usuario", "gl": "Debe proporcionar email ou nome de usuario", "en": "You must provide an email or username", "pt": "Você deve fornecer email ou nome de usuário", "fr": "Vous devez fournir un email ou un nom d'utilisateur", "it": "Devi fornire un'email o un nome utente", "de": "Du musst eine E-Mail oder einen Benutzernamen angeben"},
    "err_invitacion_no_encontrada": {"es": "Invitación no encontrada o expirada", "gl": "Invitación non atopada ou caducada", "en": "Invitation not found or expired", "pt": "Convite não encontrado ou expirado", "fr": "Invitation introuvable ou expirée", "it": "Invito non trovato o scaduto", "de": "Einladung nicht gefunden oder abgelaufen"},
    "err_invitacion_usada": {"es": "Esta invitación ya ha sido usada", "gl": "Esta invitación xa foi usada", "en": "This invitation has already been used", "pt": "Este convite já foi usado", "fr": "Cette invitation a déjà été utilisée", "it": "Questo invito è già stato utilizzato", "de": "Diese Einladung wurde bereits verwendet"},
    "err_invitacion_expirada": {"es": "La invitación ha expirado", "gl": "A invitación caducou", "en": "The invitation has expired", "pt": "O convite expirou", "fr": "L'invitation a expiré", "it": "L'invito è scaduto", "de": "Die Einladung ist abgelaufen"},
    "err_aceptar_invitacion_generico": {"es": "Error al aceptar invitación: {error}", "gl": "Erro ao aceptar a invitación: {error}", "en": "Error accepting invitation: {error}", "pt": "Erro ao aceitar convite: {error}", "fr": "Erreur lors de l'acceptation de l'invitation : {error}", "it": "Errore nell'accettazione dell'invito: {error}", "de": "Fehler beim Annehmen der Einladung: {error}"},

    # --- Backend: ocr_tickets / tickets ---
    "err_sin_archivo": {"es": "No se envió archivo", "gl": "Non se enviou ficheiro", "en": "No file was sent", "pt": "Nenhum arquivo foi enviado", "fr": "Aucun fichier envoyé", "it": "Nessun file inviato", "de": "Keine Datei gesendet"},
    "err_archivo_vacio": {"es": "Archivo vacío", "gl": "Ficheiro baleiro", "en": "Empty file", "pt": "Arquivo vazio", "fr": "Fichier vide", "it": "File vuoto", "de": "Leere Datei"},
    "err_formato_no_permitido": {"es": "Formato no permitido. Usa PNG, JPG, etc.", "gl": "Formato non permitido. Usa PNG, JPG, etc.", "en": "Format not allowed. Use PNG, JPG, etc.", "pt": "Formato não permitido. Use PNG, JPG, etc.", "fr": "Format non autorisé. Utilisez PNG, JPG, etc.", "it": "Formato non consentito. Usa PNG, JPG, ecc.", "de": "Format nicht erlaubt. Verwende PNG, JPG usw."},
    "err_archivo_muy_grande": {"es": "Archivo demasiado grande (máx {mb}MB)", "gl": "Ficheiro demasiado grande (máx {mb}MB)", "en": "File too large (max {mb}MB)", "pt": "Arquivo muito grande (máx {mb}MB)", "fr": "Fichier trop volumineux (max {mb}Mo)", "it": "File troppo grande (max {mb}MB)", "de": "Datei zu groß (max. {mb}MB)"},
    "err_procesando_ticket": {"es": "Error procesando ticket", "gl": "Erro procesando o tíquet", "en": "Error processing receipt", "pt": "Erro ao processar o recibo", "fr": "Erreur lors du traitement du reçu", "it": "Errore durante l'elaborazione della ricevuta", "de": "Fehler bei der Verarbeitung des Belegs"},
    "err_sin_imagen": {"es": "No se ha recibido ninguna imagen", "gl": "Non se recibiu ningunha imaxe", "en": "No image was received", "pt": "Nenhuma imagem foi recebida", "fr": "Aucune image reçue", "it": "Nessuna immagine ricevuta", "de": "Kein Bild empfangen"},
}


def main():
    with open(TRANSLATIONS_FILE, "r", encoding="utf-8") as f:
        translations = json.load(f)

    idiomas = list(translations.keys())
    añadidas = 0
    for clave, textos in NUEVAS.items():
        for idioma in idiomas:
            if clave not in translations[idioma]:
                translations[idioma][clave] = textos.get(idioma, textos["es"])
                añadidas += 1

    with open(TRANSLATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Claves nuevas: {len(NUEVAS)}. Entradas añadidas: {añadidas}.")
    for idioma in idiomas:
        print(f"  {idioma}: {len(translations[idioma])} claves totales")


if __name__ == "__main__":
    main()
