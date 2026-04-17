# 🏛️ LegalAI - AI-Powered Legal Assistant

A comprehensive AI legal assistant built with **FastAPI** + **HuggingFace Free Models** — generates legal papers, assignments, test papers, PPT presentations, answers legal questions, analyzes images, and provides an admin control panel.

---

## 🌐 Live URLs

| Page | URL |
|------|-----|
| **App** | `https://8000-SANDBOX.sandbox.novita.ai` |
| **API Docs** | `/api/docs` |
| **Admin Panel** | `/admin` (admin login required) |
| **GitHub** | `https://github.com/abdullah-v-cmd/legalai` |

---

## ✅ Features

### 🤖 AI Features (3 Free HuggingFace Models)
| Model | Use Case |
|-------|----------|
| `mistralai/Mistral-7B-Instruct-v0.2` | Legal Q&A, Paper Generation, Test Papers |
| `HuggingFaceH4/zephyr-7b-beta` | Assignment Writing, PPT Content |
| `Salesforce/blip-image-captioning-large` | Image/Document Analysis |

### 📄 Document Generation
- **Legal Papers** — Full case studies, research papers, legal briefs (.docx)
- **Assignments** — Custom word count, style matching, AI-humanized, plagiarism-free (.docx)
- **Test Papers** — MCQ / Subjective / Mixed, unseen questions with answer keys (.docx)
- **Presentations (PPT)** — Professional slides with complete speech script for any duration (.pptx)

### 💬 Chat Features
- **Legal Q&A** — Ask anything about law, get cited answers
- **Image Analysis** — Upload legal documents/law book photos for AI analysis (login required)
- **Chat History** — Saved automatically for logged-in users (anonymous = no history)

### 🔐 Authentication
- Register / Login with JWT tokens
- Anonymous chat allowed (history not saved)
- Upload features require login
- Admin panel for staff

### 👑 Admin Panel (`/admin`)
- **Dashboard** — User stats, system resources overview
- **User Management** — View, enable/disable, delete users
- **Chat Management** — Monitor all chat sessions
- **Document Management** — Track all generated documents
- **System Monitoring** — Real-time CPU, Memory, Disk, Process metrics (auto-refreshes)
- **Database Control** — Table stats, create backups, list backups
- **Analytics** — 30-day usage trends, document type breakdown

---

## 🚀 Quick Start (Local)

### Requirements
- Python 3.11+
- pip

### Setup
```bash
git clone https://github.com/abdullah-v-cmd/legalai.git
cd legalai
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
mkdir -p uploads exports backups logs
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Default Admin Credentials
```
Username: admin
Password: Admin@123456
Email:    admin@legalai.com
```

### With Docker
```bash
docker compose up -d
# Access at http://localhost:8000
```

---

## 🔑 API Reference

### Authentication
```bash
# Register
POST /api/auth/register
{"username": "john", "email": "john@example.com", "password": "Pass@123", "full_name": "John"}

# Login
POST /api/auth/login (form: username, password, grant_type=password)

# Get current user
GET /api/auth/me  (Bearer token required)
```

### Chat
```bash
# Ask legal question (no auth required)
POST /api/chat/message
{"message": "What is habeas corpus?", "session_id": null}

# Upload image for analysis (auth required)
POST /api/chat/image (multipart: file + question)

# Chat history (auth required)
GET /api/chat/history
```

### Documents (most require auth)
```bash
# Legal Paper
POST /api/documents/legal-paper
{"subject": "Right to Privacy", "case_details": "...", "paper_type": "case_study"}

# Assignment (auth required)
POST /api/documents/assignment
{"topic": "Constitutional Law", "sample_text": "...", "word_count": 1500, "author_name": "John"}

# Test Paper
POST /api/documents/test-paper
{"subject": "Criminal Law", "num_questions": 10, "difficulty": "medium", "test_type": "mcq"}

# Presentation (auth required)
POST /api/documents/presentation
{"topic": "Human Rights", "duration_minutes": 15, "theme": "legal_blue"}

# Download generated file
GET /api/documents/download/{filename}
```

### Admin (admin token required)
```bash
GET /api/admin/dashboard
GET /api/admin/users?search=john&page=1
PATCH /api/admin/users/{id}  {"is_active": false}
GET /api/admin/monitoring       # Real-time system stats
GET /api/admin/database/stats
POST /api/admin/database/backup
GET /api/admin/analytics?days=30
```

---

## 🐳 Docker Deployment

```bash
# Development
docker compose up -d

# Production (with nginx)
docker compose --profile production up -d

