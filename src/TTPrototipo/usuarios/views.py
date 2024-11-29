from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from .models import Estudiante, Anfitrion, Vivienda, ViviendaFoto, Contrato, FotoEstadoVivienda, SignatureModel
from django.template.loader import render_to_string
from django.http import FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from weasyprint import HTML
from .forms import FotoEstadoViviendaForm, ViviendaForm, CrearContratoForm, EditarContratoForm, SignatureForm
import logging
from django.conf import settings

# Esto me permite convertir una firma dibujada en una Imagen o en un PDF
from jsignature.utils import draw_signature

# Esto es para especificar donde quiero que se me guarden las Firmas Dibujadas
import os

# Necesito estas 2 bibliotecas para meter mi firma dibujada en mi carpeta "media"
from django.core.files.base import ContentFile
import base64

# # Importar el módulo ast para convertir un string en un diccionario para las Viviendas
# import ast

""" Vista con la Lista de Viviendas.

Tienes que estar autenticado como anfitrión para acceder a esta vista. Si no estás autenticado, o si no eres anfitrión, 
te redirigirá a la página de inicio de sesión.
"""


@login_required
def listar_viviendas(request):
    if not hasattr(request.user, 'anfitrion'):
        messages.error(request, "No tienes permiso para acceder a esta página.")
        return redirect('Inicio de Sesion')

    anfitrion = request.user.anfitrion
    viviendas = Vivienda.objects.filter(anfitrion=anfitrion)
    return render(request, 'viviendas/listar_viviendas.html', {'viviendas': viviendas})


""" Vista para Editar una Vivienda.

Solo el anfitrión asociado a la vivienda puede editarla. 

Si el usuario no tiene permiso para editar la vivienda, se le mostrará un mensaje de error y se le redirigirá a la
lista de viviendas.

Tengo que editar esta vista ya que ahora el Tipo de Inmueble y el resto de los detalles del inmueble se guardan en
campos separados en el modelo de Vivienda.
"""


@login_required
def editar_vivienda(request, vivienda_id):
    vivienda = get_object_or_404(Vivienda, id=vivienda_id)

    if request.user.anfitrion != vivienda.anfitrion:
        messages.error(request, "No tienes permiso para editar esta vivienda.")
        return redirect('listar_viviendas')

    if request.method == 'POST':
        form = ViviendaForm(request.POST, request.FILES, instance=vivienda)
        if form.is_valid():
            form.save()
            messages.success(request, "Vivienda actualizada exitosamente.")
            return redirect('listar_viviendas')
    else:
        form = ViviendaForm(instance=vivienda)

    return render(request, 'viviendas/editar_vivienda.html', {'form': form})


""" Vista para Eliminar una Vivienda.

No te sale un mensaje de confirmación antes de borrar la vivienda. Solo se borra directamente.
"""


@login_required
def eliminar_vivienda(request, vivienda_id):
    vivienda = get_object_or_404(Vivienda, id=vivienda_id)

    # Verificar si la vivienda tiene contratos activos
    contrato_activo = Contrato.objects.filter(vivienda=vivienda, firmado=True).exists()

    if contrato_activo:
        messages.error(request, "No puedes eliminar esta vivienda porque tiene un contrato activo.")
        return redirect('listar_viviendas')  # Redirige a la lista de viviendas del anfitrión

    if request.method == 'POST':
        vivienda.delete()
        messages.success(request, "Vivienda eliminada exitosamente.")
        return redirect('listar_viviendas')  # Redirige después de la eliminación

    return render(request, 'viviendas/confirmar_eliminar_vivienda.html', {'vivienda': vivienda})


""" Vista para ver la Lista de Contratos de una Anfitrión, y para Gestionar un Contrato. Por gestionar un contrato, me
refiero a poder firmar, agregarle fotos a un contrato, y hasta generar ese contrato en PDF. No puedes editar un contrato 
desde aquí.

Esta vista se usa para 2 páginas distintas: para ver la lista de Contratos, y para Firmar un Contrato.

Uso el paquete django-jsignature para poder firmar contratos dibujando en la pantalla. Para poder usarlo, tengo que
importar la vista SignatureField y el formulario SignatureForm en el forms.py.

Para poder firmar un contrato, tengo que meter la firma dibujada en la base de datos. Para hacer esto, tengo que
importar el modelo SignatureModel en el models.py.

**Problem 1: Incorrect handling of the signature file**

The code is attempting to save the signature as a file, but the method used to create the `ContentFile` object is 
incorrect. The `draw_signature` function returns a file path, not the file content. This needs to be corrected to 
properly save the image file.

**Solution: Read the file content and save it correctly**

This code correctly reads the content of the generated signature file and saves it as a `ContentFile` in the 
`SignatureModel`. This should resolve the issue of the corrupted PNG image.

Estoy haciendo una prueba para dibujar una firma, y meterlo en un modelo de Prueba usando Jsignature. Ya se 
puede hacer: dibujas una firma, clicas en "Save", y se genera una imagen PNG con la firma, y se mete
en la carpeta "firmas/archivos" de la carpeta "media". Se mete en el modelo de SignatureModel, en el campo de
"file". Es algo complicado de usar.

Ahora, voy a modificar el view de gestionar_contrato del anfitrión para que, cuando cliques en “Firmar”, se envíe es la 
firma del Jsignature, NO la del hash. Ya no quiero generar el hash.

Ya puedo guardar la firma dibujada del anfitrión correctamente en el campo de la firma del anfitrión como una imagen 
PNG, y me guarda la firma dibujada.

To change the name of the generated image to include the username of the logged user, you can retrieve the username 
from the request.user object and concatenate it to the filename. I'm retrieving the username of the logged user and 
I use it to create a new filename for the signature image. The image is then saved with this new filename.

To add an else statement for the if form_firma_dibujada.is_valid() condition, you can use the 
form_firma_dibujada.errors to get the error messages and pass them to messages.error.
"""


