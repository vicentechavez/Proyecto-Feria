window.addEventListener('DOMContentLoaded', () => {
  fetch("nav.html")
    .then(res => res.text())
    .then(data => {
      document.getElementById("nav-container").innerHTML = data;

      const menuIcon = document.getElementById('menu-icon');
      const menu = document.getElementById('menu');

      // Restaurar estado guardado
      const menuAbierto = localStorage.getItem('menuAbierto') === 'true';

      if (menuAbierto) {
        menu.classList.remove('hidden');
        menu.classList.add('open');
        menuIcon.classList.add('open');
      }

      // Evento para alternar menú
      menuIcon.addEventListener('click', () => {
        const isHidden = menu.classList.contains('hidden');

        if (isHidden) {
          // Mostrar menú con transición
          menu.classList.remove('hidden');
          void menu.offsetWidth; // fuerza repaint
          menu.classList.add('open');
          menuIcon.classList.add('open');
          localStorage.setItem('menuAbierto', 'true');
        } else {
          // Quitar clase open para hacer transición de cierre
          menu.classList.remove('open');
          menuIcon.classList.remove('open');
          menu.addEventListener('transitionend', function handler() {
            menu.classList.add('hidden');
            menu.removeEventListener('transitionend', handler);
          });
          localStorage.setItem('menuAbierto', 'false');
        }
      });
    })
    .catch(err => console.error("Error cargando menú:", err));
});