# Environment variables
SECRET_KEY=your-super-secret-key-32-chars
ADMIN_EMAIL=admin@yoursite.com
ADMIN_PASSWORD=YourStrongPass@123
HUGGINGFACE_API_TOKEN=hf_optional_token  # Free inference without token
```

---

## 🔄 CI/CD Pipeline

The project includes a GitHub Actions CI/CD pipeline at `.github/workflows/ci-cd.yml`:

```
Push to main →
  ↓ Test Job (pytest)
  ↓ Security Scan (bandit + safety)
  ↓ Build Docker Image (ghcr.io)
  ↓ Deploy to Production
```

### Setting up CI/CD
1. Go to **Repository Settings → Secrets**
2. Add: `SECRET_KEY`, `ADMIN_PASSWORD`
3. For deployment: Add `SERVER_HOST`, `SERVER_USER`, `SSH_PRIVATE_KEY`
4. Uncomment the SSH deploy step in `ci-cd.yml`

### To enable the workflow file (requires PAT with `workflow` scope):
```bash
git add .github/workflows/ci-cd.yml
git commit -m "Add CI/CD workflow"
git push origin main
```

---

## 📊 Database Versioning with Alembic

```bash
# Initialize (already done)
alembic init migrations

# Create new migration
alembic revision --autogenerate -m "add new table"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Check current version
alembic current
```

---

## 🔒 Security Features

- **JWT Authentication** — Access + Refresh tokens
- **Password Hashing** — bcrypt with strong rounds
- **Rate Limiting** — 30 req/min API, 5 req/min login
- **IP Lockout** — Auto-lock after 5 failed login attempts (15 min)
- **Input Sanitization** — bleach library for XSS prevention
- **Security Headers** — X-Frame-Options, X-Content-Type-Options, etc.
- **CORS Control** — Configurable allowed origins
- **GZip Compression** — Automatic response compression
- **File Upload Validation** — Type + size checks
- **Path Traversal Prevention** — Safe filename handling

---

## 📈 Monitoring

### Real-time System Monitoring (Admin Panel)
- CPU usage, count, user/system time
- Memory: total, used, available, percent
- Disk: total, used, free, percent
- Process: PID, memory usage, CPU percent
- Auto-refreshes every 5 seconds

### Application Logs
```bash
# PM2 logs
pm2 logs legalai --nostream

# Or log files
tail -f logs/out.log
tail -f logs/error.log
```

### Prometheus Metrics (for production setup)
Add to requirements.txt: `prometheus-fastapi-instrumentator`
```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
# Metrics at: /metrics
```

---

## 🗃️ Data Architecture

### Models
```
User        → username, email, role, stats
ChatSession → user_id, session_id, type
ChatMessage → session_id, role, content, type
Document    → user_id, title, type, file_path, humanized
```

### Storage
- **Database**: SQLite (async with aiosqlite) — upgrade to PostgreSQL for production
- **Files**: Local filesystem (uploads/, exports/, backups/)
- **Sessions**: JWT tokens (stateless)

---

## 🤗 HuggingFace AI Models

All models are **100% free** — no paid API needed:

| Model | Purpose | Notes |
|-------|---------|-------|
| `mistralai/Mistral-7B-Instruct-v0.2` | Primary legal AI | Best for Q&A and papers |
| `HuggingFaceH4/zephyr-7b-beta` | Writing tasks | Assignments, PPT content |
| `Salesforce/blip-image-captioning-large` | Image analysis | Legal document photos |

**Optional**: Add `HUGGINGFACE_API_TOKEN` in `.env` for faster inference (free at huggingface.co).

**Note**: Free tier may have 20-60 second delays when model is loading. The app handles this with automatic retries and fallback templates.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11+) |
| Database | SQLAlchemy 2.0 + aiosqlite |
| Auth | JWT (python-jose) + bcrypt |
| AI | HuggingFace Inference API |
| Documents | python-docx + python-pptx |
| Frontend | Jinja2 Templates + Tailwind CSS |
| Deployment | Docker + Nginx |
| CI/CD | GitHub Actions |
| Process Manager | PM2 (development) |

---

## 📝 Future Roadmap

- [ ] PostgreSQL database for production
- [ ] Redis for caching and sessions
- [ ] Email verification
- [ ] More HuggingFace models (legal-specific BERT)
- [ ] PDF export support
- [ ] Multi-language support
- [ ] Citation management system
- [ ] User subscription tiers
- [ ] Real-time notifications

---

*Generated by LegalAI | Educational Use Only | Not Professional Legal Advice*
