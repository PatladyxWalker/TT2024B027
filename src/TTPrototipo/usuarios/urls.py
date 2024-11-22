from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.Inicio, name = 'Inicio'),
    path('Inicio/', views.Inicio, name = 'Inicio'),
    path('InicioSesion/', views.login_view, name = 'Inicio de Sesion'),
    path('RegistroUsuario/', views.RegistroUsuario, name = 'Registro de Usuario'),
    path('InicioEstudiante/', views.InicioEstudiante, name = 'Inicio de Estudiante'),
    path('InicioAnfitrion/', views.InicioAnfitrion, name = 'Inicio de Anfitrion'),
    path('Registrovivienda/', views.Registrovivienda, name = 'Registro de vivienda'),
    path('logout/', views.logout_view, name='logout'),
    path('contrato/descargar/<int:contrato_id>/', views.descargar_contrato, name='descargar_contrato'),
    path('contrato/firmar/<int:contrato_id>/', views.firmar_contrato, name='firmar_contrato'),
    path('contrato/generar-pdf/<int:contrato_id>/', views.generar_contrato_pdf, name='generar_contrato_pdf'),
    path('contrato/subir-fotos/<int:contrato_id>/', views.subir_fotos, name='subir_fotos'),
    path('contrato/gestionar/<int:contrato_id>/', views.gestionar_contrato, name='gestionar_contrato'),
    path('contrato/gestionar/', views.gestionar_contrato, name='gestionar_contrato'),  # Para crear un nuevo contrato
    path('contrato/cancelar/<int:contrato_id>/', views.cancelar_contrato, name='cancelar_contrato'),
    path('viviendas/', views.listar_viviendas, name='listar_viviendas'),
    path('viviendas/registro/', views.Registrovivienda, name='Registro de vivienda'),
    path('viviendas/editar/<int:vivienda_id>/', views.editar_vivienda, name='editar_vivienda'),
    path('viviendas/eliminar/<int:vivienda_id>/', views.eliminar_vivienda, name='eliminar_vivienda'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)