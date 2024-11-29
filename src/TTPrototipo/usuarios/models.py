from django.db import models
from django.contrib.auth.models import User
import hashlib
from datetime import date

# Esto me deja usar el campo JSignatureField en los modelos para Guardar Firmas Dibujadas.
# Fuente: https://github.com/fle/django-jsignature.
from jsignature.fields import JSignatureField


class Estudiante(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nombre = models.CharField(max_length=100, default="Estudiante")
    contraseña = models.CharField(max_length=100, default="12345678")
    correo = models.EmailField(unique=True, default="estudiante@gmail.com")
    celular = models.CharField(max_length=15, default="5500000000")
    escuela = models.CharField(max_length=100)
    presupuesto = models.DecimalField(max_digits=10, decimal_places=2, default="2000.00")
    vivienda_contratada = models.OneToOneField('Vivienda', on_delete=models.SET_NULL, null=True, blank=True,
                                               related_name="estudiante_contratado")

    def __str__(self):
        return self.nombre


""" Modelo de Anfitrión.

Este modelo representa a un anfitrión, que es un usuario que ofrece una vivienda en renta a estudiantes.
    
Le voy a cambiar el __str__ para que muestre el nombre del anfitrión en lugar de "Anfitrion Object(numero)". 
"""


class Anfitrion(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nombre = models.CharField(max_length=100, default="Anfitrion")
    contraseña = models.CharField(max_length=100, default="12345678")
    correo = models.EmailField(unique=True, default="anfitrion@gmail.com")
    celular = models.CharField(max_length=10, default="5500000000")
    viviendas_registradas = models.IntegerField(default=1)

    # Esto hace que cada registro de Anfitrión muestre su nombre en lugar de "Anfitrión Object(numero)"
    def __str__(self):
        return self.nombre


""" Modelo de Vivienda.

Tengo que modificar este modelo para que todos los campos acepten texto simple en lugar de JSON. Creo que TextField
sería el tipo de dato más adecuado para la mayoría de los campos que usaban JSON.

Creé un nuevo campo llamado "tipo de inmueble" para que el usuario pueda seleccionar si es un departamento, casa, etc.
Esto será usado al generar el PDF con el contrato para evitar un bug que no me dejaba generar el contrato.
"""


class Vivienda(models.Model):
    id = models.AutoField(primary_key=True)
    anfitrion = models.ForeignKey(Anfitrion, on_delete=models.CASCADE)
    calle = models.CharField(max_length=255, default="Sin Calle")
    numero_exterior = models.CharField(max_length=10, default="S/N")
    codigo_postal = models.CharField(max_length=5, default="07000")
    precio_renta = models.DecimalField(max_digits=10, decimal_places=2, default=2000.00)

    # Tipo de inmueble: Departamento, Casa, Habitación, etc.
    tipo_inmueble = models.CharField(max_length=150, default="Departamento")

    # Estos campos debo modificarlos para que acepten texto simple en lugar de JSON
    detalles_inmueble = models.TextField()  # Almacena tipo, num_habitaciones, num_banos, etc.
    servicios = models.TextField()  # Para almacenar los servicios en un diccionario
    detalles_inmueble_compartido = models.TextField()  # Para almacenar detalles si es compartido
    areas_comunes = models.TextField()  # Áreas comunes como Sala, Cocina, Baño, etc.
    estacionamiento = models.TextField()  # Areas de estacionamiento
    muebles = models.TextField()  # Muebles como Cama, Closet, Escritorio, etc.
    electrodomesticos = models.TextField()  # Electrodomésticos como Microondas, Refri, Lavadora, etc.
    transporte_cercano = models.TextField()  # Transporte como Metro, Metrobus, RTP, etc.

    # detalles_inmueble = models.JSONField(default=dict)  # Almacena tipo, num_habitaciones, num_banos, etc.
    # servicios = models.JSONField(default=dict)  # Para almacenar los servicios en un diccionario
    # detalles_inmueble_compartido = models.JSONField(default=dict)  # Para almacenar detalles si es compartido
    # areas_comunes = models.JSONField(default=dict)  # Áreas comunes como Sala, Cocina, Baño, etc.
    # estacionamiento = models.JSONField(default=dict)  # Areas de estacionamiento
    # muebles = models.JSONField(default=dict)  # Muebles como Cama, Closet, Escritorio, etc.
    # electrodomesticos = models.JSONField(default=dict)  # Electrodomésticos como Microondas, Refri, Lavadora, etc.
    # transporte_cercano = models.JSONField(default=dict)  # Transporte como Metro, Metrobus, RTP, etc.

    # Fin de los campos que debo modificar para aceptar texto simple en lugar de JSON

    # fotos = models.ImageField(upload_to='viviendas_fotos/', blank=True, null=True)

    # def __str__(self):
    # return f"{self.detalles_inmueble.get('tipo', 'Inmueble')} en {self.calle}, {self.codigo_postal}"

    def __str__(self):
        return f"{self.calle}, {self.numero_exterior} ({self.precio_renta} MXN)"


class ViviendaFoto(models.Model):
    vivienda = models.ForeignKey(Vivienda, on_delete=models.CASCADE, related_name="fotos")
    imagen = models.ImageField(upload_to="viviendas_fotos/")

    def __str__(self):
        return f"Foto de {self.vivienda.calle}"


""" Modelo de Contrato.

If you don't have the contratos/default.pdf file, it would be better to leave the archivo_contrato field as optional. 
You can set null=True and blank=True to allow the field to be empty.

Los archivos que se deben adjuntar deben ser obligatoriamente PDFs. de lo contrario, te generará PDFs dañados 
al descargar el documento, y no podrás abrir esos contratos.

Aquí es que están las funciones para cancelar un contrato, y la que verifica si puede cancelarse.

Tendré que modificar el campo de “firma” para que acepte archivos o imagenes (ImageField o FileField), y le meteré la 
firma generada por Jsignature cuando el usuario la dibuje y clique en “Firmar” en la pagina de “gestionar contratos”.
Esto lo tengo que hacer tanto para el estudiante como para el anfitrión. 
"""


class Contrato(models.Model):
    id = models.AutoField(primary_key=True)
    estudiante = models.OneToOneField(Estudiante, on_delete=models.CASCADE, related_name="contrato")
    vivienda = models.OneToOneField(Vivienda, on_delete=models.CASCADE, related_name="contrato")
    anfitrion = models.ForeignKey(Anfitrion, on_delete=models.CASCADE, related_name="contratos")
    precio_renta = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Archivo del Contrato. Lo deje como opcional para evitar bugs.
    archivo_contrato = models.FileField(upload_to="contratos/", null=True, blank=True)

    # archivo_contrato = models.FileField(upload_to="contratos/", null=True, blank=True)

    firmado = models.BooleanField(default=False)

    # Firma digital del estudiante (OPCIONAL)
    firma_estudiante = models.ImageField(upload_to="firmas/firmas_estudiantes/", null=True, blank=True)

    # firma_estudiante = models.TextField(null=True, blank=True)

    # Firma del anfitrión (OPCIONAL)
    firma_anfitrion = models.ImageField(upload_to="firmas/firmas_anfitriones/", null=True, blank=True)

    # firma_anfitrion = models.TextField(null=True, blank=True)  # Firma digital del anfitrión

    fotos_subidas_anfitrion = models.BooleanField(default=False)
    fotos_subidas_estudiante = models.BooleanField(default=False)
    cancelado = models.BooleanField(default=False)
    fecha_inicio = models.DateField(null=False, blank=False, default=date.today)
    fecha_fin = models.DateField(null=True, blank=True)

    # Función para verificar si el contrato puede cancelarse
    def puede_cancelarse(self):
        """Verifica si el contrato puede ser cancelado"""
        return not self.firmado  # Sólo se puede cancelar si no está firmado

    # Función para cancelar un contrato
    def cancelar_contrato(self):
        """Marca el contrato como cancelado y libera la vivienda y el estudiante"""
        if self.puede_cancelarse():
            self.cancelado = True
            self.estudiante.vivienda_contratada = None
            self.estudiante.save()
            self.save()
            return True
        return False

    def generar_firma(self, usuario):
        """Genera un hash único como firma digital"""
        data = f"{self.id}-{usuario.id}-{self.fecha_inicio}-{self.fecha_fin}-{self.precio_renta}"
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def save(self, *args, **kwargs):
        if self.firma_estudiante and self.firma_anfitrion:
            self.firmado = True
        super(Contrato, self).save(*args, **kwargs)

    def contrato_firmado(self):
        """Verifica si ambas partes han firmado"""
        return bool(self.firma_estudiante and self.firma_anfitrion)

    def puede_firmarse(self):
        """Verifica si el contrato está listo para ser firmado"""
        return self.fotos_subidas_anfitrion  # Deben subirse las fotos del anfitrión obligatoriamente

    def finalizar_contrato(self):
        """Finaliza el contrato y libera la vivienda y el estudiante."""
        self.activo = False
        self.fecha_fin = models.DateField(auto_now=True)  # Registra la fecha actual como fin
        self.estudiante.vivienda_contratada = None
        self.estudiante.save()  # Guarda los cambios en el estudiante
        self.save()  # Guarda los cambios en el contrato

    def __str__(self):
        return f"Contrato {self.id}: Estudiante {self.estudiante.nombre} - Vivienda {self.vivienda.calle}"


""" Fotos del Estado de la Vivienda al momento de firmar el contrato. Aquí se meten las Fotos de un Contrato al Editar
un Contrato.

Quiero agregar el ID del registro de la foto en la lista de entradas usando un __str__ personalizado, ya que si
un solo contrato tiene varias fotos, todas tendrán el mismo nombre en la lista de entradas en el panel de admin de +
Django.
"""


class FotoEstadoVivienda(models.Model):
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name="fotos_estado")
    imagen = models.ImageField(upload_to="contratos/fotos_vivienda/")

    def __str__(self):
        return f"ID: {self.id} - Foto para contrato {self.contrato.id}"


""" Modelo de Prueba de Firmas Digitales usando Django JSignature.

El JSignature Field NO se puede renderizar en el panel de administración de Django, pero sí se puede guardar en
este modelo.

Dejame ver si puedo guardar la firma como una imagen y/o como un archivo. Haré estos 2 campos opcionales por los 
momentos.

NO USAR. ESTO ES SOLO DE PRUEBA.
"""


class SignatureModel(models.Model):
    signature = JSignatureField()

    image = models.ImageField(upload_to='firmas/imagenes/', null=True, blank=True)
    file = models.FileField(upload_to='firmas/archivos/', null=True, blank=True)
