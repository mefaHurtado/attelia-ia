import os
import re
import json
import hmac
import base64
import hashlib
import secrets
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Header, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.concurrency import run_in_threadpool
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("ATTELIA_DB", str(ROOT / "data" / "attelia.db")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

FRONTEND_ORIGINS = os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")


def conectar_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_db():
    with conectar_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                creado TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sesiones (
                token_hash TEXT PRIMARY KEY,
                usuario_id INTEGER NOT NULL,
                expira TEXT NOT NULL,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS conversaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                pregunta TEXT NOT NULL,
                respuesta TEXT NOT NULL,
                fuentes TEXT NOT NULL DEFAULT '[]',
                creado TEXT NOT NULL,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS documentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                ruta TEXT NOT NULL,
                creado TEXT NOT NULL,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            );
        """)


@asynccontextmanager
async def lifespan(app: FastAPI):
    inicializar_db()
    yield


app = FastAPI(
    title="AtteliA API",
    description="Asesora de moda con LangGraph, Ollama y RAG.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None, redoc_url=None, openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in FRONTEND_ORIGINS if o.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class Registro(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=10, max_length=128)


class Login(BaseModel):
    email: str
    password: str


class Pregunta(BaseModel):
    pregunta: str = Field(min_length=2, max_length=2000)


def normalizar_email(email: str) -> str:
    email = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(422, "Escribe un correo electrónico válido.")
    return email


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    return base64.b64encode(salt + derived).decode("ascii")


def verificar_password(password: str, guardado: str) -> bool:
    try:
        datos = base64.b64decode(guardado.encode("ascii"))
        salt, esperado = datos[:16], datos[16:]
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1,
            dklen=32,
        )
        return hmac.compare_digest(actual, esperado)
    except (ValueError, TypeError):
        return False


def crear_sesion(usuario_id: int) -> str:
    token = secrets.token_urlsafe(36)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expira = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

    with conectar_db() as db:
        db.execute(
            "INSERT INTO sesiones(token_hash, usuario_id, expira) VALUES (?, ?, ?)",
            (token_hash, usuario_id, expira),
        )
    return token


def usuario_actual(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Inicia sesión para continuar.")

    token = authorization[7:].strip()
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    with conectar_db() as db:
        fila = db.execute("""
            SELECT u.id, u.email, u.nombre, s.expira
            FROM sesiones s
            JOIN usuarios u ON u.id = s.usuario_id
            WHERE s.token_hash = ?
        """, (token_hash,)).fetchone()

        if not fila:
            raise HTTPException(401, "Sesión inválida. Inicia sesión de nuevo.")

        if datetime.fromisoformat(fila["expira"]) <= datetime.now(timezone.utc):
            db.execute("DELETE FROM sesiones WHERE token_hash = ?", (token_hash,))
            raise HTTPException(401, "Tu sesión expiró. Inicia sesión de nuevo.")

        return {
            "id": fila["id"],
            "email": fila["email"],
            "nombre": fila["nombre"],
            "token_hash": token_hash,
        }



def ejecutar_agente(pregunta: str, usuario_id: int) -> dict:
    """
    Ejecuta el grafo compilado de AtteliA sin duplicar
    la lógica del agente.
    """
    from app.agents.graph import consultar_attelia

    return consultar_attelia(pregunta, usuario_id=usuario_id)



@app.get("/")
def inicio(usuario: dict = Depends(usuario_actual)):
    return {"aplicacion": "AtteliA", "estado": "activa", "version": "1.0.0"}


@app.get("/api/health")
def salud(usuario: dict = Depends(usuario_actual)):
    return {"estado": "ok", "servicio": "AtteliA API"}


@app.post("/api/auth/register", status_code=201)
def registrar(datos: Registro):
    email = normalizar_email(datos.email)
    nombre = datos.nombre.strip()

    if len(nombre) < 2:
        raise HTTPException(422, "Escribe un nombre válido.")

    with conectar_db() as db:
        try:
            cursor = db.execute("""
                INSERT INTO usuarios(email, nombre, password_hash, creado)
                VALUES (?, ?, ?, ?)
            """, (
                email,
                nombre,
                hash_password(datos.password),
                datetime.now(timezone.utc).isoformat(),
            ))
            usuario_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Ese correo ya está registrado.")

    token = crear_sesion(usuario_id)
    return {
        "token": token,
        "tipo": "bearer",
        "usuario": {"id": usuario_id, "nombre": nombre, "email": email},
    }


@app.post("/api/auth/login")
def iniciar_sesion(datos: Login):
    email = normalizar_email(datos.email)

    with conectar_db() as db:
        usuario = db.execute(
            "SELECT * FROM usuarios WHERE email = ?", (email,)
        ).fetchone()

    if not usuario or not verificar_password(
        datos.password, usuario["password_hash"]
    ):
        raise HTTPException(401, "Correo o contraseña incorrectos.")

    token = crear_sesion(usuario["id"])
    return {
        "token": token,
        "tipo": "bearer",
        "usuario": {
            "id": usuario["id"],
            "nombre": usuario["nombre"],
            "email": usuario["email"],
        },
    }


@app.get("/api/auth/me")
def mi_perfil(usuario: dict = Depends(usuario_actual)):
    return {
        "id": usuario["id"],
        "nombre": usuario["nombre"],
        "email": usuario["email"],
    }


@app.post("/api/auth/logout")
def cerrar_sesion(usuario: dict = Depends(usuario_actual)):
    with conectar_db() as db:
        db.execute(
            "DELETE FROM sesiones WHERE token_hash = ?",
            (usuario["token_hash"],),
        )
    return {"mensaje": "Sesión cerrada."}


@app.post("/api/chat")
def chatear(datos: Pregunta, usuario: dict = Depends(usuario_actual)):
    pregunta = datos.pregunta.strip()

    try:
        resultado = ejecutar_agente(pregunta, usuario["id"])
    except Exception as error:
        print(f"Error del agente: {type(error).__name__}: {error}")
        raise HTTPException(
            503,
            "No se pudo consultar el asesor. Comprueba que Ollama esté activo.",
        )

    if resultado.get("error_rag") or resultado.get("error_modelo"):
        raise HTTPException(503, "No está disponible el agente o la recuperación documental. Comprueba Ollama y ChromaDB.")

    with conectar_db() as db:
        db.execute("""
            INSERT INTO conversaciones(usuario_id, pregunta, respuesta, fuentes, creado)
            VALUES (?, ?, ?, ?, ?)
        """, (
            usuario["id"],
            pregunta,
            resultado["respuesta"],
            json.dumps(resultado["fuentes"], ensure_ascii=False),
            datetime.now(timezone.utc).isoformat(),
        ))

    return resultado


@app.get("/api/chat/history")
def historial(usuario: dict = Depends(usuario_actual)):
    with conectar_db() as db:
        filas = db.execute("""
            SELECT id, pregunta, respuesta, fuentes, creado
            FROM conversaciones
            WHERE usuario_id = ?
            ORDER BY id DESC
            LIMIT 100
        """, (usuario["id"],)).fetchall()

    return [
        {
            "id": fila["id"],
            "pregunta": fila["pregunta"],
            "respuesta": fila["respuesta"],
            "fuentes": json.loads(fila["fuentes"]),
            "creado": fila["creado"],
        }
        for fila in reversed(filas)
    ]


@app.delete("/api/chat/history")
def borrar_historial(usuario: dict = Depends(usuario_actual)):
    with conectar_db() as db:
        db.execute(
            "DELETE FROM conversaciones WHERE usuario_id = ?",
            (usuario["id"],),
        )
    return {"mensaje": "Historial eliminado."}

# DOCUMENTOS - cada persona tiene su propia colección Chroma y permisos por usuario.
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(ROOT / "data" / "uploads")))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024


@app.get("/api/documents")
def listar_documentos(usuario: dict = Depends(usuario_actual)):
    with conectar_db() as db:
        filas = db.execute("SELECT id, nombre, creado FROM documentos WHERE usuario_id=? ORDER BY id DESC", (usuario["id"],)).fetchall()
    return [dict(f) for f in filas]


@app.post("/api/documents", status_code=201)
async def subir_documento(archivo: UploadFile = File(...), usuario: dict = Depends(usuario_actual)):
    from app.services.documentos import EXTENSIONES, indexar_archivo, eliminar_vectores
    nombre = Path(archivo.filename or "").name.strip()
    if not nombre or Path(nombre).suffix.lower() not in EXTENSIONES:
        raise HTTPException(422, "Adjunta un archivo PDF, DOCX, TXT, MD o CSV.")
    contenido = bytearray()
    try:
        while bloque := await archivo.read(1024 * 1024):
            contenido.extend(bloque)
            if len(contenido) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "Archivo demasiado grande; máximo 10 MB por defecto.")
    finally:
        await archivo.close()
    if not contenido:
        raise HTTPException(422, "El archivo está vacío.")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ruta = UPLOAD_DIR / f"{uuid4().hex}{Path(nombre).suffix.lower()}"
    ruta.write_bytes(contenido)
    with conectar_db() as db:
        cursor = db.execute("INSERT INTO documentos(usuario_id, nombre, ruta, creado) VALUES(?,?,?,?)",
                            (usuario["id"], nombre, str(ruta), datetime.now(timezone.utc).isoformat()))
        document_id = cursor.lastrowid
    try:
        fragmentos = await run_in_threadpool(indexar_archivo, usuario["id"], document_id, nombre, bytes(contenido))
    except Exception as exc:
        try:
            await run_in_threadpool(eliminar_vectores, usuario["id"], document_id)
        except Exception:
            pass
        with conectar_db() as db:
            db.execute("DELETE FROM documentos WHERE id=? AND usuario_id=?", (document_id, usuario["id"]))
        ruta.unlink(missing_ok=True)
        if isinstance(exc, ValueError):
            raise HTTPException(422, str(exc))
        print("Fallo indexando documento:", type(exc).__name__, exc)
        raise HTTPException(503, "No fue posible indexar el archivo. Comprueba Ollama y la base vectorial.")
    return {"id": document_id, "nombre": nombre, "fragmentos": fragmentos,
            "mensaje": "Documento procesado y disponible para consultas."}


@app.delete("/api/documents/{document_id}")
async def borrar_documento(document_id: int, usuario: dict = Depends(usuario_actual)):
    from app.services.documentos import eliminar_vectores
    with conectar_db() as db:
        documento = db.execute("SELECT * FROM documentos WHERE id=? AND usuario_id=?", (document_id, usuario["id"])).fetchone()
    if documento is None:
        raise HTTPException(404, "Documento no encontrado.")
    try:
        await run_in_threadpool(eliminar_vectores, usuario["id"], document_id)
    except Exception as exc:
        print("Fallo borrando vectores:", type(exc).__name__, exc)
        raise HTTPException(503, "No fue posible eliminar los vectores del documento.")
    with conectar_db() as db:
        db.execute("DELETE FROM documentos WHERE id=? AND usuario_id=?", (document_id, usuario["id"]))
    ruta = Path(documento["ruta"]).resolve()
    # No seguir rutas externas arbitrarias registradas accidentalmente.
    if ruta.is_relative_to(UPLOAD_DIR.resolve()):
        ruta.unlink(missing_ok=True)
    return {"mensaje": "Documento eliminado de la base de conocimiento."}
