from pathlib import Path
from docx import Document
from docx.text.paragraph import Paragraph
from docx.table import Table
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
import re

ORIGEN = Path("docs/word")
DESTINO = Path("docs/preparados")


def extraer_contenido(ruta):
    documento = Document(ruta)
    partes = []

    # Recorre párrafos y tablas en el orden en que aparecen en Word.
    for elemento in documento.element.body.iterchildren():
        if isinstance(elemento, CT_P):
            parrafo = Paragraph(elemento, documento)
            texto = parrafo.text.strip()

            if texto:
                partes.append(texto)

        elif isinstance(elemento, CT_Tbl):
            tabla = Table(elemento, documento)
            filas = []

            for fila in tabla.rows:
                celdas = [
                    re.sub(r"\s+", " ", celda.text).strip()
                    for celda in fila.cells
                ]
                if any(celdas):
                    filas.append(" | ".join(celdas))

            if filas:
                partes.append("[TABLA]")
                partes.extend(filas)
                partes.append("[FIN DE TABLA]")

    return partes


def numero_volumen(ruta):
    coincidencia = re.search(r"Volumen\s+(\d+)", ruta.stem, re.IGNORECASE)
    return int(coincidencia.group(1)) if coincidencia else 999


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    archivos = sorted(
        ORIGEN.glob("*.docx"),
        key=lambda ruta: (numero_volumen(ruta), ruta.name)
    )

    if not archivos:
        print(f"No se encontraron archivos .docx en {ORIGEN}")
        return

    procesados = set()

    for archivo in archivos:
        numero = numero_volumen(archivo)

        if numero == 999:
            print(f"AVISO: no se identificó el volumen de {archivo.name}")
            continue

        if numero in procesados:
            print(
                f"AVISO: hay más de un Word para el volumen {numero}. "
                f"Se omite el duplicado: {archivo.name}"
            )
            continue

        contenido = extraer_contenido(archivo)

        if not contenido:
            print(f"AVISO: el documento no contiene texto: {archivo.name}")
            continue

        salida = DESTINO / f"volumen_{numero}.txt"
        encabezado = [
            f"ATTELIA — BASE DE CONOCIMIENTO — VOLUMEN {numero}",
            f"Documento original: {archivo.name}",
            "Nota: las tablas se representan separando sus celdas con |.",
            "",
        ]

        salida.write_text(
            "\n".join(encabezado + contenido) + "\n",
            encoding="utf-8"
        )

        procesados.add(numero)
        print(
            f"OK: Volumen {numero} | "
            f"{len(contenido)} bloques | "
            f"{salida.stat().st_size:,} bytes"
        )

    print(f"\nArchivos preparados en: {DESTINO}")


if __name__ == "__main__":
    main()
