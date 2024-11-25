from django.contrib import admin

# Register your models here.
from .models import Estudiante, Anfitrion, Vivienda, ViviendaFoto, Contrato, FotoEstadoVivienda

""" This file is used for registering the models in the Django admin panel, so that you can easily add, delete, and
see the database records in the Django admin panel.

To render all the models in your Django admin panel, you need to register each model in the admin.py file.

This code imports all the models from the models.py file and registers them with the Django admin site, making them 
accessible in the admin panel.
"""

admin.site.register(Estudiante)
admin.site.register(Anfitrion)
admin.site.register(Vivienda)
admin.site.register(ViviendaFoto)
admin.site.register(Contrato)
admin.site.register(FotoEstadoVivienda)