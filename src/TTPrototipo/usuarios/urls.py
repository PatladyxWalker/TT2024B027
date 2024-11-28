from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
                  path('', views.Inicio, name='Inicio'),
                  path('Inicio/', views.Inicio, name='Inicio'),
                  path('InicioSesion/', views.login_view, name='Inicio de Sesion'),
                  path('RegistroUsuario/', views.RegistroUsuario, name='Registro de Usuario'),
                  path('InicioEstudiante/', views.InicioEstudiante, name='Inicio de Estudiante'),
                  path('InicioAnfitrion/', views.InicioAnfitrion, name='Inicio de Anfitrion'),
                  path('Registrovivienda/', views.Registrovivienda, name='Registro de vivienda'),
                  path('logout/', views.logout_view, name='logout'),

                  # URLs de los Contratos.
                  # Para Crear un Contrato.
                  path('contrato/crear/', views.crear_contrato, name='crear_contrato'),

                  # Esto me permite descargar el contrato seleccionado en formato PDF
                  path('contrato/descargar/<int:contrato_id>/', views.descargar_contrato, name='descargar_contrato'),

                  # Para firmar el contrato seleccionado. Creo que es una API.
                  path('contrato/firmar/<int:contrato_id>/', views.firmar_contrato, name='firmar_contrato'),
                  path('contrato/generar-pdf/<int:contrato_id>/', views.generar_contrato_pdf,
                       name='generar_contrato_pdf'),  # Para convertir el Contrato seleccionado a un archivo PDF

                  # Para subir fotos del estado de la vivienda al Contrato Seleccionado
                  path('contrato/subir-fotos/<int:contrato_id>/', views.subir_fotos, name='subir_fotos'),

                  # Para gestionar el contrato seleccionado
                  path('contrato/gestionar/<int:contrato_id>/', views.gestionar_contrato, name='gestionar_contrato'),

                  # Muestra la Lista de Todos los Contratos. TIENE EL MISMO VIEW QUE EL ANTERIOR.
                  path('contrato/gestionar/', views.gestionar_contrato, name='gestionar_contrato'),

                  # Para cancelar el contrato seleccionado, si el contrato no está firmado.
                  path('contrato/cancelar/<int:contrato_id>/', views.cancelar_contrato, name='cancelar_contrato'),

                  # Para Editar un Contrato
                  path('contrato/editar/<int:contrato_id>/', views.editar_contrato, name='editar_contrato'),

                  # Para Eliminar un Contrato
                  path('contrato/eliminar/<int:contrato_id>/', views.eliminar_contrato, name='eliminar_contrato'),
                  # Fin de las URLs de los Contratos.

                  path('viviendas/', views.listar_viviendas, name='listar_viviendas'),

                  # Para crear una Vivienda
                  path('viviendas/registro/', views.Registrovivienda, name='Registro de vivienda'),

                  # Para Editar una Vivienda
                  path('viviendas/editar/<int:vivienda_id>/', views.editar_vivienda, name='editar_vivienda'),
                  path('viviendas/eliminar/<int:vivienda_id>/', views.eliminar_vivienda, name='eliminar_vivienda'),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
