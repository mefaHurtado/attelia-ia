"""Pruebas LangGraph con recuperación simulada. Requieren dependencias del backend."""
import pytest
pytest.importorskip("langgraph")
pytest.importorskip("langchain_ollama")
from app.agents import graph


def test_rechazo_no_invoca_generador(monkeypatch):
    monkeypatch.setattr(graph, "buscar_contexto_evaluado", lambda pregunta, usuario_id=None, cantidad=4: {
        "contexto": "", "fuentes": [], "suficiente": False, "distancias": []})
    def no_generar(*args, **kwargs):
        raise AssertionError("El modelo no debe invocarse sin contexto")
    from types import SimpleNamespace
    monkeypatch.setattr(graph, "modelo_respuesta", SimpleNamespace(invoke=no_generar))
    respuesta = graph.consultar_attelia("¿Qué zapatos puedo usar?", usuario_id=7)
    assert respuesta["rechazada"] is True
    assert "No tengo suficiente información" in respuesta["respuesta"]
    assert respuesta["fuentes"] == []


def test_grafo_contiene_ruta_de_rechazo():
    nodos = graph.agente_attelia.get_graph().nodes
    assert "recuperar" in nodos
    assert "rechazar" in nodos
    assert "responder" in nodos


def test_pregunta_registrada_es_literal_y_no_invoca_modelo(monkeypatch):
    from types import SimpleNamespace
    texto = """FUENTE: prueba_rag_attelia_aurora47.txt | DISTANCIA: 0.2
En esta colección el pañuelo coral Aurora-47 se combina exclusivamente con
una chaqueta gris grafito, un pantalón color marfil y zapatos azul petróleo.
Pregunta de verificación: ¿Cómo se combina el pañuelo coral Aurora-47 según el documento de prueba?
Respuesta registrada: con una chaqueta gris grafito, un pantalón marfil y zapatos azul petróleo.
"""
    monkeypatch.setattr(graph, "buscar_contexto_evaluado", lambda *a, **kw: {
        "contexto": texto,
        "fuentes": ["prueba_rag_attelia_aurora47.txt"],
        "suficiente": True,
        "distancias": [0.2],
    })
    def no_generar(*args, **kwargs):
        raise AssertionError("No debe inventar una respuesta cuando existe una literal")
    monkeypatch.setattr(graph, "modelo_respuesta", SimpleNamespace(invoke=no_generar))
    pregunta = "¿Cómo se combina el pañuelo coral Aurora-47 según el documento de prueba? Copiar pregunta"
    resultado = graph.consultar_attelia(pregunta, usuario_id=9)
    assert "chaqueta gris grafito" in resultado["respuesta"]
    assert "pantalón marfil" in resultado["respuesta"]
    assert "zapatos azul petróleo" in resultado["respuesta"]
    assert "cinturón" not in resultado["respuesta"]
    assert resultado["fuentes"] == ["prueba_rag_attelia_aurora47.txt"]
