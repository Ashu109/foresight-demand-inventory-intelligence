# Dockerization

Build the image locally:

```bash
docker build -t forsight-dashboard:local .
```

Run with Docker:

```bash
docker run --rm -p 8501:8501 -v "${PWD}/data:/app/data:ro" forsight-dashboard:local
```

Or use docker-compose for a convenient run:

```bash
docker-compose up --build
```

Notes:
- The image uses `python:3.11-slim` and installs build dependencies required by numerical libraries.
- Mount `data/` as a volume for reproducible runs instead of embedding raw data in the image.
