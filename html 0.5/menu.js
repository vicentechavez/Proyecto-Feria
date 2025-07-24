window.addEventListener('DOMContentLoaded', () => {
  fetch("nav.html")
    .then(res => res.text())
    .then(data => {
      document.getElementById("nav-container").innerHTML = data;

      const menuIcon = document.getElementById('menu-icon');
      const menu = document.getElementById('menu');

      // Restaurar estado guardado
      const menuAbierto = localStorage.getItem('menuAbierto') === 'true';

      // Variables para evitar múltiples clicks durante animación
      let animando = false;

      if (menuAbierto) {
        menu.classList.add('open');
        menu.classList.remove('hidden');
        menuIcon.classList.add('open');
      } else {
        menu.classList.remove('open');
        menu.classList.add('hidden');
        menuIcon.classList.remove('open');
      }

      menuIcon.addEventListener('click', () => {
        if (animando) return; // evitar click mientras animación

        if (menu.classList.contains('hidden')) {
          // Mostrar menú
          menu.classList.remove('hidden');
          // Forzar repaint para que la animación funcione
          void menu.offsetWidth;
          menu.classList.add('open');
          menuIcon.classList.add('open');
          localStorage.setItem('menuAbierto', 'true');
        } else {
          // Ocultar menú con animación
          animando = true;
          menu.classList.remove('open');
          menuIcon.classList.remove('open');

          // Escuchar una vez el final de la transición para esconder menú y liberar bloqueo
          const onTransitionEnd = (e) => {
            if (e.propertyName === 'opacity') { // esperar la transición de opacidad
              menu.classList.add('hidden');
              animando = false;
              menu.removeEventListener('transitionend', onTransitionEnd);
            }
          };

          menu.addEventListener('transitionend', onTransitionEnd);
          localStorage.setItem('menuAbierto', 'false');
        }
      });
    })
    .catch(err => console.error("Error cargando menú:", err));
});
