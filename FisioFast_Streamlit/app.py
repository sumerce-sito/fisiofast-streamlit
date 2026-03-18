import streamlit as st
import json
import os
from datetime import datetime

# ─── Configuración de página ────────────────────────────────────────────────
st.set_page_config(
    page_title="FisioFast ⚡",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ─── CSS personalizado ───────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #080e1a; color: #f1f5f9; }
    section[data-testid="stSidebar"] { background-color: #0d1525; }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #38bdf8, #0ea5e9);
        border: none; border-radius: 14px;
        font-weight: 800; font-size: 1.05rem;
        padding: 0.7rem 1.5rem; color: #fff;
        box-shadow: 0 8px 20px -4px rgba(56,189,248,0.4);
    }
    .nota-box {
        background: #0d1a2b;
        border: 1px solid rgba(56,189,248,0.3);
        border-radius: 14px;
        padding: 1.2rem 1.5rem;
        font-size: 1rem;
        line-height: 1.7;
        white-space: pre-wrap;
    }
    h1 { color: #38bdf8; }
    h2, h3 { color: #94a3b8; }
    .section-badge {
        display: inline-block;
        background: rgba(56,189,248,0.12);
        border: 1px solid rgba(56,189,248,0.3);
        border-radius: 8px;
        padding: 2px 10px;
        font-size: 0.75rem;
        color: #38bdf8;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ─── Cargar prompt del sistema ───────────────────────────────────────────────
PROMPT_SISTEMA = """Eres un asistente experto en redacción clínica para fisioterapia. Tu tarea es recibir datos estructurados y breves (micro-notas) y convertirlos en registros completos, profesionales y con lenguaje técnico-científico, bajo el modelo SOAP.

El JSON de entrada tendrá la propiedad "tipo_registro" que indicará si es una "valoracion" (Valoración Inicial) o un "seguimiento" (Evolución de rutina).

=========================================
SI EL TIPO DE REGISTRO ES "valoracion"
=========================================
Recibirás los siguientes datos:
- paciente, ocupacion, motivo
- examenes, antecedentes, examen_fisico
- diag_ppal, diag_rel1, diag_rel2
- eva, funcion, ejercicios, tecnicas, accesorios, tolerancia

Tu tarea es redactar una NOTA DE INGRESO estructurada con los siguientes apartados (usa negritas para los títulos):
**PACIENTE:** [Nombre completo del paciente]
**MOTIVO DE CONSULTA:** [Redactar como "Paciente manifiesta venir por..."]
**OCUPACIÓN:** [Dato]
**EXÁMENES:** [Dato]
**ANTECEDENTES:** [Redactar patologías, quirúrgicos, alérgicos, etc.]
**EXAMEN FÍSICO:** [Desarrollar usando lenguaje técnico las alteraciones mencionadas]
**DIAGNÓSTICOS:** [Lista de CIE-10 Principal y Relacionados]
**PLAN DE MANEJO (SESIÓN DE HOY):**
[Redacta de forma continua las variables de tratamiento]. Usa "funcion", "ejercicios", "tecnicas" y "accesorios" para describir lo que se realizó. Incluye el EVA al inicio. Ejemplo: "EVA 5/10. Se ejecuta activación muscular en posición [funcion], con ejercicios [ejercicios] en [región], aplicación de [tecnicas], utilizando [accesorios]. Tolerancia [tolerancia]."

=========================================
SI EL TIPO DE REGISTRO ES "seguimiento"
=========================================
Recibirás los siguientes datos:
- paciente, eva, cambio
- funcion, ejercicios, tecnicas, accesorios, tolerancia

Tu salida debe tener OBLIGATORIAMENTE este formato exacto:

**[valor de "paciente"]:** [párrafo de evolución]

El párrafo de evolución debe incluir en orden:
1. Una frase inicial sobre el estado del paciente basado en "cambio" y "eva".
2. Detalle de la activación muscular, posición de trabajo y ejercicios realizados.
3. Detalle de las técnicas manuales, medios físicos y masaje aplicados, y accesorios utilizados.
4. Cierre con la "tolerancia".

REGLAS GENERALES:
- Usa un tono formal, técnico, objetivo y en tercera persona ("Se realiza", "Paciente refiere").
- NO INVENTES síntomas, enfermedades o lesiones diferentes a las que vienen en el JSON.
- Usa terminología médica para los conectores lógicos."""

# ─── Session State ───────────────────────────────────────────────────────────
if "registros" not in st.session_state:
    st.session_state.registros = []
if "ultimo_payload" not in st.session_state:
    st.session_state.ultimo_payload = None
if "nota_generada" not in st.session_state:
    st.session_state.nota_generada = None

# ─── Obtener API Key ─────────────────────────────────────────────────────────
# Primero busca en secrets de Streamlit Cloud, luego en la barra lateral
groq_api_key = ""
try:
    groq_api_key = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuración IA")

    if not groq_api_key:
        groq_api_key = st.text_input(
            "🔑 Groq API Key",
            type="password",
            placeholder="gsk_...",
            help="Obtén tu clave gratis en groq.com → Console → API Keys"
        )
        st.caption("La clave no se guarda en ningún lado.")
    else:
        st.success("✅ API Key configurada")

    modelo = st.selectbox(
        "Modelo",
        [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ],
        index=0,
        help="llama-3.3-70b es el más capaz. llama-3.1-8b es el más rápido."
    )

    st.divider()
    st.caption(f"📋 Registros en sesión: **{len(st.session_state.registros)}**")
    st.divider()
    st.markdown("""
    **Groq es gratis:**
    - 14,400 req / día
    - Llama 3.3 70B incluido
    - Sin tarjeta de crédito

    Regístrate en [groq.com](https://groq.com)
    """)

# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("# ⚡ FisioFast")
st.markdown("<p style='color:#64748b; font-size:0.85rem; letter-spacing:2px; text-transform:uppercase;'>Documentación Clínica con IA — Fisioterapia</p>", unsafe_allow_html=True)
st.divider()

# ═══════════════════════════════════════════════════════════════════════════
#  FORMULARIO
# ═══════════════════════════════════════════════════════════════════════════
with st.form("fisio_form", clear_on_submit=False):

    # ── Paciente + Tipo ──────────────────────────────────────────────────
    st.markdown('<div class="section-badge">👤 Paciente</div>', unsafe_allow_html=True)
    paciente = st.text_input("Nombre completo", placeholder="Ej. Juan Pérez García", label_visibility="collapsed")

    st.markdown('<div class="section-badge">📋 Tipo de Registro</div>', unsafe_allow_html=True)
    tipo_label = st.radio(
        "Tipo", ["Valoración Inicial", "Seguimiento / Evolución"],
        horizontal=True, label_visibility="collapsed"
    )
    tipo_key = "valoracion" if tipo_label == "Valoración Inicial" else "seguimiento"

    # ── Valoración Inicial ────────────────────────────────────────────────
    ocupacion = motivo = examenes = antecedentes = examen_fisico = ""
    diag_ppal = diag_rel1 = diag_rel2 = ""
    cambio = "Igual"

    if tipo_key == "valoracion":
        st.divider()
        st.markdown('<div class="section-badge">🟣 Datos Clínicos</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            ocupacion = st.text_input("Ocupación", placeholder="Ej. Docente, Obrero")
        with col2:
            examenes = st.text_input("Exámenes", value="NO TRAE")
        motivo = st.text_area("Motivo de Consulta", placeholder="Paciente refiere...", height=80)
        antecedentes = st.text_area("Antecedentes Clínicos", placeholder="Patológicos, quirúrgicos, alérgicos...", height=80)
        examen_fisico = st.text_area("Examen Físico", placeholder="Hallazgos al examen...", height=100)

        st.markdown('<div class="section-badge">📌 Diagnósticos CIE-10</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            diag_ppal = st.text_input("Principal", placeholder="Ej. M54.5")
        with col2:
            diag_rel1 = st.text_input("Relacionado 1", placeholder="Ej. M47.8")
        with col3:
            diag_rel2 = st.text_input("Relacionado 2", placeholder="Ej. M62.0")

    # ── Seguimiento ───────────────────────────────────────────────────────
    if tipo_key == "seguimiento":
        st.divider()
        st.markdown('<div class="section-badge">📈 Cambio vs. Sesión Previa</div>', unsafe_allow_html=True)
        cambio = st.radio("Estado", ["Mejoró", "Igual", "Empeoró"],
                          horizontal=True, index=1, label_visibility="collapsed")

    # ── EVA ───────────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-badge">🔴 EVA — Dolor Actual</div>', unsafe_allow_html=True)
    eva = st.slider("Escala de Dolor (0-10)", 0, 10, 5, label_visibility="collapsed")
    eva_color = "🟢" if eva <= 3 else ("🟡" if eva <= 6 else "🔴")
    st.caption(f"{eva_color} EVA: **{eva}/10**")

    # ── Función ───────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-badge">🏃 Función</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Posición de trabajo")
        funcion_pos = st.multiselect("pos", [
            "Act. Muscular Sedente",
            "Act. Muscular Decúbito Supino",
            "Act. Muscular Bípedo",
            "Act. Muscular Decúbito Prono",
            "Act. Muscular Decúbito Lateral D",
            "Act. Muscular Decúbito Lateral I",
            "Act. Muscular Carga Unipodal",
            "Act. Muscular Cuadrúpedo",
        ], label_visibility="collapsed")
    with col2:
        st.caption("Actividad funcional")
        funcion_act = st.multiselect("act", [
            "Marcha (Descargas de Peso)",
            "Balanceo", "Propiocepción", "Equilibrio",
            "Higiene Postural", "AVD", "Balonterapia",
        ], label_visibility="collapsed")

    # ── Ejercicios ────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-badge">💪 Ejercicios</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("Tipo")
        ej_tipo = st.multiselect("ejt", [
            "Isométricos", "Isotónicos",
            "Resistidos (Autocarga)",
            "Estiramientos a Tolerancia",
            "Estiramientos (Flexibilidad)",
        ], label_visibility="collapsed")
    with col2:
        st.caption("Cadenas")
        ej_cadenas = st.multiselect("ejc", [
            "Cadena Cinética Abierta (CCA)",
            "Cadena Cinética Cerrada (CCC)",
            "Cadena Cinética Mixta",
            "Disociación Cintura Escapular",
            "Disociación Cintura Humeral",
            "Disociación Escapulohumeral",
            "Disociación Cintura Pélvica",
        ], label_visibility="collapsed")
    with col3:
        st.caption("Región")
        ej_region = st.multiselect("ejr", [
            "Miembros Superiores", "M. Superior Derecho",
            "M. Superior Izquierdo", "Miembros Inferiores",
            "M. Inferior Derecho", "M. Inferior Izquierdo",
            "Pelvis", "Espalda Alta", "Espalda Media", "Espalda Baja",
        ], label_visibility="collapsed")

    # ── Técnicas ──────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-badge">⚡ Técnicas</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Manuales / Otros")
        tec_manuales = st.multiselect("tm", [
            "Técnica de Codman", "Técnica de McKenzie",
            "Técnica de Williams", "Técnica de Klapp",
            "Movilización Articular", "Manipulación", "Tracción",
            "Punción Seca", "Kinesiotape", "Vendaje Funcional",
        ], label_visibility="collapsed")
        st.caption("Calor / Frío")
        tec_calor = st.multiselect("tc", [
            "Calor Húmedo", "Parafina", "Paquete Frío",
            "Batidas con Hielo", "Contrastes Caliente-Fría",
            "Hidroterapia Platón Caliente", "Hidroterapia Platón Frío",
        ], label_visibility="collapsed")
    with col2:
        st.caption("Electroterapia")
        tec_electro = st.multiselect("te", [
            "Ultrasonido", "Infrarrojo", "EMS / TENS",
            "Magnetoterapia", "Laser", "Ondas de Choque",
            "Diatermia", "Corrientes Interferenciales",
        ], label_visibility="collapsed")
        st.caption("Masaje")
        tec_masaje = st.multiselect("tmas", [
            "Masaje Manual Sedativo", "Masaje Manual Depletivo",
            "Masaje Manual Relajante", "Vibromasaje",
        ], label_visibility="collapsed")

    # ── Accesorios ────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-badge">🛠️ Accesorios</div>', unsafe_allow_html=True)
    accesorios = st.multiselect("acc", [
        "Escalerilla de Dedos", "Sistema de Poleas", "Rueda Náutica",
        "Bastón", "Rollo Terapéutico", "Balancín de Puyas Mano",
        "Balancín de Puyas Pie", "Balancín de Madera", "Disco de Madera",
        "Disco de Giros", "Patín de Madera", "Digiflex",
        "Plastilina Terapéutica", "Bandas Elásticas", "Pesas",
        "Elíptica", "Bicicleta Estática", "Caminadora",
        "Sistema de Pedales", "Escalera de Dos Pasos", "Barras Paralelas",
    ], label_visibility="collapsed")

    # ── Tolerancia ────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-badge">✅ Tolerancia</div>', unsafe_allow_html=True)
    tolerancia = st.radio("tol", ["Excelente", "Buena", "Regular", "Mala"],
                          horizontal=True, index=0, label_visibility="collapsed")

    st.divider()
    submitted = st.form_submit_button("💾  GUARDAR REGISTRO", use_container_width=True, type="primary")

# ═══════════════════════════════════════════════════════════════════════════
#  PROCESAR FORMULARIO
# ═══════════════════════════════════════════════════════════════════════════
if submitted:
    if not paciente.strip():
        st.error("⚠️ Debes ingresar el nombre del paciente.")
    else:
        payload = {
            "tipo_registro": tipo_key,
            "paciente": paciente.strip(),
            "eva": str(eva),
            "funcion": funcion_pos + funcion_act,
            "ejercicios": ej_tipo + ej_cadenas + ej_region,
            "tecnicas": tec_manuales + tec_calor + tec_electro + tec_masaje,
            "accesorios": accesorios,
            "tolerancia": tolerancia,
            "_fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        if tipo_key == "valoracion":
            payload.update({
                "ocupacion": ocupacion,
                "motivo": motivo,
                "examenes": examenes,
                "antecedentes": antecedentes,
                "examen_fisico": examen_fisico,
                "diag_ppal": diag_ppal,
                "diag_rel1": diag_rel1,
                "diag_rel2": diag_rel2,
            })
        else:
            payload["cambio"] = cambio

        st.session_state.registros.append(payload)
        st.session_state.ultimo_payload = payload
        st.session_state.nota_generada = None
        st.success(f"✅ Registro guardado para **{paciente}**")

# ═══════════════════════════════════════════════════════════════════════════
#  MÓDULO JSON + LLM
# ═══════════════════════════════════════════════════════════════════════════
if st.session_state.ultimo_payload:
    st.divider()
    st.subheader("📋 JSON del último registro")

    json_limpio = {k: v for k, v in st.session_state.ultimo_payload.items() if k != "_fecha"}
    json_str = json.dumps(json_limpio, ensure_ascii=False, indent=2)

    col1, col2 = st.columns([4, 1])
    with col1:
        st.code(json_str, language="json")
    with col2:
        st.download_button(
            "📥 Descargar\nJSON",
            data=json_str,
            file_name=f"fisiofast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )

    # ── Botón generar nota ────────────────────────────────────────────────
    st.subheader("🤖 Generar Nota Clínica con IA")

    if not groq_api_key:
        st.warning("⚠️ Ingresa tu Groq API Key en el panel izquierdo para generar notas.")
    else:
        if st.button("✨ Generar Nota con IA", use_container_width=True, type="primary"):
            with st.spinner(f"Generando nota con **{modelo}**..."):
                try:
                    from groq import Groq
                    client = Groq(api_key=groq_api_key)
                    response = client.chat.completions.create(
                        model=modelo,
                        messages=[
                            {"role": "system", "content": PROMPT_SISTEMA},
                            {"role": "user",   "content": json_str},
                        ],
                        temperature=0.3,
                        max_tokens=1500,
                    )
                    st.session_state.nota_generada = response.choices[0].message.content
                except ImportError:
                    st.error("❌ Librería `groq` no instalada. Agrega `groq` al requirements.txt")
                except Exception as e:
                    st.error(f"❌ Error con Groq API:\n\n```\n{e}\n```")

    # ── Nota generada ────────────────────────────────────────────────────
    if st.session_state.nota_generada:
        st.subheader("📝 Nota Clínica")
        st.markdown(
            f'<div class="nota-box">{st.session_state.nota_generada}</div>',
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            nombre_archivo = st.session_state.ultimo_payload.get("paciente", "paciente").replace(" ", "_")
            st.download_button(
                "📥 Descargar Nota (.txt)",
                data=st.session_state.nota_generada,
                file_name=f"nota_{nombre_archivo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with col2:
            if st.button("🔄 Regenerar", use_container_width=True):
                st.session_state.nota_generada = None
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════
#  HISTORIAL DE SESIÓN
# ═══════════════════════════════════════════════════════════════════════════
if st.session_state.registros:
    st.divider()
    with st.expander(f"📚 Historial de sesión — {len(st.session_state.registros)} registro(s)"):
        todos_json = json.dumps(st.session_state.registros, ensure_ascii=False, indent=2)
        st.code(todos_json, language="json")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 Descargar historial completo",
                data=todos_json,
                file_name=f"fisiofast_historial_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True,
            )
        with col2:
            if st.button("🗑️ Limpiar historial", use_container_width=True):
                st.session_state.registros = []
                st.session_state.ultimo_payload = None
                st.session_state.nota_generada = None
                st.rerun()
