document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('registerForm');
    const usernameInput = document.getElementById('new-username');
    const passwordInput = document.getElementById('new-password');
    const emailInput = document.getElementById('email');
    const phoneInput = document.getElementById('phone');

    form.addEventListener('submit', function (event) {
        let isValid = true;
        let errorMessage = '';

        // Validación de nombre completo (primer nombre, segundo nombre opcional, dos apellidos)
        const username = usernameInput.value.trim();
        const nameParts = username.split(/\s+/);
        if (nameParts.length < 3 || nameParts.length > 4) {
            errorMessage += 'Por favor, ingresa tu primer nombre, segundo nombre (opcional) y ambos apellidos.\n';
            isValid = false;
        }

        // Validación de número de celular (10 dígitos)
        const phoneRegex = /^\d{10}$/;
        const phone = phoneInput.value.trim();
        if (!phoneRegex.test(phone)) {
            errorMessage += 'Por favor, ingresa un número de celular válido de 10 dígitos.\n';
            isValid = false;
        }

        // Validación de contraseña (mínimo 8 caracteres, incluyendo letras, números y un carácter especial)
        const passwordRegex = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$/;
        const password = passwordInput.value.trim();
        if (!passwordRegex.test(password)) {
            errorMessage += 'La contraseña debe tener al menos 8 caracteres, incluyendo al menos una letra, un número y un carácter especial.\n';
            isValid = false;
        }

        // Validación de correo electrónico
        const email = emailInput.value.trim();
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!emailRegex.test(email)) {
            errorMessage += 'Por favor, ingresa un correo electrónico válido.\n';
            isValid = false;
        }

        // Validación de caracteres especiales en el nombre
        const invalidCharsRegex = /[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/;
        if (invalidCharsRegex.test(username)) {
            errorMessage += 'El nombre solo debe contener letras y espacios.\n';
            isValid = false;
        }

        if (!isValid) {
            alert(errorMessage);
            event.preventDefault();
        }
    });
});
