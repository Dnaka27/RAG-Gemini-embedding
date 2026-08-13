# RAG with Gemini

Web application for uploading Markdown documents and asking questions grounded in their content.

---

## Technologies

![Python](https://img.shields.io/badge/Python-1F2194?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini%20API-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![HTMX](https://img.shields.io/badge/HTMX-3366CC?style=for-the-badge&logo=htmx&logoColor=white)

---

## About

This project implements a small retrieval-augmented generation (RAG) application using Google Gemini embeddings and text generation.

The user uploads a UTF-8 Markdown document, which is split into overlapping chunks and embedded. Questions are embedded and matched against the document chunks by cosine distance. Gemini then generates an answer using only the retrieved context.

The application uses Django with server-rendered HTML, CSS and HTMX — no frontend framework. The active document index is kept in process memory, which keeps the project compatible with a Vercel-only deployment without requiring an external database or storage service.

> Because Vercel functions can restart, the document may need to be uploaded and processed again before a new question.

Each answer is shown alongside a small radial diagram that plots the retrieved passages by their real cosine distance to the question — closer to the center means more relevant, and the ranking shown matches the numbered passages listed below it.

---

## Interface

The active look is **Signal**, a dark amber-on-near-black theme (`static/css/app.css`, JetBrains Mono + Space Grotesk) built around that same retrieval diagram: a rotating radar sweep inside the plot, a blinking terminal cursor on the headline, and subtle fade-in transitions on HTMX swaps. All motion is CSS-only (`transform`/`opacity`), contained to small elements, and disabled under `prefers-reduced-motion`.

Two alternate themes ship unused in `static/css/` and can be swapped in by copying their contents into `app.css` and updating the Google Fonts link in `templates/web/base.html`:

- `theme-marginalia.css` — warm editorial serif (Fraunces + Public Sans + Space Mono), indigo ink, drop-cap answers.
- `theme-blueprint.css` — pale technical schematic (Barlow Condensed + Archivo + Roboto Mono), sharp corners, dashed dimension lines.

---

## Project structure

```text
config/
├── settings.py       # Django and environment configuration
├── urls.py           # Project routes
└── wsgi.py           # Vercel/WSGI entrypoint

rag/
├── chunking.py       # Document chunking
├── client.py         # Gemini client
├── config.py         # Model configuration
├── embeddings.py     # Document and query embeddings
├── generation.py     # Context-grounded answer generation
└── services.py       # In-memory RAG orchestration

web/
├── forms.py          # Markdown upload validation
├── urls.py           # Application routes
└── views.py          # Upload/question endpoints + retrieval-plot geometry

templates/web/
├── base.html          # Shell, hero, ambient retrieval plot
├── home.html          # Upload + question forms
└── partials/          # HTMX swap targets (answer, upload result, error)

static/css/
├── app.css             # Active theme (Signal)
├── theme-marginalia.css  # Alternate theme, not loaded by default
└── theme-blueprint.css   # Alternate theme, not loaded by default

manage.py             # Django command-line entrypoint
requirements.txt      # Python dependencies
```

---

## Installation

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here
DJANGO_SECRET_KEY=your_secret_key_here
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1
```

Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/).

---

## Running locally

```bash
python manage.py check
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

## Application flow

1. Upload a UTF-8 `.md` file.
2. Process the document and generate its embeddings.
3. Ask a question about the uploaded content.
4. Receive an answer based only on the most relevant retrieved chunks.

The upload accepts Markdown files up to 2 MB. The active index is stored only in memory and is cleared when the application process restarts.

---

## Deploying to Vercel

Vercel detects Django automatically from `manage.py` and `requirements.txt` — no `vercel.json` is required. Import the repository into Vercel and configure these environment variables:

```env
DJANGO_SECRET_KEY=your_production_secret
GEMINI_API_KEY=your_api_key
DEBUG=0
ALLOWED_HOSTS=your-project.vercel.app
```

`settings.py` derives `CSRF_TRUSTED_ORIGINS` from `ALLOWED_HOSTS` automatically (Django's CSRF check needs the scheme spelled out behind Vercel's proxy) and appends the deployment's own `VERCEL_URL` to `ALLOWED_HOSTS`, so preview deployments work without extra configuration.

The deployment does not require an external database, queue or storage service. Static files are collected and served from Vercel's CDN.

---

## License

This project is licensed under the MIT License.

---

## Contact

[![LinkedIn](https://img.shields.io/badge/LinkedIn-78d?style=for-the-badge&logo=linkedin&logoColor=0A0AAF)](https://www.linkedin.com/in/diogo-oike-kanefuku-23639b223/)
[![E-mail](https://img.shields.io/badge/-Email-e9a?style=for-the-badge&logo=gmail&logoColor=E94D5F)](mailto:diogooikejapan@gmail.com)
