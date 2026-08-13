from django import forms


MAX_DOCUMENT_SIZE = 2 * 1024 * 1024
TEXT_EXTENSIONS = (".md", ".txt")
ALLOWED_EXTENSIONS = TEXT_EXTENSIONS + (".pdf",)


class DocumentUploadForm(forms.Form):
    document = forms.FileField(
        label="Document",
        allow_empty_file=False,
        widget=forms.ClearableFileInput(attrs={"accept": ",".join(ALLOWED_EXTENSIONS)}),
    )
    max_size = forms.IntegerField(min_value=500, max_value=2000, initial=1500)
    overlap = forms.IntegerField(min_value=0, max_value=1499, initial=100)

    def clean_document(self):
        document = self.cleaned_data["document"]
        name = document.name.lower()
        if not name.endswith(ALLOWED_EXTENSIONS):
            raise forms.ValidationError("Only .md, .txt, or .pdf files are accepted.")
        if document.size > MAX_DOCUMENT_SIZE:
            raise forms.ValidationError("The document must be smaller than 2 MB.")
        if name.endswith(TEXT_EXTENSIONS):
            try:
                document.seek(0)
                content = document.read().decode("utf-8")
                document.seek(0)
            except (UnicodeDecodeError, AttributeError):
                raise forms.ValidationError("The document must be valid UTF-8 text.")
            if not content.strip():
                raise forms.ValidationError("The document cannot be empty.")
        return document

    def clean(self):
        cleaned_data = super().clean()
        max_size = cleaned_data.get("max_size")
        overlap = cleaned_data.get("overlap")
        if max_size is not None and overlap is not None and overlap >= max_size:
            self.add_error("overlap", "Overlap must be smaller than the maximum chunk size.")
        return cleaned_data
