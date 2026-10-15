# Pruebas multiusuario

Simulan varios usuarios entrando a la vez contra una instancia en marcha
(frontend en `:3000`, backend en `:5000`, gunicorn con `--keep-alive 75` como en Docker).
El registro tiene limite de 10/hora por IP: reinicia el backend entre ejecuciones.

- `escenario_hogar_compartido.py`: 8 usuarios, hogar compartido, stock, compra, gastos, recetas, ajustes.
- `escenario_carga_30_usuarios.py`: 30 logins y escrituras simultaneas, reautenticacion, fuerza bruta.
- `ui_tres_usuarios.js` / `ui_rol_solo_lectura.js`: navegador real (Playwright), 3 usuarios a la vez
  (uno movil) y comprobacion del rol "ver". `NODE_PATH` debe apuntar a `node_modules` con playwright.
