import json
import re
from pathlib import Path
from collections import Counter

BASE = Path("data/datasets/polyvore-github")
ORIGEN = BASE / "extraido" / "train_no_dup.json"
MAPA_CATEGORIAS = BASE / "category_id.txt"
SALIDA = BASE / "procesado" / "train_outfits.jsonl"

# Cargar las categorías del dataset.
categorias = {}

with MAPA_CATEGORIAS.open(encoding="utf-8") as archivo:
    for linea in archivo:
        partes = linea.strip().split(maxsplit=1)
        if len(partes) == 2:
            categorias[partes[0]] = partes[1]


def limpiar_nombre(valor):
    """Normaliza el nombre sin inventar características de la prenda."""
    if not isinstance(valor, str):
        return ""

    nombre = re.sub(r"\s+", " ", valor).strip()
    return nombre


def es_nombre_util(nombre):
    """Descarta nombres vacíos o registros genéricos del dataset."""
    if not nombre:
        return False

    if nombre.casefold() in {
        "polyvore",
        "clothing",
        "unknown",
        "none",
        "null",
    }:
        return False

    return True


with ORIGEN.open(encoding="utf-8") as archivo:
    outfits = json.load(archivo)

SALIDA.parent.mkdir(parents=True, exist_ok=True)

total_originales = len(outfits)
total_guardados = 0
total_descartados = 0
prendas_originales = 0
prendas_guardadas = 0
categorias_contadas = Counter()
ejemplos = []

with SALIDA.open("w", encoding="utf-8") as salida:
    for outfit in outfits:
        items_originales = outfit.get("items", [])
        prendas_originales += len(items_originales)

        items_limpios = []
        nombres_vistos = set()

        for item in items_originales:
            nombre = limpiar_nombre(item.get("name", ""))

            if not es_nombre_util(nombre):
                continue

            # Evitar repetir el mismo nombre dentro del conjunto.
            clave = nombre.casefold()
            if clave in nombres_vistos:
                continue
            nombres_vistos.add(clave)

            categoria_id = str(item.get("categoryid", ""))
            categoria = categorias.get(
                categoria_id,
                "Categoría sin descripción"
            )

            prenda = {
                "nombre": nombre,
                "categoria": categoria,
                "categoria_id": categoria_id,
            }

            items_limpios.append(prenda)
            categorias_contadas[categoria] += 1

        # Un conjunto debe tener al menos tres prendas útiles.
        if len(items_limpios) < 3:
            total_descartados += 1
            continue

        nombre_conjunto = limpiar_nombre(outfit.get("name", ""))
        descripcion = limpiar_nombre(outfit.get("desc", ""))

        texto = (
            f"Conjunto de moda: {nombre_conjunto or 'Sin título'}.\n"
            "Prendas que aparecen juntas en el conjunto:\n"
        )

        for prenda in items_limpios:
            texto += (
                f"- {prenda['nombre']} "
                f"(categoría: {prenda['categoria']}).\n"
            )

        if descripcion:
            texto += f"Descripción original: {descripcion}\n"

        registro = {
            "set_id": str(outfit.get("set_id", "")),
            "nombre_conjunto": nombre_conjunto,
            "items": items_limpios,
            "texto": texto.strip(),
        }

        salida.write(
            json.dumps(registro, ensure_ascii=False) + "\n"
        )

        total_guardados += 1
        prendas_guardadas += len(items_limpios)

        if len(ejemplos) < 3:
            ejemplos.append(registro)

print("\n=== RESULTADO DEL PROCESAMIENTO ===")
print(f"Conjuntos originales: {total_originales}")
print(f"Conjuntos guardados: {total_guardados}")
print(f"Conjuntos descartados: {total_descartados}")
print(f"Prendas originales: {prendas_originales}")
print(f"Prendas guardadas: {prendas_guardadas}")
print(f"Archivo generado: {SALIDA}")

print("\n=== CATEGORÍAS MÁS FRECUENTES ===")
for categoria, cantidad in categorias_contadas.most_common(15):
    print(f"{categoria}: {cantidad}")

print("\n=== EJEMPLOS PROCESADOS ===")
for ejemplo in ejemplos:
    print("\n" + ejemplo["texto"])
    print("-" * 50)
