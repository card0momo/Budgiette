# Budgiette API

A REST API for **Budgiette**, built with **FastAPI** and **SQLAlchemy**, providing the backend services for personal budget and expense management.

## Features

* FastAPI-powered REST API
* PostgreSQL database support
* SQLAlchemy ORM
* Pydantic request/response validation
* Modular project structure
* Docker support
* GitHub Actions CI/CD
* Automatic deployment to a VPS via Docker Compose

## Project Structure

```text
.
├── app
│   ├── api
│   ├── core
│   ├── db
│   ├── models
│   ├── schemas
│   ├── services
│   └── main.py
├── requirements.txt
├── Dockerfile
└── .github
    └── workflows
```

## Running Locally

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it and install dependencies:

```bash
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

* http://localhost:8000
* Swagger UI: http://localhost:8000/docs
* ReDoc: http://localhost:8000/redoc

## Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Configure the required database connection and any additional application settings.

## Docker

Build the image:

```bash
docker build -t budgiette-api .
```

Run the container:

```bash
docker run -p 8000:8000 budgiette-api
```

## Deployment

The project is configured with GitHub Actions to:

1. Build a Docker image.
2. Publish it to GitHub Container Registry (GHCR).
3. Connect to the deployment server via SSH.
4. Pull the latest image.
5. Restart the API container using Docker Compose.

## License

This project is intended for educational and personal use unless otherwise specified.
