from django import forms
from .models import FotoEstadoVivienda,Vivienda

class FotoEstadoViviendaForm(forms.ModelForm):
    class Meta:
        model = FotoEstadoVivienda
        fields = ['imagen']

class ViviendaForm(forms.ModelForm):
    class Meta:
        model = Vivienda
        fields = ['calle', 'numero_exterior', 'codigo_postal', 'precio_renta',
                  'detalles_inmueble', 'servicios', 'detalles_inmueble_compartido',
                  'areas_comunes', 'muebles', 'estacionamiento', 'electrodomesticos']
