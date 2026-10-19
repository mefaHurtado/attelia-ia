
from pathlib import Path
import json

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings


ARCHIVO_DATASET = Path(
    "data/datasets/polyvore-github/procesado/train_outfits.jsonl"
)

DIRECTORIO_CHROMA = "data/chroma"
NOMBRE_COLECCION = "attelia_polyvore"
MODELO_EMBEDDINGS = "bge-m3"

TAMANO_LOTE = 50


def obtener_vectorstore_polyvore():
    """Abre la colección independiente de conjuntos Polyvore."""
    return Chroma(
        collection_name=NOMBRE_COLECCION,
        embedding_function=OllamaEmbeddings(
            model=MODELO_EMBEDDINGS
        ),
        persist_directory=DIRECTORIO_CHROMA,
    )


def preparar_documento(registro):
    """Convierte un conjunto en un documento buscable."""

    set_id = str(registro["set_id"])
    nombre = str(registro.get("nombre_conjunto", "Sin título"))

    items = registro.get("items", [])

    prendas = []
    categorias = []

    for item in items:
        nombre_prenda = str(item.get("nombre", "")).strip()
        categoria = str(item.get("categoria", "")).strip()

        if nombre_prenda:
            prendas.append(nombre_prenda)

        if categoria:
            categorias.append(categoria)

    # Construimos el texto a partir de los campos procesados.
    # Así no dependemos únicamente del título original.
    contenido = (
        f"Conjunto de moda: {nombre}\n"
        f"Identificador del conjunto: {set_id}\n"
        f"Prendas: {', '.join(prendas)}\n"
        f"Categorías: {', '.join(sorted(set(categorias)))}\n"
        f"Descripción adicional: {registro.get('texto', '')}"
    )

    documento = Document(
        page_content=contenido,
        metadata={
            "source": "Polyvore",
            "set_id": set_id,
            "nombre_conjunto": nombre[:500],
            "cantidad_prendas": len(prendas),
            "categorias": ", ".join(sorted(set(categorias)))[:2000],
            "prendas": ", ".join(prendas)[:4000],
        },
    )

    # ID estable: volver a ejecutar el indexador actualiza
    # los mismos conjuntos en lugar de crear IDs nuevos.
    identificador = f"polyvore_{set_id}"

    return documento, identificador


def indexar_polyvore():
    """Indexa los conjuntos por lotes sin borrar la colección."""

    if not ARCHIVO_DATASET.exists():
        raise FileNotFoundError(
            f"No se encontró el dataset: {ARCHIVO_DATASET}"
        )

    base = obtener_vectorstore_polyvore()

    print(f"Colección: {NOMBRE_COLECCION}")
    print("Registros existentes:", base._collection.count())
    print("Preparando indexación de Polyvore...")

    lote_documentos = []
    lote_ids = []
    procesados = 0
    omitidos = 0

    with ARCHIVO_DATASET.open(encoding="utf-8") as archivo:
        for numero_linea, linea in enumerate(archivo, start=1):
            if not linea.strip():
                continue

            try:
                registro = json.loads(linea)

                if not registro.get("set_id") or not registro.get("items"):
                    omitidos += 1
                    continue

                documento, identificador = preparar_documento(registro)

                lote_documentos.append(documento)
                lote_ids.append(identificador)

            except (json.JSONDecodeError, KeyError, TypeError) as error:
                omitidos += 1
                print(
                    f"Registro omitido en línea {numero_linea}: {error}"
                )
                continue

            if len(lote_documentos) >= TAMANO_LOTE:
                base.add_documents(
                    documents=lote_documentos,
                    ids=lote_ids,
                )

                procesados += len(lote_documentos)

                print(f"Procesados: {procesados:,} conjuntos")

                lote_documentos = []
                lote_ids = []

    # Guardar el último lote, si quedaron registros pendientes.
    if lote_documentos:
        base.add_documents(
            documents=lote_documentos,
            ids=lote_ids,
        )
        procesados += len(lote_documentos)

    print("\nIndexación de Polyvore terminada.")
    print(f"Colección: {NOMBRE_COLECCION}")
    print(f"Conjuntos procesados: {procesados:,}")
    print(f"Registros omitidos: {omitidos:,}")
    print(f"Total de registros en la colección: {base._collection.count()}")

    return base


if __name__ == "__main__":
    indexar_polyvore()
