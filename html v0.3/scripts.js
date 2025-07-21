document.addEventListener('DOMContentLoaded', () => {
  // 1. Destacar menú activo según URL
  const links = document.querySelectorAll('nav a');
  const current = window.location.pathname.split('/').pop() || 'index.html';
  links.forEach(link => {
    if (link.getAttribute('href') === current) {
      link.classList.add('active');
    }
  });

  // 2. Animación suave para links que apuntan a anclas internas
  links.forEach(link => {
    if (link.hash) {
      link.addEventListener('click', e => {
        e.preventDefault();
        const target = document.querySelector(link.hash);
        if (target) {
          target.scrollIntoView({ behavior: 'smooth' });
        }
      });
    }
  });

  // 3. Validación simple formulario contacto
  const form = document.querySelector('form');
  if (form) {
    form.addEventListener('submit', e => {
      const name = form.querySelector('input[type="text"]');
      const email = form.querySelector('input[type="email"]');
      let valid = true;
      if (!name.value.trim()) {
        alert('Por favor ingresa tu nombre.');
        name.focus();
        valid = false;
      } else if (!email.value.trim() || !email.value.includes('@')) {
        alert('Por favor ingresa un correo válido.');
        email.focus();
        valid = false;
      }
      if (!valid) e.preventDefault();
    });
  }

  // 4. Animar barras de progreso cuando se ven en pantalla
  const progressBars = document.querySelectorAll('.progress-bar');
  if (progressBars.length) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const bar = entry.target;
          const width = bar.style.width;
          bar.style.width = '0';
          setTimeout(() => {
            bar.style.transition = 'width 2s ease-in-out';
            bar.style.width = width;
          }, 100);
          observer.unobserve(bar);
        }
      });
    }, { threshold: 0.5 });

    progressBars.forEach(bar => observer.observe(bar));
  }

  // 5. Toggle modo oscuro/neón (opcional)
  const toggleBtn = document.createElement('button');
  toggleBtn.textContent = 'Modo Neón';
  toggleBtn.style.position = 'fixed';
  toggleBtn.style.bottom = '20px';
  toggleBtn.style.right = '20px';
  toggleBtn.style.padding = '10px 16px';
  toggleBtn.style.backgroundColor = '#39ff14';
  toggleBtn.style.color = '#0b0c0f';
  toggleBtn.style.border = 'none';
  toggleBtn.style.borderRadius = '8px';
  toggleBtn.style.cursor = 'pointer';
  toggleBtn.style.boxShadow = '0 0 12px #39ff14';
  toggleBtn.style.zIndex = '9999';

  document.body.appendChild(toggleBtn);

  toggleBtn.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    if (document.body.classList.contains('dark-mode')) {
      toggleBtn.textContent = 'Modo Claro';
    } else {
      toggleBtn.textContent = 'Modo Neón';
    }
  });
});
