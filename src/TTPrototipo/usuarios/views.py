from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from .models import Estudiante, Anfitrion, Vivienda, ViviendaFoto, Contrato, FotoEstadoVivienda
from django.template.loader import render_to_string
from django.http import FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from weasyprint import HTML
from .forms import FotoEstadoViviendaForm, ViviendaForm, CrearContratoForm
import logging
from django.conf import settings

# Importar el módulo ast para convertir un string en un diccionario para las Viviendas
import ast

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
    return render(request, 'listar_viviendas.html', {'viviendas': viviendas})


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

    return render(request, 'editar_vivienda.html', {'form': form})


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

    return render(request, 'confirmar_eliminar_vivienda.html', {'vivienda': vivienda})


""" Vista para ver la Lista de Contratos de una Anfitrión, y para Modificar o Gestionar un Contrato.

Esta vista se usa para 2 páginas distintas: para ver la lista de Contratos, y para Editar un Contrato.
"""


@login_required
def gestionar_contrato(request, contrato_id=None):
    """
    Vista general para gestionar contratos.
    """
    usuario = request.user

    # Caso 1: Sin contrato_id
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

            return render(request, 'seleccionar_vivienda.html', {'viviendas': viviendas_disponibles})

        if hasattr(usuario, 'anfitrion'):
            anfitrion = usuario.anfitrion
            contratos = Contrato.objects.filter(anfitrion=anfitrion)
            return render(request, 'listar_contratos_anfitrion.html', {'contratos': contratos})

        return HttpResponseForbidden("No tienes permisos para acceder a esta página.")

    # Caso 2: Con contrato_id
    contrato = get_object_or_404(Contrato, id=contrato_id)

    if hasattr(usuario, 'anfitrion') and contrato.anfitrion.user == usuario:
        fotos = contrato.fotos_estado.all()
        form = FotoEstadoViviendaForm()

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

        if request.method == 'POST' and 'firmar' in request.POST:
            if not contrato.fotos_estado.exists():
                messages.error(request, "Debes subir al menos una foto antes de firmar el contrato.")
                return redirect('gestionar_contrato', contrato_id=contrato.id)

            contrato.firma_anfitrion = contrato.generar_firma(usuario)
            contrato.save()
            messages.success(request, "Has firmado el contrato.")

        return render(request, 'gestionar_contrato_anfitrion.html', {
            'contrato': contrato,
            'fotos': fotos,
            'form': form,
        })

    if hasattr(usuario, 'estudiante') and contrato.estudiante.user == usuario:
        fotos = contrato.fotos_estado.all()
        form = FotoEstadoViviendaForm()

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

        if request.method == 'POST' and 'firmar' in request.POST:
            if not contrato.fotos_estado.exists():
                messages.error(request, "Debes subir al menos una foto antes de firmar el contrato.")
                return redirect('gestionar_contrato', contrato_id=contrato.id)

            contrato.firma_estudiante = contrato.generar_firma(usuario)
            contrato.save()
            messages.success(request, "Has firmado el contrato.")

        return render(request, 'gestionar_contrato_estudiante.html', {
            'contrato': contrato,
            'fotos': fotos,
            'form': form,
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

    return render(request, 'seleccionar_vivienda.html', {'viviendas': viviendas})


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

"""


def generar_contrato_pdf(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id)

    if request.method == "POST":
        ciudad = request.POST.get("ciudad", "Ciudad de México")  # Valor por defecto
        fecha = request.POST.get("fecha", "")

        # BOOKMARK

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

        html_content = render_to_string("contrato.html", {
            "contrato": contrato,
            "ciudad": ciudad,
            "fecha": fecha,
            "tipo_inmueble": tipo_inmueble,  # DEBUGGEO: desactivare esto para ver si puedo generar el contrato
            "ubicacion": ubicacion,
            "nombre_arrendador": nombre_arrendador,
            "nombre_arrendatario": nombre_arrendatario,
            "fotos": fotos_urls,
        })

        pdf = HTML(string=html_content).write_pdf()
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="Contrato_{contrato.id}.pdf"'
        return response

    # Renderizar el formulario para generar el contrato
    return render(request, "formulario_contrato.html", {"contrato": contrato})


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

    return render(request, 'Registrovivienda.html')


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
        return render(request, 'crear-contrato.html', {'form': form})

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
                return render(request, 'InicioSesion.html')
                # return redirect('login')
        else:
            messages.error(request, "Nombre de usuario o contraseña incorrectos.")

            # Esto redirige al usuario a esta misma página
            return render(request, 'InicioSesion.html')
            # return redirect('login')

    # Esto se ejecuta si el método de la petición es GET, para así mostrar el formulario de inicio de sesión
    else:
        return render(request, 'InicioSesion.html')


def logout_view(request):
    logout(request)
    return redirect('Inicio')


@login_required
def InicioAnfitrion(request):
    return render(request, 'InicioAnfitrion.html')


@login_required
def InicioEstudiante(request):
    return render(request, 'InicioEstudiante.html')


def Inicio(request):
    return render(request, 'Inicio.html')
