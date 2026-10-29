import math
import re
import secrets

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .forms import DocumentUploadForm
from .ratelimit import rate_limited
from rag import services
from rag.config import SESSION_TTL_SECONDS
from rag.extraction import extract_text

SESSION_COOKIE = "rag_sid"
_SESSION_ID = re.compile(r"[A-Za-z0-9_-]{16,64}")

PLOT_SIZE = 200
PLOT_CENTER = PLOT_SIZE / 2
PLOT_MIN_RADIUS = 32
PLOT_MAX_RADIUS = 88


def _owner(request):
    """Session token that scopes the in-memory index to this browser, if any."""
    value = request.COOKIES.get(SESSION_COOKIE, "")
    return value if _SESSION_ID.fullmatch(value) else None


def _remember_owner(response, owner):
    response.set_cookie(SESSION_COOKIE, owner, max_age=SESSION_TTL_SECONDS, httponly=True, samesite="Lax", secure=not settings.DEBUG)


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "web/home.html", {"upload_form": DocumentUploadForm(), "has_context": services.has_context(_owner(request))})


@require_POST
@rate_limited("upload")
def upload_document(request: HttpRequest) -> HttpResponse:
    form = DocumentUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "web/partials/upload_result.html", {"form": form, "has_context": False}, status=400)

    document = form.cleaned_data["document"]
    owner = _owner(request) or secrets.token_urlsafe(16)
    try:
        text = extract_text(document)
        chunk_count = services.process_document(owner, text, form.cleaned_data["max_size"], form.cleaned_data["overlap"])
    except ValueError as exc:
        return render(request, "web/partials/error.html", {"message": str(exc)}, status=400)
    except Exception as exc:
        return render(request, "web/partials/error.html", {"message": _safe_error(exc)}, status=502)
    previews = services.chunk_previews(owner)
    context = {"success": True, "chunk_count": chunk_count, "chunk_previews": previews, "chunks_hidden": chunk_count - len(previews), "has_context": True}
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
        return render(request, "web/partials/error.html", {"message": "Enter a question first."}, status=400)
    if len(question) > 2000:
        return render(request, "web/partials/error.html", {"message": "The question must be 2,000 characters or fewer."}, status=400)
    try:
        result = services.ask_question(_owner(request), question)
    except ValueError as exc:
        return render(request, "web/partials/error.html", {"message": str(exc)}, status=400)
    except RuntimeError as exc:
        return render(request, "web/partials/error.html", {"message": str(exc)}, status=409)
    except Exception as exc:
        return render(request, "web/partials/error.html", {"message": _safe_error(exc, "The question could not be answered. Try again.")}, status=502)
    context = {
        **result,
        "plot_points": _build_retrieval_plot(result["sources"]),
        "plot_size": PLOT_SIZE,
        "plot_center": PLOT_CENTER,
        "plot_sweep_y": PLOT_CENTER - PLOT_MAX_RADIUS,
    }
    return render(request, "web/partials/chat_answer.html", context)


def _safe_error(error, fallback="The document could not be processed. Check the file and try again."):
    message = str(error)
    if "GEMINI_API_KEY" in message:
        return "Gemini is not configured. Set GEMINI_API_KEY and try again."
    if getattr(error, "code", None) == 429:
        return "Gemini rate limit reached. Wait a moment and try again."
    return fallback


def _build_retrieval_plot(sources):
    """Place retrieved chunks on a circle, radius scaled by their real distance.

    Purely presentational: makes the abstract cosine-distance ranking visible
    next to the answer, using the same distance values already shown below.
    """
    if not sources:
        return []
    max_distance = max(item["distance"] for item in sources) or 1e-9
    points = []
    for index, item in enumerate(sources):
        angle = -math.pi / 2 + (2 * math.pi * index / len(sources))
        radius = PLOT_MIN_RADIUS + (item["distance"] / max_distance) * (PLOT_MAX_RADIUS - PLOT_MIN_RADIUS)
        x = PLOT_CENTER + radius * math.cos(angle)
        y = PLOT_CENTER + radius * math.sin(angle)
        points.append({"x": round(x, 1), "y": round(y, 1), "label_y": round(y - 11, 1), "rank": index + 1})
    return points
