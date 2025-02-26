web: gunicorn -w 4 -b 0.0.0.0:8000 cleanup_atlassian_healthcheck:app && python -m http.server --directory /app/fake ${PORT:-8000}
