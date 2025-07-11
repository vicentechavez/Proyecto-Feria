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
        self.root.geometry("700x550")  # Un poco más alto para los botones
        self.root.resizable(False, False)

        # Frame principal para video y botones
        self.frame_principal = tk.Frame(self.root)
        self.frame_principal.pack()

        # Etiqueta para mostrar la cámara (video)
        self.label_video = tk.Label(self.frame_principal)
        self.label_video.pack()

        # Frame para botones justo debajo del video
        self.frame_botones = tk.Frame(self.frame_principal)
        self.frame_botones.pack(pady=10)

        # Botones para iniciar y detener detección
        self.btn_iniciar = tk.Button(self.frame_botones, text="Iniciar Detección", command=self.iniciar)
        self.btn_iniciar.grid(row=0, column=0, padx=5)

        self.btn_detener = tk.Button(self.frame_botones, text="Detener", command=self.detener, state=tk.DISABLED)
        self.btn_detener.grid(row=0, column=1, padx=5)

        self.btn_registrar = tk.Button(self.frame_botones, text="Registrar Persona", command=self.registrar)
        self.btn_registrar.grid(row=0, column=2, padx=5)
        self.btn_registrar.config(state=tk.DISABLED)

        # resto del código igual...


        # Inicialización de variables
        self.cap = None
        self.running = False
        self.frame_anterior = None
        self.datos_registrados = self.cargar_datos_registrados()
        self.ultimo_reconocimiento = 0  # Tiempo del último reconocimiento facial
        self.nombre_reconocido = []
        self.procesando = False

    def iniciar(self):
        if not self.running:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("❌ No se pudo abrir la cámara.")
                return
            self.running = True
            self.btn_iniciar.config(state=tk.DISABLED)
            self.btn_detener.config(state=tk.NORMAL)
            self.btn_registrar.config(state=tk.NORMAL)
            self.detectar()

    def detener(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.label_video.config(image="")
        self.btn_iniciar.config(state=tk.NORMAL)
        self.btn_detener.config(state=tk.DISABLED)
        self.btn_registrar.config(state=tk.DISABLED)
        self.frame_anterior = None
        self.nombre_reconocido = []

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
        def registrar_accion():
            nombre = nombre_entry.get()
            if nombre:
                self.registrar_persona(nombre)
                ventana_registro.destroy()

        ventana_registro = tk.Toplevel(self.root)
        ventana_registro.title("Registrar Persona")
        ventana_registro.geometry("400x200")

        tk.Label(ventana_registro, text="Nombre:").pack(pady=5)
        nombre_entry = tk.Entry(ventana_registro)
        nombre_entry.pack(pady=5)

        tk.Button(ventana_registro, text="Registrar", command=registrar_accion).pack(pady=10)

    def registrar_persona(self, nombre):
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("❌ No se pudo abrir la cámara.")
                return

        ret, frame = self.cap.read()
        if ret:
            rostro = self.detectar_rostro(frame)
            if rostro is not None:
                nombre_archivo = f"{CARPETA_REGISTRO}/{nombre}.jpg"
                cv2.imwrite(nombre_archivo, rostro)
                self.datos_registrados[nombre] = self.extraer_encoding(rostro)
                self.guardar_datos_registrados()
                print(f"✅ Persona registrada: {nombre}")
            else:
                print("⚠️ No se detectó rostro.")
        else:
            print("❌ Error al capturar la imagen.")

    def cargar_datos_registrados(self):
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
        rostro_rgb = cv2.cvtColor(rostro, cv2.COLOR_BGR2RGB)
        ubicaciones_rostros = face_recognition.face_locations(rostro_rgb)
        encodings_rostros = face_recognition.face_encodings(rostro_rgb, ubicaciones_rostros)
        if len(encodings_rostros) > 0:
            return encodings_rostros[0]
        return None

    def guardar_datos_registrados(self):
        with open("datos_registrados.npy", "wb") as archivo:
            np.save(archivo, self.datos_registrados)

    def detectar_rostro(self, frame):
        rostro_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ubicaciones_rostros = face_recognition.face_locations(rostro_rgb)
        if len(ubicaciones_rostros) > 0:
            top, right, bottom, left = ubicaciones_rostros[0]
            rostro = frame[top:bottom, left:right]
            return rostro
        return None

    def reconocer_rostros(self, frame):
        rostros_encontrados = []
        nombres_reconocidos = []

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ubicaciones = face_recognition.face_locations(frame_rgb)
        encodings = face_recognition.face_encodings(frame_rgb, ubicaciones)

        for encoding, (top, right, bottom, left) in zip(encodings, ubicaciones):
            nombre = "Desconocido"
            matches = face_recognition.compare_faces(list(self.datos_registrados.values()), encoding)
            face_distances = face_recognition.face_distance(list(self.datos_registrados.values()), encoding)

            if matches:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    nombre = list(self.datos_registrados.keys())[best_match_index]
                    nombres_reconocidos.append(nombre)

            rostros_encontrados.append((top, right, bottom, left, nombre))

        return rostros_encontrados, nombres_reconocidos

    def detectar(self):
        if self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gris = cv2.GaussianBlur(gris, (21, 21), 0)

                if self.frame_anterior is None:
                    self.frame_anterior = gris
                else:
                    delta = cv2.absdiff(self.frame_anterior, gris)
                    thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
                    thresh = cv2.dilate(thresh, None, iterations=2)
                    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    movimiento_detectado = False
                    for contorno in contornos:
                        if cv2.contourArea(contorno) > 1000:
                            movimiento_detectado = True
                            (x, y, w, h) = cv2.boundingRect(contorno)
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                            break

                    self.frame_anterior = gris

                    if movimiento_detectado and not self.procesando and (time.time() - self.ultimo_reconocimiento > 5):
                        self.procesando = True
                        # Reducir el tamaño del frame para acelerar el reconocimiento
                        frame_pequeno = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                        
                        def reconocimiento_async():
                            rostros_encontrados, nombres = self.reconocer_rostros(frame_pequeno)
                            if rostros_encontrados:
                                # Ajustar las posiciones de los rostros al tamaño original multiplicando por 4
                                rostros_ajustados = []
                                for (top, right, bottom, left, nombre) in rostros_encontrados:
                                    top *= 4
                                    right *= 4
                                    bottom *= 4
                                    left *= 4
                                    rostros_ajustados.append((top, right, bottom, left, nombre))
                                self.rostros_actuales = rostros_ajustados
                                self.nombre_reconocido = nombres
                                print("Rostros reconocidos:", nombres)
                                if nombres:
                                    self.reproducir_sonido()
                            else:
                                self.rostros_actuales = []
                                self.nombre_reconocido = []
                                print("No se detectó ningún rostro")

                            self.ultimo_reconocimiento = time.time()
                            self.procesando = False

                        threading.Thread(target=reconocimiento_async, daemon=True).start()

                # Mostrar los rectángulos y nombres de todos los rostros reconocidos (con posiciones ya ajustadas)
                if hasattr(self, 'rostros_actuales') and self.rostros_actuales:
                    for (top, right, bottom, left, nombre) in self.rostros_actuales:
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                        cv2.putText(frame, f"Bienvenido {nombre}", (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                    (0, 255, 0), 2)
                else:
                    cv2.putText(frame, "No se detecto rostro", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                imgtk = ImageTk.PhotoImage(image=img)
                self.label_video.imgtk = imgtk
                self.label_video.configure(image=imgtk)

            if self.running:
                self.root.after(30, self.detectar)



if __name__ == "__main__":
    root = tk.Tk()
    app = DeteccionMovimientoApp(root)
    root.mainloop()
