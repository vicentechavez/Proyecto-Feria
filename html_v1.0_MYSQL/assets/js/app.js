document.addEventListener('DOMContentLoaded', () => {
    // DEBUG: 1. Confirma que el script se carga. Deberías ver esto en la consola al cargar la página.
    console.log("✅ app.js cargado y listo.");

    // --- REFERENCIAS GLOBALES ---
    const apiBaseUrl = 'assets/api/api.php'; 

    // --- FUNCIÓN DE NOTIFICACIONES ---
    const notificationContainer = document.getElementById('notification-container');
    function showNotification(message, type = 'success') {
        if (!notificationContainer) return;
        const notif = document.createElement('div');
        notif.className = `notification ${type}`;
        notif.textContent = message;
        notificationContainer.appendChild(notif);
        setTimeout(() => { notif.remove(); }, 3000);
    }

    // --- LÓGICA DEL MENÚ HAMBURGUESA ---
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');
    if (hamburger && navMenu) {
        hamburger.addEventListener('click', () => {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('active');
        });
    }

    // --- GESTIÓN DE LA SESIÓN DEL USUARIO (SIMULADA) ---
    function updateUserNav(userEmail = null) {
        const loggedInViewNav = document.getElementById('logged-in-view');
        const loggedOutViewNav = document.getElementById('logged-out-view');
        const userEmailDisplay = document.getElementById('user-email-display');
        const contactFormEmailInput = document.querySelector('#main-contact-form input[name="email"]');

        if (userEmail) {
            sessionStorage.setItem('userEmail', userEmail);
            if(loggedInViewNav) loggedInViewNav.style.display = 'flex';
            if(loggedOutViewNav) loggedOutViewNav.style.display = 'none';
            if(userEmailDisplay) userEmailDisplay.textContent = userEmail;
            if (contactFormEmailInput) contactFormEmailInput.value = userEmail;
        } else {
            sessionStorage.removeItem('userEmail');
            if(loggedInViewNav) loggedInViewNav.style.display = 'none';
            if(loggedOutViewNav) loggedOutViewNav.style.display = 'flex';
            if (contactFormEmailInput) contactFormEmailInput.value = '';
        }
    }
    updateUserNav(sessionStorage.getItem('userEmail'));

    // --- LÓGICA DEL MODAL DE AUTENTICACIÓN (Solo para abrir/cerrar) ---
    const modal = document.getElementById('auth-modal');
    if (modal) {
        const loginBtn = document.getElementById('login-btn');
        const registerBtn = document.getElementById('register-btn');
        const closeBtn = modal.querySelector('.close-btn');
        const loginView = document.getElementById('login-view');
        const registerView = document.getElementById('register-view');
        const toggleToRegisterLink = document.getElementById('form-toggle-login');
        const toggleToLoginLink = document.getElementById('form-toggle-register');
        
        const openModal = () => modal.style.display = 'flex';
        const closeModal = () => modal.style.display = 'none';

        if(loginBtn) loginBtn.addEventListener('click', () => { openModal(); loginView.style.display = 'block'; registerView.style.display = 'none'; });
        if(registerBtn) registerBtn.addEventListener('click', () => { openModal(); registerView.style.display = 'block'; loginView.style.display = 'none'; });
        if(closeBtn) closeBtn.addEventListener('click', closeModal);
        window.addEventListener('click', (event) => { if (event.target == modal) closeModal(); });
        if(toggleToRegisterLink) toggleToRegisterLink.querySelector('a').addEventListener('click', (e) => { e.preventDefault(); loginView.style.display = 'none'; registerView.style.display = 'block'; });
        if(toggleToLoginLink) toggleToLoginLink.querySelector('a').addEventListener('click', (e) => { e.preventDefault(); registerView.style.display = 'none'; loginView.style.display = 'block'; });
    }

    // --- MANEJO DE FORMULARIOS CON PHP/MYSQL ---
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    
    if (registerForm) {
        registerForm.addEventListener('submit', (e) => {
            e.preventDefault(); // Prevenir recarga de la página
            // DEBUG: 2. Confirma que el evento de envío se captura.
            console.log("🔘 Evento 'submit' de REGISTRO capturado.");

            const email = registerForm.querySelector('#register-email').value;
            const password = registerForm.querySelector('#register-password').value;
            const dataToSend = { email, password };

            // DEBUG: 3. Muestra los datos que se van a enviar.
            console.log("➡️ Enviando datos a la API (Registro):", dataToSend);

            fetch(`${apiBaseUrl}?action=register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dataToSend)
            })
            .then(res => res.json())
            .then(response => {
                // DEBUG: 4. Muestra la respuesta del servidor.
                console.log("⬅️ Respuesta recibida del servidor (Registro):", response);
                if (response.success) {
                    showNotification('✅ ¡Registro exitoso!', 'success');
                    registerForm.reset();
                    if(modal) modal.style.display = 'none';
                } else {
                    showNotification(`❌ Error: ${response.message}`, 'error');
                }
            })
            .catch(error => {
                // DEBUG: 5. Muestra si hubo un error de red o de conexión.
                console.error("🔥 Error en FETCH (Registro):", error);
                showNotification('❌ Error de conexión con el servidor.', 'error');
            });
        });
    }

    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            console.log("🔘 Evento 'submit' de LOGIN capturado.");

            const email = loginForm.querySelector('#login-email').value;
            const password = loginForm.querySelector('#login-password').value;
            const dataToSend = { email, password };

            console.log("➡️ Enviando datos a la API (Login):", dataToSend);

            fetch(`${apiBaseUrl}?action=login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dataToSend)
            })
            .then(res => res.json())
            .then(response => {
                console.log("⬅️ Respuesta recibida del servidor (Login):", response);
                if (response.success) {
                    showNotification('✅ ¡Sesión iniciada correctamente!', 'success');
                    updateUserNav(response.user.email);
                    loginForm.reset();
                    if(modal) modal.style.display = 'none';
                } else {
                    showNotification(`❌ Error: ${response.message}`, 'error');
                }
            })
            .catch(error => {
                console.error("🔥 Error en FETCH (Login):", error);
                showNotification('❌ Error de conexión con el servidor.', 'error');
            });
        });
    }

    // --- CERRAR SESIÓN ---
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            updateUserNav(null);
            showNotification('👋 Has cerrado sesión. ¡Vuelve pronto!', 'success');
        });
    }

    // --- FORMULARIO DE CONTACTO ---
    const contactForm = document.getElementById('main-contact-form');
    if (contactForm) {
        contactForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const formData = new FormData(contactForm);
            const data = Object.fromEntries(formData.entries());
            fetch(`${apiBaseUrl}?action=contact`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(res => res.json())
            .then(response => {
                if (response.success) {
                    showNotification('✔️ Mensaje enviado. ¡Gracias por contactarnos!', 'success');
                    contactForm.reset();
                    const userEmail = sessionStorage.getItem('userEmail');
                    if (userEmail) {
                        const emailInput = contactForm.querySelector('input[name="email"]');
                        if (emailInput) emailInput.value = userEmail;
                    }
                } else {
                    showNotification(`❌ Error: ${response.message}`, 'error');
                }
            })
            .catch(() => showNotification('❌ Error de conexión con el servidor.', 'error'));
        });
    }
});