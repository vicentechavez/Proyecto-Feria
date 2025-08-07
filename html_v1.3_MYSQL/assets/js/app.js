"use strict";

document.addEventListener('DOMContentLoaded', () => {
    // --- CONSTANTES Y REFERENCIAS GLOBALES ---
    const apiBaseUrl = 'assets/api/api.php';
    const notificationContainer = document.getElementById('notification-container');
    const modal = document.getElementById('auth-modal');

    // ====================================================== //
    // ||                    NOTIFICACIONES                || //
    // ====================================================== //
    function showNotification(message, type = 'success') {
        if (!notificationContainer) return;
        const notif = document.createElement('div');
        notif.className = `notification ${type}`;
        notif.textContent = message;
        notificationContainer.appendChild(notif);
        setTimeout(() => { notif.remove(); }, 3000);
    }

    // ====================================================== //
    // ||               MENÚ HAMBURGUESA (MÓVIL)           || //
    // ====================================================== //
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');
    if (hamburger && navMenu) {
        hamburger.addEventListener('click', () => {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('active');
        });
    }

    // ====================================================== //
    // ||               GESTIÓN DE SESIÓN DE USUARIO       || //
    // ====================================================== //
    const loggedInViewNav = document.getElementById('logged-in-view');
    const loggedOutViewNav = document.getElementById('logged-out-view');
    const userEmailDisplay = document.getElementById('user-email-display');
    const contactFormEmailInput = document.querySelector('#main-contact-form input[name="email"]');
    const logoutBtn = document.getElementById('logout-btn');

    function updateUserNav(userEmail = null) {
        if (userEmail) {
            sessionStorage.setItem('userEmail', userEmail);
            if (loggedInViewNav) loggedInViewNav.style.display = 'flex';
            if (loggedOutViewNav) loggedOutViewNav.style.display = 'none';
            if (userEmailDisplay) userEmailDisplay.textContent = userEmail;
            if (contactFormEmailInput) contactFormEmailInput.value = userEmail;
        } else {
            sessionStorage.removeItem('userEmail');
            if (loggedInViewNav) loggedInViewNav.style.display = 'none';
            if (loggedOutViewNav) loggedOutViewNav.style.display = 'flex';
        }
    }

    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            updateUserNav(null);
            showNotification('👋 Has cerrado sesión. ¡Vuelve pronto!', 'success');
            // FIX: Limpia el campo de email del formulario de contacto al cerrar sesión.
            if (contactFormEmailInput) {
                contactFormEmailInput.value = '';
            }
        });
    }
    
    updateUserNav(sessionStorage.getItem('userEmail'));

    // ====================================================== //
    // ||              MODAL DE AUTENTICACIÓN              || //
    // ====================================================== //
    if (modal) {
        const loginBtn = document.getElementById('login-btn');
        const registerBtn = document.getElementById('register-btn');
        const closeBtn = modal.querySelector('.close-btn');
        const loginView = document.getElementById('login-view');
        const registerView = document.getElementById('register-view');
        const toggleToRegisterLink = document.getElementById('form-toggle-login')?.querySelector('a');
        const toggleToLoginLink = document.getElementById('form-toggle-register')?.querySelector('a');
        const loginForm = document.getElementById('login-form');
        const registerForm = document.getElementById('register-form');

        const openModal = (view = 'login') => {
            modal.style.display = 'flex';
            if (view === 'register') {
                loginView.style.display = 'none';
                registerView.style.display = 'block';
            } else {
                loginView.style.display = 'block';
                registerView.style.display = 'none';
            }
        };

        const closeModal = () => {
            modal.style.display = 'none';
            // MEJORA: Resetea los formularios para una experiencia más limpia.
            if (loginForm) loginForm.reset();
            if (registerForm) registerForm.reset();
        };

        if (loginBtn) loginBtn.addEventListener('click', () => openModal('login'));
        if (registerBtn) registerBtn.addEventListener('click', () => openModal('register'));
        if (closeBtn) closeBtn.addEventListener('click', closeModal);

        modal.addEventListener('mousedown', (event) => {
            if (event.target === modal) {
                modal.dataset.closeOnMouseUp = 'true';
            }
        });
        modal.addEventListener('mouseup', (event) => {
            if (event.target === modal && modal.dataset.closeOnMouseUp === 'true') {
                closeModal();
            }
            modal.dataset.closeOnMouseUp = 'false';
        });

        if (toggleToRegisterLink) toggleToRegisterLink.addEventListener('click', (e) => { e.preventDefault(); openModal('register'); });
        if (toggleToLoginLink) toggleToLoginLink.addEventListener('click', (e) => { e.preventDefault(); openModal('login'); });
    }

    // ====================================================== //
    // ||              MANEJO DE FORMULARIOS               || //
    // ====================================================== //
    async function handleFormSubmit(action, formElement, data, onSuccess) {
        try {
            const response = await fetch(`${apiBaseUrl}?action=${action}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();
            if (result.success) {
                onSuccess(result);
            } else {
                showNotification(`❌ Error: ${result.message}`, 'error');
            }
        } catch (error) {
            showNotification('❌ Error de conexión con el servidor.', 'error');
        }
    }

    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const data = {
                email: registerForm.querySelector('#register-email').value,
                password: registerForm.querySelector('#register-password').value
            };
            handleFormSubmit('register', registerForm, data, () => {
                showNotification('✅ ¡Registro exitoso! Ahora puedes iniciar sesión.', 'success');
                if (modal) modal.style.display = 'none';
            });
        });
    }

    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const data = {
                email: loginForm.querySelector('#login-email').value,
                password: loginForm.querySelector('#login-password').value
            };
            handleFormSubmit('login', loginForm, data, (result) => {
                showNotification(`✅ ¡Sesión iniciada! Bienvenido, ${result.data.user.email}.`, 'success');
                updateUserNav(result.data.user.email);
                if (modal) modal.style.display = 'none';
            });
        });
    }

    const contactForm = document.getElementById('main-contact-form');
    if (contactForm) {
        contactForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const formData = new FormData(contactForm);
            const data = Object.fromEntries(formData.entries());
            handleFormSubmit('contact', contactForm, data, () => {
                showNotification('✔️ Mensaje enviado. ¡Gracias por contactarnos!', 'success');
                contactForm.reset();
                const userEmail = sessionStorage.getItem('userEmail');
                if (userEmail && contactFormEmailInput) {
                    contactFormEmailInput.value = userEmail;
                }
            });
        });
    }

    // ====================================================== //
    // ||           LÓGICA DE CONTRATACIÓN DE PLANES       || //
    // ====================================================== //
    const planButtons = document.querySelectorAll('.btn-contratar');
    if (planButtons.length > 0) {
        planButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const userIsLoggedIn = !!sessionStorage.getItem('userEmail');
                const plan = button.dataset.plan;
                if (!userIsLoggedIn) {
                    e.preventDefault();
                    showNotification('Debes iniciar sesión para contratar un plan.', 'error');
                    if (modal) {
                       const loginView = document.getElementById('login-view');
                       const registerView = document.getElementById('register-view');
                       modal.style.display = 'flex';
                       loginView.style.display = 'block';
                       registerView.style.display = 'none';
                    }
                    return;
                }
                if (plan === 'Prueba') {
                    e.preventDefault();
                    window.location.href = `gracias.html?plan=Prueba`;
                }
            });
        });
    }

    // ====================================================== //
    // ||              FUNCIONES DE INICIALIZACIÓN         || //
    // ====================================================== //
    // MEJORA: Actualiza el año del copyright dinámicamente.
    const copyrightYear = document.getElementById('copyright-year');
    if (copyrightYear) {
        copyrightYear.textContent = new Date().getFullYear();
    }
});
