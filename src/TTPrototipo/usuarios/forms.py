from django import forms
from .models import FotoEstadoVivienda, Vivienda, Contrato

# Esto me deja usar el campo JSignatureField en los formularios para Guardar Firmas Dibujadas.
from jsignature.forms import JSignatureField

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

To add a date picker widget to the fecha_inicio and fecha_fin fields in your Django form, you can use the DateInput 
widget with the attrs parameter to specify the HTML5 date input type. Here is how you can do it:  

1) Import the DateInput widget from django.forms.
2) Update the CrearContratoForm to use the DateInput widget for the fecha_inicio and fecha_fin fields.

This will render the fecha inicio and fecha fin fields as date pickers in your form, allowing users to select dates 
from a calendar widget.
"""


class CrearContratoForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ['estudiante', 'vivienda', 'anfitrion', 'precio_renta', 'archivo_contrato',
                  'fotos_subidas_anfitrion', 'fotos_subidas_estudiante', 'cancelado', 'fecha_inicio',
                  'fecha_fin'
                  ]

        # Esto le agregará el widget para seleccionar una fecha de un calendario para los campos de las fechas
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }


""" Formulario para Editar un Contrato.

En la página de editar un contrato, pondré que el anfitrión pueda editar su propia firma, PERO NO LA FIRMA DEL 
ESTUDIANTE. QUE EL ANFITRIÓN pueda editar la firma de un estudiante sería muy peligroso.

To add a date picker widget to the fecha_inicio and fecha_fin fields in your Django form, you can use the DateInput 
widget with the attrs parameter to specify the HTML5 date input type. Here is how you can do it:  

1) Import the DateInput widget from django.forms.
2) Update the EditarContratoForm to use the DateInput widget for the fecha_inicio and fecha_fin fields.
"""


class EditarContratoForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ['estudiante', 'vivienda', 'anfitrion', 'precio_renta', 'archivo_contrato', 'firmado',
                  'firma_anfitrion', 'fotos_subidas_anfitrion', 'fotos_subidas_estudiante', 'cancelado', 'fecha_inicio',
                  'fecha_fin'
                  ]

        # Esto le agregará el widget para seleccionar una fecha de un calendario para los campos de las fechas
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }


""" Formulario de prueba para guardar Firmas Dibujadas.

"""


class SignatureForm(forms.Form):
    signature = JSignatureField()
