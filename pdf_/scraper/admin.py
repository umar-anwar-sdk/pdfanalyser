from django.contrib import admin
from .models import PDFDocument, ParsedTableData, PDFComparison

admin.site.register(PDFDocument)
admin.site.register(ParsedTableData)
admin.site.register(PDFComparison)