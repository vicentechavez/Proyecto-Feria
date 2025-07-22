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
