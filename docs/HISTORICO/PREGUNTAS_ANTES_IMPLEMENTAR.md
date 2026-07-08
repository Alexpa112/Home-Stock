# Preguntas Finales Antes de Implementar

Tengo el **plan 100% documentado**, pero antes de empezar a tocar código, necesito clarificar algunos detalles:

---

## 1️⃣ Prioridad: ¿Por dónde empezamos?

**Opción A:** 
- Primero solucionar problemas críticos (iOS teclado, scroll, zoom)
- Luego integrar listas compartidas
- **Tiempo:** 4-5 horas total

**Opción B:**
- Implementar todo junto (problemas + listas)
- **Tiempo:** 5-6 horas total, pero más complejo de testear

**¿Cuál prefieres?**

---

## 2️⃣ Listas Compartidas: ¿Necesitabas esto AHORA o DESPUÉS?

Recordando que:
- La API de listas compartidas YA ESTÁ lista (Bring! model)
- La UI en móvil es lo nuevo
- Stock + Compra seguirá funcionando igual

**Opciones:**
- **A)** Implementar listas compartidas junto con el redesño (todo junto)
- **B)** Primero arreglar móvil, luego añadir UI de listas compartidas en otra sesión
- **C)** Otro timeline

**¿Cuál?**

---

## 3️⃣ Cambios en Estructura HTML: ¿Estás cómodo?

El plan propone:
- Cambiar selector de "espacios" por selector de "listas"
- Añadir modal nuevo para cambiar listas
- Preservar TODO lo demás (tabs, FAB, modales de producto/compra)

**¿Algo que NO quieras cambiar?**

---

## 4️⃣ Interacción en Móvil: ¿Confirmamos este flujo?

**Flujo propuesto:**

```
Usuario abre app en móvil
    ↓
Ve cabecera + selector de lista actual
    ↓
Ve tabs (Stock | Compra)
    ↓
Toca selector de lista
    ↓
Se abre modal flotante con:
  - Mis listas (propias)
  - Listas compartidas conmigo
    ↓
Toca una lista
    ↓
Cambio inmediato + contenido recarga
    ↓
Modal se cierra
```

**¿Te parece bien este flujo o lo cambio?**

---

## 5️⃣ Función "Escanear Ticket" (OCR): ¿Probó bien?

El modal de escaneo:
- Abre cámara (fotografía)
- OCR extrae productos + cantidades
- Muestra modal editable
- Procesa datos

**Preguntas:**
- **A)** ¿Este modal también necesita ser redimensionable con teclado?
- **B)** ¿O es menos crítico (rara vez usas en móvil)?

**Respuesta:**

---

## 6️⃣ Acceso a Listas: ¿Necesita autenticación extra?

En el plan:
- GET `/api/listas` devuelve las que tienes acceso
- El cambio de lista es local (localStorage)

**Pregunta:**
- **A)** ¿Quieres que al cambiar de lista se haga una petición al servidor para validar?
- **B)** ¿O simplemente cargar localmente sin validar?

**Recomendación:** A (más seguro)

**¿Cuál?**

---

## 7️⃣ Datos Persistentes: ¿Cómo guardamos "lista actual"?

**Opciones:**
- **A)** `localStorage.getItem('lista-actual')` - Persiste en el navegador
- **B)** `sessionStorage` - Solo mientras está abierta la pestaña
- **C)** Sincronizar con servidor (cada cambio = petición POST)

**¿Cuál prefieres?**

---

## 8️⃣ Pantalla Inicial: ¿Qué se carga primero?

**Caso de uso:**
Usuario abre la app por primera vez en una sesión

**Opciones:**
- **A)** Cargar última lista usada (desde localStorage)
- **B)** Cargar lista "predeterminada" (la primera propia)
- **C)** Mostrar selector de lista (modal) al iniciar

**¿Cuál?**

---

## 9️⃣ Visual: ¿El selector de lista debería verse así?

```
┌──────────────────────────────────┐
│ 📋 Supermercado [PROPIETARIO] ▾  │
└──────────────────────────────────┘
```

**Opciones:**
- **A)** Sí, exactamente así (icono + nombre + rol + flecha)
- **B)** Más pequeño (solo icono + nombre)
- **C)** Diferente (propón)

**¿Cuál?**

---

## 🔟 Testing: ¿Disponibilidad de dispositivos?

Necesito saber:
- ¿Tienes iPhone con iOS 18 para testing? ¿Cuál modelo?
- ¿Tienes dispositivo Android? ¿Cuál versión?
- ¿Puedo testear en un navegador (DevTools) o necesito device físico?

**Dispositivos para testing:**

---

## 1️⃣1️⃣ Animaciones: ¿Quieres transiciones suaves?

Propongo:
- Modal aparece con animación suave (300ms)
- Cambio de lista = animación fade
- Teclado abierto = transición smooth

**¿Sí o mantenemos todo instant?**

---

## 1️⃣2️⃣ Modo Oscuro: ¿Sigue igual?

El CSS tiene soporte para dark mode.
**¿Seguir usando `prefers-color-scheme` + `data-theme`?**

---

## 1️⃣3️⃣ Compatibilidad: ¿Necesitas soportar navegadores viejos?

- iOS 15? (versión anterior a iOS 18)
- Android 10? (versión antigua)

**¿O solo iOS 17+ y Android 12+?**

---

## 1️⃣4️⃣ Performance: ¿Hay límite de listas?

Si un usuario tiene:
- 1-5 listas propias → rápido
- 20 listas compartidas → cuesta más

**¿Necesitas paginación en el modal o todo de una vez?**

---

## 1️⃣5️⃣ Comportamiento del FAB (+): ¿Se sube con teclado?

Propuesta en el plan:
```javascript
body.keyboard-open .fab {
  bottom: calc(16px + keyboard-height);
}
```

**Resultado:** Cuando el teclado abre, el FAB sube para no quedar debajo.

**¿Te parece bien o prefieres que se quede fijo?**

---

## 🎯 Resumen de lo que Necesito Saber

Responde en orden:

1. **Prioridad:** ¿A o B? (crítico vs. todo)
2. **Listas compartidas:** ¿Ahora o después?
3. **Cambios HTML:** ¿Alguna restricción?
4. **Flujo móvil:** ¿Confirmas el propuesto?
5. **Escaneo ticket:** ¿También redimensionar?
6. **Auth en cambio de lista:** ¿A o B?
7. **Persistencia:** ¿localStorage, sessionStorage o servidor?
8. **Pantalla inicial:** ¿Última lista, predeterminada o selector?
9. **Visual selector:** ¿Tal como propuesto?
10. **Testing:** ¿Qué dispositivos tienes?
11. **Animaciones:** ¿Suaves o instantáneas?
12. **Dark mode:** ¿Seguir igual?
13. **Navegadores viejos:** ¿Necesario soportar?
14. **Performance:** ¿Paginación en listas?
15. **FAB con teclado:** ¿Se sube o fijo?

---

## 📋 Una vez responda estas 15 preguntas...

Podré:
- [x] Empezar a implementar con confianza
- [x] No hacer cambios innecesarios
- [x] Asegurar que el resultado te guste
- [x] Hacer testing correcto

**Adelante cuando estés listo.** 🚀