@login_required
def gestionar_contrato(request, contrato_id=None):
    """
    Vista general para gestionar contratos.
    """
    usuario = request.user

    # Get the username of the logged user
    username = request.user.username

    # Concatenate the username to the signature image's filename. This will be used later to save the image.
    filename = f'signature_{username}.png'

    # Caso 1: Sin contrato_id
    # Esto es principalmente para Estudiantes. Si el estudiante no está asociado a ningún contrato, se le redirige a
    # una página con una lista de viviendas para que escoja una.
    if contrato_id is None:
        if hasattr(usuario, 'estudiante'):
            estudiante = usuario.estudiante

            if hasattr(estudiante, 'contrato'):
                return redirect('gestionar_contrato', contrato_id=estudiante.contrato.id)

            viviendas_disponibles = Vivienda.objects.filter(estudiante_contratado__isnull=True)
            if request.method == 'POST':
                vivienda_id = request.POST.get('vivienda_id')
                vivienda = get_object_or_404(Vivienda, id=vivienda_id)

                contrato = Contrato.objects.create(
                    estudiante=estudiante,
                    vivienda=vivienda,
                    anfitrion=vivienda.anfitrion,
                    precio_renta=vivienda.precio_renta,
                )
                estudiante.vivienda_contratada = vivienda
                estudiante.save()
                return redirect('gestionar_contrato', contrato_id=contrato.id)

            return render(request, 'viviendas/seleccionar_vivienda.html', {'viviendas': viviendas_disponibles})

        if hasattr(usuario, 'anfitrion'):
            anfitrion = usuario.anfitrion
            contratos = Contrato.objects.filter(anfitrion=anfitrion)
            return render(request, 'contratos/listar_contratos_anfitrion.html', {'contratos': contratos})

        return HttpResponseForbidden("No tienes permisos para acceder a esta página.")
    # Fin del Caso 1

    # Caso 2: Con contrato_id
    contrato = get_object_or_404(Contrato, id=contrato_id)

    # Si el usuario es un Anfitrión
    if hasattr(usuario, 'anfitrion') and contrato.anfitrion.user == usuario:
        fotos = contrato.fotos_estado.all()
        form = FotoEstadoViviendaForm()

        # Formulario para guardar Firmas Dibujadas. Esto activa el canvas para dibujar
        form_firma_dibujada = SignatureForm()

        # form_firma_prueba = SignatureForm()

        # # Prueba para meter una Firma Dibujada en la base de datos usando Django JSignature
        # if request.method == 'POST':
        #     form_firma_prueba = SignatureForm(request.POST)
        #     if form_firma_prueba.is_valid():
        #         signature = form_firma_prueba.cleaned_data.get('signature')
        #         if signature:
        #             # # Save the signature as an image
        #             # signature_picture = draw_signature(signature)
        #
        #             # Save the signature as a file
        #             signature_file_path = draw_signature(signature, as_file=True)
        #
        #             # Read the file content
        #             with open(signature_file_path, 'rb') as f:
        #                 image_content = f.read()
        #
        #             # # Decode the base64 image and save it to the media folder
        #             # # image_data = base64.b64decode(signature_file_path)
        #             # image = ContentFile(signature_file_path, 'signature.png')
        #
        #             # Save the instance of the Jsignature field (neither image nor file) to the database
        #             signature_model = SignatureModel(
        #                 signature=signature,
        #                 # file=signature_file_path,  # This saves the image version of the signature
        #             )
        #             signature_model.file.save('signature.png', ContentFile(image_content))
        #
        #             # signature_model.file.save(signature_file_path)
        #             # signature_model.file.save('signature.png', image)
        #             # signature_model.file.save('signature.png', signature_file_path)
        #             signature_model.save()
        #             # FIN de la prueba de meter una Firma Dibujada en la base de datos usando Django JSignature

        if request.method == 'POST' and 'subir_fotos' in request.POST:
            form = FotoEstadoViviendaForm(request.POST, request.FILES)
            if form.is_valid():
                foto = form.save(commit=False)
                foto.contrato = contrato
                foto.save()
                contrato.fotos_subidas_anfitrion = True
                contrato.save()
                messages.success(request, "Foto subida correctamente.")
            else:
                messages.error(request, "No se pudo subir la foto. Verifica el formulario.")

        # Esto firma el contrato. Lo voy a modificar para que meta una imagen en lugar de un hash.
        if request.method == 'POST' and 'firmar' in request.POST:

            # Necesitas haber subido al menos una foto antes de firmar el contrato
            if not contrato.fotos_estado.exists():
                messages.error(request, "Debes subir al menos una foto antes de firmar el contrato.")
                return redirect('gestionar_contrato', contrato_id=contrato.id)

            # Esto agarra la Firma Dibujada, la convierte en imagen, y la guarda en el modelo de Contrato

            # Detecto si el usuario dibujó la firma usando mi Formulario de Firmas usando Jsignature
            form_firma_dibujada = SignatureForm(request.POST)

            # Esto valida la firma dibujada
            if form_firma_dibujada.is_valid():

                # Agarra la firma dibujada del campo que te deja dibujar la firma del formulario
                signature = form_firma_dibujada.cleaned_data.get('signature')
                if signature:
                    # Esto convierte la firma dibujada en una imagen como un archivo temporal
                    signature_file_path = draw_signature(signature, as_file=True)

                    # Abre la imagen de la firma, y luego la lee. Necesito esto antes de poder guardar la imagen.
                    with open(signature_file_path, 'rb') as f:
                        image_content = f.read()

                    # # Save the instance of the Jsignature field (neither image nor file) to the database
                    # signature_model = SignatureModel(
                    #     signature=signature,
                    #     # file=signature_file_path,  # This saves the image version of the signature
                    # )

                    # Metiendo de manera permanente la imagen de la firma del anfitrión en el modelo de Contrato
                    contrato.firma_anfitrion.save(filename, ContentFile(image_content))

                    contrato.save()  # Guarda todos los cambios hechos en el modelo de Contrato

                    # # Esto genera la firma creando un Hash. MODIFICAR.
                    # contrato.firma_anfitrion = contrato.generar_firma(usuario)

                    contrato.save()  # Guarda la firma en el modelo de Contrato

                    # Mensaje de confirmación de que se firmó el contrato
                    messages.success(request, "Has firmado el contrato.")

                    # FIN del snippet que mete una Firma Dibujada en la base de datos usando Django JSignature

            # Si la firma está vacía os en inválida, se muestra un mensaje de error
            else:
                # Insertar los mensajes de error generados por is_valid() en messages.error
                for field, errors in form_firma_dibujada.errors.items():
                    for error in errors:
                        messages.error(request, f"Error en el campo {field}: {error}")



        return render(request, 'contratos/gestionar_contrato_anfitrion.html', {
            'contrato': contrato,
            'fotos': fotos,
            'form': form,
            'form_firma_dibujada': form_firma_dibujada,  # Formulario de para Dibujar una Firma
            # 'form_firma_prueba': form_firma_prueba,
        })

    # Si el usuario es un Estudiante
    if hasattr(usuario, 'estudiante') and contrato.estudiante.user == usuario:
        fotos = contrato.fotos_estado.all()
        form = FotoEstadoViviendaForm()

        # Formulario para Dibujar una Firma. Esta es para los Estudiantes.
        form_firma_dibujada_estudiante = SignatureForm()

        if request.method == 'POST' and 'subir_fotos' in request.POST:
            form = FotoEstadoViviendaForm(request.POST, request.FILES)
            if form.is_valid():
                foto = form.save(commit=False)
                foto.contrato = contrato
                foto.save()
                contrato.fotos_subidas_estudiante = True
                contrato.save()
                messages.success(request, "Foto subida correctamente.")
            else:
                messages.error(request, "No se pudo subir la foto. Verifica el formulario.")

        # BOOKMARK
        # Esto firma el contrato. Lo voy a modificar para que meta una imagen en lugar de un hash.
        if request.method == 'POST' and 'firmar' in request.POST:
            if not contrato.fotos_estado.exists():
                messages.error(request, "Debes subir al menos una foto antes de firmar el contrato.")
                return redirect('gestionar_contrato', contrato_id=contrato.id)

            contrato.firma_estudiante = contrato.generar_firma(usuario)
            contrato.save()
            messages.success(request, "Has firmado el contrato.")

        # FIN del snippet que debo modificar par meter la Firma Dibujada del Estudiante

        return render(request, 'contratos/gestionar_contrato_estudiante.html', {
            'contrato': contrato,
            'fotos': fotos,
            'form': form,
            'form_firma_dibujada_estudiante': form_firma_dibujada_estudiante,  # Formulario de para Dibujar una Firma
        })

    return HttpResponseForbidden("No tienes permisos para gestionar este contrato.")


