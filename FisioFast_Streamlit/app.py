import json
import os
from datetime import datetime

import streamlit as st


PROMPT_SISTEMA = """Eres un asistente experto en redaccion clinica para fisioterapia. Tu tarea es recibir datos estructurados y breves y convertirlos en registros completos, profesionales y con lenguaje tecnico-cientifico, bajo el modelo SOAP.

El JSON de entrada tendra la propiedad "tipo_registro" que indicara si es una "valoracion" (valoracion inicial) o un "seguimiento" (evolucion de rutina).

Si el tipo de registro es "valoracion", recibiras estos campos:
- paciente, ocupacion, motivo
- examenes, antecedentes, examen_fisico
- diag_ppal, diag_rel1, diag_rel2
- eva, funcion, ejercicios, tecnicas, accesorios, tolerancia

Tu tarea es redactar una nota de ingreso con estos apartados y en este orden:
**PACIENTE:** [Nombre completo del paciente]
**MOTIVO DE CONSULTA:** [Redactar como "Paciente manifiesta venir por..."]
**OCUPACION:** [Dato]
**EXAMENES:** [Dato]
**ANTECEDENTES:** [Redactar patologicos, quirurgicos, alergicos, etc.]
**EXAMEN FISICO:** [Desarrollar con lenguaje tecnico las alteraciones mencionadas]
**DIAGNOSTICOS:** [Lista de CIE-10 principal y relacionados]
**PLAN DE MANEJO (SESION DE HOY):**
[Redacta de forma continua las variables de tratamiento]. Usa "funcion", "ejercicios", "tecnicas" y "accesorios" para describir lo realizado. Incluye el EVA al inicio.

Si el tipo de registro es "seguimiento", recibiras estos campos:
- paciente, eva, cambio
- funcion, ejercicios, tecnicas, accesorios, tolerancia

La salida debe tener obligatoriamente este formato exacto:
**[valor de "paciente"]:** [parrafo de evolucion]

El parrafo de evolucion debe incluir, en orden:
1. Una frase inicial sobre el estado del paciente basada en "cambio" y "eva".
2. Activacion muscular, posicion de trabajo y ejercicios realizados.
3. Tecnicas manuales, medios fisicos, masaje y accesorios utilizados.
4. Cierre con la tolerancia.

Reglas generales:
- Usa un tono formal, tecnico, objetivo y en tercera persona.
- No inventes sintomas, enfermedades ni lesiones que no esten en el JSON.
- Usa terminologia medica y conectores clinicos.
"""

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]


def ensure_session_state() -> None:
    if "registros" not in st.session_state:
        st.session_state.registros = []
    if "ultimo_payload" not in st.session_state:
        st.session_state.ultimo_payload = None
    if "nota_generada" not in st.session_state:
        st.session_state.nota_generada = None
    if "selected_record_index" not in st.session_state:
        st.session_state.selected_record_index = None
    if "note_source_index" not in st.session_state:
        st.session_state.note_source_index = None


def get_groq_api_key() -> tuple[str, str | None]:
    try:
        secret_value = str(st.secrets["GROQ_API_KEY"]).strip()
    except Exception:
        secret_value = ""

    if secret_value:
        return secret_value, "Streamlit secrets"

    env_value = os.getenv("GROQ_API_KEY", "").strip()
    if env_value:
        return env_value, "variable de entorno"

    return "", None


def clean_text(value: object, default: str = "No especificado") -> str:
    text = str(value).strip()
    return text or default


def join_items(values: list[str], default: str = "No especificado") -> str:
    cleaned = [str(item).strip() for item in values if str(item).strip()]
    return ", ".join(cleaned) if cleaned else default


def build_record_label(payload: dict, index: int) -> str:
    paciente = clean_text(payload.get("paciente"), default="Paciente sin nombre")
    tipo = "Valoracion" if payload.get("tipo_registro") == "valoracion" else "Seguimiento"
    fecha = clean_text(payload.get("_fecha"), default="Sin fecha")
    return f"{index + 1}. {paciente} | {tipo} | {fecha}"


