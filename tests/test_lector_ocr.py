"""Mejoras del lector: iluminacion, lineas perdidas, basura, segunda pasada, cuadre."""
import unittest
from unittest.mock import patch

import numpy as np

from stockhogar.integraciones import ticket_ocr as o
from stockhogar.servicios.ocr.procesador_imagen import ProcesadorImagen
from stockhogar.servicios.ocr.reconstructor_espacial import LineaReconstruida, Palabra


def _linea(texto, y, izquierda=20, ancho=400, conf=90.0):
    return LineaReconstruida(palabras=[Palabra(texto, izquierda, y - 10, ancho, 20, conf)])


class AplanarIluminacionTests(unittest.TestCase):
    def test_una_sombra_en_un_lado_se_iguala(self):
        papel = np.full((400, 600), 220, dtype=np.uint8)
        papel[150:160, 50:550] = 30                           # un trazo de texto
        sombra = (np.linspace(1.0, 0.25, 600)[None, :] * papel).astype(np.uint8)  # lado derecho oscuro
        plano = ProcesadorImagen._aplanar_iluminacion(sombra)
        fondo_izq, fondo_dcha = plano[300, 20:80].mean(), plano[300, 520:580].mean()
        self.assertLess(abs(float(fondo_izq) - float(fondo_dcha)), 25)
        self.assertGreater(float(sombra[300, 20:80].mean()) - float(sombra[300, 520:580].mean()), 80)

    def test_el_texto_sigue_siendo_mas_oscuro_que_el_papel(self):
        papel = np.full((400, 600), 220, dtype=np.uint8)
        papel[150:160, 50:550] = 30
        plano = ProcesadorImagen._aplanar_iluminacion(papel)
        self.assertLess(int(plano[155, 300]), int(plano[300, 300]) - 100)


class BasuraTests(unittest.TestCase):
    def test_reconoce_bordes_y_rayas(self):
        for t in ("A |", "y am - y - - o ¡", "¡ +. ..b..“<XL£. noe ono... e. ...RAK(. e .onenko.. Xo.o. en. e. cen. o oso. o... ..o..en .. e... .o oo ¡",
                  "— — — — — —", "I PIDA PAPA PPD PAPA PIPA AAA PAPA AAA PA PDA AA l"):
            with self.subTest(t=t):
                self.assertTrue(o._es_basura(t, 60))

    def test_no_descarta_lineas_reales(self):
        for t in ("LECHE ENTERA 1L 0,89", "2 x 1,85", "0,850 kg x 1,89 EUR/kg", "PAN", "TOTAL 23,68", "Tarjeta de credito",
                  "400137 MEJILLON ESCABECHE 3,00", "CIF A-28425270", "PAN DE MOLDE", "AGUA MINERAL", "ZUMO DE NARANJA"):
            with self.subTest(t=t):
                self.assertFalse(o._es_basura(t, 80))

    def test_una_linea_con_importe_nunca_es_basura(self):
        self.assertFalse(o._es_basura("¡¡ .. 1,85", 10))


class LineasPerdidasTests(unittest.TestCase):
    def test_un_hueco_grande_se_lee_y_se_inserta(self):
        lineas = [_linea("A 1,00", 100), _linea("B 2,00", 130), _linea("C 3,00", 160), _linea("E 5,00", 250)]
        gris = np.full((400, 600), 255, dtype=np.uint8)
        with patch.object(o, "_leer_recorte", return_value=("4 x 1,50", 80.0)) as leer:
            nuevas = o._recuperar_lineas_perdidas(lineas, gris)
        self.assertTrue(leer.called)
        self.assertEqual(nuevas[0][1], "4 x 1,50")
        self.assertTrue(160 < nuevas[0][0] < 250)

    def test_sin_hueco_no_lee_nada(self):
        lineas = [_linea(f"L{i} 1,00", 100 + 30 * i) for i in range(6)]
        with patch.object(o, "_leer_recorte") as leer:
            self.assertEqual(o._recuperar_lineas_perdidas(lineas, np.zeros((400, 600), np.uint8)), [])
        leer.assert_not_called()


class LineasTruncadasTests(unittest.TestCase):
    def test_detecta_el_nombre_sin_importe_y_corto(self):
        lineas = [_linea("LECHE 1,00", 100), _linea("PAN 1,00", 130, ancho=400), _linea("BEBIDA SOJA", 160, ancho=120),
                  _linea("ARROZ 1,35", 190)]
        self.assertEqual(o._lineas_truncadas(lineas), [2])

    def test_no_marca_la_cabecera(self):
        lineas = [_linea("TIENDA CENTRAL", 40, ancho=100)] + [_linea(f"A{i} 1,0{i}", 100 + 30 * i) for i in range(4)]
        self.assertEqual(o._lineas_truncadas(lineas), [])


class SegundaPasadaTests(unittest.TestCase):
    def _llamar(self, resultados):
        pasadas = iter(resultados)
        with patch.object(o, "_procesador_imagen") as proc, \
                patch.object(o, "_leer_pagina", side_effect=lambda g: next(pasadas)), \
                patch.object(o, "_texto_con_relectura", side_effect=lambda l, g: "|".join(x.texto for x in l)), \
                patch("builtins.open", unittest.mock.mock_open(read_data=b"x")):
            proc.procesar.side_effect = lambda b, suavizado=0: np.full((10, 10), suavizado, np.uint8)
            texto = o.extraer_texto("x.jpg")
            return texto, proc.procesar.call_count

    def test_lectura_buena_no_repite(self):
        texto, n = self._llamar([([_linea("BUENA 1,00", 50)], 95.0)])
        self.assertEqual((texto, n), ("BUENA 1,00", 1))

    def test_lectura_floja_prueba_suavizado_y_se_queda_la_mejor(self):
        texto, n = self._llamar([([_linea("MALA", 50)], 70.0), ([_linea("MEJOR 1,00", 50)], 88.0)])
        self.assertEqual((texto, n), ("MEJOR 1,00", 2))

    def test_si_la_segunda_es_peor_se_queda_la_primera(self):
        texto, n = self._llamar([([_linea("PRIMERA", 50)], 80.0), ([_linea("SEGUNDA", 50)], 60.0)])
        self.assertEqual(texto, "PRIMERA")


if __name__ == "__main__":
    unittest.main()
