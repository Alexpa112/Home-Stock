"""Regresiones de rendimiento del backend: fijan la FORMA de las consultas,
no los milisegundos (que dependen de la maquina y harian el test inestable).

Dos defectos medidos que estos tests impiden que vuelvan:

  1. GET /api/gastos consultaba los participantes gasto por gasto. Con 300
     gastos eran 308 sentencias SQL por peticion; ahora son 9, y no crecen al
     añadir gastos. El coste real no se veia aqui sino en la Raspberry Pi,
     donde cada consulta paga la latencia de la tarjeta SD.

  2. Las mismas rutas seleccionaban "g.*", que arrastra imagen_recibo (la foto
     del recibo, un BLOB) para usarla solo como bool(...). Medido: 300 gastos
     con recibos de 300 KB movian 88 MB de disco en cada peticion, y solo para
     saber si cada gasto tenia foto o no.
"""
import io
import unittest
import uuid

from PIL import Image
from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


def _jpeg_de_prueba(lado=1) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (lado, lado), color="red").save(buffer, format="JPEG")
    return buffer.getvalue()


class ConexionEspia:
    """Envuelve la conexion de SQLite y registra cada SQL ejecutada."""

    def __init__(self, real):
        self._real = real
        self.sentencias = []

    def execute(self, sql, *args, **kwargs):
        self.sentencias.append(" ".join(sql.split()))
        return self._real.execute(sql, *args, **kwargs)

    def __getattr__(self, nombre):
        return getattr(self._real, nombre)


