# Web App hecha en Django de alquiler de viviendas


## Instrucciones de uso

### Instalar todos los módulos pip del requirements.txt

Instala todos los paquetes en el requirements.txt usando el siguiente comando:

```bash
pip install -r requirements.txt
```

### Paquete python-dotenv para usar el SECRET KEY

Se agregó un archivo .env para almacenar la SECRET KEY de Django, y la variable DEBUG del settings.py. Se hizo esto por razones de ciberseguridad, ya que no es seguro tener la SECRET KEY en un archivo de código fuente.

Para poder hacer funcionar la web app de ahora en adelante, necesitas tener instalado el paquete pip de "python-dotenv", y tener un archivo .env con las variables "SECRET KEY" y "DEBUG". De lo contrario, la web app no te funcionará.

Necesitas agregar "True" o "False" para la variable "Debug", y una clave de 50 caracteres para el Secret Key.

Tienes que instalar el paquete pip de python-dotenv. La versión que debes usar es el python-dotenv 1.0.1. 

Puede ser que el nombre del paquete sea distinto en Linux y en Mac. En Windows, se llama "python-dotenv". Si no se puede instalar el modulo python-dotenv, busca como se llama el nombre del modulo en tu sistema operativo.

### Paquete django-jsignature para firmar contratos

Agregué un módulo de pip llamado django-jsignature para que los usuarios puedan firmar los contratos dibujando su firma, y almacenando esa firma como una imagen en la base de datos.

## Legal

### Uso de inteligencias artificiales LLM

Se usaron inteligencias artificiales LLM (Large Language Models) para generar parte del código de este proyecto.