""" Vista para Cancelar un Contrato.

¿Supongo que esto es para cuando se quiere eliminar el contrato? No estoy seguro.

Las funciones de cancelar_contrato() y puede_cancelarse() están en el modelo de Contrato en el models.py.

Lo que hace el meterme a la URL de esta vista es marcar la casilla “Cancelado” del campo “cancelado” del modelo de 
Contrato. Es decir, marca el booleano “Cancelado” como “true”. El contrato solo puede marcarse como cancelado si no
está firmado. De lo contrario, esta vista no hará nada.

Te redirige a la página principal después de cancelar el contrato.
"""


@login_required
def cancelar_contrato(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id)

    # Verificar permisos: sólo el estudiante o el anfitrión asociados pueden cancelar
    usuario = request.user
    if not (contrato.estudiante.user == usuario or contrato.anfitrion.user == usuario):
        return HttpResponseForbidden("No tienes permiso para cancelar este contrato.")

    # Intentar cancelar el contrato
    if contrato.puede_cancelarse():
        contrato.cancelar_contrato()
        messages.success(request, "El contrato ha sido cancelado exitosamente.")
        return redirect('Inicio')  # Redirigir a la página principal u otra página
    else:
        messages.error(request, "El contrato no puede ser cancelado porque ya ha sido firmado.")
        return redirect('gestionar_contrato', contrato_id=contrato.id)


@login_required
def seleccionar_vivienda(request):
    # Asegurarse de que el usuario sea un estudiante
    if not hasattr(request.user, 'estudiante'):
        return HttpResponseForbidden("Solo los estudiantes pueden acceder a esta funcionalidad.")

    estudiante = request.user.estudiante

    # Listar todas las viviendas disponibles
    viviendas = Vivienda.objects.filter(estudiante_contratado__isnull=True)

    if request.method == 'POST':
        vivienda_id = request.POST.get('vivienda_id')
        vivienda = get_object_or_404(Vivienda, id=vivienda_id)

        # Crear el contrato
        contrato = Contrato.objects.create(
            estudiante=estudiante,
            vivienda=vivienda,
            anfitrion=vivienda.anfitrion,
            precio_renta=vivienda.precio_renta,
            fecha_inicio="2024-11-01",  # Puedes usar una fecha dinámica aquí
            fecha_fin="2025-11-01",  # Ejemplo de fecha de fin
        )

        # Asociar la vivienda con el estudiante
        estudiante.vivienda_contratada = vivienda
        estudiante.save()

        messages.success(request, "El contrato ha sido generado correctamente.")
        return redirect('generar_contrato_pdf', contrato_id=contrato.id)

    return render(request, 'viviendas/seleccionar_vivienda.html', {'viviendas': viviendas})