def build_demo_note(payload: dict) -> str:
    eva = clean_text(payload.get("eva"))
    funcion = join_items(payload.get("funcion", []))
    ejercicios = join_items(payload.get("ejercicios", []))
    tecnicas = join_items(payload.get("tecnicas", []))
    accesorios = join_items(payload.get("accesorios", []))
    tolerancia = clean_text(payload.get("tolerancia"))

    if payload.get("tipo_registro") == "valoracion":
        diagnosticos = ", ".join(
            [
                code.strip()
                for code in [
                    str(payload.get("diag_ppal", "")),
                    str(payload.get("diag_rel1", "")),
                    str(payload.get("diag_rel2", "")),
                ]
                if code.strip()
            ]
        ) or "No especificado"

        return "\n".join(
            [
                f"**PACIENTE:** {clean_text(payload.get('paciente'))}",
                f"**MOTIVO DE CONSULTA:** Paciente manifiesta venir por {clean_text(payload.get('motivo')).lower()}",
                f"**OCUPACION:** {clean_text(payload.get('ocupacion'))}",
                f"**EXAMENES:** {clean_text(payload.get('examenes'))}",
                f"**ANTECEDENTES:** {clean_text(payload.get('antecedentes'))}",
                f"**EXAMEN FISICO:** {clean_text(payload.get('examen_fisico'))}",
                f"**DIAGNOSTICOS:** {diagnosticos}",
                "**PLAN DE MANEJO (SESION DE HOY):** "
                f"EVA {eva}/10. Se realiza activacion muscular y trabajo funcional en {funcion}, "
                f"con ejercicios {ejercicios}. Se complementa con {tecnicas}, utilizando {accesorios}. "
                f"Tolerancia {tolerancia}.",
            ]
        )

    cambio = clean_text(payload.get("cambio"), "Igual")
    estado_map = {
        "Mejoro": f"Paciente cursa con evolucion favorable y EVA {eva}/10.",
        "Empeoro": f"Paciente refiere incremento de sintomatologia y EVA {eva}/10.",
        "Igual": f"Paciente se mantiene clinicamente estable con EVA {eva}/10.",
    }
    inicio = estado_map.get(cambio, f"Paciente en seguimiento con EVA {eva}/10.")

    return (
        f"**{clean_text(payload.get('paciente'))}:** "
        f"{inicio} Se realiza activacion muscular en {funcion}, con ejercicios {ejercicios}. "
        f"Se aplican tecnicas de apoyo que incluyen {tecnicas}, con uso de {accesorios}. "
        f"Paciente presenta tolerancia {tolerancia} durante la sesion."
    )


def generate_note_with_groq(json_str: str, groq_api_key: str, model: str) -> str:
    from groq import Groq

    client = Groq(api_key=groq_api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": json_str},
        ],
        temperature=0.3,
        max_tokens=1500,
    )

    content = response.choices[0].message.content if response.choices else ""
    content = (content or "").strip()
    if not content:
        raise RuntimeError("Groq devolvio una respuesta vacia.")
    return content


