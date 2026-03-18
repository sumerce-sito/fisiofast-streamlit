# FisioFast Streamlit

Aplicación Streamlit para captura de registros de fisioterapia y generación de notas clínicas con Groq.

## Estructura

- `FisioFast_Streamlit/app.py`: aplicación principal.
- `FisioFast_Streamlit/requirements.txt`: dependencias.
- `FisioFast_Streamlit/iniciar.bat`: arranque rápido en Windows.

## Ejecutar localmente

```powershell
cd FisioFast_Streamlit
pip install -r requirements.txt
streamlit run app.py
```

## API key

La app usa `GROQ_API_KEY`. Puedes configurarla en:

- `st.secrets["GROQ_API_KEY"]`
- O ingresarla manualmente en la barra lateral al abrir la app.

## Subir a GitHub

Este repositorio está configurado para versionar solo la versión Streamlit del proyecto.
