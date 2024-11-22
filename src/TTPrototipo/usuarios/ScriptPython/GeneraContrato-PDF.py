from weasyprint import HTML

# HTML de prueba
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Prueba de WeasyPrint</title>
</head>
<body>
    <h1>¡WeasyPrint Funciona Correctamente!</h1>
    <p>Este PDF fue generado usando WeasyPrint en Python.</p>
</body>
</html>
"""

# Generar PDF
HTML(string=html_content).write_pdf("prueba.pdf")

print("PDF generado: prueba.pdf")
