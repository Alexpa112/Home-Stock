"""Test de regresión: facturas de mayorista/"cash and carry" (p.ej. Cash
Galicia) tienen una cabecera mucho mas larga que un ticket de super normal
(razon social, direccion, CIF, cajero, fecha/hora, Y ADEMAS una fila de
encabezados de columna: "Descripcion del Articulo ... Cantidad ...
Precio") y un pie de pagina largo (resumen de IVA por tramos, numero de
sorteo, texto legal de proteccion de datos).

Antes de este fix, ParserMejorado colaba TODO eso como si fueran productos
(28 "items" en vez de los 8 reales): _detectar_inicio_productos limitaba
la busqueda a 12 lineas (insuficiente para esta cabecera) y no reconocia
la fila de encabezados de columna como marcador de inicio; y aunque
_detectar_fin_productos cortaba en "Total Bultos", nada evitaba que la
cabecera larga se colase entera al principio.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockhogar.servicios.ocr.parser_mejorado import ParserMejorado


TICKET_MAYORISTA = """ca * gus
alicia D
9 AUTOSERVICIO MAYORISTA
PARA LA HOSTELERÍA Y EL COMERCIO j AN —
| Comercial Martínez Sánchez, S.L. 5d CASH
e Carretera de Bayona Interior, 48 - 36213 Vigo. Teléfooo 986 213 771 E
E CE. B-36.010.031 // Hoja PO-5556 IRUS: 1000086 Poli ni ¡ón $1.
18 ¡Registro Sanitario: 40 17214/PO /1/ e-mail: A, co A VIGO
Factura Simplificada! VENTAS AL POR
LE ATENDIO EL CAJERO: Noe (Vigo) MENOR AL
CA A CONTADO
A AN E
; TS ns E % | Precio
A AE
Descripción del Artículo Cantidad b VA] «LVA
02728-01 or| TOMATE FRITO SOLIS 725 GRS. 5 s| 1,69 8,45] 10] 1,86
20255-01 GOMINOLAS FINI SOUR BOOM MIX 500 GRS. ] 115;ss 3,85] 10| 4,24
21108-01 | COCTEL EL NOGAL MIX SALADO N'3 B/2KG 1 ¡7,98 7.98) 10] 8.78
2327-01 HOT DOG HERMANOS JUAN 12 UDS. 1 1] 2,64 2,64] 4 2,75
661,01 DESODORANTE AXE LEATHER/COOKIES 150 ML. 1 1. 3,95 395] 21| 4,78
21871-01 INSECTICIDA MATON RESIDUAL RASTREROS 600 ] 14,95 a9s| 21] 5,99
16348-01 INSECTICIDA VINFER MATON VOLADORES 750 M 1 329 329) 21] 3,98
10881-03 (€ ERV LA MAHOU MIXTA SHANDY LATA 33 01 Es 1 24 0,48 11,52] 21 0,58
, Total Bultos: | 12 Importe |1.V.A. NAO
y, 1 E,
ES,
L _—_ ERE —a y A > _A—>2 _ __— -=>>— >>
20 2,03 53,75 EUR |
18 es : poli? ESTA F ACTURA SIMPLIFICADA
2 o o o dom
O E » 150 o
E E 208 Ear. 20 N* Sorteo 50 A .
A A ños: 265395
"""


def test_factura_mayorista_reconoce_solo_los_8_articulos():
    parser = ParserMejorado()
    productos = parser.parsear(TICKET_MAYORISTA)

    assert len(productos) == 8

    nombres = [p.nombre.lower() for p in productos]
    assert any("tomate" in n for n in nombres)
    assert any("gominolas" in n for n in nombres)
    assert any("coctel" in n for n in nombres)
    assert any("hot dog" in n for n in nombres)
    assert any("desodorante" in n for n in nombres)
    assert any("insecticida maton residual" in n for n in nombres)
    assert any("insecticida vinfer" in n for n in nombres)
    assert any("mahou" in n for n in nombres)

    # Nada de cabecera (razon social, CIF, cajero) ni pie (IVA, sorteo,
    # texto legal) debe colarse como producto.
    texto_completo = " ".join(nombres)
    for ruido in ("cash", "autoservicio", "cajero", "sorteo", "simplificada", "bultos"):
        assert ruido not in texto_completo

    # Los codigos de articulo (p.ej. "02728-01") no deben quedar pegados
    # al nombre del producto.
    for nombre in nombres:
        assert not any(ch.isdigit() for ch in nombre[:8])
