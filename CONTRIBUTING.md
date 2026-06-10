# Contributing to PDF-Assistant-RAG 🤝

Welcome! This project is open for contributions.
Read this guide fully before opening a PR — it keeps things smooth for everyone.

---

## 📌 Important Branch Rules

| Branch | Purpose | Who pushes? |
|--------|---------|------------|
| `main` | Production (deployed to HuggingFace Spaces) | **Admin only** |
| `dev` | Integration — all contributor PRs target here | Contributors via PRs |
| `feature/*` | New features | Contributors |
| `fix/*` | Bug fixes | Contributors |
| `docs/*` | Documentation only | Contributors |

> ⚠️ **Never open a PR targeting `main`.** It will be closed automatically.  
> ⚠️ **Never modify `deploy.yml`, `render.yaml`, or HuggingFace config.**

---

## 🚀 Getting Started

### 1. Fork & Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/<your-username>/PDF-Assistant-RAG.git
cd PDF-Assistant-RAG
```

### 2. Add upstream remote

```bash
git remote add upstream https://github.com/param20h/PDF-Assistant-RAG.git
```

### 3. Always branch from `dev`

```bash
git fetch upstream
git checkout -b feature/my-cool-feature upstream/dev
```

---

## 🛠️ Local Development Setup

### Backend (FastAPI)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Copy env template
cp ../.env.example .env            # Fill in your own dev values

uvicorn app.main:app --reload --port 8000
```

### Pre-commit Hooks (Required)

We use [`pre-commit`](https://pre-commit.com/) to enforce code style automatically before every commit. This prevents style-related CI failures.

```bash
# Install pre-commit (one-time setup)
pip install pre-commit

# Install the hooks into your local clone (one-time per checkout)
pre-commit install

# (Optional) Run against all files to verify setup
pre-commit run --all-files
```

**What the hooks check:**

| Hook | Tool | Scope |
|------|------|-------|
| Python formatting | `black` (line-length 120) | `backend/` |
| Python linting | `flake8` (errors only) | `backend/` |
| JS/TS/JSON/CSS/MD formatting | `prettier` | `frontend/` |
| Trailing whitespace | `pre-commit-hooks` | All files |
| YAML/JSON validity | `pre-commit-hooks` | All files |
| Merge-conflict markers | `pre-commit-hooks` | All files |
| Large file guard (>1 MB) | `pre-commit-hooks` | All files |
| Secret detection | `detect-secrets` | All files |

> ⚠️ If a hook modifies files, it will block your commit. Just `git add` the auto-fixed files and commit again.

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev                         # Runs on http://localhost:3000
```

Make sure the backend is running first — the frontend proxies API requests to `localhost:8000`.

### Email Verification Setup

Password registration sends a verification link before users can log in. Add SMTP values to your local `.env` file:

```env
FRONTEND_URL=http://localhost:3000
EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS=24
MAIL_USERNAME=your_smtp_username
MAIL_PASSWORD=your_smtp_or_gmail_app_password
MAIL_FROM=your_sender_email@example.com
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
```

For Gmail, enable 2-Step Verification on the sender Google account, create a 16-character App Password from Google Account > Security > App passwords, then use:

```env
MAIL_USERNAME=yourgmail@gmail.com
MAIL_PASSWORD=your_16_character_app_password
MAIL_FROM=yourgmail@gmail.com
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
```

The verification link opens `/verify-email?token=...` in the frontend, which calls `GET /api/v1/auth/verify?token=...`. Users who miss the first email can request another link through `POST /api/v1/auth/resend-verification`.

When SMTP is not configured in a non-production environment, registration returns a local `verification_url` so contributors can test the verification flow without private email credentials. With SMTP configured, the app sends the link by email.

---

## 📬 Opening a Pull Request

1. **Pick an issue** — comment "I'd like to work on this" before starting
2. **Create your branch** from `dev` (see above)
3. **Make your changes** — keep commits focused and well-named
4. **Push and open a PR targeting `dev`**
5. **Fill in the PR template** completely
6. **Wait for CI to pass** — the `CI — Dev Branch` workflow must be green
7. **Address review feedback** — the admin (@param20h) is auto-assigned as reviewer

### Commit Message Format

```
type: short description (max 72 chars)

Optional longer explanation if needed.
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat: add PDF page count to document card
fix: scroll to bottom on new message
docs: add local setup instructions to README
```

---

## ✅ CI Checks

Every PR to `dev` automatically runs:

| Check | What it does |
|-------|-------------|
| 🐍 **Backend Lint** | `flake8` on `backend/app/` (errors only) |
| ⚛️ **Frontend Type Check** | `tsc --noEmit` |
| ⚛️ **ESLint** | `npm run lint` |
| ⚛️ **Next.js Build** | Full production build to catch runtime errors |
| 📏 **PR Size Gate** | Warns if PR is unusually large |

All checks must be green before your PR can be merged.

---

## 🚫 What NOT to do

- Don't push directly to `main` or `dev` — always use PRs
- Don't commit `.env` files or API keys/secrets
- Don't add large binary files without discussing first
- Don't change CI/deployment workflows without admin approval
- Don't open multiple PRs for the same issue

---

## 🏷️ Issue Labels

| Label | Meaning |
|-------|---------|
| `good first issue` | Great for beginners |
| `bug` | Something is broken |
| `enhancement` | New feature request |
| `needs-triage` | Needs admin review |
| `help wanted` | Open for contributors |
| `wip` | Work in progress |

---

## 💬 Need Help?

Open a [Discussion](https://github.com/param20h/PDF-Assistant-RAG/discussions) before opening an issue if you're unsure. Mentors and the admin check discussions regularly.

---

Thanks for contributing! Every PR, no matter how small, makes a difference. 🚀
