from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from .models import Estudiante, Anfitrion, Vivienda,ViviendaFoto,Contrato,FotoEstadoVivienda
from django.template.loader import render_to_string
from django.http import FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from weasyprint import HTML
from .forms import FotoEstadoViviendaForm, ViviendaForm
import logging
from django.conf import settings

@login_required
def listar_viviendas(request):
    if not hasattr(request.user, 'anfitrion'):
        messages.error(request, "No tienes permiso para acceder a esta página.")
        return redirect('Inicio de Sesion')

    anfitrion = request.user.anfitrion
    viviendas = Vivienda.objects.filter(anfitrion=anfitrion)
    return render(request, 'listar_viviendas.html', {'viviendas': viviendas})

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
def generar_contrato_pdf(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id)

    if request.method == "POST":
        ciudad = request.POST.get("ciudad", "Ciudad de México")  # Valor por defecto
        fecha = request.POST.get("fecha", "")
        tipo_inmueble = contrato.vivienda.detalles_inmueble.get("tipo", "Inmueble")
        ubicacion = f"{contrato.vivienda.calle}, {contrato.vivienda.numero_exterior}, {contrato.vivienda.codigo_postal} CDMX"
        nombre_arrendador = contrato.anfitrion.nombre
        nombre_arrendatario = contrato.estudiante.nombre

        fotos = contrato.fotos_estado.all()
        fotos_urls = [request.build_absolute_uri(settings.MEDIA_URL + foto.imagen.name) for foto in fotos]

        html_content = render_to_string("contrato.html", {
            "contrato": contrato,
            "ciudad": ciudad,
            "fecha": fecha,
            "tipo_inmueble": tipo_inmueble,
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

# Descargar Contrato Firmado
def descargar_contrato(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id, firmado=True)
    return FileResponse(contrato.archivo_contrato.open(), as_attachment=True, filename=f"Contrato_{contrato.id}.pdf")

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

        #anfitrion = get_object_or_404(Anfitrion, correo=request.user.email)
        #anfitrion = request.user.anfitrion  # Obtiene el anfitrión autenticado

        # Recibe los datos del formulario
        calle = request.POST.get('Ingresar-calle')
        numero_exterior = request.POST.get('NumExt')
        codigo_postal = request.POST.get('CP')
        precio_renta = request.POST.get('Renta')

        # Servicios en JSON

        detalles_inmueble = {
                "tipo": request.POST.get('TipoInmueble'),
                "num_habitaciones": request.POST.get('NumHabitaciones'),
                "num_banos": request.POST.get('NumBaños'),
                "num_medio_banos": request.POST.get('NumMedBaños'),
                "compartido": request.POST.get('Compartido') == 'Si',
            }

        servicios = {
                "Luz": request.POST.get("Luz") == "on",
                "Agua": request.POST.get("Agua") == "on",
                "Internet": request.POST.get("Internet") == "on",
                "Vigilancia": request.POST.get("vigilancia") == "on",
                "Portero": request.POST.get("Portero") == "on",
                "Limpieza": request.POST.get("Limpieza") == "on",
                "GYM": request.POST.get("GYM") == "on",
                "Elevador": request.POST.get("Elevador") == "on",
                "Lavanderia": request.POST.get("Lavanderia") == "on",
                "Entrada Propia": request.POST.get("Entrada-Propia") == "on",
                "Mascotas": request.POST.get("Mascotas") == "on",
                "Gas": request.POST.get("Gas") == "on",
            }

        detalles_inmueble_compartido = {
                "visitas": request.POST.get('visitas'),
                "NumPersonasMax": request.POST.get('NumPersonasMax'),
                "Genero": request.POST.get('Genero'),
            }

        areas_comunes = {
                "Sala": "on" if request.POST.get("Sala") else "off",
                "Cocina": "on" if request.POST.get("Cocina") else "off",
                "Regadera": "on" if request.POST.get("Regadera") else "off",
                "Baño": "on" if request.POST.get("Baño") else "off",
                "Comedor": "on" if request.POST.get("Comedor") else "off",
                "Garage": "on" if request.POST.get("Garage") else "off",
            }

        # Recoger datos estacionamiento
        estacionamiento = {
                "Auto": "on" if request.POST.get("Auto") else "off",
                "Bicicleta": "on" if request.POST.get("Bicicleta") else "off",
                "Moto": "on" if request.POST.get("Moto") else "off",
                "Scooter": "on" if request.POST.get("Scooter") else "off",
            }

        # Recoger los muebles
        muebles = {
                "Locker": "on" if request.POST.get("Locker") else "off",
                "Closet": "on" if request.POST.get("Closet") else "off",
                "Cama": "on" if request.POST.get("Cama") else "off",
                "Escritorio": "on" if request.POST.get("Escritorio") else "off",
                "Silla": "on" if request.POST.get("Silla") else "off",
            }

        # Recoger los electrodomésticos
        electrodomesticos = {
                "Microondas": "on" if request.POST.get("Micro") else "off",
                "Refrigerador": "on" if request.POST.get("Refri") else "off",
                "Clima": "on" if request.POST.get("Micro") else "off",
                "Lavadora": "on" if request.POST.get("Refri") else "off",
                "Licuadora": "on" if request.POST.get("Micro") else "off",
                "Cafetera": "on" if request.POST.get("Refri") else "off",
            }

        # Recoger los medios de transporte cercanos
        transporte_cercano = {
                "Metro": "on" if request.POST.get("Metro") else "off",
                "Metrobus": "on" if request.POST.get("Metrobus") else "off",
                "Trolebus": "on" if request.POST.get("Metro") else "off",
                "RTP": "on" if request.POST.get("Metrobus") else "off",
                "Bus": "on" if request.POST.get("Metro") else "off",
                "Cablebus": "on" if request.POST.get("Metrobus") else "off",
            }

        # Guardar en la base de datos
        vivienda = Vivienda(
            anfitrion=anfitrion,  # Asigna el anfitrión
            calle=calle,# Guardamos los detalles en un JSON
            numero_exterior=numero_exterior,
            codigo_postal=codigo_postal,
            precio_renta=precio_renta,
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

        return redirect('Inicio de Sesion')
    return render(request, 'Registrovivienda.html')


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


