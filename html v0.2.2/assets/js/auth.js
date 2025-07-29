// assets/js/auth.js

// Para integrar con Firebase, primero debes incluir los SDKs en tu HTML.
// Por ejemplo, antes de cerrar la etiqueta </body>:
/*
<script src="https://www.gstatic.com/firebasejs/9.6.1/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.6.1/firebase-auth-compat.js"></script>
<script>
    const firebaseConfig = {
        // ... tus credenciales de Firebase aquí ...
    };
    firebase.initializeApp(firebaseConfig);
    const auth = firebase.auth();
</script>
*/

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('auth-modal');
    const loginBtn = document.getElementById('login-btn');
    const registerBtn = document.getElementById('register-btn');
    const closeBtn = document.querySelector('.close-btn');

    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const formToggleLink = document.querySelector('#form-toggle a');

    const showModal = () => {
        if(modal) modal.style.display = 'flex';
    };
    
    const closeModal = () => {
        if(modal) modal.style.display = 'none';
    };

    if (loginBtn) {
        loginBtn.onclick = () => {
            loginForm.style.display = 'block';
            registerForm.style.display = 'none';
            formToggleLink.parentElement.innerHTML = '¿No tienes cuenta? <a href="#">Regístrate aquí</a>';
            showModal();
        };
    }
    
    if(registerBtn) {
        registerBtn.onclick = () => {
            loginForm.style.display = 'none';
            registerForm.style.display = 'block';
            formToggleLink.parentElement.innerHTML = '¿Ya tienes cuenta? <a href="#">Inicia sesión</a>';
            showModal();
        };
    }
    
    if(closeBtn) closeBtn.onclick = closeModal;
    window.onclick = (event) => {
        if (event.target == modal) {
            closeModal();
        }
    };

    // Lógica para cambiar entre formularios
    if (formToggleLink) {
        formToggleLink.parentElement.addEventListener('click', (e) => {
            e.preventDefault();
            if (loginForm.style.display === 'none') {
                loginForm.style.display = 'block';
                registerForm.style.display = 'none';
                formToggleLink.parentElement.innerHTML = '¿No tienes cuenta? <a href="#">Regístrate aquí</a>';
            } else {
                loginForm.style.display = 'none';
                registerForm.style.display = 'block';
                formToggleLink.parentElement.innerHTML = '¿Ya tienes cuenta? <a href="#">Inicia sesión</a>';
            }
        });
    }

    // --- Lógica de Firebase (Simulada) ---
    
    // Registro de usuario
    if (registerForm) {
        registerForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const email = document.getElementById('register-email').value;
            const password = document.getElementById('register-password').value;
            
            console.log(`Intentando registrar con ${email}`);
            alert(`¡Registro exitoso para ${email}! Ahora puedes iniciar sesión.`);
            
            // CONEXIÓN REAL A FIREBASE (descomentar al configurar)
            /*
            auth.createUserWithEmailAndPassword(email, password)
                .then(userCredential => {
                    console.log('Usuario registrado:', userCredential.user);
                    closeModal();
                })
                .catch(error => {
                    alert('Error en el registro: ' + error.message);
                });
            */
            closeModal();
        });
    }

    // Inicio de sesión
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const email = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;
            
            console.log(`Intentando iniciar sesión con ${email}`);
            alert(`¡Bienvenido de nuevo, ${email}!`);
            
            // CONEXIÓN REAL A FIREBASE (descomentar al configurar)
            /*
            auth.signInWithEmailAndPassword(email, password)
                .then(userCredential => {
                    console.log('Usuario autenticado:', userCredential.user);
                    closeModal();
                })
                .catch(error => {
                    alert('Error al iniciar sesión: ' + error.message);
                });
            */
            closeModal();
        });
    }
});