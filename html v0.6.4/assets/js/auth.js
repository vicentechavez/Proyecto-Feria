// assets/js/auth.js

// Asegúrate de que este script se carga DESPUÉS de haber inicializado Firebase en tu HTML.

document.addEventListener('DOMContentLoaded', () => {
    // --- Referencias a los elementos del DOM ---
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    // Asume que hay un botón de descarga con la clase .btn-descarga en tu HTML
    // Ejemplo: <button class="btn btn-secondary btn-descarga" disabled>Inicia Sesión para Descargar</button>
    const botonDescarga = document.querySelector('.btn-descarga'); 

    // --- Lógica de Registro de Nuevos Usuarios ---
    if (registerForm) {
        registerForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const email = registerForm['register-email'].value;
            const password = registerForm['register-password'].value;

            // 1. Crea el usuario en el servicio de Autenticación de Firebase
            auth.createUserWithEmailAndPassword(email, password)
                .then(userCredential => {
                    const user = userCredential.user;
                    console.log('Usuario registrado con UID:', user.uid);

                    // 2. Guarda información adicional en la base de datos Firestore
                    return db.collection('users').doc(user.uid).set({
                        email: email,
                        createdAt: firebase.firestore.FieldValue.serverTimestamp()
                    });
                })
                .then(() => {
                    alert('✅ ¡Registro exitoso! Ya puedes iniciar sesión.');
                    registerForm.reset();
                    closeModal(); // Cierra el modal de registro/login
                })
                .catch(error => {
                    console.error('Error en el registro:', error);
                    // Muestra un mensaje de error más amigable
                    if (error.code === 'auth/email-already-in-use') {
                        alert('❌ Error: El correo electrónico ya está en uso.');
                    } else if (error.code === 'auth/weak-password') {
                        alert('❌ Error: La contraseña debe tener al menos 6 caracteres.');
                    } else {
                        alert('❌ Error en el registro: ' + error.message);
                    }
                });
        });
    }

    // --- Lógica de Inicio de Sesión ---
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const email = loginForm['login-email'].value;
            const password = loginForm['login-password'].value;

            // Inicia sesión con las credenciales proporcionadas
            auth.signInWithEmailAndPassword(email, password)
                .then(userCredential => {
                    console.log('Usuario autenticado:', userCredential.user.uid);
                    alert('👍 ¡Bienvenido de nuevo!');
                    loginForm.reset();
                    closeModal(); // Cierra el modal
                })
                .catch(error => {
                    console.error('Error al iniciar sesión:', error);
                    alert('❌ Error: Correo o contraseña incorrectos.');
                });
        });
    }

    // --- Lógica para el Botón de Descarga Condicional ---
    // Esta función escucha los cambios en el estado de autenticación (login/logout)
    auth.onAuthStateChanged(user => {
        if (botonDescarga) {
            if (user) {
                // Si hay un usuario con sesión iniciada:
                console.log('Usuario con sesión activa. Habilitando descarga.');
                botonDescarga.disabled = false;
                botonDescarga.textContent = 'Descargar Aplicación';
                // Opcional: Asigna el enlace de descarga real
                // botonDescarga.onclick = () => window.location.href = 'URL_DEL_ARCHIVO_A_DESCARGAR';
            } else {
                // Si no hay sesión iniciada:
                console.log('No hay sesión activa. Deshabilitando descarga.');
                botonDescarga.disabled = true;
                botonDescarga.textContent = 'Inicia Sesión para Descargar';
            }
        }
    });

    // --- Funcionalidad para cerrar sesión (ejemplo) ---
    // Podrías tener un botón de "Cerrar Sesión" en tu navbar que llame a esto
    const logoutButton = document.getElementById('logout-btn'); // Asume que tienes un <button id="logout-btn">
    if (logoutButton) {
        logoutButton.addEventListener('click', () => {
            auth.signOut().then(() => {
                alert('Has cerrado la sesión.');
            }).catch((error) => {
                console.error('Error al cerrar sesión:', error);
            });
        });
    }
});