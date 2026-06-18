#!/bin/bash

mkdir -p /workspace/.streamlit

if [ -n "$STREAMLIT_SECRETS" ]; then
    echo "$STREAMLIT_SECRETS" > /workspace/.streamlit/secrets.toml
    echo "secrets.toml written from STREAMLIT_SECRETS env var."
else
    echo "WARNING: STREAMLIT_SECRETS env var is not set. Streamlit secrets will not be available."
fi
