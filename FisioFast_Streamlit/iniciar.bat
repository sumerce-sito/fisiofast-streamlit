@echo off
title FisioFast Streamlit

echo ============================================
echo   FISIOFAST - Iniciando aplicacion...
echo ============================================
echo.

:: Instalar dependencias si no estan
echo [1/2] Verificando dependencias...
pip install -r requirements.txt --quiet

:: Iniciar Streamlit accesible desde la red local (tablet)
echo [2/2] Iniciando FisioFast en red local...
echo.
echo  Accede desde la tablet en:
echo  http://%COMPUTERNAME%:8501
echo  o busca la IP de este PC y pon :8501
echo.
echo  La aplicacion usa GROQ_API_KEY desde Streamlit Secrets
echo  o desde la barra lateral.
echo.
streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --browser.gatherUsageStats false

pause