st.set_page_config(
    page_title="FisioFast",
    page_icon="FF",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    :root {
        --page-bg-top: #08131f;
        --page-bg-bottom: #0e2033;
        --panel-bg: rgba(18, 32, 51, 0.96);
        --panel-border: rgba(125, 211, 252, 0.22);
        --text-main: #f8fafc;
        --text-soft: #dbe7f3;
        --text-muted: #b7c7d9;
        --accent: #22c55e;
        --accent-strong: #16a34a;
    }
    .stApp {
        background:
            radial-gradient(circle at top right, rgba(34, 197, 94, 0.14), transparent 28%),
            linear-gradient(180deg, var(--page-bg-top) 0%, var(--page-bg-bottom) 100%);
        color: var(--text-main);
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0b1625 0%, #11233a 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }
    section[data-testid="stSidebar"] * {
        color: var(--text-main);
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2.5rem;
    }
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-main);
        letter-spacing: -0.02em;
    }
    p, label, .stCaption, .stMarkdown, .stRadio label, .stSelectbox label {
        color: var(--text-soft);
    }
    [data-testid="stMarkdownContainer"] p {
        color: var(--text-soft);
    }
    [data-testid="stMetricLabel"],
    [data-testid="stCaptionContainer"] {
        color: var(--text-muted);
    }
    [data-baseweb="input"] > div,
    [data-baseweb="select"] > div,
    [data-baseweb="textarea"] > div,
    div[data-testid="stTextInputRootElement"] > div,
    div[data-testid="stNumberInputContainer"] > div,
    div[data-testid="stSelectbox"] > div,
    textarea {
        background: rgba(10, 20, 33, 0.92) !important;
        border: 1px solid var(--panel-border) !important;
        color: var(--text-main) !important;
        border-radius: 12px !important;
        box-shadow: none !important;
    }
    input, textarea {
        color: var(--text-main) !important;
        -webkit-text-fill-color: var(--text-main) !important;
    }
    textarea::placeholder,
    input::placeholder {
        color: #9eb3c9 !important;
        opacity: 1 !important;
    }
    [data-baseweb="tag"] {
        background: rgba(34, 197, 94, 0.18) !important;
        border: 1px solid rgba(34, 197, 94, 0.35) !important;
        color: var(--text-main) !important;
    }
    div[data-testid="stForm"] {
        background: rgba(10, 19, 31, 0.72);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 22px;
        padding: 1.2rem 1.2rem 0.4rem 1.2rem;
        box-shadow: 0 18px 38px rgba(0, 0, 0, 0.22);
    }
    div[data-testid="stCodeBlock"] {
        border: 1px solid var(--panel-border);
        border-radius: 16px;
        overflow: hidden;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--accent), var(--accent-strong));
        border: none;
        border-radius: 14px;
        font-weight: 700;
        color: white;
        box-shadow: 0 10px 24px -8px rgba(34, 197, 94, 0.55);
    }
    .stButton > button {
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .stButton > button:hover {
        border-color: rgba(255, 255, 255, 0.14);
    }
    .nota-box {
        background: var(--panel-bg);
        border: 1px solid rgba(148, 163, 184, 0.24);
        border-radius: 18px;
        padding: 1.25rem 1.5rem;
        line-height: 1.7;
        white-space: pre-wrap;
        color: var(--text-main);
        box-shadow: 0 16px 32px rgba(0, 0, 0, 0.18);
    }
    .stAlert {
        border-radius: 14px;
    }
    [data-testid="stExpander"] {
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        background: rgba(10, 19, 31, 0.62);
    }
</style>
""",
    unsafe_allow_html=True,
)

ensure_session_state()
groq_api_key, api_key_source = get_groq_api_key()

with st.sidebar:
    st.title("Configuracion")

    generation_mode = st.radio(
        "Modo de generacion",
        ["Groq API", "Demo local"],
        help="Demo local crea una nota simulada para validar el flujo sin usar una API.",
    )

    if generation_mode == "Groq API":
        if not groq_api_key:
            manual_api_key = st.text_input(
                "GROQ_API_KEY",
                type="password",
                placeholder="gsk_...",
                help="Puedes obtener la clave en https://console.groq.com/keys",
            ).strip()
            if manual_api_key:
                groq_api_key = manual_api_key
                api_key_source = "entrada manual"

        if groq_api_key:
            st.success(f"API lista desde {api_key_source}.")
        else:
            st.warning("Falta la API key. Puedes seguir con Demo local.")

        model = st.selectbox(
            "Modelo Groq",
            GROQ_MODELS,
            index=0,
            help="Se muestran solo modelos verificados para este proyecto.",
        )
    else:
        model = ""
        st.info("El modo Demo local sirve para probar el formulario y la salida final sin Groq.")

    st.divider()
    st.caption(f"Registros en sesion: {len(st.session_state.registros)}")
    st.caption("En Streamlit Cloud configura GROQ_API_KEY desde Settings > Secrets.")

st.title("FisioFast")
st.caption("Documentacion clinica con IA para fisioterapia")
st.divider()

with st.form("fisio_form", clear_on_submit=True):
    st.subheader("Paciente")
    paciente = st.text_input("Nombre completo", placeholder="Ej. Juan Perez Garcia")

    tipo_label = st.radio(
        "Tipo de registro",
        ["Valoracion inicial", "Seguimiento / evolucion"],
        horizontal=True,
    )
    tipo_key = "valoracion" if tipo_label == "Valoracion inicial" else "seguimiento"

    ocupacion = ""
    motivo = ""
    examenes = ""
    antecedentes = ""
    examen_fisico = ""
    diag_ppal = ""
    diag_rel1 = ""
    diag_rel2 = ""
    cambio = "Igual"

    if tipo_key == "valoracion":
        st.subheader("Datos clinicos")
        col1, col2 = st.columns(2)
        with col1:
            ocupacion = st.text_input("Ocupacion", placeholder="Ej. Docente")
        with col2:
            examenes = st.text_input("Examenes", value="NO TRAE")

        motivo = st.text_area("Motivo de consulta", height=80)
        antecedentes = st.text_area("Antecedentes clinicos", height=80)
        examen_fisico = st.text_area("Examen fisico", height=100)

        st.subheader("Diagnosticos CIE-10")
        col1, col2, col3 = st.columns(3)
        with col1:
            diag_ppal = st.text_input("Principal", placeholder="Ej. M54.5")
        with col2:
            diag_rel1 = st.text_input("Relacionado 1", placeholder="Ej. M47.8")
        with col3:
            diag_rel2 = st.text_input("Relacionado 2", placeholder="Ej. M62.0")

    if tipo_key == "seguimiento":
        st.subheader("Cambio vs sesion previa")
        cambio = st.radio(
            "Estado",
            ["Mejoro", "Igual", "Empeoro"],
            horizontal=True,
            index=1,
        )

    st.subheader("EVA")
    eva = st.slider("Escala de dolor (0-10)", 0, 10, 5)

    st.subheader("Funcion")
    col1, col2 = st.columns(2)
    with col1:
        funcion_pos = st.multiselect(
            "Posicion de trabajo",
            [
                "Act. Muscular Sedente",
                "Act. Muscular Decubito Supino",
                "Act. Muscular Bipedo",
                "Act. Muscular Decubito Prono",
                "Act. Muscular Decubito Lateral D",
                "Act. Muscular Decubito Lateral I",
                "Act. Muscular Carga Unipodal",
                "Act. Muscular Cuadrupedo",
            ],
        )
    with col2:
        funcion_act = st.multiselect(
            "Actividad funcional",
            [
                "Marcha (Descargas de Peso)",
                "Balanceo",
                "Propiocepcion",
                "Equilibrio",
                "Higiene Postural",
                "AVD",
                "Balonterapia",
            ],
        )

    st.subheader("Ejercicios")
    col1, col2, col3 = st.columns(3)
    with col1:
        ej_tipo = st.multiselect(
            "Tipo",
            [
                "Isometricos",
                "Isotonicos",
                "Resistidos (Autocarga)",
                "Estiramientos a Tolerancia",
                "Estiramientos (Flexibilidad)",
            ],
        )
    with col2:
        ej_cadenas = st.multiselect(
            "Cadenas",
            [
                "Cadena Cinetica Abierta (CCA)",
                "Cadena Cinetica Cerrada (CCC)",
                "Cadena Cinetica Mixta",
                "Disociacion Cintura Escapular",
                "Disociacion Cintura Humeral",
                "Disociacion Escapulohumeral",
                "Disociacion Cintura Pelvica",
            ],
        )
    with col3:
        ej_region = st.multiselect(
            "Region",
            [
                "Miembros Superiores",
                "M. Superior Derecho",
                "M. Superior Izquierdo",
                "Miembros Inferiores",
                "M. Inferior Derecho",
                "M. Inferior Izquierdo",
                "Pelvis",
                "Espalda Alta",
                "Espalda Media",
                "Espalda Baja",
            ],
        )

    st.subheader("Tecnicas")
    col1, col2 = st.columns(2)
    with col1:
        tec_manuales = st.multiselect(
            "Manuales / otros",
            [
                "Tecnica de Codman",
                "Tecnica de McKenzie",
                "Tecnica de Williams",
                "Tecnica de Klapp",
                "Movilizacion Articular",
                "Manipulacion",
                "Traccion",
                "Puncion Seca",
                "Kinesiotape",
                "Vendaje Funcional",
            ],
        )
        tec_calor = st.multiselect(
            "Calor / frio",
            [
                "Calor Humedo",
                "Parafina",
                "Paquete Frio",
                "Batidas con Hielo",
                "Contrastes Caliente-Fria",
                "Hidroterapia Platon Caliente",
                "Hidroterapia Platon Frio",
            ],
        )
    with col2:
        tec_electro = st.multiselect(
            "Electroterapia",
            [
                "Ultrasonido",
                "Infrarrojo",
                "EMS / TENS",
                "Magnetoterapia",
                "Laser",
                "Ondas de Choque",
                "Diatermia",
                "Corrientes Interferenciales",
            ],
        )
        tec_masaje = st.multiselect(
            "Masaje",
            [
                "Masaje Manual Sedativo",
                "Masaje Manual Depletivo",
                "Masaje Manual Relajante",
                "Vibromasaje",
            ],
        )

    st.subheader("Accesorios")
    accesorios = st.multiselect(
        "Accesorios terapeuticos",
        [
            "Escalerilla de Dedos",
            "Sistema de Poleas",
            "Rueda Nautica",
            "Baston",
            "Rollo Terapeutico",
            "Balancin de Puyas Mano",
            "Balancin de Puyas Pie",
            "Balancin de Madera",
            "Disco de Madera",
            "Disco de Giros",
            "Patin de Madera",
            "Digiflex",
            "Plastilina Terapeutica",
            "Bandas Elasticas",
            "Pesas",
            "Eliptica",
            "Bicicleta Estatica",
            "Caminadora",
            "Sistema de Pedales",
            "Escalera de Dos Pasos",
            "Barras Paralelas",
        ],
    )

    st.subheader("Tolerancia")
    tolerancia = st.radio(
        "Respuesta a la sesion",
        ["Excelente", "Buena", "Regular", "Mala"],
        horizontal=True,
        index=0,
    )

    submitted = st.form_submit_button(
        "Guardar registro",
        use_container_width=True,
        type="primary",
    )

if submitted:
    if not paciente.strip():
        st.error("Debes ingresar el nombre del paciente.")
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
            payload.update(
                {
                    "ocupacion": ocupacion,
                    "motivo": motivo,
                    "examenes": examenes,
                    "antecedentes": antecedentes,
                    "examen_fisico": examen_fisico,
                    "diag_ppal": diag_ppal,
                    "diag_rel1": diag_rel1,
                    "diag_rel2": diag_rel2,
                }
            )
        else:
            payload["cambio"] = cambio

        st.session_state.registros.append(payload)
        st.session_state.ultimo_payload = payload
        st.session_state.selected_record_index = len(st.session_state.registros) - 1
        st.session_state.nota_generada = None
        st.session_state.note_source_index = None
        st.success(
            f"Registro guardado para {paciente.strip()}. "
            "El formulario se limpio y el dato quedo almacenado en la sesion."
        )

if st.session_state.registros:
    st.divider()
    st.subheader("Registros guardados en sesion")
    st.caption(
        "Puedes capturar varios registros durante el dia y generar la nota mas tarde, "
        "cuando selecciones el registro que quieras redactar."
    )

    record_options = list(range(len(st.session_state.registros) - 1, -1, -1))
    default_record_index = st.session_state.selected_record_index
    if default_record_index not in record_options:
        default_record_index = record_options[0]

    previous_record_index = st.session_state.selected_record_index
    selected_record_index = st.selectbox(
        "Registro para revisar o convertir en nota",
        options=record_options,
        index=record_options.index(default_record_index),
        format_func=lambda idx: build_record_label(st.session_state.registros[idx], idx),
    )

    if (
        previous_record_index is not None
        and selected_record_index != previous_record_index
        and st.session_state.note_source_index != selected_record_index
    ):
        st.session_state.nota_generada = None

    st.session_state.selected_record_index = selected_record_index
    selected_payload = st.session_state.registros[selected_record_index]

    json_limpio = {
        key: value
        for key, value in selected_payload.items()
        if key != "_fecha"
    }
    json_str = json.dumps(json_limpio, ensure_ascii=False, indent=2)

    col1, col2 = st.columns([4, 1])
    with col1:
        st.code(json_str, language="json")
    with col2:
        st.download_button(
            "Descargar JSON",
            data=json_str,
            file_name=f"fisiofast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )

    st.subheader("Generar nota clinica")

    if generation_mode == "Groq API" and not groq_api_key:
        st.warning("Ingresa una GROQ_API_KEY o cambia a Demo local para probar el flujo.")
    else:
        button_label = (
            "Generar nota con Groq"
            if generation_mode == "Groq API"
            else "Generar nota demo"
        )

        if st.button(button_label, use_container_width=True, type="primary", key="generate_note"):
            try:
                with st.spinner("Generando nota..."):
                    if generation_mode == "Groq API":
                        st.session_state.nota_generada = generate_note_with_groq(
                            json_str=json_str,
                            groq_api_key=groq_api_key,
                            model=model,
                        )
                    else:
                        st.session_state.nota_generada = build_demo_note(json_limpio)
                    st.session_state.note_source_index = selected_record_index
            except ImportError:
                st.error(
                    "La libreria 'groq' no esta instalada. "
                    "Instala las dependencias desde requirements.txt."
                )
            except Exception as exc:
                st.error(f"Error al generar la nota: {exc}")

    if (
        st.session_state.nota_generada
        and st.session_state.note_source_index == selected_record_index
    ):
        if generation_mode == "Demo local":
            st.info("Esta salida fue generada en Demo local. Sirve para validar flujo, no reemplaza al LLM.")

        st.subheader("Nota clinica")
        st.markdown(
            f'<div class="nota-box">{st.session_state.nota_generada}</div>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            nombre_archivo = clean_text(
                selected_payload.get("paciente", "paciente"),
                default="paciente",
            ).replace(" ", "_")
            st.download_button(
                "Descargar nota (.txt)",
                data=st.session_state.nota_generada,
                file_name=f"nota_{nombre_archivo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with col2:
            if st.button("Regenerar", use_container_width=True, key="regenerate_note"):
                st.session_state.nota_generada = None
                st.session_state.note_source_index = None
                st.rerun()

if st.session_state.registros:
    st.divider()
    with st.expander(f"Historial de sesion - {len(st.session_state.registros)} registro(s)"):
        todos_json = json.dumps(st.session_state.registros, ensure_ascii=False, indent=2)
        st.code(todos_json, language="json")

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Descargar historial",
                data=todos_json,
                file_name=f"fisiofast_historial_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True,
            )
        with col2:
            if st.button("Limpiar historial", use_container_width=True):
                st.session_state.registros = []
                st.session_state.ultimo_payload = None
                st.session_state.nota_generada = None
                st.session_state.selected_record_index = None
                st.session_state.note_source_index = None
                st.rerun()