class ConsultasDeGastosTests(unittest.TestCase):
    N_GASTOS = 25

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.cliente = self.app.test_client()

        sufijo = uuid.uuid4().hex[:8]
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (f"perf_{sufijo}", generate_password_hash("password123"), ahora()),
            )
            self.usuario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, ?, ?)",
                (f"Hogar perf {sufijo}", self.usuario_id, ahora(), ahora()),
            )
            self.hogar_id = cur.lastrowid

            # Un segundo miembro: asi cada gasto tiene 2 participantes y el
            # agrupado por gasto_id se ejercita de verdad.
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (f"perf2_{sufijo}", "x", ahora()),
            )
            self.otro_id = cur.lastrowid
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) "
                "VALUES (?, ?, 'editar', ?)",
                (self.hogar_id, self.otro_id, ahora()),
            )

            foto = _jpeg_de_prueba()
            for i in range(self.N_GASTOS):
                cur = db.execute(
                    "INSERT INTO gastos (hogar_id, descripcion, importe_total, fecha, usuario_pagador_id, "
                    "fecha_creacion, imagen_recibo, imagen_recibo_mime) VALUES (?, ?, ?, ?, ?, ?, ?, 'image/jpeg')",
                    (self.hogar_id, f"Gasto {i}", 10.0, f"2026-0{1 + i % 9}-01",
                     self.usuario_id, ahora(), foto),
                )
                gasto_id = cur.lastrowid
                for miembro in (self.usuario_id, self.otro_id):
                    db.execute(
                        "INSERT INTO gastos_participantes (gasto_id, usuario_id, importe) VALUES (?, ?, 5.0)",
                        (gasto_id, miembro),
                    )
            db.commit()

        with self.cliente.session_transaction() as sess:
            sess["usuario"] = f"perf_{sufijo}"
            sess["usuario_id"] = self.usuario_id
            sess["hogar_actual_id"] = self.hogar_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM usuarios WHERE id IN (?, ?)", (self.usuario_id, self.otro_id))
            db.commit()

    def _espiar(self, ruta):
        """Ejecuta la peticion contando las sentencias SQL que emite."""
        import stockhogar.db as modulo_db

        espias = []
        original = modulo_db.get_db

        def get_db_espiado():
            real = original()
            if not espias:
                espias.append(ConexionEspia(real))
            return espias[0]

        modulo_db.get_db = get_db_espiado
        # Los modulos de rutas importaron get_db por nombre, hay que sustituirlo ahi.
        import stockhogar.rutas.gastos as rutas_gastos
        import stockhogar.servicios.stock as servicio_stock
        originales = []
        for modulo in (rutas_gastos, servicio_stock):
            if hasattr(modulo, "get_db"):
                originales.append((modulo, modulo.get_db))
                modulo.get_db = get_db_espiado
        try:
            respuesta = self.cliente.get(ruta)
        finally:
            modulo_db.get_db = original
            for modulo, fn in originales:
                modulo.get_db = fn
        return respuesta, (espias[0].sentencias if espias else [])

    def test_listar_gastos_no_consulta_los_participantes_gasto_por_gasto(self):
        respuesta, sentencias = self._espiar("/api/gastos")
        self.assertEqual(respuesta.status_code, 200, respuesta.get_data(as_text=True))
        self.assertEqual(len(respuesta.get_json()), self.N_GASTOS)

        de_participantes = [s for s in sentencias if "gastos_participantes" in s and s.upper().startswith("SELECT")]
        self.assertLessEqual(
            len(de_participantes), 1,
            f"se consultan los participantes {len(de_participantes)} veces para "
            f"{self.N_GASTOS} gastos: ha vuelto el N+1. Sentencias: {de_participantes[:3]}",
        )

    def test_listar_gastos_no_lee_el_blob_de_los_recibos(self):
        """Solo hace falta saber SI hay recibo. Leer la foto de cada gasto para
        descartarla movia megabytes por peticion."""
        respuesta, sentencias = self._espiar("/api/gastos")
        self.assertEqual(respuesta.status_code, 200)

        selects_de_gastos = [
            s for s in sentencias
            if s.upper().startswith("SELECT") and " FROM gastos " in f" {s} "
        ]
        self.assertTrue(selects_de_gastos, "no se detecto la consulta de gastos")
        for sql in selects_de_gastos:
            with self.subTest(sql=sql[:70]):
                self.assertNotIn(
                    "g.*", sql,
                    "SELECT g.* arrastra imagen_recibo (BLOB) sin necesidad",
                )

        # Y la respuesta sigue diciendo la verdad sobre el recibo.
        self.assertTrue(all(g["tiene_recibo"] for g in respuesta.get_json()))

    def test_la_respuesta_conserva_todos_los_participantes_de_cada_gasto(self):
        """El agrupado en una sola consulta no debe perder ni mezclar filas."""
        respuesta, _ = self._espiar("/api/gastos")
        datos = respuesta.get_json()
        for gasto in datos:
            with self.subTest(gasto=gasto["id"]):
                ids = sorted(p["usuario_id"] for p in gasto["participantes"])
                self.assertEqual(ids, sorted([self.usuario_id, self.otro_id]))
                self.assertAlmostEqual(sum(p["importe"] for p in gasto["participantes"]), 10.0, places=2)

    def test_el_recibo_se_sigue_sirviendo(self):
        """_obtener_gasto_con_permiso ya no selecciona la imagen por defecto:
        la ruta del recibo tiene que pedirla explicitamente (con_imagen=True)."""
        gasto_id = self.cliente.get("/api/gastos").get_json()[0]["id"]
        respuesta = self.cliente.get(f"/api/gastos/{gasto_id}/recibo")
        # El cuerpo es un JPEG: no se decodifica para el mensaje de error.
        self.assertEqual(respuesta.status_code, 200, respuesta.status)
        self.assertEqual(respuesta.mimetype, "image/jpeg")
        self.assertGreater(len(respuesta.get_data()), 0)

    def test_exportar_csv_tampoco_consulta_gasto_por_gasto(self):
        respuesta, sentencias = self._espiar("/api/gastos/exportar")
        self.assertEqual(respuesta.status_code, 200, respuesta.get_data(as_text=True))
        de_participantes = [s for s in sentencias if "gastos_participantes" in s and s.upper().startswith("SELECT")]
        self.assertLessEqual(
            len(de_participantes), 1,
            f"la exportacion consulta los participantes {len(de_participantes)} veces",
        )
        # El CSV sigue teniendo una linea por participante de cada gasto.
        lineas = respuesta.get_data(as_text=True).strip().splitlines()
        self.assertGreaterEqual(len(lineas), self.N_GASTOS * 2)


if __name__ == "__main__":
    unittest.main()
