from django import forms
from .models import FotoEstadoVivienda, Vivienda

""" Formulario para Registrar una nueva Vivienda.
"""


class FotoEstadoViviendaForm(forms.ModelForm):
    class Meta:
        model = FotoEstadoVivienda
        fields = ['imagen']


""" Formulario para Editar una Vivienda.

Tengo que editar este formulario ya que el Tipo de Inmueble y el resto de los Detalles del Inmueble ahora se guardan
en campos separados.

Este formulario automáticamente agarra todos los campos del modelo de Vivienda, y los transforma en un formulario.
"""


class ViviendaForm(forms.ModelForm):
    class Meta:
        model = Vivienda
        fields = ['calle', 'numero_exterior', 'codigo_postal', 'precio_renta', 'tipo_inmueble',
                  'detalles_inmueble', 'servicios', 'detalles_inmueble_compartido',
                  'areas_comunes', 'muebles', 'estacionamiento', 'electrodomesticos']
