"""Filtros semántico/léxico probados con vectores simulados (sin Ollama)."""
import pytest
pytest.importorskip("langchain_chroma")
from types import SimpleNamespace
from app.vectorstore import rag


def test_rechazo_por_terminos_no_relacionados(monkeypatch):
    base = SimpleNamespace(similarity_search_with_score=lambda pregunta, k: [
        (SimpleNamespace(page_content="El blazer azul se combina con jeans oscuros.", metadata={"source": "volumen_1.txt"}), 0.42)])
    monkeypatch.setattr(rag, "obtener_vectorstore", lambda usuario_id=None: base)
    resultado = rag.buscar_contexto_evaluado("¿Qué ingredientes lleva el sushi?", cantidad=1)
    assert resultado["suficiente"] is False
    assert resultado["fuentes"] == []


def test_documento_relevante_y_fuente(monkeypatch):
    base = SimpleNamespace(similarity_search_with_score=lambda pregunta, k: [
        (SimpleNamespace(page_content="El blazer azul combina con jeans para un estilo casual.", metadata={"source": "volumen_1.txt"}), 0.42)])
    monkeypatch.setattr(rag, "obtener_vectorstore", lambda usuario_id=None: base)
    resultado = rag.buscar_contexto_evaluado("¿Cómo combinar blazer y jeans?", cantidad=1)
    assert resultado["suficiente"] is True
    assert resultado["fuentes"] == ["volumen_1.txt"]


def test_identificador_excluye_fuentes_genericas(monkeypatch):
    from types import SimpleNamespace
    moda = SimpleNamespace(page_content="Un pañuelo coral combina con cinturón y camiseta de rayas.", metadata={"source":"volumen_1.txt"})
    aurora = SimpleNamespace(page_content="El pañuelo coral Aurora-47 se combina con una chaqueta gris grafito, un pantalón marfil y zapatos azul petróleo.", metadata={"source":"prueba_rag_attelia_aurora47.txt"})
    comun = SimpleNamespace(similarity_search_with_score=lambda pregunta, k: [(moda, 0.31)])
    privado = SimpleNamespace(similarity_search_with_score=lambda pregunta, k: [(aurora, 0.41)])
    monkeypatch.setattr(rag, "obtener_vectorstore", lambda usuario_id=None: comun if usuario_id is None else privado)
    resultado = rag.buscar_contexto_evaluado("¿Cómo se combina el pañuelo coral Aurora-47?", usuario_id=9)
    assert resultado["fuentes"] == ["prueba_rag_attelia_aurora47.txt"]
    assert "camiseta de rayas" not in resultado["contexto"]
