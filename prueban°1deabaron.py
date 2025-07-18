import cv2
import tkinter as tk
from PIL import Image, ImageTk
import threading
import pygame
import time
import face_recognition
import numpy as np
import mysql.connector

# Inicializa pygame para sonido
pygame.mixer.init()
ALERTA_SONIDO_RECONOCIDO = "confirmacion.mp3"
ALERTA_SONIDO_NO_RECONOCIDO = "error.mp3"

class DeteccionMovimientoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Detector de Movimiento y Reconocimiento Facial")
        self.root.geometry("700x550")
        self.root.resizable(False, False)

        self.frame_principal = tk.Frame(self.root)
        self.frame_principal.pack()

        self.label_video = tk.Label(self.frame_principal)
        self.label_video.pack()

        self.frame_botones = tk.Frame(self.frame_principal)
        self.frame_botones.pack(pady=10)

        self.btn_iniciar = tk.Button(self.frame_botones, text="Iniciar Detección", command=self.iniciar)
        self.btn_iniciar.grid(row=0, column=0, padx=5)

        self.btn_detener = tk.Button(self.frame_botones, text="Detener", command=self.detener, state=tk.DISABLED)
        self.btn_detener.grid(row=0, column=1, padx=5)

        self.btn_registrar = tk.Button(self.frame_botones, text="Registrar Persona", command=self.registrar)
        self.btn_registrar.grid(row=0, column=2, padx=5)
        self.btn_registrar.config(state=tk.DISABLED)

        self.cap = None
        self.running = False
        self.frame_anterior = None
        self.procesando = False
        self.ultimo_reconocimiento = 0
        self.nombre_reconocido = []

        self.inicializar_base_datos()
        self.datos_registrados = self.cargar_datos_registrados()

    def inicializar_base_datos(self):
        self.conexion = mysql.connector.connect(
            host="192.168.1.120",
            user="prueba1",
            password="",  # Agrega tu contraseña si aplica
            database="seguridad"  # Cambia por el nombre real de tu base de datos
        )
        self.cursor = self.conexion.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS reconocimiento (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(255) NOT NULL UNIQUE,
                imagen LONGBLOB NOT NULL,
                encoding LONGBLOB NOT NULL
            )
        """)
        self.conexion.commit()

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

    def reproducir_sonido(self, archivo_sonido):
        def play():
            try:
                time.sleep(1)
                pygame.mixer.music.load(archivo_sonido)
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
                encoding = self.extraer_encoding(rostro)
                if encoding is not None:
                    _, imagen_codificada = cv2.imencode('.jpg', rostro)
                    imagen_bytes = imagen_codificada.tobytes()
                    encoding_bytes = encoding.tobytes()
                    try:
                        self.cursor.execute("INSERT INTO reconocimiento (nombre, imagen, encoding) VALUES (%s, %s, %s)", (nombre, imagen_bytes, encoding_bytes))
                        self.conexion.commit()
                        self.datos_registrados[nombre] = encoding
                        print(f"✅ Persona registrada: {nombre}")
                    except mysql.connector.IntegrityError:
                        print("⚠️ El nombre ya está registrado.")
                else:
                    print("⚠️ No se pudo extraer encoding.")
            else:
                print("⚠️ No se detectó rostro.")
        else:
            print("❌ Error al capturar la imagen.")

    def cargar_datos_registrados(self):
        datos = {}
        self.cursor.execute("SELECT nombre, encoding FROM reconocimiento")
        for nombre, encoding_bytes in self.cursor.fetchall():
            encoding = np.frombuffer(encoding_bytes, dtype=np.float64)
            datos[nombre] = encoding
        return datos

    def extraer_encoding(self, rostro):
        rostro_rgb = cv2.cvtColor(rostro, cv2.COLOR_BGR2RGB)
        ubicaciones = face_recognition.face_locations(rostro_rgb)
        encodings = face_recognition.face_encodings(rostro_rgb, ubicaciones)
        if len(encodings) > 0:
            return encodings[0]
        return None

    def detectar_rostro(self, frame):
        rostro_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ubicaciones = face_recognition.face_locations(rostro_rgb)
        if len(ubicaciones) > 0:
            top, right, bottom, left = ubicaciones[0]
            return frame[top:bottom, left:right]
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

                    movimiento_detectado = any(cv2.contourArea(c) > 1000 for c in contornos)
                    self.frame_anterior = gris

                    if movimiento_detectado and not self.procesando and (time.time() - self.ultimo_reconocimiento > 5):
                        self.procesando = True
                        frame_pequeno = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

                        def reconocimiento_async():
                            rostros_encontrados, nombres = self.reconocer_rostros(frame_pequeno)
                            if rostros_encontrados:
                                rostros_ajustados = [(t*4, r*4, b*4, l*4, n) for (t, r, b, l, n) in rostros_encontrados]
                                self.rostros_actuales = rostros_ajustados
                                self.nombre_reconocido = nombres
                                print("Rostros reconocidos:", nombres)
                                sonido = ALERTA_SONIDO_RECONOCIDO if nombres else ALERTA_SONIDO_NO_RECONOCIDO
                                self.reproducir_sonido(sonido)
                            else:
                                self.rostros_actuales = []
                                self.nombre_reconocido = []
                                print("No se detectó ningún rostro")
                                self.reproducir_sonido(ALERTA_SONIDO_NO_RECONOCIDO)
                            self.ultimo_reconocimiento = time.time()
                            self.procesando = False

                        threading.Thread(target=reconocimiento_async, daemon=True).start()

                if hasattr(self, 'rostros_actuales'):
                    for (top, right, bottom, left, nombre) in self.rostros_actuales:
                        color = (0, 255, 0) if nombre != "Desconocido" else (0, 0, 255)
                        texto = f"Bienvenido {nombre}" if nombre != "Desconocido" else "ROSTRO NO REGISTRADO"
                        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                        cv2.putText(frame, texto, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

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
