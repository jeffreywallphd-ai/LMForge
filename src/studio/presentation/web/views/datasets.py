from django.shortcuts import render
from studio.domain.models import SourceDocumentMetadata
from studio.presentation.web.forms.documents import DocumentForm
from django.core.paginator import Paginator
from decouple import config

DEFAULT_HF_KEY = config("HF_API_KEY", default="")
DEFAULT_HF_ACCOUNT = config("HF_ACCOUNT_NAME", default=None)

def dataset_workflow_view(request):
    messages = []
    documents_list = SourceDocumentMetadata.objects.all().order_by('-created_at')  # Order by latest entries

    # Apply pagination (10 documents per page)
    paginator = Paginator(documents_list, 10)
    page_number = request.GET.get('page')
    documents = paginator.get_page(page_number)

    form = DocumentForm()

    if request.session.get("redirect_message"):
        messages.append(request.session.get("redirect_message"))
        del request.session["redirect_message"]

    return render(request, "web/pages/datasets/workflow.html", {"form": form, "documents":documents, "messages": messages})

def dataset_workflow_document_processor(request):
    return render(request, "web/pages/datasets/document_upload.html")
