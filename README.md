# FisioFast Streamlit

Aplicación Streamlit para captura de registros de fisioterapia y generación de notas clínicas con un LLM vía API.

## Arquitectura

- `Streamlit` corre en la nube como interfaz web.
- El `LLM` no se ejecuta dentro de Streamlit.
- La app consume un modelo remoto por API, actualmente `Groq`.

Ese enfoque es el correcto para despliegue cloud: Streamlit maneja la UI y el proveedor LLM maneja la inferencia.

## Estructura

- `FisioFast_Streamlit/app.py`: aplicación principal.
- `FisioFast_Streamlit/requirements.txt`: dependencias Python.
- `FisioFast_Streamlit/iniciar.bat`: arranque local en Windows.
- `.streamlit/config.toml`: configuración compartida para local y nube.
- `.streamlit/secrets.toml.example`: ejemplo de secretos locales.

## Ejecutar localmente

```powershell
pip install -r FisioFast_Streamlit/requirements.txt
streamlit run FisioFast_Streamlit/app.py
```

## Configuración del LLM

La app busca `GROQ_API_KEY` en este orden:

1. `st.secrets["GROQ_API_KEY"]`
2. Variable de entorno `GROQ_API_KEY`
3. Entrada manual en la barra lateral

Para desarrollo local, crea `.streamlit/secrets.toml` a partir de `.streamlit/secrets.toml.example`.

## Despliegue en nube

### Streamlit Community Cloud

- Conecta este repositorio desde GitHub.
- Usa como archivo principal `FisioFast_Streamlit/app.py`.
- Configura el secreto `GROQ_API_KEY` en la sección `Secrets`.
- La app instalará dependencias desde `FisioFast_Streamlit/requirements.txt`, porque ese archivo está junto al entrypoint.

### Otras plataformas

Usa como comando de arranque:

```bash
streamlit run FisioFast_Streamlit/app.py --server.address 0.0.0.0 --server.port $PORT
```

Y define `GROQ_API_KEY` como variable de entorno.

## GitHub

Este repositorio está configurado para versionar solo la versión Streamlit del proyecto.
