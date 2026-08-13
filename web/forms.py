from django import forms


MAX_DOCUMENT_SIZE = 2 * 1024 * 1024


class DocumentUploadForm(forms.Form):
    document = forms.FileField(label="Markdown document", allow_empty_file=False)
    max_size = forms.IntegerField(min_value=500, max_value=2000, initial=1500)
    overlap = forms.IntegerField(min_value=0, max_value=1499, initial=100)

    def clean_document(self):
        document = self.cleaned_data["document"]
        if not document.name.lower().endswith(".md"):
            raise forms.ValidationError("Only Markdown files with a .md extension are accepted.")
        if document.size > MAX_DOCUMENT_SIZE:
            raise forms.ValidationError("The document must be smaller than 2 MB.")
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
