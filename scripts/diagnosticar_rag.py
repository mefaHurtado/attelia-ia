"""Evalúa distancias reales y fuentes; ejecutar con PYTHONPATH=backend y Ollama activo."""
import sys
from app.vectorstore.rag import obtener_vectorstore

if __name__ == "__main__":
    consultas = sys.argv[1:] or [
        "¿Cómo combinar blazer con jeans?",
        "¿Qué accesorios usar con vestido negro?",
        "¿Qué ingredientes lleva el sushi?",
    ]
    base = obtener_vectorstore()
    for pregunta in consultas:
        print(f"\nPregunta: {pregunta}")
        try:
            for doc, distancia in base.similarity_search_with_score(pregunta, k=4):
                print(f"  Distancia={distancia:.3f}  Fuente={doc.metadata.get('source')}  Texto={doc.page_content[:85]!r}")
        except Exception as error:
            print(f"  ERROR: {type(error).__name__}: {error}")
            print("  Verifica que Ollama tenga bge-m3 y que el corpus esté indexado.")
