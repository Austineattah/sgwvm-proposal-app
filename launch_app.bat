@echo off
title NEXUSVAULT Sovereign Enterprise Portal
color 0B
echo ====================================================
echo Starting NEXUSVAULT Sovereign Enterprise Portal...
echo ====================================================
cd /d "C:\Users\USER\Desktop\sgwvm-proposal-app"
call env\Scripts\activate
echo [INFO] Environment active. Launching application...
streamlit run app.py --server.headless=false
pause