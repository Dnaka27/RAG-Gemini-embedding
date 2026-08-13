import math

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .forms import DocumentUploadForm
from rag import services
from rag.extraction import extract_text

PLOT_SIZE = 200
PLOT_CENTER = PLOT_SIZE / 2
PLOT_MIN_RADIUS = 32
PLOT_MAX_RADIUS = 88


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "web/home.html", {"upload_form": DocumentUploadForm(), "has_context": services.has_context()})


@require_POST
def upload_document(request: HttpRequest) -> HttpResponse:
    form = DocumentUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "web/partials/upload_result.html", {"form": form, "has_context": False}, status=400)

    document = form.cleaned_data["document"]
    try:
        text = extract_text(document)
        chunk_count = services.process_document(text, form.cleaned_data["max_size"], form.cleaned_data["overlap"])
    except ValueError as exc:
        return render(request, "web/partials/error.html", {"message": str(exc)}, status=400)
    except Exception as exc:
        return render(request, "web/partials/error.html", {"message": _safe_error(exc)}, status=502)
    return render(request, "web/partials/upload_result.html", {"success": True, "chunk_count": chunk_count, "has_context": True})


@require_POST
def ask_question(request: HttpRequest) -> HttpResponse:
    question = request.POST.get("question", "").strip()
    if not question:
        return render(request, "web/partials/error.html", {"message": "Enter a question first."}, status=400)
    if len(question) > 2000:
        return render(request, "web/partials/error.html", {"message": "The question must be 2,000 characters or fewer."}, status=400)
    try:
        result = services.ask_question(question)
    except RuntimeError as exc:
        return render(request, "web/partials/error.html", {"message": str(exc)}, status=409)
    except Exception as exc:
        return render(request, "web/partials/error.html", {"message": _safe_error(exc)}, status=502)
    context = {
        **result,
        "plot_points": _build_retrieval_plot(result["sources"]),
        "plot_size": PLOT_SIZE,
        "plot_center": PLOT_CENTER,
        "plot_sweep_y": PLOT_CENTER - PLOT_MAX_RADIUS,
    }
    return render(request, "web/partials/chat_answer.html", context)


def _safe_error(error):
    message = str(error)
    if "GEMINI_API_KEY" in message:
        return "Gemini is not configured. Set GEMINI_API_KEY and try again."
    return "The document could not be processed. Check the file and try again."


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
