"use strict";

document.addEventListener('DOMContentLoaded', () => {
    // --- REFERENCIAS A ELEMENTOS DEL DOM ---
    const paymentTitle = document.getElementById('payment-title');
    const cardNumberInput = document.getElementById('card-number');
    const expiryDateInput = document.getElementById('expiry-date');
    const paymentForm = document.getElementById('payment-form');
    const loadingOverlay = document.getElementById('loading-overlay');

    // --- OBTENER PARÁMETROS DE LA URL ---
    const params = new URLSearchParams(window.location.search);
    const plan = params.get('plan') || 'Desconocido';

    // --- LÓGICA DE LA PÁGINA ---

    // 1. Actualizar título con el nombre del plan
    if (paymentTitle) {
        paymentTitle.innerHTML = `Contratar Plan <span class="neon-green">${plan}</span>`;
    }

    // 2. Formateo automático de los campos del formulario
    // Formato del número de tarjeta (XXXX XXXX XXXX XXXX)
    if (cardNumberInput) {
        cardNumberInput.addEventListener('input', (e) => {
            const value = e.target.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
            let formattedValue = '';
            for (let i = 0; i < value.length; i++) {
                if (i > 0 && i % 4 === 0) {
                    formattedValue += ' ';
                }
                formattedValue += value[i];
            }
            e.target.value = formattedValue;
        });
    }

    // Formato de la fecha de expiración (MM/AA)
    if (expiryDateInput) {
        expiryDateInput.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\//g, '').replace(/[^0-9]/gi, '');
            if (value.length > 2) {
                e.target.value = value.slice(0, 2) + '/' + value.slice(2);
            } else {
                e.target.value = value;
            }
        });
    }

    // 3. Simulación del proceso de pago al enviar el formulario
    if (paymentForm) {
        paymentForm.addEventListener('submit', (e) => {
            e.preventDefault();

            // Mostrar pantalla de carga
            if (loadingOverlay) {
                loadingOverlay.style.display = 'flex';
            }

            // Simular un tiempo de espera aleatorio para la verificación (entre 1 y 4 segundos)
            const randomDelay = Math.floor(Math.random() * (4000 - 1000 + 1)) + 1000;

            setTimeout(() => {
                // Redirigir a la página de agradecimiento con el plan como parámetro
                window.location.href = `gracias.html?plan=${encodeURIComponent(plan)}`;
            }, randomDelay);
        });
    }
});