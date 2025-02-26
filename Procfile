web: sh -c "gunicorn -w 4 -b 0.0.0.0:5000 cleanup_atlassian:app && python -m http.server --directory /app/fake 8000"
