# 🚀 Primeros Pasos - Home-Stock

**Bienvenido a Home-Stock, completamente refactorizado con OOP + DRY.**

---

## ⚡ 1 minuto: Verificación Rápida

```bash
# Verifica que git está configurado con tu nombre
git config --list | grep user
# Debe mostrar:
#   user.name=alejandro.paz
#   user.email=alejandro.paz@edisa.com
```

Si NO sale, configúralo:
```bash
git config user.name "alejandro.paz"
git config user.email "alejandro.paz@edisa.com"
```

---

## 🎯 5 minutos: Primer Commit

```bash
# 1. Ver qué va a subir
git status

# 2. Agregar todo (o archivos específicos)
git add .

# 3. Hacer commit CON TU NOMBRE
git commit -m "Initial commit: refactorización OOP + DRY

Cambios principales:
- Estructura limpia (docs/, scripts/, docker/)
- Clases base OOP (APIResponse, Validator, DataConverter)
- Singletons JS (window.DOM, window.API)
- 4.5 rutas refactorizadas (sin duplicación)
- Documentación completa

Patrón establecido para resto de rutas en:
docs/PATRON_REFACTORIZACION.md

Co-Authored-By: alejandro.paz <alejandro.paz@edisa.com>"

# 4. Verificar que commitió con tu nombre
git log --oneline -1
```

---

## 🌐 10 minutos: Subir a GitHub

```bash
# 1. Crear repositorio en GitHub (web)
# https://github.com/Alexpa112/Home-Stock
# (Cambiar nombre si es diferente)

# 2. Conectar repositorio local con remoto
git remote add origin https://github.com/Alexpa112/Home-Stock.git
git branch -M main
git push -u origin main

# 3. Verificar en GitHub
# Abrir https://github.com/Alexpa112/Home-Stock
# Debe ver tu commit con tu nombre
```

---

## 📖 15 minutos: Entender la Estructura

```bash
# 1. Lee el diagrama
cat docs/00-INICIO.md

# 2. Lee las reglas que debes seguir
cat CLAUDE.md

# 3. Lee tu guía de desarrollo
cat docs/DESARROLLO.md

# 4. Entiende la arquitectura
cat docs/ARQUITECTURA.md
```

---

## 🧪 20 minutos: Probar que Funciona

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar aplicación
python run.py
# → http://localhost:5000

# 4. Probar en navegador
# - Crear usuario
# - Crear producto
# - Editar, borrar
# - Ver que funciona

# 5. Ctrl+C para parar servidor
```

---

## ✅ Checklist de Primeros Pasos

- [ ] Git configurado con tu nombre
- [ ] Primer commit hecho
- [ ] Repo subido a GitHub
- [ ] Leído CLAUDE.md (reglas)
- [ ] Leído docs/00-INICIO.md (diagrama)
- [ ] Entorno virtual funcionando
- [ ] App probada (python run.py)
- [ ] Navegador: http://localhost:5000

---

## 🎯 Próxima Tarea

### Opción A: Completar refactorización (20 min)
```bash
# Sigue docs/PATRON_REFACTORIZACION.md
# Refactoriza: auth.py, historial.py, tickets.py, ocr_tickets.py, paginas.py
```

### Opción B: Frontend OOP (2-3 horas)
```bash
# Crea stockhogar/static/modules/
# Refactoriza app.js con clases Manager
# Usa window.DOM y window.API singletons
```

### Opción C: Tests (2-3 horas)
```bash
# pytest backend
# vitest frontend
# Apunta a >80% cobertura
```

---

## 📚 Referencias Rápidas

| Necesito | Leo |
|----------|------|
| Entender estructura | docs/00-INICIO.md |
| Mis reglas | CLAUDE.md |
| Cómo desarrollar | docs/DESARROLLO.md |
| Arquitectura técnica | docs/ARQUITECTURA.md |
| Patrón para nuevas rutas | docs/PATRON_REFACTORIZACION.md |
| Referencia rápida | QUICKSTART.md |
| Cómo instalar | docs/INSTALACION.md |
| API endpoints | docs/API.md |
| Problemas | docs/TROUBLESHOOTING.md |

---

## 🆘 Si Algo Falla

### Git config no guarda
```bash
# Config local (solo este repo)
git config user.name "alejandro.paz"
git config user.email "alejandro.paz@edisa.com"

# Verificar
git config --list | grep user
```

### python run.py no funciona
```bash
# 1. Verificar entorno virtual
which python  # (o where python en Windows)
# Debe mostrar algo como: venv/bin/python

# 2. Reinstalar dependencias
pip install -r requirements.txt

# 3. Limpiar caché
python -m compileall stockhogar/ -b
rm -rf stockhogar/__pycache__
```

### App no abre en navegador
```bash
# 1. Verifica que sigue ejecutándose
# (no debe mostrar error en terminal)

# 2. Intenta en otro navegador
# http://localhost:5000

# 3. Revisa los logs
# (en la terminal donde ejecutas python run.py)

# 4. Revisa docs/TROUBLESHOOTING.md
```

---

## 🎉 Estás Listo

El proyecto está:
- ✅ Refactorizado (OOP + DRY)
- ✅ Documentado (7 guías)
- ✅ Estructurado (limpio, escalable)
- ✅ Listo para GitHub

**Ahora solo sigue las reglas en CLAUDE.md y disfruta desarrollando.**

---

**Próxima lectura**: `docs/DESARROLLO.md` cuando estés listo para codificar.
