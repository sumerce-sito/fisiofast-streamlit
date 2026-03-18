# FisioFast Streamlit

Aplicacion Streamlit para capturar registros de fisioterapia y generar notas clinicas con IA.

## Estado del proyecto

Este repositorio ya esta preparado para:

- Subirse a GitHub sin arrastrar archivos locales ni secretos.
- Ejecutarse en Streamlit Community Cloud.
- Probar el flujo completo sin API usando `Demo local`.
- Generar notas reales con Groq usando `GROQ_API_KEY`.

## Estructura

- `FisioFast_Streamlit/app.py`: aplicacion principal.
- `FisioFast_Streamlit/requirements.txt`: dependencias Python fijadas.
- `FisioFast_Streamlit/iniciar.bat`: arranque local en Windows.
- `.streamlit/config.toml`: configuracion compartida.
- `.streamlit/secrets.toml.example`: ejemplo de secreto local.

## Probar localmente

### Opcion 1: flujo completo sin API

```powershell
python -m pip install -r FisioFast_Streamlit/requirements.txt
streamlit run FisioFast_Streamlit/app.py
```

En la barra lateral selecciona `Demo local`.

Ese modo permite:

- Llenar el formulario.
- Guardar el registro.
- Ver el JSON.
- Generar una nota simulada.
- Descargar la nota final.

### Opcion 2: flujo real con Groq

Puedes cargar la API key de tres maneras:

1. `st.secrets["GROQ_API_KEY"]`
2. Variable de entorno `GROQ_API_KEY`
3. Entrada manual en la barra lateral

Ejemplo por variable de entorno en PowerShell:

```powershell
$env:GROQ_API_KEY="tu_api_key_real"
streamlit run FisioFast_Streamlit/app.py
```

O crea `.streamlit/secrets.toml` a partir de `.streamlit/secrets.toml.example`.

## Modelos Groq habilitados

La app deja visibles solo estos modelos verificados:

- `llama-3.3-70b-versatile`
- `llama-3.1-8b-instant`

## Control de acceso

La app soporta login simple con usuario y contrasena usando `Streamlit Secrets`.

Si defines estos valores, la app pedira credenciales antes de dejar entrar:

```toml
APP_USERNAME = "tu_usuario"
APP_PASSWORD = "tu_password_seguro"
```

Si no los defines, la app sigue funcionando sin bloqueo para no romper el despliegue.

## Despliegue en Streamlit Community Cloud

1. Sube este repositorio a GitHub.
2. En Streamlit Community Cloud, crea una nueva app conectando ese repo.
3. Usa como archivo principal `FisioFast_Streamlit/app.py`.
4. En `Settings > Secrets`, agrega:

```toml
GROQ_API_KEY = "tu_api_key_real"
APP_USERNAME = "tu_usuario"
APP_PASSWORD = "tu_password_seguro"
```

5. Despliega.

Como `requirements.txt` vive junto al entrypoint, Streamlit Community Cloud tomara ese archivo de dependencias para la instalacion.

## Seguridad

- `.streamlit/secrets.toml` no se versiona.
- No pongas claves reales dentro del codigo ni del repo.
- Usa `.streamlit/secrets.toml.example` solo como plantilla.

## GitHub

Si el repositorio local aun no tiene remoto configurado:

```powershell
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

Si prefieres interfaz grafica, tambien puedes crear el repo vacio en GitHub y conectar el remoto desde tu cliente Git.
