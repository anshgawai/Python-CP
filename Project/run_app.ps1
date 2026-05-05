$appPath = Join-Path $PSScriptRoot "app.py"
& "$env:LOCALAPPDATA\Programs\Python\Python314\Scripts\streamlit.exe" run $appPath --server.port 8507
