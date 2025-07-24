let stream = null;

function iniciarCamara() {
  const video = document.getElementById('video');

  // Pedir acceso a la cámara
  navigator.mediaDevices.getUserMedia({ video: true, audio: false })
    .then(mediaStream => {
      stream = mediaStream;
      video.srcObject = mediaStream;
    })
    .catch(err => {
      console.error("No se pudo acceder a la cámara:", err);
      alert("Error al acceder a la cámara: " + err.message);
    });
}

function detenerCamara() {
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
    stream = null;
    const video = document.getElementById('video');
    video.srcObject = null;
  }
}


window.addEventListener('DOMContentLoaded', () => {
  const menuIcon = document.getElementById('menu-icon');
  const menu = document.getElementById('menu');

  // Recuperar estado guardado
  const menuAbierto = localStorage.getItem('menuAbierto') === 'true';

  if (menuAbierto) {
    menu.classList.add('open');
    menu.classList.remove('hidden');
    menuIcon.classList.add('open');
  } else {
    menu.classList.remove('open');
    menu.classList.add('hidden');
    menuIcon.classList.remove('open');
  }

  let animando = false;

  menuIcon.addEventListener('click', () => {
    if (animando) return;

    if (menu.classList.contains('hidden')) {
      menu.classList.remove('hidden');
      void menu.offsetWidth; // fuerza repaint
      menu.classList.add('open');
      menuIcon.classList.add('open');
      localStorage.setItem('menuAbierto', 'true');
    } else {
      animando = true;
      menu.classList.remove('open');
      menuIcon.classList.remove('open');

      const onTransitionEnd = (e) => {
        if (e.propertyName === 'opacity') {
          menu.classList.add('hidden');
          animando = false;
          menu.removeEventListener('transitionend', onTransitionEnd);
        }
      };

      menu.addEventListener('transitionend', onTransitionEnd);
      localStorage.setItem('menuAbierto', 'false');
    }
  });
});
