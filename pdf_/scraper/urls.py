from django.urls import path
from .views import upload_pdf, parsed_data, comparison_detail

urlpatterns = [
    path('', upload_pdf),
    path('upload/', upload_pdf, name='upload_pdf'),
    path('data/<int:pdf_id>/', parsed_data, name='parsed_data'),
    path('comparison/<int:comparison_id>/', comparison_detail, name='comparison_detail'),
]