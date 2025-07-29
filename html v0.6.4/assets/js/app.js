// assets/js/app.js - Versión final compatible con el nuevo modal

document.addEventListener('DOMContentLoaded', () => {
    // --- Referencias a Elementos del DOM ---
    const modal = document.getElementById('auth-modal');
    const loginBtn = document.getElementById('login-btn');
    const registerBtn = document.getElementById('register-btn');
    // ... (resto de tus referencias como hamburger, etc.)

    // Si no hay modal en la página, no hagas nada más.
    if (!modal) return;
    
    // Elementos DENTRO del modal
    const closeBtn = modal.querySelector('.close-btn');
    const loginView = document.getElementById('login-view');
    const registerView = document.getElementById('register-view');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const toggleToRegisterLink = document.getElementById('form-toggle-login');
    const toggleToLoginLink = document.getElementById('form-toggle-register');


    // --- Funciones y Eventos para UI del Modal ---
    const openModal = () => modal.style.display = 'flex';
    const closeModal = () => modal.style.display = 'none';

    if (loginBtn) loginBtn.addEventListener('click', () => {
        loginView.style.display = 'block';
        registerView.style.display = 'none';
        openModal();
    });

    if (registerBtn) registerBtn.addEventListener('click', () => {
        registerView.style.display = 'block';
        loginView.style.display = 'none';
        openModal();
    });

    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    window.addEventListener('click', (event) => {
        if (event.target == modal) closeModal();
    });
    
    // Lógica para cambiar de formulario
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

    // ======================================================
    // ||           LÓGICA DE FIREBASE (SIN CAMBIOS)       ||
    // ======================================================
    // ... (Toda tu lógica de auth.createUser, auth.signIn, y auth.onAuthStateChanged
    // se mantiene exactamente igual que en la respuesta anterior) ...

    if (registerForm) registerForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = registerForm['register-email'].value;
        const password = registerForm['register-password'].value;
        
        auth.createUserWithEmailAndPassword(email, password)
            .then(userCredential => db.collection('users').doc(userCredential.user.uid).set({
                email: email,
                createdAt: firebase.firestore.FieldValue.serverTimestamp()
            }))
            .then(() => {
                alert('✅ ¡Registro exitoso!');
                registerForm.reset();
                closeModal();
            })
            .catch(error => {
                if (error.code === 'auth/email-already-in-use') alert('❌ Error: El correo ya está registrado.');
                else if (error.code === 'auth/weak-password') alert('❌ Error: La contraseña debe tener al menos 6 caracteres.');
                else alert('❌ Error en el registro: ' + error.message);
            });
    });

    if (loginForm) loginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = loginForm['login-email'].value;
        const password = loginForm['login-password'].value;
        
        auth.signInWithEmailAndPassword(email, password)
            .then(() => {
                loginForm.reset();
                closeModal();
            })
            .catch(() => alert('❌ Error: Correo o contraseña incorrectos.'));
    });

    auth.onAuthStateChanged(user => {
        const loggedInViewNav = document.getElementById('logged-in-view');
        const loggedOutViewNav = document.getElementById('logged-out-view');
        const userEmailDisplay = document.getElementById('user-email-display');
        const botonDescarga = document.querySelector('.btn-descarga');

        if (user) {
            loggedInViewNav.style.display = 'flex';
            loggedOutViewNav.style.display = 'none';
            userEmailDisplay.textContent = user.email;
            if (botonDescarga) {
                botonDescarga.disabled = false;
                botonDescarga.textContent = 'Descargar Aplicación';
            }
        } else {
            loggedInViewNav.style.display = 'none';
            loggedOutViewNav.style.display = 'flex';
            if (botonDescarga) {
                botonDescarga.disabled = true;
                botonDescarga.textContent = 'Inicia Sesión para Descargar';
            }
        }
    });

    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) logoutBtn.addEventListener('click', () => {
        auth.signOut();
    });
});