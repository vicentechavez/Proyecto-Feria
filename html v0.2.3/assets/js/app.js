// assets/js/app.js - Versión definitiva que controla TODO

document.addEventListener('DOMContentLoaded', () => {
    // --- Referencias a Elementos del DOM ---
    const modal = document.getElementById('auth-modal');
    const loginBtn = document.getElementById('login-btn');
    const registerBtn = document.getElementById('register-btn');
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');

    // Menú de hamburguesa para móviles
    if (hamburger && navMenu) {
        hamburger.addEventListener('click', () => {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('active');
        });
    }
    
    // Si no hay modal en la página, no hagas nada más.
    if (!modal) return;
    
    // Elementos DENTRO del modal
    const closeBtn = modal.querySelector('.close-btn');
    const formToggle = modal.querySelector('#form-toggle');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    // --- Funciones para abrir y cerrar el modal ---
    const openModal = () => modal.style.display = 'flex';
    const closeModal = () => modal.style.display = 'none';

    // --- Event Listeners para la Interfaz del Modal ---
    if (loginBtn) {
        loginBtn.addEventListener('click', () => {
            loginForm.style.display = 'block';
            registerForm.style.display = 'none';
            formToggle.innerHTML = '¿No tienes cuenta? <a href="#">Regístrate aquí</a>';
            openModal();
        });
    }

    if (registerBtn) {
        registerBtn.addEventListener('click', () => {
            registerForm.style.display = 'block';
            loginForm.style.display = 'none';
            formToggle.innerHTML = '¿Ya tienes cuenta? <a href="#">Inicia sesión</a>';
            openModal();
        });
    }

    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    window.addEventListener('click', (event) => {
        if (event.target == modal) closeModal();
    });

    if (formToggle) {
        formToggle.addEventListener('click', (e) => {
            if (e.target.tagName === 'A') {
                e.preventDefault();
                const isLoginVisible = loginForm.style.display === 'block';
                loginForm.style.display = isLoginVisible ? 'none' : 'block';
                registerForm.style.display = isLoginVisible ? 'block' : 'none';
                formToggle.innerHTML = isLoginVisible ? '¿Ya tienes cuenta? <a href="#">Inicia sesión</a>' : '¿No tienes cuenta? <a href="#">Regístrate aquí</a>';
            }
        });
    }

    // ======================================================
    // ||           LÓGICA DE FIREBASE (AQUÍ MISMO)        ||
    // ======================================================

    // --- Lógica de Registro ---
    if (registerForm) {
        registerForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const email = registerForm['register-email'].value;
            const password = registerForm['register-password'].value;
            
            auth.createUserWithEmailAndPassword(email, password)
                .then(userCredential => {
                    return db.collection('users').doc(userCredential.user.uid).set({
                        email: email,
                        createdAt: firebase.firestore.FieldValue.serverTimestamp()
                    });
                })
                .then(() => {
                    alert('✅ ¡Registro exitoso! Ya puedes iniciar sesión.');
                    registerForm.reset();
                    closeModal();
                })
                .catch(error => {
                    if (error.code === 'auth/email-already-in-use') {
                        alert('❌ Error: El correo ya está registrado.');
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
            
            auth.signInWithEmailAndPassword(email, password)
                .then(() => {
                    alert('👍 ¡Bienvenido de nuevo!');
                    loginForm.reset();
                    closeModal();
                })
                .catch(() => {
                    alert('❌ Error: Correo o contraseña incorrectos.');
                });
        });
    }

    // --- Lógica para el Botón de Descarga ---
    auth.onAuthStateChanged(user => {
        const botonDescarga = document.querySelector('.btn-descarga'); // Asegúrate de tener un botón con esta clase
        if (botonDescarga) {
            botonDescarga.disabled = !user;
            botonDescarga.textContent = user ? 'Descargar Aplicación' : 'Inicia Sesión para Descargar';
        }
    });
});