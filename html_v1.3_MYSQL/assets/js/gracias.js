"use strict";

document.addEventListener('DOMContentLoaded', () => {
    // --- OBTENER PARÁMETROS DE LA URL ---
    const params = new URLSearchParams(window.location.search);
    const plan = params.get('plan');

    // --- REFERENCIAS A ELEMENTOS DEL DOM ---
    const titleElement = document.getElementById('thank-you-title');
    const messageElement = document.getElementById('thank-you-message');
    const ctaButton = document.getElementById('thank-you-cta');
    
    // El botón de descarga se mantiene para futura implementación.
    // const downloadButton = document.getElementById('download-btn'); 

    // Si los elementos principales no existen, no se ejecuta el script.
    if (!titleElement || !messageElement || !ctaButton) {
        console.error("No se encontraron los elementos necesarios en la página de agradecimiento.");
        return;
    }

    // --- PERSONALIZAR MENSAJE SEGÚN EL PLAN CONTRATADO ---
    if (plan === 'Prueba') {
        // Mensaje para el plan de prueba gratuito
        titleElement.innerHTML = `¡<span class="neon-green">Prueba gratuita</span> activada!`;
        messageElement.textContent = 'Has iniciado tu prueba de 7 días. Explora todas las funciones de Ojo Digital y descubre la seguridad inteligente.';
        ctaButton.textContent = 'Ir al Inicio';
        ctaButton.href = 'index.html';
    } else if (plan && plan !== 'Desconocido') {
        // Mensaje para planes de pago (ej. Esencial, Profesional)
        titleElement.innerHTML = `¡<span class="neon-green">Gracias</span> por tu compra!`;
        messageElement.textContent = `Hemos procesado tu pago del plan "${plan}". Ya puedes empezar a proteger lo que más importa.`;
        ctaButton.textContent = 'Volver al Inicio';
        ctaButton.href = 'index.html';
    } else {
        // Mensaje genérico si no se especifica un plan
        titleElement.innerHTML = `¡Operación <span class="neon-green">Completada</span>!`;
        messageElement.textContent = 'Tu solicitud ha sido procesada exitosamente. ¡Gracias por confiar en Ojo Digital!';
        ctaButton.textContent = 'Volver al Inicio';
        ctaButton.href = 'index.html';
    }
});