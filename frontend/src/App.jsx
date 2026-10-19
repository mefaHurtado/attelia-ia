import React from "react";
import { useEffect, useRef, useState } from "react";
import {
  Sparkles, Send, LogOut, Plus, MessageCircle,
  Clock3, Shirt, Paperclip, Menu, X, ArrowUpRight, Trash2, FileText, UploadCloud
} from "lucide-react";

const API = (import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? "http://127.0.0.1:8000" : window.location.origin)).replace(/\/$/, "");

async function request(path, options = {}, token = "") {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {})
    }
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "No fue posible completar la solicitud.");
  }
  return data;
}

export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem("attelia_token") || "");
  const [user, setUser] = useState(null);
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nombre, setNombre] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [history, setHistory] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activePage, setActivePage] = useState("chat");
  const [currentConversation, setCurrentConversation] = useState(0);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const fileRef = useRef(null);
  const [documents, setDocuments] = useState([]);
  const [fileBusy, setFileBusy] = useState(false);
  const [docMessage, setDocMessage] = useState("");

  useEffect(() => {
    if (!token) return;
    request("/api/auth/me", {}, token)
      .then(setUser)
      .catch(() => logout());
  }, []);

  useEffect(() => {
    if (token && user) { loadHistory(); loadDocuments(); }
  }, [token, user]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function authenticate(event) {
    event.preventDefault();
    setError("");
    setAuthLoading(true);

    try {
      const path = mode === "register" ? "/api/auth/register" : "/api/auth/login";
      const body = mode === "register"
        ? { nombre: nombre.trim(), email: email.trim(), password }
        : { email: email.trim(), password };

      const data = await request(path, {
        method: "POST",
        body: JSON.stringify(body)
      });

      sessionStorage.setItem("attelia_token", data.token);
      setToken(data.token);
      setUser(data.usuario);
      setMessages([]);
      setPassword("");
    } catch (err) {
      setError(err.message);
    } finally {
      setAuthLoading(false);
    }
  }

  function logout() {
    const savedToken = token || sessionStorage.getItem("attelia_token");
    if (savedToken) {
      request("/api/auth/logout", { method: "POST" }, savedToken).catch(() => {});
    }
    sessionStorage.removeItem("attelia_token");
    setToken("");
    setUser(null);
    setMessages([]);
    setHistory([]);
    setDocuments([]);
    setQuestion("");
    setError("");
  }

  async function loadHistory() {
    try {
      const data = await request("/api/chat/history", {}, token);
      setHistory(data);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadDocuments() {
    try {
      const data = await request("/api/documents", {}, token);
      setDocuments(data);
    } catch (err) { setError(err.message); }
  }

  async function uploadDocument(event) {
    const file = event.target.files?.[0];
    if (!file || fileBusy) return;
    if (file.size > 10 * 1024 * 1024) {
      setError("El archivo supera 10 MB."); event.target.value = ""; return;
    }
    setError(""); setDocMessage(""); setFileBusy(true);
    try {
      const form = new FormData(); form.append("archivo", file);
      const response = await fetch(`${API}/api/documents`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "No se pudo procesar el documento.");
      await loadDocuments();
      setDocMessage(`${data.nombre}: ${data.fragmentos} fragmentos indexados. Ya puedes preguntar sobre su contenido.`);
      setActivePage("documents");
    } catch (err) { setError(err.message); }
    finally { setFileBusy(false); event.target.value = ""; }
  }

  async function deleteDocument(id) {
    if (!window.confirm("¿Eliminar este documento y su contenido vectorial?")) return;
    setError(""); setDocMessage("");
    try {
      await request(`/api/documents/${id}`, { method: "DELETE" }, token);
      await loadDocuments(); setDocMessage("Documento eliminado.");
    } catch (err) { setError(err.message); }
  }

  async function sendMessage(event) {
    event?.preventDefault();
    const text = question.trim();
    if (!text || busy) return;

    setError("");
    setQuestion("");
    setActivePage("chat");
    setMessages(prev => [...prev, { role: "user", content: text }]);
    setBusy(true);

    try {
      const data = await request("/api/chat", {
        method: "POST",
        body: JSON.stringify({ pregunta: text })
      }, token);

      setMessages(prev => [
        ...prev,
        {
          role: "assistant",
          content: data.respuesta,
          sources: data.fuentes || []
        }
      ]);
      await loadHistory();
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: "assistant",
          content: `No pude completar la consulta: ${err.message}`
        }
      ]);
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  function newChat() {
    setMessages([]);
    setQuestion("");
    setError("");
    setActivePage("chat");
    setCurrentConversation(0);
    inputRef.current?.focus();
  }

  function openHistory(item) {
    setMessages([
      { role: "user", content: item.pregunta },
      {
        role: "assistant",
        content: item.respuesta,
        sources: item.fuentes || []
      }
    ]);
    setCurrentConversation(item.id);
    setActivePage("chat");
    setSidebarOpen(false);
  }

  if (!token || !user) {
    return (
      <main className="auth-page">
        <section className="auth-art">
          <div className="brand light-brand">
            <span className="brand-mark"><Sparkles size={21} /></span>
            <span>AtteliA</span>
          </div>
          <div className="art-copy">
            <span className="eyebrow">TU ESTILO, TU ESENCIA</span>
            <h1>Vístete como<br />te quieres sentir.</h1>
            <p>Una asesora personal que te ayuda a descubrir combinaciones, explorar colores y vestir con intención.</p>
          </div>
          <div className="art-bottom">
            <span>ESTILO CON INTENCIÓN</span>
            <span>01 — PERSONAL</span>
          </div>
          <div className="art-orb orb-one" />
          <div className="art-orb orb-two" />
        </section>

        <section className="auth-panel">
          <div className="mobile-brand brand">
            <span className="brand-mark"><Sparkles size={20} /></span>
            <span>AtteliA</span>
          </div>
          <div className="auth-form-wrap">
            <span className="eyebrow">BIENVENIDA A TU ESPACIO</span>
            <h2>{mode === "login" ? "Qué bueno tenerte aquí." : "Comencemos juntas."}</h2>
            <p className="auth-subtitle">
              {mode === "login"
                ? "Inicia sesión para continuar explorando tu estilo."
                : "Crea tu cuenta y encuentra nuevas formas de expresarte."}
            </p>

            <form className="auth-form" onSubmit={authenticate}>
              {mode === "register" && (
                <label>
                  Nombre
                  <input value={nombre} onChange={e => setNombre(e.target.value)}
                    placeholder="¿Cómo te llamas?" minLength={2} required />
                </label>
              )}
              <label>
                Correo electrónico
                <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                  placeholder="tu@correo.com" required />
              </label>
              <label>
                Contraseña
                <input type="password" value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Mínimo 10 caracteres" minLength={10} required />
              </label>

              {error && <div className="error-message">{error}</div>}

              <button className="primary-button auth-submit" disabled={authLoading}>
                {authLoading ? "Un momento..." : mode === "login" ? "Iniciar sesión" : "Crear mi cuenta"}
                {!authLoading && <ArrowUpRight size={17} />}
              </button>
            </form>

            <p className="switch-auth">
              {mode === "login" ? "¿Es tu primera vez aquí?" : "¿Ya tienes una cuenta?"}
              <button onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
                {mode === "login" ? "Crear cuenta" : "Iniciar sesión"}
              </button>
            </p>
            <p className="auth-footnote">Tu estilo es tuyo. AtteliA está aquí para acompañarte.</p>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "" : "sidebar-closed"}`}>
        <div className="sidebar-top">
          <div className="brand">
            <span className="brand-mark"><Sparkles size={20} /></span>
            <span>AtteliA</span>
          </div>
          <button className="icon-button mobile-close" onClick={() => setSidebarOpen(false)} aria-label="Cerrar menú">
            <X size={19} />
          </button>
        </div>

        <button className="new-chat-button" onClick={newChat}>
          <Plus size={17} /> Nueva conversación
        </button>

        <button className="documents-nav-button" onClick={() => { setActivePage("documents"); setSidebarOpen(false); loadDocuments(); }}>
          <FileText size={16} /> Mis documentos <span>{documents.length}</span>
        </button>
        <div className="sidebar-label"><Clock3 size={14} /> TUS CONVERSACIONES</div>
        <div className="history-list">
          {history.length === 0 && <p className="empty-history">Tus conversaciones aparecerán aquí.</p>}
          {history.map(item => (
            <button key={item.id}
              className={`history-item ${currentConversation === item.id ? "selected" : ""}`}
              onClick={() => openHistory(item)}>
              <MessageCircle size={15} />
              <span>{item.pregunta}</span>
            </button>
          ))}
        </div>

        <div className="sidebar-bottom">
          <div className="user-card">
            <div className="avatar">{(user.nombre || "U").charAt(0).toUpperCase()}</div>
            <div className="user-info">
              <strong>{user.nombre}</strong>
              <span>{user.email}</span>
            </div>
            <button className="icon-button" onClick={logout} title="Cerrar sesión" aria-label="Cerrar sesión">
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>

      <section className="main-panel">
        <header className="topbar">
          <button className="icon-button menu-toggle" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Menú">
            <Menu size={20} />
          </button>
          <div className="breadcrumb"><span>Tu espacio</span><span className="crumb-divider">/</span><strong>{activePage === "documents" ? "Base de conocimiento" : "Asesora de estilo"}</strong></div>
          <div className="online-label"><span className="status-dot" /> ASISTENTE IA</div>
        </header>

        <div className="chat-area">
          {activePage === "documents" ? (
            <div className="documents-panel">
              <span className="eyebrow">BASE DE CONOCIMIENTO</span>
              <h1>Tus documentos</h1>
              <p>AtteliA consulta seis volúmenes de moda y los archivos que cargues. Los documentos de tu cuenta son privados.</p>
              <button className="primary-button" onClick={() => fileRef.current?.click()} disabled={fileBusy}>
                <UploadCloud size={18}/> {fileBusy ? "Procesando archivo..." : "Subir un documento"}
              </button>
              <small>PDF, DOCX, TXT, MD o CSV, máximo 10 MB. Los PDF escaneados requieren OCR.</small>
              {docMessage && <div className="document-success">{docMessage}</div>}
              {error && <div className="error-message">{error}</div>}
              <div className="document-list">
                {documents.length === 0 ? <p>Aún no has cargado documentos propios.</p> : documents.map(doc => (
                  <div className="document-row" key={doc.id}>
                    <FileText size={20} /> <div><strong>{doc.nombre}</strong><small>{new Date(doc.creado).toLocaleDateString("es-CO")}</small></div>
                    <button onClick={() => deleteDocument(doc.id)} aria-label={`Eliminar ${doc.nombre}`} title="Eliminar documento"><Trash2 size={17}/></button>
                  </div>
                ))}
              </div>
              <button className="new-chat-button" onClick={newChat}>Volver al chat</button>
            </div>
          ) : messages.length === 0 ? (
            <div className="welcome">
              <div className="welcome-icon"><Sparkles size={25} /></div>
              <span className="eyebrow">TU ASESORA PERSONAL</span>
              <h1>Hola, {user.nombre.split(" ")[0]}.<br /><span>¿Qué vamos a crear hoy?</span></h1>
              <p className="welcome-description">
                Hablemos de tu estilo. Cuéntame qué tienes en el armario, adónde vas o qué combinación te gustaría probar.
              </p>

              <div className="suggestion-grid">
                <button className="suggestion-card" onClick={() => setQuestion("¿Cómo combino un blazer con jeans para un look casual elegante?")}>
                  <span className="suggestion-icon"><Shirt size={19} /></span>
                  <strong>Combina tu ropa</strong>
                  <span>Ideas con prendas que ya tienes</span>
                  <ArrowUpRight size={16} className="suggestion-arrow" />
                </button>
                <button className="suggestion-card" onClick={() => setQuestion("¿Qué colores combinan bien con el azul marino?")}>
                  <span className="suggestion-icon color-icon">◐</span>
                  <strong>Descubre tus colores</strong>
                  <span>Armonías para crear nuevos looks</span>
                  <ArrowUpRight size={16} className="suggestion-arrow" />
                </button>
                <button className="suggestion-card" onClick={() => setQuestion("¿Qué me puedo poner para una entrevista de trabajo virtual?")}>
                  <span className="suggestion-icon"><Sparkles size={19} /></span>
                  <strong>Vístete para la ocasión</strong>
                  <span>Encuentra el look adecuado</span>
                  <ArrowUpRight size={16} className="suggestion-arrow" />
                </button>
                <button className="suggestion-card" onClick={() => setQuestion("¿Qué accesorios combinan con un vestido negro minimalista?")}>
                  <span className="suggestion-icon">✳</span>
                  <strong>Cuida los detalles</strong>
                  <span>Accesorios que completan tu estilo</span>
                  <ArrowUpRight size={16} className="suggestion-arrow" />
                </button>
              </div>
            </div>
          ) : (
            <div className="messages">
              {messages.map((message, index) => (
                <article className={`message ${message.role}`} key={index}>
                  {message.role === "assistant" && (
                    <div className="message-avatar"><Sparkles size={16} /></div>
                  )}
                  <div className="message-body">
                    <span className="message-author">{message.role === "user" ? "Tú" : "AtteliA"}</span>
                    <p>{message.content}</p>
                    {message.sources?.length > 0 && (
                      <div className="sources">
                        <span>Fuentes consultadas</span>
                        {message.sources.map((source, i) => (
                          <small key={i}>{typeof source === "string" ? source : JSON.stringify(source)}</small>
                        ))}
                      </div>
                    )}
                  </div>
                </article>
              ))}
              {busy && (
                <div className="message assistant">
                  <div className="message-avatar"><Sparkles size={16} /></div>
                  <div className="typing"><span /><span /><span /> <small>AtteliA está pensando...</small></div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <input ref={fileRef} type="file" hidden accept=".pdf,.docx,.txt,.md,.csv" onChange={uploadDocument} />
        {activePage === "chat" && <div className="composer-wrap">
          {error && <div className="error-message composer-error">{error}</div>}
          <form className="composer" onSubmit={sendMessage}>
            <button type="button" className="composer-attach" onClick={() => fileRef.current?.click()} disabled={fileBusy}
              title="Subir documento" aria-label="Subir documento">
              {fileBusy ? <UploadCloud size={19}/> : <Paperclip size={19}/>}
            </button>
            <textarea
              ref={inputRef}
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Cuéntame qué tienes en mente..."
              rows={1}
              maxLength={2000}
            />
            <button type="submit" className="send-button" disabled={!question.trim() || busy} aria-label="Enviar mensaje">
              <Send size={18} />
            </button>
          </form>
          <div className="composer-caption">AtteliA responde con la base de conocimiento recuperada. Puedes cargar nuevos documentos con el clip.</div>
        </div>}
      </section>
    </main>
  );
}