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
        self.root.title("Detector de Movimiento y Reconocimiento Facial - Dos Cámaras")
        self.root.geometry("1400x600")
        self.root.resizable(False, False)

        self.frame_principal = tk.Frame(self.root)
        self.frame_principal.pack()

        # Dos labels para video
        self.label_video1 = tk.Label(self.frame_principal)
        self.label_video1.grid(row=0, column=0, padx=10)

        self.label_video2 = tk.Label(self.frame_principal)
        self.label_video2.grid(row=0, column=1, padx=10)

        self.frame_botones = tk.Frame(self.root)
        self.frame_botones.pack(pady=10)

        self.btn_iniciar = tk.Button(self.frame_botones, text="Iniciar Detección", command=self.iniciar)
        self.btn_iniciar.grid(row=0, column=0, padx=5)

        self.btn_detener = tk.Button(self.frame_botones, text="Detener", command=self.detener, state=tk.DISABLED)
        self.btn_detener.grid(row=0, column=1, padx=5)

        self.btn_registrar = tk.Button(self.frame_botones, text="Registrar Persona", command=self.registrar)
        self.btn_registrar.grid(row=0, column=2, padx=5)
        self.btn_registrar.config(state=tk.DISABLED)

        # Capturas y flags para dos cámaras
        self.cap1 = None
        self.cap2 = None
        self.running = False
        self.frame_anterior1 = None
        self.frame_anterior2 = None
        self.procesando1 = False
        self.procesando2 = False
        self.ultimo_reconocimiento1 = 0
        self.ultimo_reconocimiento2 = 0
        self.nombre_reconocido1 = []
        self.nombre_reconocido2 = []

        self.inicializar_base_datos()
        self.datos_registrados = self.cargar_datos_registrados()

    def inicializar_base_datos(self):
        self.conexion = mysql.connector.connect(
            host="192.168.1.122",
            user="ojodigital",
            password="feria2025",
            database="ojodigital"
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
            self.cap1 = cv2.VideoCapture(0)
            self.cap2 = cv2.VideoCapture(2)

            if not self.cap1.isOpened():
                print("❌ No se pudo abrir la cámara 0.")
                self.cap1 = None
            if not self.cap2.isOpened():
                print("❌ No se pudo abrir la cámara 2.")
                self.cap2 = None

            if self.cap1 is None and self.cap2 is None:
                print("❌ No se pudo abrir ninguna cámara. Abortando.")
                return

            self.running = True
            self.btn_iniciar.config(state=tk.DISABLED)
            self.btn_detener.config(state=tk.NORMAL)
            self.btn_registrar.config(state=tk.NORMAL)
            self.detectar()

    def detener(self):
        self.running = False
        if self.cap1:
            self.cap1.release()
            self.cap1 = None
        if self.cap2:
            self.cap2.release()
            self.cap2 = None

        self.label_video1.config(image="")
        self.label_video2.config(image="")
        self.btn_iniciar.config(state=tk.NORMAL)
        self.btn_detener.config(state=tk.DISABLED)
        self.btn_registrar.config(state=tk.DISABLED)
        self.frame_anterior1 = None
        self.frame_anterior2 = None
        self.nombre_reconocido1 = []
        self.nombre_reconocido2 = []

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
                # Intenta registrar con la camara1 primero, si falla usa camara2
                if self.cap1 and self.cap1.isOpened():
                    self.registrar_persona(nombre, self.cap1)
                elif self.cap2 and self.cap2.isOpened():
                    self.registrar_persona(nombre, self.cap2)
                else:
                    print("❌ No hay cámara disponible para registrar.")
                ventana_registro.destroy()

        ventana_registro = tk.Toplevel(self.root)
        ventana_registro.title("Registrar Persona")
        ventana_registro.geometry("400x200")

        tk.Label(ventana_registro, text="Nombre:").pack(pady=5)
        nombre_entry = tk.Entry(ventana_registro)
        nombre_entry.pack(pady=5)

        tk.Button(ventana_registro, text="Registrar", command=registrar_accion).pack(pady=10)

    def registrar_persona(self, nombre, camara):
        ret, frame = camara.read()
        frame = cv2.flip(frame, 1)
        if ret:
            rostro = self.detectar_rostro(frame)
            if rostro is not None:
                encoding = self.extraer_encoding(rostro)
                if encoding is not None:
                    _, imagen_codificada = cv2.imencode('.jpg', rostro)
                    imagen_bytes = imagen_codificada.tobytes()
                    encoding_bytes = encoding.tobytes()
                    try:
                        self.cursor.execute("INSERT INTO reconocimiento (nombre, imagen, encoding) VALUES (%s, %s, %s)",
                                            (nombre, imagen_bytes, encoding_bytes))
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
            print("❌ Error al capturar la imagen para registrar.")

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
        if not self.running:
            return

        # Procesar camara 1
        if self.cap1 and self.cap1.isOpened():
            ret1, frame1 = self.cap1.read()
            if ret1:
                frame1 = cv2.flip(frame1, 1)
                gris1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
                gris1 = cv2.GaussianBlur(gris1, (21, 21), 0)

                if self.frame_anterior1 is None:
                    self.frame_anterior1 = gris1
                else:
                    delta1 = cv2.absdiff(self.frame_anterior1, gris1)
                    thresh1 = cv2.threshold(delta1, 25, 255, cv2.THRESH_BINARY)[1]
                    thresh1 = cv2.dilate(thresh1, None, iterations=2)
                    contornos1, _ = cv2.findContours(thresh1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    movimiento_detectado1 = any(cv2.contourArea(c) > 1000 for c in contornos1)
                    self.frame_anterior1 = gris1

                    if movimiento_detectado1 and not self.procesando1 and (time.time() - self.ultimo_reconocimiento1 > 5):
                        self.procesando1 = True
                        frame_pequeno1 = cv2.resize(frame1, (0, 0), fx=0.25, fy=0.25)

                        def reconocimiento_async_1():
                            rostros_encontrados1, nombres1 = self.reconocer_rostros(frame_pequeno1)
                            if rostros_encontrados1:
                                rostros_ajustados1 = [(t*4, r*4, b*4, l*4, n) for (t, r, b, l, n) in rostros_encontrados1]
                                self.rostros_actuales1 = rostros_ajustados1
                                self.nombre_reconocido1 = nombres1
                                print("Cámara 1 - Rostros reconocidos:", nombres1)
                                sonido = ALERTA_SONIDO_RECONOCIDO if nombres1 else ALERTA_SONIDO_NO_RECONOCIDO
                                self.reproducir_sonido(sonido)
                            else:
                                self.rostros_actuales1 = []
                                self.nombre_reconocido1 = []
                                print("Cámara 1 - No se detectó ningún rostro")
                                self.reproducir_sonido(ALERTA_SONIDO_NO_RECONOCIDO)
                            self.ultimo_reconocimiento1 = time.time()
                            self.procesando1 = False

                        threading.Thread(target=reconocimiento_async_1, daemon=True).start()

                if hasattr(self, 'rostros_actuales1'):
                    for (top, right, bottom, left, nombre) in self.rostros_actuales1:
                        color = (0, 255, 0) if nombre != "Desconocido" else (0, 0, 255)
                        texto = f"Bienvenido {nombre}" if nombre != "Desconocido" else "ROSTRO NO REGISTRADO"
                        cv2.rectangle(frame1, (left, top), (right, bottom), color, 2)
                        cv2.putText(frame1, texto, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                img1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)
                img1 = Image.fromarray(img1)
                imgtk1 = ImageTk.PhotoImage(image=img1)
                self.label_video1.imgtk = imgtk1
                self.label_video1.configure(image=imgtk1)

        # Procesar camara 2
        if self.cap2 and self.cap2.isOpened():
            ret2, frame2 = self.cap2.read()
            if ret2:
                frame2 = cv2.flip(frame2, 1)
                gris2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
                gris2 = cv2.GaussianBlur(gris2, (21, 21), 0)

                if self.frame_anterior2 is None:
                    self.frame_anterior2 = gris2
                else:
                    delta2 = cv2.absdiff(self.frame_anterior2, gris2)
                    thresh2 = cv2.threshold(delta2, 25, 255, cv2.THRESH_BINARY)[1]
                    thresh2 = cv2.dilate(thresh2, None, iterations=2)
                    contornos2, _ = cv2.findContours(thresh2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    movimiento_detectado2 = any(cv2.contourArea(c) > 1000 for c in contornos2)
                    self.frame_anterior2 = gris2

                    if movimiento_detectado2 and not self.procesando2 and (time.time() - self.ultimo_reconocimiento2 > 5):
                        self.procesando2 = True
                        frame_pequeno2 = cv2.resize(frame2, (0, 0), fx=0.25, fy=0.25)

                        def reconocimiento_async_2():
                            rostros_encontrados2, nombres2 = self.reconocer_rostros(frame_pequeno2)
                            if rostros_encontrados2:
                                rostros_ajustados2 = [(t*4, r*4, b*4, l*4, n) for (t, r, b, l, n) in rostros_encontrados2]
                                self.rostros_actuales2 = rostros_ajustados2
                                self.nombre_reconocido2 = nombres2
                                print("Cámara 2 - Rostros reconocidos:", nombres2)
                                sonido = ALERTA_SONIDO_RECONOCIDO if nombres2 else ALERTA_SONIDO_NO_RECONOCIDO
                                self.reproducir_sonido(sonido)
                            else:
                                self.rostros_actuales2 = []
                                self.nombre_reconocido2 = []
                                print("Cámara 2 - No se detectó ningún rostro")
                                self.reproducir_sonido(ALERTA_SONIDO_NO_RECONOCIDO)
                            self.ultimo_reconocimiento2 = time.time()
                            self.procesando2 = False

                        threading.Thread(target=reconocimiento_async_2, daemon=True).start()

                if hasattr(self, 'rostros_actuales2'):
                    for (top, right, bottom, left, nombre) in self.rostros_actuales2:
                        color = (0, 255, 0) if nombre != "Desconocido" else (0, 0, 255)
                        texto = f"Bienvenido {nombre}" if nombre != "Desconocido" else "ROSTRO NO REGISTRADO"
                        cv2.rectangle(frame2, (left, top), (right, bottom), color, 2)
                        cv2.putText(frame2, texto, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                img2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
                img2 = Image.fromarray(img2)
                imgtk2 = ImageTk.PhotoImage(image=img2)
                self.label_video2.imgtk = imgtk2
                self.label_video2.configure(image=imgtk2)

        # Continuar el ciclo
        if self.running:
            self.root.after(30, self.detectar)

if __name__ == "__main__":
    root = tk.Tk()
    app = DeteccionMovimientoApp(root)
    root.mainloop()
