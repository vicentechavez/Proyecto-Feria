// Esta es la versión final y recomendada de app.js.
// Se enfoca únicamente en Firebase, manteniendo el código limpio y simple.

document.addEventListener('DOMContentLoaded', () => {
    // --- REFERENCIAS GLOBALES ---
    const auth = firebase.auth();
    const db = firebase.firestore();

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

    // --- LÓGICA DEL MODAL DE AUTENTICACIÓN ---
    const modal = document.getElementById('auth-modal');
    const loginView = document.getElementById('login-view');
    const registerView = document.getElementById('register-view');

    function openModalToLogin() {
        if(modal) {
            loginView.style.display = 'block';
            registerView.style.display = 'none';
            modal.style.display = 'flex';
        }
    }

    if (modal) {
        const loginBtn = document.getElementById('login-btn');
        const registerBtn = document.getElementById('register-btn');
        const closeBtn = modal.querySelector('.close-btn');
        const loginForm = document.getElementById('login-form');
        const registerForm = document.getElementById('register-form');
        const toggleToRegisterLink = document.getElementById('form-toggle-login');
        const toggleToLoginLink = document.getElementById('form-toggle-register');

        const closeModal = () => modal.style.display = 'none';

        loginBtn.addEventListener('click', openModalToLogin);
        
        registerBtn.addEventListener('click', () => {
            registerView.style.display = 'block';
            loginView.style.display = 'none';
            modal.style.display = 'flex';
        });

        closeBtn.addEventListener('click', closeModal);
        window.addEventListener('click', (event) => {
            if (event.target == modal) closeModal();
        });
        toggleToRegisterLink.querySelector('a').addEventListener('click', (e) => {
            e.preventDefault();
            loginView.style.display = 'none';
            registerView.style.display = 'block';
        });
        toggleToLoginLink.querySelector('a').addEventListener('click', (e) => {
            e.preventDefault();
            registerView.style.display = 'none';
            loginView.style.display = 'block';
        });

        // --- MANEJO DE FORMULARIOS DE FIREBASE ---
        registerForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const email = registerForm['register-email'].value;
            const password = registerForm['register-password'].value;
            
            auth.createUserWithEmailAndPassword(email, password)
                .then(userCredential => db.collection('users').doc(userCredential.user.uid).set({
                    email: email,
                    createdAt: firebase.firestore.FieldValue.serverTimestamp()
                }))
                .then(() => {
                    showNotification('✅ ¡Registro exitoso!', 'success');
                    registerForm.reset();
                    closeModal(); 
                })
                .catch(error => {
                    if (error.code === 'auth/email-already-in-use') showNotification('❌ Error: El correo ya está registrado.', 'error');
                    else if (error.code === 'auth/weak-password') showNotification('❌ Error: La contraseña debe tener al menos 6 caracteres.', 'error');
                    else showNotification('❌ Error en el registro: ' + error.message, 'error');
                });
        });

        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const email = loginForm['login-email'].value;
            const password = loginForm['login-password'].value;
            auth.signInWithEmailAndPassword(email, password)
                .then(() => {
                    loginForm.reset();
                    closeModal();
                    showNotification('✅ ¡Sesión iniciada correctamente!', 'success');
                })
                .catch(() => showNotification('❌ Error: Correo o contraseña incorrectos.', 'error'));
        });
    }

    // --- OBSERVADOR DE ESTADO DE AUTENTICACIÓN (CENTRAL) ---
    auth.onAuthStateChanged(user => {
        const loggedInViewNav = document.getElementById('logged-in-view');
        const loggedOutViewNav = document.getElementById('logged-out-view');
        const userEmailDisplay = document.getElementById('user-email-display');
        
        if (user) {
            if(loggedInViewNav) loggedInViewNav.style.display = 'flex';
            if(loggedOutViewNav) loggedOutViewNav.style.display = 'none';
            if(userEmailDisplay) userEmailDisplay.textContent = user.email;
            
            const contactFormEmailInput = document.querySelector('#main-contact-form input[name="email"]');
            if (contactFormEmailInput) {
                contactFormEmailInput.value = user.email;
            }
        } else {
            if(loggedInViewNav) loggedInViewNav.style.display = 'none';
            if(loggedOutViewNav) loggedOutViewNav.style.display = 'flex';
        }
    });

    // --- CERRAR SESIÓN ---
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            auth.signOut().then(() => {
                showNotification('👋 Has cerrado sesión. ¡Vuelve pronto!', 'success');
            });
        });
    }

    // --- FORMULARIO DE CONTACTO ---
    const contactForm = document.getElementById('main-contact-form');
    if (contactForm) {
        contactForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const name = contactForm.name.value;
            const email = contactForm.email.value;
            const message = contactForm.message.value;

            db.collection('messages').add({
                name: name,
                email: email,
                message: message,
                sentAt: firebase.firestore.FieldValue.serverTimestamp()
            })
            .then(() => {
                showNotification('✔️ Mensaje enviado. ¡Gracias por contactarnos!', 'success');
                contactForm.reset();
                if (auth.currentUser) {
                    contactForm.email.value = auth.currentUser.email;
                }
            })
            .catch(error => {
                showNotification('❌ Error al enviar el mensaje: ' + error.message, 'error');
            });
        });
    }

    // --- LÓGICA PARA CONTRATAR PLANES ---
    const planButtons = document.querySelectorAll('.btn-plan');
    planButtons.forEach(button => {
        button.addEventListener('click', () => {
            const user = auth.currentUser;
            if (user) {
                // El usuario ha iniciado sesión
                const plan = button.dataset.plan;
                if (plan === 'Prueba') {
                    // Si es el plan de prueba, ir a la página de gracias directamente
                    window.location.href = `gracias.html?plan=${plan}`;
                } else {
                    // Para otros planes, ir a la página de pago
                    window.location.href = `pago.html?plan=${plan}`;
                }
            } else {
                // El usuario no ha iniciado sesión
                showNotification('⚠️ Debes iniciar sesión para seguir', 'error');
                openModalToLogin();
            }
        });
    });
});
