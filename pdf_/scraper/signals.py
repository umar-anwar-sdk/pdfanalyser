import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.db.utils import IntegrityError

from .models import PDFDocument, ParsedTableData, PDFComparison
from .utils import scrape_pdf, compare_pdf_records

logger = logging.getLogger(__name__)


# Important: This signal handler ONLY processes the CURRENT PDF (the one just uploaded)
# NOT all PDFs in the system. The "created=True" check ensures this only runs on new uploads.


# -----------------------------
# helper: validate row
# -----------------------------
def is_valid_row(row):
    if not row:
        return False

    # remove header rows
    if any("Symbol" in str(x) or "Name" in str(x) for x in row):
        return False

    # remove empty rows
    if all(v in [None, "", " "] for v in row):
        return False

    return True


@receiver(post_save, sender=PDFDocument)
def process_pdf_after_upload(sender, instance, created, **kwargs):

    if not created:
        return

    if instance.is_processed or not instance.file:
        return

    try:
        result = scrape_pdf(instance.file.path)

        # -----------------------------
        # FAILED PROCESSING
        # -----------------------------
        if not result.get('success'):
            instance.processing_error = result.get('error')
            instance.processed_at = timezone.now()
            instance.save(update_fields=[
                'processing_error',
                'processed_at',
                'is_processed'
            ])
            return

        # -----------------------------
        # SAVE PDF META (DATE/TIME)
        # -----------------------------
        try:
            instance.report_date = result['report_date']
            instance.report_time = result['report_time']
            instance.is_processed = True
            instance.processed_at = timezone.now()
            instance.processing_error = None

            instance.save(update_fields=[
                'report_date',
                'report_time',
                'is_processed',
                'processing_error',
                'processed_at'
            ])

        except IntegrityError:
            logger.warning("⚠ Duplicate report_date/time detected")
            return

        # -----------------------------
        # SAVE TABLE DATA (ONLY CURRENT PDF)
        # -----------------------------
        tables = result.get('tables', [])

        for table_index, table in enumerate(tables):

            for row_index, row in enumerate(table):

                # skip bad rows
                if not is_valid_row(row):
                    continue

                cleaned_row = {
                    "sr": row[0] if len(row) > 0 else None,
                    "symbol": row[1] if len(row) > 1 else None,
                    "name": row[2] if len(row) > 2 else None,
                    "sector": row[3] if len(row) > 3 else None,
                    "price": row[4] if len(row) > 4 else None,
                    "change": row[5] if len(row) > 5 else None,
                    "change_percent": row[6] if len(row) > 6 else None,
                    "volume": row[7] if len(row) > 7 else None,
                    "trend": row[8] if len(row) > 8 else None,
                }

                # ❌ FIX: duplicate insert bug removed
                ParsedTableData.objects.create(
                    pdf_document=instance,
                    table_index=table_index,
                    row_index=row_index,
                    row_data=cleaned_row
                )

        # compare against the most recent prior processed PDF with the same name
        previous_pdf = PDFDocument.objects.filter(
            name=instance.name,
            is_processed=True
        ).exclude(id=instance.id).order_by('-processed_at').first()
        comparison_basis = 'same_name'

        if not previous_pdf:
            # fallback: compare against the latest processed PDF overall
            previous_pdf = PDFDocument.objects.filter(
                is_processed=True
            ).exclude(id=instance.id).order_by('-processed_at').first()
            comparison_basis = 'latest_processed' if previous_pdf else None

        if previous_pdf:
            base_rows = ParsedTableData.objects.filter(pdf_document=previous_pdf)
            new_rows = ParsedTableData.objects.filter(pdf_document=instance)
            summary, changes = compare_pdf_records(base_rows, new_rows)
            summary['comparison_basis'] = comparison_basis

            if not PDFComparison.objects.filter(base_pdf=previous_pdf, new_pdf=instance).exists():
                PDFComparison.objects.create(
                    base_pdf=previous_pdf,
                    new_pdf=instance,
                    summary=summary,
                    changes=changes,
                )

        logger.info(f"✅ PDF processed successfully: {instance.name}")

    except Exception as e:
        instance.processing_error = str(e)
        instance.processed_at = timezone.now()
        instance.save(update_fields=[
            'processing_error',
            'processed_at',
            'is_processed'
        ])

        logger.error(f"❌ Unexpected error: {str(e)}", exc_info=True)