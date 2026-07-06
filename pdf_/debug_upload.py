import os
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pdf_compare.settings')
django.setup()

from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile

file_path = Path('media/pdfs/psx_pdf.pdf')
if not file_path.exists():
    file_path = Path('test_upload.pdf')

if not file_path.exists():
    raise FileNotFoundError(
        'No sample PDF found for debug_upload.py. Place a PDF at media/pdfs/psx_pdf.pdf or test_upload.pdf.'
    )

client = Client()

uploaded = SimpleUploadedFile(
    file_path.name,
    file_path.read_bytes(),
    content_type='application/pdf'
)

response = client.post('/upload/', {
    'name': 'Test PDF',
    'file': uploaded,
}, HTTP_HOST='localhost')

print('status_code=', response.status_code)
print('templates=', [t.name for t in response.templates if t.name])
print('context=', response.context)
print('content_snippet=', response.content[:200].decode('utf-8', 'replace'))
