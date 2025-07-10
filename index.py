import cv2
import tkinter as tk
from PIL import Image, ImageTk
import threading
import pygame
import time
import face_recognition
import os
import numpy as np

# Inicializa pygame para sonido
pygame.mixer.init()
ALERTA_SONIDO = "discord.mp3"  # Asegúrate de que el archivo exista en la misma carpeta

# Ruta para almacenar los rostros y nombres registrados
CARPETA_REGISTRO = "rostros_registrados"

if not os.path.exists(CARPETA_REGISTRO):
    os.makedirs(CARPETA_REGISTRO)

class DeteccionMovimientoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Detector de Movimiento y Reconocimiento Facial")
        self.root.geometry("700x500")
        self.root.resizable(False, False)

        # Interfaz de la app
        self.label_video = tk.Label(self.root)
        self.label_video.pack()

        # Botones para iniciar y detener detección
        self.btn_iniciar = tk.Button(self.root, text="Iniciar Detección", command=self.iniciar)
        self.btn_iniciar.pack(pady=10)

        self.btn_detener = tk.Button(self.root, text="Detener", command=self.detener)
        self.btn_detener.pack(pady=10)

        self.btn_registrar = tk.Button(self.root, text="Registrar Persona", command=self.registrar)
        self.btn_registrar.pack(pady=10)

        # Inicialización de variables
        self.cap = None
        self.running = False
        self.frame_anterior = None
        self.datos_registrados = self.cargar_datos_registrados()

    def iniciar(self):
        if not self.running:
            self.cap = cv2.VideoCapture(0)
            self.running = True
            self.detectar()

    def detener(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.label_video.config(image="")

    def reproducir_sonido(self):
        def play():
            try:
                time.sleep(1)  # Espera 1 segundo antes de sonar
                pygame.mixer.music.load(ALERTA_SONIDO)
                pygame.mixer.music.play()
            except Exception as e:
                print("Error al reproducir sonido:", e)

        threading.Thread(target=play, daemon=True).start()

    def registrar(self):
        # Función para registrar una nueva persona
        def registrar_persona(nombre):
            # Captura la imagen del rostro
            ret, frame = self.cap.read()
            if ret:
                rostro = self.detectar_rostro(frame)
                if rostro is not None:
                    # Guardar imagen de rostro
                    nombre_archivo = f"{CARPETA_REGISTRO}/{nombre}.jpg"
                    cv2.imwrite(nombre_archivo, rostro)
                    # Agregar los datos al archivo
                    self.datos_registrados[nombre] = self.extraer_encoding(rostro)
                    self.guardar_datos_registrados()
                    print(f"Persona registrada: {nombre}")
                else:
                    print("No se detectó rostro")
            else:
                print("Error al capturar la imagen")

        # Interfaz de registro
        def mostrar_interfaz_registro():
            ventana_registro = tk.Toplevel(self.root)
            ventana_registro.title("Registrar Persona")
            ventana_registro.geometry("400x200")

            tk.Label(ventana_registro, text="Nombre:").pack(pady=5)
            nombre_entry = tk.Entry(ventana_registro)
            nombre_entry.pack(pady=5)

            def registrar_accion():
                nombre = nombre_entry.get()
                if nombre:
                    registrar_persona(nombre)
                    ventana_registro.destroy()

            tk.Button(ventana_registro, text="Registrar", command=registrar_accion).pack(pady=10)

        mostrar_interfaz_registro()

    def cargar_datos_registrados(self):
        # Cargar las caras registradas desde los archivos
        datos = {}
        for archivo in os.listdir(CARPETA_REGISTRO):
            if archivo.endswith(".jpg"):
                nombre = archivo.split(".")[0]
                rostro = cv2.imread(f"{CARPETA_REGISTRO}/{archivo}")
                encoding = self.extraer_encoding(rostro)
                if encoding is not None:
                    datos[nombre] = encoding
        return datos

    def extraer_encoding(self, rostro):
        # Extrae los "encodings" de un rostro
        rostro_rgb = cv2.cvtColor(rostro, cv2.COLOR_BGR2RGB)
        ubicaciones_rostros = face_recognition.face_locations(rostro_rgb)
        encodings_rostros = face_recognition.face_encodings(rostro_rgb, ubicaciones_rostros)
        if len(encodings_rostros) > 0:
            return encodings_rostros[0]
        return None

    def guardar_datos_registrados(self):
        # Guardar los encodings en un archivo para persistir los registros
        with open("datos_registrados.npy", "wb") as archivo:
            np.save(archivo, self.datos_registrados)

    def detectar_rostro(self, frame):
        # Detectar rostro en la imagen capturada
        rostro_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ubicaciones_rostros = face_recognition.face_locations(rostro_rgb)
        if len(ubicaciones_rostros) > 0:
            # Asumir que solo hay un rostro
            top, right, bottom, left = ubicaciones_rostros[0]
            rostro = frame[top:bottom, left:right]
            return rostro
        return None

    def reconocer_rostro(self, rostro_detectado):
        # Reconocer el rostro detectado
        encoding_detectado = self.extraer_encoding(rostro_detectado)
        if encoding_detectado is not None:
            for nombre, encoding_guardado in self.datos_registrados.items():
                coincidencia = face_recognition.compare_faces([encoding_guardado], encoding_detectado)
                if coincidencia[0]:
                    return nombre
        return None

    def detectar(self):
        if self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # Convertir a escala gris para detección de movimiento
                gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gris = cv2.GaussianBlur(gris, (21, 21), 0)

                if self.frame_anterior is None:
                    self.frame_anterior = gris
                else:
                    delta = cv2.absdiff(self.frame_anterior, gris)
                    thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
                    thresh = cv2.dilate(thresh, None, iterations=2)
                    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    for contorno in contornos:
                        if cv2.contourArea(contorno) > 1000:
                            (x, y, w, h) = cv2.boundingRect(contorno)
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                            
                            rostro_detectado = self.detectar_rostro(frame)
                            if rostro_detectado is not None:
                                nombre_reconocido = self.reconocer_rostro(rostro_detectado)
                                if nombre_reconocido:
                                    print(f"Rostro reconocido: {nombre_reconocido}")
                                    self.reproducir_sonido()
                                    cv2.putText(frame, f"Bienvenido {nombre_reconocido}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                                    break
                            else:
                                print("Rostro no reconocido")
                    
                    self.frame_anterior = gris

                # Mostrar en la interfaz
                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                imgtk = ImageTk.PhotoImage(image=img)
                self.label_video.imgtk = imgtk
                self.label_video.configure(image=imgtk)

            if self.running:
                self.root.after(30, self.detectar)


# Ejecutar la interfaz
if __name__ == "__main__":
    root = tk.Tk()
    app = DeteccionMovimientoApp(root)
    root.mainloop()
