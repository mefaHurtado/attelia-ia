"""Pruebas HTTP reproducibles sin depender del servicio Ollama.

Las pruebas de RAG real deben realizarse adicionalmente con Ollama activo.
"""
import sys
import types
import pytest
from fastapi.testclient import TestClient
from app import main as api


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(api, "UPLOAD_DIR", tmp_path / "uploads")
    with TestClient(api.app) as c:
        yield c


def autenticar(cliente, email="prueba@ejemplo.com"):
    respuesta = cliente.post("/api/auth/register", json={
        "nombre": "Usuario Test", "email": email, "password": "ClaveDePrueba2026!"
    })
    assert respuesta.status_code == 201, respuesta.text
    return {"Authorization": "Bearer " + respuesta.json()["token"]}


def test_api_privada_y_sesiones(cliente):
    for url in ["/", "/api/health", "/api/auth/me", "/api/chat/history", "/api/documents"]:
        assert cliente.get(url).status_code == 401
    assert cliente.post("/api/chat", json={"pregunta": "Zapatos para jeans"}).status_code == 401
    assert cliente.post("/api/documents", files={"archivo": ("ejemplo.txt", b"texto")}).status_code == 401
    cabeceras = autenticar(cliente)
    assert cliente.get("/api/auth/me", headers=cabeceras).status_code == 200
    assert cliente.get("/api/health", headers=cabeceras).status_code == 200
    assert cliente.post("/api/auth/logout", headers=cabeceras).status_code == 200
    assert cliente.get("/api/auth/me", headers=cabeceras).status_code == 401


def test_login_historial_y_aislamiento(cliente, monkeypatch):
    u1 = autenticar(cliente, "uno@ejemplo.com")
    u2 = autenticar(cliente, "dos@ejemplo.com")
    monkeypatch.setattr(api, "ejecutar_agente", lambda pregunta, usuario_id: {
        "respuesta": "Respuesta de prueba con documentos.",
        "fuentes": ["volumen_1.txt"], "categoria": "general", "pregunta": pregunta
    })
    respuesta = cliente.post("/api/chat", json={"pregunta": "Cómo vestir para una cena"}, headers=u1)
    assert respuesta.status_code == 200
    assert len(cliente.get("/api/chat/history", headers=u1).json()) == 1
    assert cliente.get("/api/chat/history", headers=u2).json() == []
    login = cliente.post("/api/auth/login", json={"email": "uno@ejemplo.com", "password": "ClaveDePrueba2026!"})
    assert login.status_code == 200
    assert cliente.post("/api/auth/login", json={"email": "uno@ejemplo.com", "password": "contraseñaerrónea"}).status_code == 401


def test_carga_listado_y_borrado_autorizados(cliente, monkeypatch):
    # Doble control de API/DB; la indexación se sustituye solo en este test.
    indexados, borrados = [], []
    servicio_simulado = types.ModuleType("app.services.documentos")
    servicio_simulado.EXTENSIONES = {".txt", ".pdf", ".docx", ".md", ".csv"}
    servicio_simulado.indexar_archivo = lambda uid, did, nombre, content: (indexados.append((uid, did, nombre)), 2)[1]
    servicio_simulado.eliminar_vectores = lambda uid, did: borrados.append((uid, did))
    monkeypatch.setitem(sys.modules, "app.services.documentos", servicio_simulado)
    u1 = autenticar(cliente, "archivo1@ejemplo.com")
    u2 = autenticar(cliente, "archivo2@ejemplo.com")
    subida = cliente.post("/api/documents", headers=u1, files={"archivo": ("mis_notas.txt", b"Teoria del color y prendas suficientes", "text/plain")})
    assert subida.status_code == 201, subida.text
    did = subida.json()["id"]
    assert subida.json()["fragmentos"] == 2
    assert len(cliente.get("/api/documents", headers=u1).json()) == 1
    assert cliente.get("/api/documents", headers=u2).json() == []
    assert cliente.delete(f"/api/documents/{did}", headers=u2).status_code == 404
    assert cliente.delete(f"/api/documents/{did}", headers=u1).status_code == 200
    assert len(borrados) == 1
    assert cliente.get("/api/documents", headers=u1).json() == []
    assert cliente.post("/api/documents", headers=u1, files={"archivo": ("malicioso.exe", b"binary")}).status_code == 422
