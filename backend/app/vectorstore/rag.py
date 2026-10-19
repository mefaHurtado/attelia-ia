"""Índice Chroma persistente: corpus común + colecciones independientes por usuario.

Las distancias Chroma dependen de la métrica configurada. Ajustar RAG_MAX_DISTANCE
con consultas de prueba después de indexar; un umbral no es una garantía de verdad.
"""
from pathlib import Path
import hashlib
import os
import re
import unicodedata
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

ROOT = Path(__file__).resolve().parents[3]
DIRECTORIO_DOCUMENTOS = ROOT / "docs" / "preparados"
DIRECTORIO_CHROMA = str(Path(os.getenv("CHROMA_DIR", str(ROOT / "data" / "chroma"))).resolve())
NOMBRE_COLECCION = "attelia_conocimiento"
MODELO_EMBEDDINGS = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")


def obtener_embeddings():
    return OllamaEmbeddings(model=MODELO_EMBEDDINGS, base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))


def obtener_vectorstore(usuario_id=None):
    nombre = NOMBRE_COLECCION if usuario_id is None else f"attelia_usuario_{int(usuario_id)}"
    return Chroma(collection_name=nombre, embedding_function=obtener_embeddings(), persist_directory=DIRECTORIO_CHROMA)


def cargar_documentos():
    archivos = sorted(DIRECTORIO_DOCUMENTOS.glob("volumen_*.txt"), key=lambda a: int(re.search(r"volumen_(\d+)", a.stem).group(1)))
    if not archivos:
        raise FileNotFoundError(f"Falta la base documental en {DIRECTORIO_DOCUMENTOS}")
    return [Document(page_content=a.read_text(encoding="utf-8"), metadata={"source": a.name, "volumen": int(re.search(r"volumen_(\d+)", a.stem).group(1))}) for a in archivos]


def dividir_documentos(documentos):
    return RecursiveCharacterTextSplitter(chunk_size=1100, chunk_overlap=160, separators=["\n\n", "\n", ". ", " ", ""]).split_documents(documentos)


def generar_id(documento, indice):
    return hashlib.sha256(f"{documento.metadata.get('source')}|{indice}|{documento.page_content}".encode()).hexdigest()


def indexar_documentos():
    """Se ejecuta una vez con Ollama activo; no indexa automáticamente cada arranque."""
    fragmentos = dividir_documentos(cargar_documentos())
    base = obtener_vectorstore()
    for inicio in range(0, len(fragmentos), 40):
        lote = fragmentos[inicio:inicio+40]
        base.add_documents(lote, ids=[generar_id(doc, inicio+i) for i, doc in enumerate(lote)])
    return base


STOPWORDS = set("como cómo que qué para con sin una uno unos unas los las del por este esta esa ese cual cuál cuales cuáles donde dónde necesito puedo usar ponerme ropa moda estilo mejor tienes tiene hacer vestir combinar recomendación recomendaciones funciona".split())


def tokens_informativos(texto):
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return {t for t in re.findall(r"[a-z0-9]{4,}", texto) if t not in STOPWORDS}


def identificadores_especificos(texto: str) -> set[str]:
    """Identificadores tipo Aurora-47: prevalecen sobre recomendaciones genéricas.

    Un identificador presente en la pregunta debe estar literalmente en cada
    fragmento recuperado; de otro modo ese fragmento no fundamenta la respuesta.
    """
    return {
        identificador.casefold()
        for identificador in re.findall(r"\b[a-záéíóúñ]{2,}[-‑–_]\d{2,}\b", texto, re.IGNORECASE)
    }


def buscar_contexto_evaluado(pregunta, usuario_id=None, cantidad=4):
    """Aplica distancia máxima Y solapamiento léxico (doble filtro conservador).

    Nunca garantiza verdad factual; además se obliga a citar evidencia en prompt.
    Una base vacía o un error se trata como insuficiencia, no como permiso para inventar.
    """
    limite = float(os.getenv("RAG_MAX_DISTANCE", "1.35"))
    palabras = tokens_informativos(pregunta)
    fuentes = []
    hallazgos = []
    colecciones = [obtener_vectorstore()]
    if usuario_id is not None:
        colecciones.append(obtener_vectorstore(usuario_id))
    for base in colecciones:
        for doc, distancia in base.similarity_search_with_score(pregunta, k=cantidad):
            if not doc.page_content.strip() or float(distancia) > limite:
                continue
            # Exigir un término específico compartido bloquea coincidencias genéricas
            # de consultas ajenas al corpus (p. ej., recetas de sushi).
            if palabras and not (palabras & tokens_informativos(doc.page_content)):
                continue
            hallazgos.append((float(distancia), doc))
    # Ejemplo: Aurora-47 solo puede contestarse con pasajes que mencionen
    # Aurora-47. Evita mezclar el documento nuevo con consejos de moda genéricos.
    identificadores = identificadores_especificos(pregunta)
    if identificadores:
        hallazgos = [
            (distancia, doc) for distancia, doc in hallazgos
            if identificadores.issubset(identificadores_especificos(doc.page_content))
        ]
    hallazgos.sort(key=lambda x: x[0])
    vistos = set()
    fragmentos = []
    for distancia, doc in hallazgos:
        clave = hashlib.sha256(doc.page_content.encode()).hexdigest()
        if clave in vistos:
            continue
        vistos.add(clave)
        fuente = str(doc.metadata.get("source", "Documento sin nombre"))
        fragmentos.append(f"FUENTE: {fuente} | DISTANCIA: {distancia:.3f}\n{doc.page_content[:1100]}")
        if fuente not in fuentes:
            fuentes.append(fuente)
        if len(fragmentos) >= cantidad:
            break
    return {"contexto": "\n\n---\n\n".join(fragmentos), "fuentes": fuentes, "suficiente": bool(fragmentos), "distancias": [round(x[0], 3) for x in hallazgos[:cantidad]]}


def buscar_contexto(pregunta, cantidad=4):
    """Compatibilidad con utilidades antiguas: solamente documentos con doble filtro."""
    base = obtener_vectorstore()
    return [d for d, score in base.similarity_search_with_score(pregunta, k=cantidad) if score <= float(os.getenv("RAG_MAX_DISTANCE", "1.35"))]


if __name__ == "__main__":
    base = indexar_documentos()
    print(f"Indexación completa: {base._collection.count()} fragmentos.")