@login_required
def subir_fotos(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id)
    usuario = request.user

    if request.method == 'POST':
        form = FotoEstadoViviendaForm(request.POST, request.FILES)
        if form.is_valid():
            foto = form.save(commit=False)
            foto.contrato = contrato
            foto.save()

            # Verificar si es anfitrión o estudiante
            if hasattr(usuario, 'anfitrion') and contrato.anfitrion.user == usuario:
                contrato.fotos_subidas_anfitrion = True
            elif hasattr(usuario, 'estudiante') and contrato.estudiante.user == usuario:
                contrato.fotos_subidas_estudiante = True

            contrato.save()
            messages.success(request, "Foto subida correctamente.")
            return redirect('generar_contrato_pdf', contrato_id=contrato.id)

    else:
        form = FotoEstadoViviendaForm()

    return render(request, 'subir_fotos.html', {'form': form, 'contrato': contrato})


# Generar PDF del Contrato
# Habilitar el logging de WeasyPrint
logging.basicConfig(level=logging.DEBUG)

""" Vista para Generar el Contrato en PDF.

Esta vista aparece cuando clicas en el botón de "Generar Contrato" en la página para Gestionar un Contrato
Seleccionado si eres un anfitrión.

BUG: la línea del tipo de inmueble me está generando un bug que no me deja terminar de generar el contrato.

Si desactivo la línea de tipo_inmueble del view de generar_contrato_pdf(), al hacer clic en Generar contrato, me genera 
perfectamente un PDF. La manera en la que se está agarrando el tipo de inmueble en esta vista está generando un bug,
ya que se está agarrando de manera ineficiente y errónea del modelo de Vivienda.

Entonces, los pasos a seguir para arreglar este bug y agarrar el tipo de inmueble son:
1) Crear el campo “tipo de inmueble” en el modelo de Vivienda.
2) Meter el tipo de inmueble en ese nuevo campo al registrar una nueva vivienda.
3) Meter el resto de los detalles del inmueble en la variable de “detalles del inmueble”.
4) En el view de generar_contrato_pdf(), agarrare el tipo del inmueble del campo “tipo de inmueble” del modelo de 
Vivienda.

En ningun momento se estaban agarrando las firmas, fueran en hash, o fueran en imagen. Voy a agarrar las firmas
como imagenes, y las intentaré meter en el PDF del contrato.

The issue is that the firma_anfitrion field is being accessed directly as a URL, but it should be accessed through the 
settings.MEDIA_URL to generate the correct URL for the image.  Solution: Use settings.MEDIA_URL to generate the correct 
URL for the signature image. This change ensures that the URL for the signature image is correctly generated using
settings.MEDIA_URL.
"""


def generar_contrato_pdf(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id)

    if request.method == "POST":
        ciudad = request.POST.get("ciudad", "Ciudad de México")  # Valor por defecto
        fecha = request.POST.get("fecha", "")

        # Esto debería resolver el bug que no me deja generar el contrato.
        # Agarrando el tipo de inmueble del campo "Tipo de Inmueble" del modelo de Vivienda.
        tipo_inmueble = contrato.vivienda.tipo_inmueble

        # NO FUNCIONO.
        # detalles_inmueble = ast.literal_eval(contrato.vivienda.detalles_inmueble)
        # tipo_inmueble = detalles_inmueble.get("tipo", "Inmueble")

        # BUG: Esta linea no me está dejando terminar de generar el contrato.
        # tipo_inmueble = contrato.vivienda.detalles_inmueble.get("tipo", "Inmueble")

        ubicacion = f"{contrato.vivienda.calle}, {contrato.vivienda.numero_exterior}, {contrato.vivienda.codigo_postal} CDMX"
        nombre_arrendador = contrato.anfitrion.nombre
        nombre_arrendatario = contrato.estudiante.nombre

        fotos = contrato.fotos_estado.all()
        fotos_urls = [request.build_absolute_uri(settings.MEDIA_URL + foto.imagen.name) for foto in fotos]

        # Esto agarra la imagen con la Firma del Anfitrión del Contrato Seleccionado.
        # Correctly generate the URL for the signature image.
        firma_anfitrion = request.build_absolute_uri(settings.MEDIA_URL + contrato.firma_anfitrion.name)

        # firma_anfitrion = contrato.firma_anfitrion.url

        html_content = render_to_string("contratos/contrato.html", {
            "contrato": contrato,
            "ciudad": ciudad,
            "fecha": fecha,
            "tipo_inmueble": tipo_inmueble,
            "ubicacion": ubicacion,
            "nombre_arrendador": nombre_arrendador,
            "nombre_arrendatario": nombre_arrendatario,
            "fotos": fotos_urls,
            "firma_anfitrion": firma_anfitrion,  # Mete la imagen de la firma del anfitrión en el PDF
        })

        pdf = HTML(string=html_content).write_pdf()
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="Contrato_{contrato.id}.pdf"'
        return response

    # Renderizar el formulario para generar el contrato
    return render(request, "contratos/formulario_contrato.html", {"contrato": contrato})


