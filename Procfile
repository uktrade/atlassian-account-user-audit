web: sh -c "gunicorn -w 4 -b 0.0.0.0:8080 cleanup_atlassian:app & python -m http.server --directory /app/fake 8000"
