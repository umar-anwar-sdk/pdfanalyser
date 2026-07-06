from django.shortcuts import render, redirect, get_object_or_404
from .forms import PDFDocumentForm
from .models import ParsedTableData, PDFDocument, PDFComparison
from .utils import get_file_hash
import logging

logger = logging.getLogger(__name__)


def upload_pdf(request):

    if request.method == 'POST':
        form = PDFDocumentForm(request.POST, request.FILES)

        if form.is_valid():

            file = request.FILES.get('file')
            
            if not file:
                return render(request, 'upload.html', {
                    'form': form,
                    'error': 'No file selected. Please choose a PDF file to upload.'
                })

            file_hash = get_file_hash(file)
            existing_pdf = PDFDocument.objects.filter(file_hash=file_hash).first()

            if existing_pdf:
                logger.warning(f"Duplicate PDF attempted upload: {file.name}")
                return render(request, 'upload.html', {
                    'form': form,
                    'error': 'This document already exists in the system.',
                    'existing_pdf': existing_pdf
                })

            obj = form.save(commit=False)
            obj.file_hash = file_hash
            obj.save()
            
            logger.info(f"✅ PDF uploaded successfully: {obj.name} (ID: {obj.id})")

            return redirect('parsed_data', pdf_id=obj.id)

        else:
            logger.error(f"❌ FORM ERRORS: {form.errors}")

    else:
        form = PDFDocumentForm()

    return render(request, 'upload.html', {'form': form})


def parsed_data(request, pdf_id):

    pdf = get_object_or_404(PDFDocument, id=pdf_id)

    if not pdf.is_processed:
        rows = []
        processing_error = pdf.processing_error
    else:
        rows = ParsedTableData.objects.filter(pdf_document_id=pdf_id)
        processing_error = None

    latest_comparison_as_new = pdf.comparisons_as_new.first()
    latest_comparison_as_base = pdf.comparisons_as_base.first()

    return render(request, 'parsed_data.html', {
        'rows': rows,
        'pdf': pdf,
        'processing_error': processing_error,
        'latest_comparison_as_new': latest_comparison_as_new,
        'latest_comparison_as_base': latest_comparison_as_base,
    })


def comparison_detail(request, comparison_id):
    comparison = get_object_or_404(PDFComparison, id=comparison_id)
    changes = comparison.changes or []
    added = [item for item in changes if item.get('type') == 'added']
    removed = [item for item in changes if item.get('type') == 'removed']
    modified = [item for item in changes if item.get('type') == 'modified']

    return render(request, 'comparison_detail.html', {
        'comparison': comparison,
        'added_changes': added,
        'removed_changes': removed,
        'modified_changes': modified,
    })