# Firmar Contrato
@login_required
def firmar_contrato(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id)
    usuario = request.user

    if not contrato.puede_firmarse():
        messages.error(request, "El contrato no puede ser firmado hasta que el anfitrión suba las fotos obligatorias.")
        return redirect('generar_contrato_pdf', contrato_id=contrato.id)

    if hasattr(usuario, 'estudiante') and contrato.estudiante.user == usuario:
        contrato.firma_estudiante = contrato.generar_firma(usuario)
        messages.success(request, "Has firmado el contrato como estudiante.")
    elif hasattr(usuario, 'anfitrion') and contrato.anfitrion.user == usuario:
        contrato.firma_anfitrion = contrato.generar_firma(usuario)
        messages.success(request, "Has firmado el contrato como anfitrión.")
    else:
        return HttpResponseForbidden("No estás autorizado para firmar este contrato.")

    if contrato.firma_estudiante and contrato.firma_anfitrion:
        contrato.firmado = True
        messages.success(request, "El contrato ha sido firmado por ambas partes.")

    contrato.save()
    return redirect('generar_contrato_pdf', contrato_id=contrato.id)


""" Descargar Contrato Firmado.

Si el contrato no está firmado, me saldrá una página de error 404: "page not found".
"""


def descargar_contrato(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id, firmado=True)
    return FileResponse(contrato.archivo_contrato.open(), as_attachment=True,
                        filename=f"Contrato_{contrato.id}.pdf"
                        )


