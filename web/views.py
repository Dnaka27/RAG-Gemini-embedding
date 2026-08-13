from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .forms import DocumentUploadForm
from rag import services


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "web/home.html", {"upload_form": DocumentUploadForm(), "has_context": services.has_context()})


@require_POST
def upload_document(request: HttpRequest) -> HttpResponse:
    form = DocumentUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "web/partials/upload_result.html", {"form": form, "has_context": False}, status=400)

    document = form.cleaned_data["document"]
    text = document.read().decode("utf-8")
    try:
        chunk_count = services.process_document(text, form.cleaned_data["max_size"], form.cleaned_data["overlap"])
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
    return render(request, "web/partials/chat_answer.html", result)


def _safe_error(error):
    message = str(error)
    if "GEMINI_API_KEY" in message:
        return "Gemini is not configured. Set GEMINI_API_KEY and try again."
    return "The document could not be processed. Check the file and try again."
