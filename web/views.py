import json
import re
import secrets
import time

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .forms import DocumentUploadForm
from .ratelimit import rate_limited
from rag import services
from rag.config import EMBEDDING_DIM, EMBEDDING_MODEL, GENERATION_MODEL, MAX_CHUNKS, SESSION_TTL_SECONDS, TOP_K
from rag.extraction import extract_text

SESSION_COOKIE = "rag_sid"
_SESSION_ID = re.compile(r"[A-Za-z0-9_-]{16,64}")

_TERM = re.compile(r"\w{4,}")
_STOPWORDS = {"what", "which", "that", "this", "with", "from", "have", "does", "about", "there", "their", "were", "when", "where", "into", "than", "then", "them", "your", "will", "would", "could", "should"}


def _owner(request):
    """Session token that scopes the in-memory index to this browser, if any."""
    value = request.COOKIES.get(SESSION_COOKIE, "")
    return value if _SESSION_ID.fullmatch(value) else None


def _error(request, message, status):
    return render(request, "web/partials/error.html", {"message": message}, status=status)


def _remember_owner(response, owner):
    response.set_cookie(SESSION_COOKIE, owner, max_age=SESSION_TTL_SECONDS, httponly=True, samesite="Lax", secure=not settings.DEBUG)


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    owner = _owner(request)
    stats = services.document_stats(owner)
    context = {
        "upload_form": DocumentUploadForm(),
        "has_context": stats is not None,
        "stats": stats,
        "cloud": _cloud(owner),
        "config": _config(),
    }
    return render(request, "web/home.html", context)


@require_POST
@rate_limited("upload")
def upload_document(request: HttpRequest) -> HttpResponse:
    form = DocumentUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        message = " ".join(error for errors in form.errors.values() for error in errors)
        return _error(request, message, 400)

    document = form.cleaned_data["document"]
    owner = _owner(request) or secrets.token_urlsafe(16)
    try:
        started = time.perf_counter()
        text = extract_text(document)
        meta = {"filename": document.name, "kind": document.name.rsplit(".", 1)[-1].lower(), "bytes": document.size, "extract_ms": round((time.perf_counter() - started) * 1000)}
        chunk_count = services.process_document(owner, text, form.cleaned_data["max_size"], form.cleaned_data["overlap"], meta=meta)
    except ValueError as exc:
        return _error(request, str(exc), 400)
    except Exception as exc:
        return _error(request, _safe_error(exc), 502)
    context = {
        "chunk_count": chunk_count,
        "stats": services.document_stats(owner),
        "cloud": _cloud(owner),
    }
    response = render(request, "web/partials/upload_result.html", context)
    _remember_owner(response, owner)
    return response


@require_POST
@rate_limited("clear")
def clear_document(request: HttpRequest) -> HttpResponse:
    services.clear_index(_owner(request))
    return render(request, "web/partials/clear_result.html")


@require_POST
@rate_limited("ask")
def ask_question(request: HttpRequest) -> HttpResponse:
    question = request.POST.get("question", "").strip()
    if not question:
        return _error(request, "Enter a question first.", 400)
    if len(question) > 2000:
        return _error(request, "The question must be 2,000 characters or fewer.", 400)
    try:
        result = services.ask_question(_owner(request), question)
    except ValueError as exc:
        return _error(request, str(exc), 400)
    except RuntimeError as exc:
        return _error(request, str(exc), 409)
    except Exception as exc:
        return _error(request, _safe_error(exc, "The question could not be answered. Try again."), 502)
    context = {
        **result,
        "query_json": json.dumps(result["query_point"]) if result.get("query_point") else "",
        "similarities": ",".join(f"{item['similarity']:.4f}" for item in result["sources"]),
        "retrieved": ",".join(str(item["number"]) for item in result["sources"]),
    }
    terms = _query_terms(question)
    for item in context["sources"]:
        item["percent"] = round(max(0.0, min(1.0, item["similarity"])) * 100)
        item["segments"] = _highlight(item["text"], terms)
    return render(request, "web/partials/chat_answer.html", context)


@require_GET
@rate_limited("chunks")
def list_chunks(request: HttpRequest) -> HttpResponse:
    chunks = services.all_chunks(_owner(request))
    if not chunks:
        return _error(request, "No document is currently available. Upload and process one first.", 409)
    return render(request, "web/partials/chunk_list.html", {"chunks": chunks})


def _config():
    """Static pipeline settings shown in the status bar and the Pipeline view."""
    return {
        "embedding_model": EMBEDDING_MODEL,
        "generation_model": GENERATION_MODEL,
        "dim": EMBEDDING_DIM,
        "top_k": TOP_K,
        "max_chunks": MAX_CHUNKS,
    }


def _query_terms(question):
    return sorted({word for word in _TERM.findall(question.lower()) if word not in _STOPWORDS}, key=len, reverse=True)


def _highlight(text, terms):
    """Split text into (segment, is_match) pairs so the template can mark question terms."""
    if not terms:
        return [(text, False)]
    pattern = re.compile("(" + "|".join(re.escape(term) for term in terms) + ")", re.IGNORECASE)
    return [(part, index % 2 == 1) for index, part in enumerate(pattern.split(text)) if part]


def _safe_error(error, fallback="The document could not be processed. Check the file and try again."):
    message = str(error)
    if "GEMINI_API_KEY" in message:
        return "Gemini is not configured. Set GEMINI_API_KEY and try again."
    if getattr(error, "code", None) == 429:
        return "Gemini rate limit reached. Wait a moment and try again."
    return fallback


def _cloud(owner):
    """3D passage positions for the retrieval cloud, serialized for a data attribute."""
    cloud = services.document_cloud(owner)
    if not cloud:
        return None
    return {"points_json": json.dumps(cloud["points"], separators=(",", ":")), "variance": cloud["variance"]}