def RegistroUsuario(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        contraseña = request.POST.get('contraseña')
        correo = request.POST.get('correo')
        celular = request.POST.get('celular')
        rol = request.POST.get('rol')  # Obteniendo el rol del campo oculto

        # Crear el usuario de Django
        user = User.objects.create_user(username=nombre, password=contraseña, email=correo)

        if rol == 'estudiante':
            # Guardar en la tabla Estudiante
            estudiante = Estudiante(
                user=user,
                nombre=nombre,
                contraseña=contraseña,
                correo=correo,
                celular=celular,
                # Agrega aquí otros campos específicos de estudiante si es necesario
            )
            estudiante.save()
            messages.success(request, "Registro de estudiante exitoso.")
            return redirect('Inicio de Sesion')  # Redirige a la página de inicio de sesión o donde prefieras

        elif rol == 'anfitrion':
            # Guardar en la tabla Anfitrion
            anfitrion = Anfitrion(
                user=user,
                nombre=nombre,
                contraseña=contraseña,
                correo=correo,
                celular=celular,
                # Agrega aquí otros campos específicos de anfitrión si es necesario
            )
            anfitrion.save()
            login(request, user)  # Autentica al usuario
            messages.success(request, "Registro de anfitrión exitoso. Continúa con el registro de tu vivienda.")
            return redirect('Registro de vivienda')  # Redirige a la página de registro de vivienda

    return render(request, 'RegistroUsuario.html')


""" Registro de Vivienda.

Esta vista permite a los anfitriones registrar una vivienda en la plataforma. Se requiere que el usuario esté 
autenticado.

Voy a modificar esta vista, ya que está insertando los datos de la vivienda como JSON en la base de datos, pero yo
quiero meterlos como texto simple.

Cuando el anfitrión registra una vivienda, es redirigido a la página de inicio de sesión, como que si cerrara su 
sesión. ¿Debería cambiar esto? Redirigir al usuario al formulario de inicio de sesión después de registrar una vivienda
no tiene mucho sentido. Tendría más sentido redirigirlo a la página de inicio de anfitrión, o a la lista de viviendas.

BUGFIX: tuve que colocar "Microondas" y "Refrigerador" al agarrar esos campos del formulario, ya que en esta vista
estaban como "Refri" y "Micro", por lo que siempre marcaba esos valores como "Off" o "No".

Voy a meter el tipo de inmueble en un nuevo campo del modelo de Vivienda llamado "Tipo de Inmueble", mientras que el
resto de los detalles del inmueble los dejaré en el campo "Detalles del Inmueble". Esto es apra corregir un bug que no
me dejaba generar el contrato como PDF.
"""


@login_required
def Registrovivienda(request):
    if request.method == 'POST':
        # Verificar que el usuario esté autenticado y que tenga un perfil de anfitrión
        if not request.user.is_authenticated:
            messages.error(request, "Necesitas iniciar sesión para registrar una vivienda.")
            return redirect('Inicio de Sesion')
        try:
            anfitrion = request.user.anfitrion  # Obtiene el anfitrión autenticado
            print(f"Anfitrion ID asociado al usuario autenticado: {anfitrion.id}")  # Verifica el ID del anfitrión
        except Anfitrion.DoesNotExist:
            messages.error(request, "No tienes un perfil de anfitrión. Por favor, regístrate como anfitrión primero.")
            return redirect('Registro de Usuario')

        # anfitrion = get_object_or_404(Anfitrion, correo=request.user.email)
        # anfitrion = request.user.anfitrion  # Obtiene el anfitrión autenticado

        # Recibe los datos del formulario
        calle = request.POST.get('Ingresar-calle')
        numero_exterior = request.POST.get('NumExt')
        codigo_postal = request.POST.get('CP')
        precio_renta = request.POST.get('Renta')

        # Esto solo recoge el Tipo de Inmueble
        tipo_inmueble = request.POST.get('TipoInmueble')

        # Servicios en JSON. LO MODIFIQUÉ ESTO PARA QUE LOS CAMPOS ACEPTEN TEXTO SIMPLE EN LUGAR DE JSON.

        # Modifiqué los detalles del Inmueble para que guarde texto simple en la base de datos en lugar de JSON.
        detalles_inmueble = (
            # f"Tipo: {request.POST.get('TipoInmueble')}\n"
            f"Número de habitaciones: {request.POST.get('NumHabitaciones')}\n"
            f"Número de baños: {request.POST.get('NumBaños')}\n"
            f"Número de medio baños: {request.POST.get('NumMedBaños')}\n"
            f"Compartido: {'Sí' if request.POST.get('Compartido') == 'Si' else 'No'}"
        )

        # detalles_inmueble = {
        #     "tipo": request.POST.get('TipoInmueble'),
        #     "num_habitaciones": request.POST.get('NumHabitaciones'),
        #     "num_banos": request.POST.get('NumBaños'),
        #     "num_medio_banos": request.POST.get('NumMedBaños'),
        #     "compartido": request.POST.get('Compartido') == 'Si',
        # }

        servicios = (
            f"Luz: {'Sí' if request.POST.get('Luz') == 'on' else 'No'}\n"
            f"Agua: {'Sí' if request.POST.get('Agua') == 'on' else 'No'}\n"
            f"Internet: {'Sí' if request.POST.get('Internet') == 'on' else 'No'}\n"
            f"Vigilancia: {'Sí' if request.POST.get('vigilancia') == 'on' else 'No'}\n"
            f"Portero: {'Sí' if request.POST.get('Portero') == 'on' else 'No'}\n"
            f"Limpieza: {'Sí' if request.POST.get('Limpieza') == 'on' else 'No'}\n"
            f"Gym: {'Sí' if request.POST.get('GYM') == 'on' else 'No'}\n"
            f"Elevador: {'Sí' if request.POST.get('Elevador') == 'on' else 'No'}\n"
            f"Lavandería: {'Sí' if request.POST.get('Lavanderia') == 'on' else 'No'}\n"
            f"Entrada Propia: {'Sí' if request.POST.get('Entrada-Propia') == 'on' else 'No'}\n"
            f"Mascotas: {'Sí' if request.POST.get('Mascotas') == 'on' else 'No'}\n"
            f"Gas: {'Sí' if request.POST.get('Gas') == 'on' else 'No'}"
        )

        # servicios = {
        #     "Luz": request.POST.get("Luz") == "on",
        #     "Agua": request.POST.get("Agua") == "on",
        #     "Internet": request.POST.get("Internet") == "on",
        #     "Vigilancia": request.POST.get("vigilancia") == "on",
        #     "Portero": request.POST.get("Portero") == "on",
        #     "Limpieza": request.POST.get("Limpieza") == "on",
        #     "GYM": request.POST.get("GYM") == "on",
        #     "Elevador": request.POST.get("Elevador") == "on",
        #     "Lavandería": request.POST.get("Lavanderia") == "on",
        #     "Entrada Propia": request.POST.get("Entrada-Propia") == "on",
        #     "Mascotas": request.POST.get("Mascotas") == "on",
        #     "Gas": request.POST.get("Gas") == "on",
        # }

        detalles_inmueble_compartido = (
            f"Visitas: {request.POST.get('visitas')}\n"
            f"Número Máximo de Personas: {request.POST.get('NumPersonasMax')}\n"
            f"Género: {request.POST.get('Genero')}"
        )

        # detalles_inmueble_compartido = {
        #     "visitas": request.POST.get('visitas'),
        #     "NumPersonasMax": request.POST.get('NumPersonasMax'),
        #     "Genero": request.POST.get('Genero'),
        # }

        areas_comunes = (
            f"Sala: {'Sí' if request.POST.get('Sala') == 'on' else 'No'}\n"
            f"Cocina: {'Sí' if request.POST.get('Cocina') == 'on' else 'No'}\n"
            f"Regadera: {'Sí' if request.POST.get('Regadera') == 'on' else 'No'}\n"
            f"Baño: {'Sí' if request.POST.get('Baño') == 'on' else 'No'}\n"
            f"Comedor: {'Sí' if request.POST.get('Comedor') == 'on' else 'No'}\n"
            f"Garage: {'Sí' if request.POST.get('Garage') == 'on' else 'No'}"
        )

        # areas_comunes = {
        #     "Sala": "on" if request.POST.get("Sala") else "off",
        #     "Cocina": "on" if request.POST.get("Cocina") else "off",
        #     "Regadera": "on" if request.POST.get("Regadera") else "off",
        #     "Baño": "on" if request.POST.get("Baño") else "off",
        #     "Comedor": "on" if request.POST.get("Comedor") else "off",
        #     "Garage": "on" if request.POST.get("Garage") else "off",
        # }

        # Recoger datos estacionamiento
        estacionamiento = (
            f"Auto: {'Sí' if request.POST.get('Auto') == 'on' else 'No'}\n"
            f"Bicicleta: {'Sí' if request.POST.get('Bicicleta') == 'on' else 'No'}\n"
            f"Moto: {'Sí' if request.POST.get('Moto') == 'on' else 'No'}\n"
            f"Scooter: {'Sí' if request.POST.get('Scooter') == 'on' else 'No'}"
        )

        # estacionamiento = {
        #     "Auto": "on" if request.POST.get("Auto") else "off",
        #     "Bicicleta": "on" if request.POST.get("Bicicleta") else "off",
        #     "Moto": "on" if request.POST.get("Moto") else "off",
        #     "Scooter": "on" if request.POST.get("Scooter") else "off",
        # }

        # Recoger los muebles
        muebles = (
            f"Locker: {'Sí' if request.POST.get('Locker') == 'on' else 'No'}\n"
            f"Closet: {'Sí' if request.POST.get('Closet') == 'on' else 'No'}\n"
            f"Cama: {'Sí' if request.POST.get('Cama') == 'on' else 'No'}\n"
            f"Escritorio: {'Sí' if request.POST.get('Escritorio') == 'on' else 'No'}\n"
            f"Silla: {'Sí' if request.POST.get('Silla') == 'on' else 'No'}"
        )

        # muebles = {
        #     "Locker": "on" if request.POST.get("Locker") else "off",
        #     "Closet": "on" if request.POST.get("Closet") else "off",
        #     "Cama": "on" if request.POST.get("Cama") else "off",
        #     "Escritorio": "on" if request.POST.get("Escritorio") else "off",
        #     "Silla": "on" if request.POST.get("Silla") else "off",
        # }

        # Recoger los electrodomésticos
        electrodomesticos = (
            f"Microondas: {'Sí' if request.POST.get('Microondas') == 'on' else 'No'}\n"
            f"Refrigerador: {'Sí' if request.POST.get('Refrigerador') == 'on' else 'No'}\n"
            f"Clima: {'Sí' if request.POST.get('Clima') == 'on' else 'No'}\n"
            f"Lavadora: {'Sí' if request.POST.get('Lavadora') == 'on' else 'No'}\n"
            f"Licuadora: {'Sí' if request.POST.get('Licuadora') == 'on' else 'No'}\n"
            f"Cafetera: {'Sí' if request.POST.get('Cafetera') == 'on' else 'No'}"
        )

        # electrodomesticos = {
        #     "Microondas": "on" if request.POST.get("Micro") else "off",
        #     "Refrigerador": "on" if request.POST.get("Refri") else "off",
        #     "Clima": "on" if request.POST.get("Clima") else "off",
        #     "Lavadora": "on" if request.POST.get("Lavadora") else "off",
        #     "Licuadora": "on" if request.POST.get("Licuadora") else "off",
        #     "Cafetera": "on" if request.POST.get("Cafetera") else "off",
        # }

        # Recoger los medios de transporte cercanos
        transporte_cercano = (
            f"Metro: {'Sí' if request.POST.get('Metro') == 'on' else 'No'}\n"
            f"Metrobus: {'Sí' if request.POST.get('Metrobus') == 'on' else 'No'}\n"
            f"Trolebus: {'Sí' if request.POST.get('Trolebus') == 'on' else 'No'}\n"
            f"RTP: {'Sí' if request.POST.get('RTP') == 'on' else 'No'}\n"
            f"Bus: {'Sí' if request.POST.get('Bus') == 'on' else 'No'}\n"
            f"Cablebus: {'Sí' if request.POST.get('Cablebus') == 'on' else 'No'}"
        )

        # transporte_cercano = {
        #     "Metro": "on" if request.POST.get("Metro") else "off",
        #     "Metrobus": "on" if request.POST.get("Metrobus") else "off",
        #     "Trolebus": "on" if request.POST.get("Metro") else "off",
        #     "RTP": "on" if request.POST.get("Metrobus") else "off",
        #     "Bus": "on" if request.POST.get("Metro") else "off",
        #     "Cablebus": "on" if request.POST.get("Metrobus") else "off",
        # }

        # Fin de la recolección de datos en JSON que debo modificar para aceptar texto simple en lugar de JSON.

        # Guardar en la base de datos
        vivienda = Vivienda(
            anfitrion=anfitrion,  # Asigna el anfitrión
            calle=calle,  # Guardamos los detalles en un JSON
            numero_exterior=numero_exterior,
            codigo_postal=codigo_postal,
            precio_renta=precio_renta,
            tipo_inmueble=tipo_inmueble,  # Guardamos el tipo de inmueble en un campo separado
            detalles_inmueble=detalles_inmueble,
            detalles_inmueble_compartido=detalles_inmueble_compartido,
            servicios=servicios,
            areas_comunes=areas_comunes,
            muebles=muebles,
            estacionamiento=estacionamiento,
            electrodomesticos=electrodomesticos,
            transporte_cercano=transporte_cercano,
        )
        vivienda.save()

        # Guardar las fotos subidas
        fotos = request.FILES.getlist('Fotos-del-Inmueble[]')
        for foto in fotos:
            ViviendaFoto.objects.create(vivienda=vivienda, imagen=foto)

        messages.success(request, "Vivienda registrada exitosamente con fotos.")

        # Redirigir a la lista de viviendas en lugar del Formulario de Inicio de Sesión
        return redirect('listar_viviendas')

        # return redirect('Inicio de Sesion')

    return render(request, 'viviendas/Registrovivienda.html')


""" Vista para Crear un Contrato.

Here is the new view crear_contrato for creating contracts, similar to the Registrovivienda view but using the Contrato 
model.

This view handles the creation of a new contract by gathering data from the form, validating the user, and saving the 
contract to the database. It also renders a template crear_contrato.html with lists of students and properties for 
selection.

Voy a validar el formulario por razones de ciberseguridad.
"""


@login_required
def crear_contrato(request):
    # Si el usuario es un estudiante, redirigirlo a la página de inicio de estudiante
    if hasattr(request.user, 'estudiante'):
        return redirect('Inicio de Estudiante')

    # Si el Anfitrión Envía el Formulario
    if request.method == 'POST':
        form = CrearContratoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Contrato creado exitosamente.")

            # Redirigir a la lista de contratos
            return redirect('gestionar_contrato')
    else:
        form = CrearContratoForm()

        # Esto renderiza el Formulario para Crear un Contrato
        return render(request, 'contratos/crear-contrato.html', {'form': form})

    # if request.method == 'POST':
    #     # Verificar que el usuario esté autenticado y que tenga un perfil de anfitrión
    #     if not request.user.is_authenticated:
    #         messages.error(request, "Necesitas iniciar sesión para crear un contrato.")
    #         return redirect('Inicio de Sesion')
    #     try:
    #         anfitrion = request.user.anfitrion  # Obtiene el anfitrión autenticado
    #         print(f"Anfitrión ID asociado al usuario autenticado: {anfitrion.id}")  # Verifica el ID del anfitrión
    #     except Anfitrion.DoesNotExist:
    #         messages.error(request,
    #                        "No tienes un perfil de anfitrión. Por favor, regístrate como anfitrión primero."
    #                        )
    #         return redirect('Registro de Usuario')
    #
    #     # Recibe los datos del formulario
    #     estudiante_id = request.POST.get('estudiante_id')
    #     vivienda_id = request.POST.get('vivienda_id')
    #     precio_renta = request.POST.get('precio_renta')
    #     fecha_inicio = request.POST.get('fecha_inicio')
    #     fecha_fin = request.POST.get('fecha_fin')
    #
    #     # Obtener las instancias de Estudiante y Vivienda
    #     estudiante = get_object_or_404(Estudiante, id=estudiante_id)
    #     vivienda = get_object_or_404(Vivienda, id=vivienda_id)
    #
    #     # Crear el contrato
    #     contrato = Contrato(
    #         estudiante=estudiante,
    #         vivienda=vivienda,
    #         anfitrion=anfitrion,
    #         precio_renta=precio_renta,
    #         fecha_inicio=fecha_inicio,
    #         fecha_fin=fecha_fin,
    #     )
    #     contrato.save()
    #
    #     messages.success(request, "Contrato creado exitosamente.")
    #     return redirect('listar_contratos')  # Redirigir a la lista de contratos
    #
    # # Esto renderiza el formulario para crear un contrato
    # else:
    #
    #     estudiantes = Estudiante.objects.all()
    #     viviendas = Vivienda.objects.filter(anfitrion=request.user.anfitrion)
    #
    #     return render(request, 'crear-contrato.html', {
    #         'estudiantes': estudiantes, 'viviendas': viviendas
    #     })


""" Vista para Editar un Contrato.

Here is the editar_contrato() view, which allows you to edit a selected contract from the Contrato model in a similar 
way to how the editar_vivienda() view edits an instance of an apartment from the Vivienda model.

This view checks if the user has permission to edit the contract, processes the form submission, and renders the form 
for editing the contract.
"""


@login_required
def editar_contrato(request, contrato_id):
    # Esto verifica que el contrato exista, y agarra la instancia del contrato del modelo de Contrato
    contrato = get_object_or_404(Contrato, id=contrato_id)

    # Verificar permisos: solo el anfitrión asociado puede editar un contrato
    if request.user.anfitrion != contrato.anfitrion:
        messages.error(request, "No tienes permiso para editar este contrato.")

        # Si el usuario es un estudiante, se le redirige a la página de inicio para estudiantes
        return redirect('Inicio de Estudiante')

    # Si el Anfitrión Envía el Formulario
    if request.method == 'POST':
        form = EditarContratoForm(request.POST, request.FILES, instance=contrato)

        # Esto valida el formulario
        if form.is_valid():
            # Esto actualiza el contrato seleccionado en la base de datos
            form.save()
            messages.success(request, "Contrato actualizado exitosamente.")

            # Te redirige a la lista de contratos
            return redirect('gestionar_contrato')

    # Esto renderiza el Formulario para Editar un Contrato
    else:
        form = EditarContratoForm(instance=contrato)

        return render(request, 'contratos/editar_contrato.html', {'form': form})


""" Vista para Eliminar un Contrato.

Here is the eliminar_contrato() view, which deletes records from the Contrato model in a similar way to how the 
eliminar_vivienda() view deletes instances of the Vivienda model.

This view checks if the user has permission to delete the contract, processes the deletion, and renders a 
confirmation page before deleting the contract.

Esta vista debería ser como una API. No debe renderizar ninguna página cuando el usuario entre aquí.
"""


@login_required
def eliminar_contrato(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id)

    # Verificar permisos: solo el anfitrión asociado puede eliminar un contrato
    if request.user.anfitrion != contrato.anfitrion:
        messages.error(request, "No tienes permiso para eliminar este contrato.")
        return redirect('gestionar_contrato')

    if request.method == 'POST':
        contrato.delete()
        messages.success(request, "Contrato eliminado exitosamente.")
        return redirect('gestionar_contrato')  # Redirige después de la eliminación

    else:
        # Esto le pregunta al usuario si realmente quiere borrar el Contrato seleccionado
        return render(request, 'contratos/confirmar-eliminar-contrato.html', {'contrato': contrato})


""" Formulario de Inicio de Sesión.

Aquí es donde debo redirigir al usuario si intenta meterse en una página en donde se requiere estar autenticado, o si
inserta unas credenciales erróneas al intentar iniciar sesión.

Corregí un bug el cual te mostraba un mensaje de error de Django amarillo si intentabas iniciar sesión con un usuario
que no existía o con credenciales incorrectas.
"""


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if hasattr(user, 'estudiante'):
                return redirect('Inicio de Estudiante')
            elif hasattr(user, 'anfitrion'):
                return redirect('Inicio de Anfitrion')
            else:
                messages.error(request, "No se pudo determinar el rol del usuario.")

                # Esto redirige al usuario a esta misma página
                return render(request, 'inicio/InicioSesion.html')
                # return redirect('login')
        else:
            messages.error(request, "Nombre de usuario o contraseña incorrectos.")

            # Esto redirige al usuario a esta misma página
            return render(request, 'inicio/InicioSesion.html')
            # return redirect('login')

    # Esto se ejecuta si el método de la petición es GET, para así mostrar el formulario de inicio de sesión
    else:
        return render(request, 'inicio/InicioSesion.html')


def logout_view(request):
    logout(request)
    return redirect('Inicio')


@login_required
def InicioAnfitrion(request):
    return render(request, 'inicio/InicioAnfitrion.html')


@login_required
def InicioEstudiante(request):
    return render(request, 'inicio/InicioEstudiante.html')


def Inicio(request):
    return render(request, 'inicio/Inicio.html')
