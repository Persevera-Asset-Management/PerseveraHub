#!/bin/bash

mkdir -p /workspace/.streamlit

# Pasta legada: faz o Streamlit usar MPA v1 e quebra F5 em subpaths.
if [ -d "/workspace/pages" ]; then
    rm -rf /workspace/pages
    echo "Removed legacy pages/ directory (use views/ instead)."
fi

if [ -n "$STREAMLIT_SECRETS" ]; then
    echo "$STREAMLIT_SECRETS" > /workspace/.streamlit/secrets.toml
    echo "secrets.toml written from STREAMLIT_SECRETS env var."
else
    echo "WARNING: STREAMLIT_SECRETS env var is not set. Streamlit secrets will not be available."
fi
