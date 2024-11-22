from django.db import models
from django.contrib.auth.models import User
import hashlib
from datetime import date

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

class Anfitrion(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nombre = models.CharField(max_length=100, default="Anfitrion")
    contraseña = models.CharField(max_length=100, default="12345678")
    correo = models.EmailField(unique=True, default="anfitrion@gmail.com")
    celular = models.CharField(max_length=10, default="5500000000")
    viviendas_registradas = models.IntegerField(default=1)

class Vivienda(models.Model):
    id = models.AutoField(primary_key=True)
    anfitrion = models.ForeignKey(Anfitrion, on_delete=models.CASCADE)
    calle = models.CharField(max_length=255, default="Sin Calle")
    numero_exterior = models.CharField(max_length=10, default="S/N")
    codigo_postal = models.CharField(max_length=5, default="07000")
    precio_renta = models.DecimalField(max_digits=10, decimal_places=2, default=2000.00)

    detalles_inmueble = models.JSONField(default=dict)  # Almacena tipo, num_habitaciones, num_banos, etc.
    servicios = models.JSONField(default=dict)  # Para almacenar los servicios en un diccionario
    detalles_inmueble_compartido = models.JSONField(default=dict) #Para almacenar detalles si es compartido
    areas_comunes = models.JSONField(default=dict)  # Áreas comunes como Sala, Cocina, Baño, etc.
    estacionamiento = models.JSONField(default=dict) #Areas de estacionamiento
    muebles = models.JSONField(default=dict)  # Muebles como Cama, Closet, Escritorio, etc.
    electrodomesticos = models.JSONField(default=dict)  # Electrodomésticos como Microondas, Refri, Lavadora, etc.
    transporte_cercano = models.JSONField(default=dict)  # Transporte como Metro, Metrobus, RTP, etc.
    #fotos = models.ImageField(upload_to='viviendas_fotos/', blank=True, null=True)

    #def __str__(self):
        #return f"{self.detalles_inmueble.get('tipo', 'Inmueble')} en {self.calle}, {self.codigo_postal}"

    def __str__(self):
        return f"{self.calle}, {self.numero_exterior} ({self.precio_renta} MXN)"

class ViviendaFoto(models.Model):
    vivienda = models.ForeignKey(Vivienda, on_delete=models.CASCADE, related_name="fotos")
    imagen = models.ImageField(upload_to="viviendas_fotos/")

    def __str__(self):
        return f"Foto de {self.vivienda.calle}"

class Contrato(models.Model):
    id = models.AutoField(primary_key=True)
    estudiante = models.OneToOneField(Estudiante, on_delete=models.CASCADE, related_name="contrato")
    vivienda = models.OneToOneField(Vivienda, on_delete=models.CASCADE, related_name="contrato")
    anfitrion = models.ForeignKey(Anfitrion, on_delete=models.CASCADE, related_name="contratos")
    precio_renta = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    archivo_contrato = models.FileField(upload_to="contratos/", null=True, blank=True)
    firmado = models.BooleanField(default=False)
    firma_estudiante = models.TextField(null=True, blank=True)  # Firma digital del estudiante
    firma_anfitrion = models.TextField(null=True, blank=True)   # Firma digital del anfitrión
    fotos_subidas_anfitrion = models.BooleanField(default=False)
    fotos_subidas_estudiante = models.BooleanField(default=False)
    cancelado = models.BooleanField(default=False)
    fecha_inicio = models.DateField(null=False, blank=False, default=date.today)
    fecha_fin = models.DateField(null=True, blank=True)

    def puede_cancelarse(self):
        """Verifica si el contrato puede ser cancelado"""
        return not self.firmado  # Sólo se puede cancelar si no está firmado

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

class FotoEstadoVivienda(models.Model):
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name="fotos_estado")
    imagen = models.ImageField(upload_to="contratos/fotos_vivienda/")

    def __str__(self):
        return f"Foto para contrato {self.contrato.id}"

