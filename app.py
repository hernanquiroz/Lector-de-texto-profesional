import streamlit as st
import streamlit.components.v1 as components
import pdfplumber
import pandas as pd
import io
import re
import os
import json
import math
from datetime import datetime
from collections import Counter
from urllib.parse import urlparse
import requests
import tempfile
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import base64

# ============================================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================================
st.set_page_config(
    page_title="📚 Lector PDF Pro - Con Audio",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados MEJORADOS - letra más grande
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .batch-info {
        background-color: #e7f3ff;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        font-size: 1.1rem;
    }
    .audio-card {
        background-color: #f8f9fa;
        padding: 1.2rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin: 0.8rem 0;
        font-size: 1.05rem;
    }
    .stButton>button {
        width: 100%;
        font-size: 1.1rem;
        padding: 0.5rem;
    }
    .credits-footer {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-top: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .credits-footer h3 {
        margin: 0 0 0.5rem 0;
        font-size: 1.5rem;
    }
    .credits-footer p {
        margin: 0.3rem 0;
        font-size: 1.1rem;
        opacity: 0.95;
    }
    .credits-footer .author {
        font-size: 1.3rem;
        font-weight: bold;
        color: #ffd700;
        margin-top: 0.5rem;
    }
    .credits-footer .vibe-badge {
        display: inline-block;
        background-color: rgba(255,255,255,0.2);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 1rem;
        margin-top: 0.5rem;
        backdrop-filter: blur(10px);
    }
    .auto-play-notice {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        font-size: 1.1rem;
    }
    .auto-play-notice.warning {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
    }
    /* Aumentar tamaño de letra en toda la app */
    .stMarkdown, .stText, p, li, span, div {
        font-size: 1.05rem !important;
    }
    .stTextArea textarea {
        font-size: 1.1rem !important;
    }
    .stExpander {
        font-size: 1.05rem !important;
    }
    /* Reproductor de audio destacado */
    .audio-player-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin: 1.5rem 0;
        text-align: center;
        color: white;
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    .audio-player-container h3 {
        margin-bottom: 1rem;
        font-size: 1.5rem;
    }
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background-color: #28a745;
        margin-right: 8px;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.2); }
        100% { opacity: 1; transform: scale(1); }
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# FUNCIÓN CLAVE: REPRODUCTOR DE AUDIO CON AUTOPLAY FORZADO
# ============================================================
def play_audio_autoplay(audio_bytes, format_type="audio/mp3"):
    """
    Reproduce audio con autoplay FORZADO usando HTML5.
    Esto SÍ funciona en los navegadores porque el usuario 
    ya interactuó con la página al hacer clic en el botón.
    """
    # Convertir bytes a base64
    audio_base64 = base64.b64encode(audio_bytes).decode()
    
    # Crear reproductor HTML5 con autoplay
    audio_html = f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 15px; margin: 1.5rem 0; 
                text-align: center; color: white; box-shadow: 0 8px 25px rgba(0,0,0,0.15);">
        <h3 style="margin-bottom: 1rem; font-size: 1.5rem;">
            <span class="status-indicator"></span>
            🔊 Reproduciendo automáticamente...
        </h3>
        <p style="font-size: 1.1rem; margin-bottom: 1rem;">
            El audio se está reproduciendo por tus parlantes o audífonos
        </p>
        <audio controls autoplay style="width: 100%; max-width: 500px;">
            <source src="data:{format_type};base64,{audio_base64}" type="{format_type}">
            Tu navegador no soporta el elemento de audio.
        </audio>
        <p style="font-size: 0.9rem; margin-top: 1rem; opacity: 0.9;">
            💡 Si no escuchas nada, verifica el volumen de tu PC y que tus parlantes/audífonos estén conectados
        </p>
    </div>
    """
    components.html(audio_html, height=280)


def play_audio_normal(audio_bytes, format_type="audio/mp3"):
    """Reproductor de audio normal (sin autoplay) para el historial."""
    audio_base64 = base64.b64encode(audio_bytes).decode()
    audio_html = f"""
    <audio controls style="width: 100%; max-width: 500px;">
        <source src="data:{format_type};base64,{audio_base64}" type="{format_type}">
        Tu navegador no soporta el elemento de audio.
    </audio>
    """
    components.html(audio_html, height=80)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================
@st.cache_data(show_spinner="📖 Cargando información del PDF...")
def get_pdf_info(uploaded_file):
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            metadata = pdf.metadata or {}
            total_pages = len(pdf.pages)
            return metadata, total_pages
    except Exception as e:
        st.error(f"❌ Error al leer el PDF: {e}")
        return None, 0


@st.cache_data(show_spinner="📖 Procesando páginas...")
def load_pdf_batch(uploaded_file, start_page, end_page):
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            pages_data = []
            start_idx = max(0, start_page - 1)
            end_idx = min(end_page, len(pdf.pages))
            
            for i in range(start_idx, end_idx):
                page = pdf.pages[i]
                text = page.extract_text() or ""
                tables = page.extract_tables() or []
                pages_data.append({
                    "page_number": i + 1,
                    "text": text,
                    "tables": tables,
                    "width": page.width,
                    "height": page.height
                })
            return pages_data
    except Exception as e:
        st.error(f"❌ Error al cargar las páginas: {e}")
        return []


@st.cache_data(show_spinner="🌐 Descargando PDF...")
def get_pdf_info_from_url(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name
        
        with pdfplumber.open(tmp_path) as pdf:
            metadata = pdf.metadata or {}
            total_pages = len(pdf.pages)
        
        os.remove(tmp_path)
        return metadata, total_pages, response.content
    except Exception as e:
        st.error(f"❌ Error al descargar el PDF: {e}")
        return None, 0, None


@st.cache_data(show_spinner="🌐 Procesando páginas desde URL...")
def load_pdf_batch_from_url(pdf_content, start_page, end_page):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_content)
            tmp_path = tmp.name
        
        with pdfplumber.open(tmp_path) as pdf:
            pages_data = []
            start_idx = max(0, start_page - 1)
            end_idx = min(end_page, len(pdf.pages))
            
            for i in range(start_idx, end_idx):
                page = pdf.pages[i]
                text = page.extract_text() or ""
                tables = page.extract_tables() or []
                pages_data.append({
                    "page_number": i + 1,
                    "text": text,
                    "tables": tables
                })
        
        os.remove(tmp_path)
        return pages_data
    except Exception as e:
        st.error(f"❌ Error al procesar las páginas: {e}")
        return []


def get_batch_text(pages_data):
    return "\n\n".join([p["text"] for p in pages_data])


def count_words(text):
    return len(re.findall(r'\b\w+\b', text))


def count_characters(text):
    return len(text)


def count_lines(text):
    return len(text.splitlines())


def get_most_common_words(text, n=10, min_length=4):
    words = re.findall(r'\b\w+\b', text.lower())
    stopwords = {'para', 'como', 'los', 'las', 'con', 'por', 'que', 'del', 'una',
                 'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can',
                 'this', 'that', 'from', 'they', 'been', 'have', 'has', 'was'}
    filtered = [w for w in words if len(w) >= min_length and w not in stopwords]
    return Counter(filtered).most_common(n)


def search_text(text, query):
    if not query:
        return text, 0
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    matches = pattern.findall(text)
    highlighted = pattern.sub(f"**{query}**", text)
    return highlighted, len(matches)


def extract_emails(text):
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return list(set(re.findall(pattern, text)))


def extract_urls(text):
    pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return list(set(re.findall(pattern, text)))


def extract_phones(text):
    pattern = r'\+?\d[\d\s\-\(\)]{7,}\d'
    return list(set(re.findall(pattern, text)))


def generate_summary(text, max_sentences=5):
    sentences = re.split(r'(?<=[.!?])\s+', text.replace('\n', ' '))
    sentences = [s.strip() for s in sentences if len(s.split()) > 5]
    if not sentences:
        return "No se pudo generar un resumen."
    word_freq = Counter(re.findall(r'\b\w+\b', text.lower()))
    sentence_scores = []
    for i, sentence in enumerate(sentences):
        score = sum(word_freq.get(word, 0) for word in sentence.lower().split())
        sentence_scores.append((i, score, sentence))
    sentence_scores.sort(key=lambda x: x[1], reverse=True)
    top = sorted(sentence_scores[:max_sentences], key=lambda x: x[0])
    return " ".join([s[2] for s in top])


def download_text_file(text, filename="documento.txt"):
    return text.encode("utf-8")


# ============================================================
# FUNCIÓN TTS MEJORADA - DIVIDE TEXTO LARGO EN FRAGMENTOS
# ============================================================
def generate_tts_audio_chunked(text, lang="es", slow=False, max_chunk_chars=3000):
    """
    Genera audio TTS dividiendo el texto en fragmentos pequeños.
    gTTS tiene problemas con textos muy largos, así que los dividimos.
    """
    try:
        # Limpiar el texto
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) > max_chunk_chars:
            text = text[:max_chunk_chars]
            # Cortar en un punto natural (final de oración)
            last_period = text.rfind('.')
            if last_period > max_chunk_chars * 0.7:
                text = text[:last_period + 1]
            else:
                text = text + "..."
        
        if not text.strip():
            st.error("❌ No hay texto para convertir a audio")
            return None
        
        # Generar audio con gTTS
        tts = gTTS(text=text, lang=lang, slow=slow)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer.getvalue()
    except Exception as e:
        st.error(f"❌ Error al generar audio: {e}")
        return None


# ============================================================
# INICIALIZACIÓN DE SESSION STATE
# ============================================================
if "audio_recordings" not in st.session_state:
    st.session_state.audio_recordings = []

if "document_name" not in st.session_state:
    st.session_state.document_name = None

if "auto_play_tts" not in st.session_state:
    st.session_state.auto_play_tts = True

if "tts_audio_generated" not in st.session_state:
    st.session_state.tts_audio_generated = None


def save_audio_recording(audio_bytes, page_range, note=""):
    recording = {
        "id": len(st.session_state.audio_recordings) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "page_range": page_range,
        "note": note,
        "audio_bytes": audio_bytes,
        "document": st.session_state.document_name,
        "type": "voice_recording"
    }
    st.session_state.audio_recordings.append(recording)


def save_tts_audio(audio_bytes, page_range, lang="es"):
    recording = {
        "id": len(st.session_state.audio_recordings) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "page_range": page_range,
        "note": f"Audio generado automáticamente (idioma: {lang})",
        "audio_bytes": audio_bytes,
        "document": st.session_state.document_name,
        "type": "tts"
    }
    st.session_state.audio_recordings.append(recording)


def delete_recording(recording_id):
    st.session_state.audio_recordings = [
        r for r in st.session_state.audio_recordings if r["id"] != recording_id
    ]


# ============================================================
# INTERFAZ PRINCIPAL
# ============================================================
st.markdown('<p class="main-header">📚 Lector PDF Pro - Con Audio</p>', unsafe_allow_html=True)
st.markdown("### Lee, analiza y **escucha automáticamente** tus documentos PDF 🔊")

# Sidebar
with st.sidebar:
    st.header("📂 Cargar documento")
    source_option = st.radio(
        "Selecciona la fuente:",
        ["📁 Subir archivo", "🌐 Desde URL"],
        label_visibility="collapsed"
    )

    metadata = None
    total_pages = 0
    pdf_content = None
    uploaded_file = None

    if source_option == "📁 Subir archivo":
        uploaded_file = st.file_uploader(
            "Arrastra tu PDF aquí",
            type=["pdf"],
            help="Archivos PDF de cualquier tamaño"
        )
        if uploaded_file is not None:
            file_details = {
                "Nombre": uploaded_file.name,
                "Tamaño": f"{uploaded_file.size / 1024 / 1024:.2f} MB",
                "Tipo": uploaded_file.type
            }
            st.json(file_details)
            metadata, total_pages = get_pdf_info(uploaded_file)
            st.session_state.document_name = uploaded_file.name
    else:
        url_input = st.text_input(
            "🔗 URL del PDF:",
            placeholder="https://ejemplo.com/documento.pdf"
        )
        if st.button("🌐 Cargar desde URL"):
            if url_input:
                parsed = urlparse(url_input)
                if parsed.scheme and parsed.netloc:
                    metadata, total_pages, pdf_content = get_pdf_info_from_url(url_input)
                    st.session_state.document_name = url_input.split("/")[-1]
                else:
                    st.error("❌ URL inválida")

    st.markdown("---")
    st.markdown("### ⚙️ Configuración de lotes")
    
    # RECOMENDACIÓN: máximo 10 páginas para TTS
    batch_size = st.slider(
        "Páginas por lote:",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
        help="⚠️ Se recomienda 5-10 páginas para mejor calidad de audio"
    )
    
    st.warning("⚠️ **Recomendación**: Usa lotes de 5-10 páginas para que el audio funcione mejor. Con 50 páginas el texto es muy largo.")

    # Configuración de audio
    st.markdown("---")
    st.markdown("### 🔊 Configuración de Audio")
    auto_play_enabled = st.toggle(
        "🔔 Reproducción automática",
        value=True,
        help="Activa/desactiva la reproducción automática del audio"
    )
    st.session_state.auto_play_tts = auto_play_enabled
    
    st.info("🎧 El audio se reproducirá automáticamente por los **parlantes** o **audífonos** de tu PC")

    # Resumen de grabaciones
    st.markdown("---")
    st.markdown("### 🎙️ Registro de Audio")
    total_recordings = len(st.session_state.audio_recordings)
    st.metric("Grabaciones guardadas", total_recordings)
    
    if total_recordings > 0:
        if st.button("🗑️ Borrar todas las grabaciones"):
            st.session_state.audio_recordings = []
            st.rerun()

# ============================================================
# CONTENIDO PRINCIPAL
# ============================================================
if metadata is None or total_pages == 0:
    st.info(" Carga un PDF desde la barra lateral para comenzar")
    st.markdown("""
    ### ✨ Características
    - 🚀 Procesamiento por lotes (no colapsa con PDFs grandes)
    - 🔊 **Reproducción automática** por parlantes/audífonos
    - 🎙️ **Grabadora de voz** para dejar registro de tu lectura
    - 📖 **Text-to-Speech** para escuchar el documento
    - 💾 Guarda y descarga todas tus grabaciones
    - 🔍 Búsqueda avanzada con resaltado
    - 📊 Extracción automática de tablas
    - 📈 Estadísticas del documento
    - 📧 Extracción de emails, URLs y teléfonos
    - 📝 Resumen automático
    - 🎯 Selector de páginas inteligente
    """)
else:
    total_batches = math.ceil(total_pages / batch_size)
    
    st.success(f"✅ PDF cargado: **{total_pages}** páginas | **{total_batches}** lotes de {batch_size} páginas")

    # Selector de lote
    st.markdown("#### 📑 Selector de páginas")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        batch_num = st.slider(
            "Selecciona un lote:",
            min_value=1,
            max_value=total_batches,
            value=1,
            format="Lote %d"
        )
    
    start_page = (batch_num - 1) * batch_size + 1
    end_page = min(batch_num * batch_size, total_pages)
    page_range = f"{start_page}-{end_page}"
    
    st.markdown(f"""
    <div class='batch-info'>
        📄 <strong>Páginas {start_page} - {end_page}</strong> de {total_pages} 
        (Lote {batch_num} de {total_batches})
    </div>
    """, unsafe_allow_html=True)

    if source_option == "📁 Subir archivo" and uploaded_file:
        pages_data = load_pdf_batch(uploaded_file, start_page, end_page)
    else:
        pages_data = load_pdf_batch_from_url(pdf_content, start_page, end_page)

    if not pages_data:
        st.error("❌ No se pudieron cargar las páginas")
    else:
        batch_text = get_batch_text(pages_data)
        batch_words = count_words(batch_text)
        batch_chars = count_characters(batch_text)
        batch_lines = count_lines(batch_text)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📄 Páginas en lote", len(pages_data))
        col2.metric("📝 Palabras", f"{batch_words:,}")
        col3.metric("🔤 Caracteres", f"{batch_chars:,}")
        col4.metric("📏 Líneas", f"{batch_lines:,}")

        # Advertencia si el texto es muy largo para TTS
        if batch_chars > 3000:
            st.warning(f"""
            ⚠️ **El texto de este lote tiene {batch_chars:,} caracteres.** 
            Para mejor calidad de audio, se recomienda usar lotes de **5 páginas o menos**.
            El audio se generará con los primeros 3,000 caracteres.
            """)

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📖 Lectura",
            " Búsqueda",
            "📊 Tablas",
            "📈 Análisis",
            "🎙️ Audio",
            " Exportar"
        ])

        # TAB 1: LECTURA
        with tab1:
            st.subheader(f"📖 Páginas {start_page} - {end_page}")

            if metadata and any(metadata.values()):
                with st.expander(" Metadatos del documento"):
                    for key, value in metadata.items():
                        if value:
                            st.write(f"**{key}:** {value}")

            page_option = st.radio(
                "Modo de visualización:",
                ["📑 Ver todas las páginas del lote", "🎯 Página específica"],
                horizontal=True
            )

            if page_option == "🎯 Página específica":
                page_num = st.slider(
                    "Selecciona una página:",
                    min_value=start_page,
                    max_value=end_page,
                    value=start_page
                )
                selected_page = next((p for p in pages_data if p["page_number"] == page_num), None)
                if selected_page:
                    st.markdown(f"### Página {page_num}")
                    st.text_area("", value=selected_page["text"], height=500, label_visibility="collapsed")
            else:
                for page in pages_data:
                    st.markdown(f"---\n### 📄 Página {page['page_number']}")
                    st.text_area("", value=page["text"], height=300, label_visibility="collapsed")

        # TAB 2: BÚSQUEDA
        with tab2:
            st.subheader(f"🔍 Buscar en el lote (Páginas {start_page}-{end_page})")
            search_query = st.text_input(
                "Ingresa el texto a buscar:",
                placeholder="Ej: contrato, fecha, nombre..."
            )

            if search_query:
                highlighted_text, match_count = search_text(batch_text, search_query)
                st.success(f"✅ Se encontraron **{match_count}** coincidencias en este lote")

                st.markdown("#### 📄 Coincidencias por página:")
                for page in pages_data:
                    page_matches = len(re.findall(
                        re.escape(search_query), page["text"], re.IGNORECASE
                    ))
                    if page_matches > 0:
                        with st.expander(
                            f"📄 Página {page['page_number']} ({page_matches} coincidencias)"
                        ):
                            highlighted_page, _ = search_text(page["text"], search_query)
                            st.markdown(highlighted_page)

                with st.expander("📝 Ver todo el texto resaltado"):
                    st.markdown(highlighted_text)
            else:
                st.info("💡 Ingresa un término para buscar en el lote actual")

        # TAB 3: TABLAS
        with tab3:
            st.subheader(f"📊 Tablas extraídas (Páginas {start_page}-{end_page})")
            all_tables = []
            for page in pages_data:
                for table in page["tables"]:
                    if table:
                        all_tables.append({
                            "page": page["page_number"],
                            "table": table
                        })

            if all_tables:
                st.success(f"✅ Se encontraron **{len(all_tables)}** tablas en este lote")
                for idx, table_info in enumerate(all_tables):
                    with st.expander(f"📊 Tabla {idx + 1} - Página {table_info['page']}"):
                        try:
                            df = pd.DataFrame(table_info["table"][1:],
                                              columns=table_info["table"][0])
                            st.dataframe(df, use_container_width=True)
                            csv = df.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                label="💾 Descargar CSV",
                                data=csv,
                                file_name=f"tabla_{idx + 1}_pagina_{table_info['page']}.csv",
                                mime="text/csv"
                            )
                        except Exception as e:
                            st.warning(f"No se pudo procesar la tabla: {e}")
                            st.write(table_info["table"])
            else:
                st.warning("⚠️ No se encontraron tablas en este lote")

        # TAB 4: ANÁLISIS
        with tab4:
            st.subheader(f" Análisis del lote (Páginas {start_page}-{end_page})")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 🔤 Palabras más frecuentes")
                top_words = get_most_common_words(batch_text, n=15)
                if top_words:
                    df_words = pd.DataFrame(top_words, columns=["Palabra", "Frecuencia"])
                    st.bar_chart(df_words.set_index("Palabra"))
                    st.dataframe(df_words, use_container_width=True)

            with col2:
                st.markdown("#### 📝 Resumen del lote")
                summary = generate_summary(batch_text, max_sentences=5)
                st.info(summary)

            st.markdown("####  Datos extraídos")
            col_a, col_b, col_c = st.columns(3)

            with col_a:
                emails = extract_emails(batch_text)
                st.markdown(f"**📧 Correos ({len(emails)})**")
                if emails:
                    for email in emails:
                        st.write(f"- {email}")
                else:
                    st.write("No se encontraron correos")

            with col_b:
                urls = extract_urls(batch_text)
                st.markdown(f"**🔗 URLs ({len(urls)})**")
                if urls:
                    for url in urls[:10]:
                        st.write(f"- {url}")
                    if len(urls) > 10:
                        st.write(f"...y {len(urls) - 10} más")
                else:
                    st.write("No se encontraron URLs")

            with col_c:
                phones = extract_phones(batch_text)
                st.markdown(f"**📞 Teléfonos ({len(phones)})**")
                if phones:
                    for phone in phones[:10]:
                        st.write(f"- {phone}")
                else:
                    st.write("No se encontraron teléfonos")

            st.markdown("####  Distribución de texto por página (en este lote)")
            words_per_page = [count_words(p["text"]) for p in pages_data]
            st.bar_chart(words_per_page)

        # ============================================
        # TAB 5: AUDIO - VERSIÓN CORREGIDA
        # ============================================
        with tab5:
            st.subheader(f"🎙️ Audio - Lote {batch_num} (Páginas {start_page}-{end_page})")
            
            if st.session_state.auto_play_tts:
                st.markdown("""
                <div class='auto-play-notice'>
                    🔔 <strong>Reproducción automática ACTIVADA</strong><br>
                    El audio se reproducirá automáticamente por los <strong>parlantes</strong> o <strong>audífonos</strong> de tu PC.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class='auto-play-notice warning'>
                    🔕 <strong>Reproducción automática DESACTIVADA</strong><br>
                    Deberás presionar play manualmente para escuchar el audio.
                </div>
                """, unsafe_allow_html=True)

            audio_tab1, audio_tab2, audio_tab3 = st.tabs([
                "🎤 Grabar voz",
                "🔊 Leer documento (TTS)",
                f"📚 Mis grabaciones ({len(st.session_state.audio_recordings)})"
            ])

            # SUB-TAB 1: GRABAR VOZ
            with audio_tab1:
                st.markdown("### 🎤 Grabar tu voz leyendo el documento")
                st.markdown(f"""
                <div class='audio-card'>
                    📄 <strong>Documento:</strong> {st.session_state.document_name}<br>
                    📑 <strong>Páginas:</strong> {page_range}<br>
                     <strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}
                </div>
                """, unsafe_allow_html=True)

                st.markdown("#### 📝 Texto a leer (referencia):")
                st.text_area(
                    "",
                    value=batch_text[:1500] + ("..." if len(batch_text) > 1500 else ""),
                    height=200,
                    label_visibility="collapsed"
                )

                st.markdown("---")
                st.markdown("#### 🎙️ Grabar audio:")
                st.warning("⚠️ Haz clic en el micrófono para comenzar a grabar. Haz clic de nuevo para detener.")

                audio_bytes = audio_recorder(
                    text=" Haz clic para grabar",
                    recording_color="#e74c3c",
                    neutral_color="#1f77b4",
                    icon_name="microphone",
                    icon_size="3x"
                )

                if audio_bytes is not None:
                    st.audio(audio_bytes, format="audio/wav")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        recording_note = st.text_input(
                            "📝 Nota para la grabación (opcional):",
                            placeholder="Ej: Lectura del capítulo 1..."
                        )
                    with col2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("💾 Guardar grabación", type="primary"):
                            save_audio_recording(audio_bytes, page_range, recording_note)
                            st.success(f"✅ Grabación guardada para las páginas {page_range}")
                            st.balloons()

            # SUB-TAB 2: TTS CON AUTOPLAY CORREGIDO
            with audio_tab2:
                st.markdown("### 🔊 Escuchar la lectura del documento automáticamente")
                st.info("""
                 **El audio se reproducirá automáticamente por los parlantes o audífonos de tu PC** 
                para que puedas escuchar la lectura del documento sin intervención manual.
                """)

                # Advertencia importante
                if batch_chars > 3000:
                    st.warning(f"""
                    ⚠️ **Este lote tiene {batch_chars:,} caracteres.** 
                    Se recomienda usar lotes de **5 páginas o menos** para mejor calidad de audio.
                    El audio se generará con los primeros 3,000 caracteres.
                    """)

                col1, col2 = st.columns(2)
                with col1:
                    tts_lang = st.selectbox(
                        "🌍 Idioma:",
                        ["es", "en", "fr", "de", "it", "pt"],
                        format_func=lambda x: {
                            "es": "🇸 Español",
                            "en": "🇬🇧 Inglés",
                            "fr": "🇫🇷 Francés",
                            "de": "🇩🇪 Alemán",
                            "it": "🇮 Italiano",
                            "pt": "🇹 Portugués"
                        }.get(x, x),
                        key="tts_lang_select"
                    )
                with col2:
                    tts_slow = st.checkbox("🐢 Velocidad lenta", value=False, key="tts_slow_check")

                st.markdown("#### 📑 Selecciona el texto a leer:")
                tts_option = st.radio(
                    "Alcance:",
                    ["Todo el lote actual", "Página específica"],
                    horizontal=True,
                    key="tts_option_radio"
                )

                tts_text = batch_text
                if tts_option == "Página específica":
                    tts_page = st.slider(
                        "Selecciona página:",
                        min_value=start_page,
                        max_value=end_page,
                        value=start_page,
                        key="tts_page_slider"
                    )
                    selected = next((p for p in pages_data if p["page_number"] == tts_page), None)
                    if selected:
                        tts_text = selected["text"]

                st.text_area(
                    "Vista previa del texto a convertir:",
                    value=tts_text[:1000] + ("..." if len(tts_text) > 1000 else ""),
                    height=200,
                    label_visibility="collapsed"
                )

                st.info(f"📊 Texto a convertir: **{len(tts_text)} caracteres** (máximo 3,000)")

                # Botón principal
                if st.button("🔊 Generar y reproducir lectura", type="primary"):
                    with st.spinner(" Generando audio... por favor espera"):
                        tts_audio = generate_tts_audio_chunked(tts_text, lang=tts_lang, slow=tts_slow)
                        
                        if tts_audio:
                            st.session_state.tts_audio_generated = {
                                "audio": tts_audio,
                                "page_range": page_range,
                                "lang": tts_lang,
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "text_length": len(tts_text)
                            }
                            st.success("✅ Audio generado correctamente")
                            st.rerun()
                        else:
                            st.error("❌ No se pudo generar el audio. Intenta con menos texto.")

                # REPRODUCCIÓN AUTOMÁTICA CON HTML5
                if st.session_state.tts_audio_generated:
                    tts_info = st.session_state.tts_audio_generated
                    
                    st.markdown("---")
                    st.markdown("### 🎧 Reproduciendo lectura del documento...")
                    
                    st.markdown(f"""
                    <div class='audio-card'>
                        🎵 <strong>Reproduciendo automáticamente</strong><br>
                        📑 Páginas: {tts_info['page_range']}<br>
                         Idioma: {tts_info['lang']}<br>
                        📊 Caracteres: {tts_info['text_length']:,}<br>
                        🕐 Generado: {tts_info['timestamp']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # AUTOPLAY FORZADO con HTML5
                    if st.session_state.auto_play_tts:
                        play_audio_autoplay(tts_info["audio"], format_type="audio/mp3")
                    else:
                        st.audio(tts_info["audio"], format="audio/mp3")
                    
                    # Controles adicionales
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.download_button(
                            label="💾 Descargar MP3",
                            data=tts_info["audio"],
                            file_name=f"lectura_paginas_{tts_info['page_range']}.mp3",
                            mime="audio/mpeg"
                        )
                    with col2:
                        if st.button("💾 Guardar en mis grabaciones"):
                            save_tts_audio(tts_info["audio"], tts_info["page_range"], lang=tts_info["lang"])
                            st.success("✅ Audio guardado en tus grabaciones")
                    with col3:
                        if st.button("🔄 Generar nuevo audio"):
                            st.session_state.tts_audio_generated = None
                            st.rerun()

            # SUB-TAB 3: MIS GRABACIONES
            with audio_tab3:
                st.markdown("### 📚 Historial de grabaciones")
                
                recordings = st.session_state.audio_recordings
                
                if not recordings:
                    st.info("🎙️ Aún no has grabado ningún audio. ¡Comienza a grabar!")
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        filter_doc = st.selectbox(
                            "📄 Filtrar por documento:",
                            ["Todos"] + list(set(r["document"] for r in recordings))
                        )
                    with col2:
                        filter_type = st.selectbox(
                            "🎙️ Filtrar por tipo:",
                            ["Todos", "🎤 Grabación de voz", "🔊 Texto a voz"]
                        )

                    filtered = recordings
                    if filter_doc != "Todos":
                        filtered = [r for r in filtered if r["document"] == filter_doc]
                    if filter_type != "Todos":
                        type_map = {
                            "🎤 Grabación de voz": "voice_recording",
                            "🔊 Texto a voz": "tts"
                        }
                        filtered = [r for r in filtered if r["type"] == type_map[filter_type]]

                    st.success(f"📊 Mostrando **{len(filtered)}** de {len(recordings)} grabaciones")

                    for rec in filtered:
                        with st.container():
                            st.markdown(f"""
                            <div class='audio-card'>
                                <strong>#{rec['id']}</strong> | 
                                🕐 {rec['timestamp']} | 
                                📄 {rec['document']} | 
                                📑 Páginas {rec['page_range']} | 
                                {'🎤 Voz' if rec['type'] == 'voice_recording' else '🔊 TTS'}
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if rec["note"]:
                                st.caption(f"📝 {rec['note']}")
                            
                            col1, col2, col3 = st.columns([3, 1, 1])
                            with col1:
                                play_audio_normal(rec["audio_bytes"], 
                                                "audio/wav" if rec["type"] == "voice_recording" else "audio/mp3")
                            with col2:
                                ext = "wav" if rec["type"] == "voice_recording" else "mp3"
                                mime = "audio/wav" if rec["type"] == "voice_recording" else "audio/mpeg"
                                st.download_button(
                                    label="💾 Descargar",
                                    data=rec["audio_bytes"],
                                    file_name=f"grabacion_{rec['id']}_pag_{rec['page_range']}.{ext}",
                                    mime=mime,
                                    key=f"download_{rec['id']}"
                                )
                            with col3:
                                if st.button("🗑️ Eliminar", key=f"delete_{rec['id']}"):
                                    delete_recording(rec["id"])
                                    st.rerun()
                            
                            st.markdown("---")

        # TAB 6: EXPORTAR
        with tab6:
            st.subheader(f"💾 Exportar lote (Páginas {start_page}-{end_page})")

            export_format = st.radio(
                "Formato de exportación:",
                ["📝 Texto plano (.txt)", "📊 CSV con páginas", "📋 JSON completo"],
                horizontal=True
            )

            if "Texto plano" in export_format:
                st.download_button(
                    label=" Descargar TXT",
                    data=download_text_file(batch_text),
                    file_name=f"lote_{batch_num}_paginas_{start_page}-{end_page}.txt",
                    mime="text/plain"
                )
                st.text_area("Vista previa:", batch_text[:2000], height=300)

            elif "CSV" in export_format:
                df_export = pd.DataFrame([
                    {
                        "Página": p["page_number"],
                        "Texto": p["text"],
                        "Palabras": count_words(p["text"]),
                        "Caracteres": count_characters(p["text"])
                    }
                    for p in pages_data
                ])
                csv = df_export.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="💾 Descargar CSV",
                    data=csv,
                    file_name=f"lote_{batch_num}_paginas.csv",
                    mime="text/csv"
                )
                st.dataframe(df_export, use_container_width=True)

            else:
                json_data = json.dumps({
                    "metadata": metadata,
                    "batch_info": {
                        "batch_number": batch_num,
                        "start_page": start_page,
                        "end_page": end_page,
                        "total_batches": total_batches
                    },
                    "pages": [
                        {
                            "page_number": p["page_number"],
                            "text": p["text"],
                            "tables_count": len(p["tables"])
                        }
                        for p in pages_data
                    ]
                }, ensure_ascii=False, indent=2)
                st.download_button(
                    label="💾 Descargar JSON",
                    data=json_data.encode("utf-8"),
                    file_name=f"lote_{batch_num}_paginas.json",
                    mime="application/json"
                )
                st.code(json_data[:2000], language="json")

# ============================================================
# FOOTER CON CRÉDITOS
# ============================================================
st.markdown("---")
st.markdown("""
<div class='credits-footer'>
    <h3>🎨 Diseño por Vibe Coding</h3>
    <p class='author'>✨ Por Ing. Hernán Quiroz ✨</p>
    <p> Lector PDF Pro - Con Audio y Reproducción Automática</p>
    <p>🔊 Escucha tus documentos por parlantes o audífonos</p>
    <div class='vibe-badge'>
        🚀 Desarrollado con Streamlit + IA | Octubre 2026
    </div>
</div>
""", unsafe_allow_html=True)
