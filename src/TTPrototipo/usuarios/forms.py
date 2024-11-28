from django import forms
from .models import FotoEstadoVivienda, Vivienda, Contrato

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


""" Formulario para Crear un Contrato.

Le meteré el modelo del Contrato para que sepa qué campos debe tener el formulario.

The form.save() line in your crear_contrato view will not create a new instance of the Contrato model because the 
CrearContratoForm class in forms.py is defined as a forms.Form instead of a forms.ModelForm. The forms.Form class does 
not have a save method by default.  To fix this, you need to change the CrearContratoForm class to inherit from 
forms.ModelForm and ensure it is correctly set up to handle the Contrato model.

No pondré los campos para firmar, ya que, cuando creas un contrato, no tiene sentido que el contrato este firmado.
"""


class CrearContratoForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ['estudiante', 'vivienda', 'anfitrion', 'precio_renta', 'archivo_contrato',
                  'fotos_subidas_anfitrion', 'fotos_subidas_estudiante', 'cancelado', 'fecha_inicio',
                  'fecha_fin'
                  ]


""" Formulario para Editar un Contrato.

En la página de editar un contrato, pondré que el anfitrión pueda editar su propia firma, PERO NO LA FIRMA DEL 
ESTUDIANTE. QUE EL ANFITRIÓN pueda editar la firma de un estudiante sería muy peligroso.
"""


class EditarContratoForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ['estudiante', 'vivienda', 'anfitrion', 'precio_renta', 'archivo_contrato', 'firmado',
                  'firma_anfitrion', 'fotos_subidas_anfitrion', 'fotos_subidas_estudiante', 'cancelado', 'fecha_inicio',
                  'fecha_fin'
                  ]
