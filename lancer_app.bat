@echo off
title Lancement de l'Application Streamlit

:: Verification de l'environnement virtuel (ici nommé .venv comme vu précédemment)
if not exist .venv (
    echo Creation de l'environnement virtuel...
    py -m venv .venv
    
    echo Activation et installation des dependances...
    call .\.venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    :: Activation de l'environnement (Le CALL est obligatoire ici)
    call .\.venv\Scripts\activate.bat
)

echo Lancement du serveur...
:: On utilise bien la commande Streamlit
streamlit run main.py

pause