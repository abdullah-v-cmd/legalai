# LegalAI — AI-Powered Legal Document & Q&A Assistant

A full-stack AI application built with FastAPI and Hugging Face models for legal question answering, document generation, image/document analysis, and administrative workflows.

## Highlights

- AI-powered legal Q&A
- Legal paper, assignment, test-paper, and presentation generation
- Image/document analysis
- JWT authentication and role-based administration
- Rate limiting and security controls
- FastAPI REST API with Swagger documentation
- Docker deployment
- GitHub Actions CI/CD workflow
- Database migrations with Alembic

## Architecture

```text
User
 │
 ▼
Web UI
 │
 ▼
FastAPI API
 ├── Authentication / Authorization
 ├── AI Services
 ├── Document Generation
 ├── Image Analysis
 └── Admin / Monitoring
        │
        ├── Database
        └── Hugging Face Inference
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.11+ |
| AI | Hugging Face Inference API, Transformer models |
| Database | SQLAlchemy + SQLite (development) |
| Auth | JWT + bcrypt |
| Documents | python-docx, python-pptx |
| Frontend | Jinja2 + Tailwind CSS |
| Deployment | Docker + Nginx |
| CI/CD | GitHub Actions |

## Local Setup

```bash
git clone https://github.com/abdullah-v-cmd/legalai.git
cd legalai
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

```bash
docker compose up -d
```

## API Areas

- `/api/auth/*` — authentication and user management
- `/api/chat/*` — AI chat and image analysis
- `/api/documents/*` — document generation and downloads
- `/api/admin/*` — administrative and monitoring workflows
- `/api/docs` — Swagger / OpenAPI documentation

## Security

Do not place admin passwords, API tokens, private keys, or other secrets in README files or source control. Configure secrets through `.env` and deployment secret management.

## Portfolio Value

LegalAI demonstrates **LLM integration, backend engineering, document automation, authentication, security, monitoring, CI/CD, and containerized deployment** in a complete application.

## Author

**Abdullah Naveed** — AI / ML Engineer | Generative AI | Backend Engineering
