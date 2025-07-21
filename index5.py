import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
import pygame
import time
import face_recognition
import numpy as np
import mysql.connector
from io import BytesIO

pygame.mixer.init()
ALERTA_SONIDO_RECONOCIDO = "confirmacion.mp3"
ALERTA_SONIDO_NO_RECONOCIDO = "error.mp3"

class DeteccionMovimientoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Detector de Movimiento y Reconocimiento Facial")
        self.root.geometry("800x650")
        self.root.resizable(False, False)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#e0e0e0')
        style.configure('TButton', font=('Helvetica Neue', 10), padding=8, background='#4CAF50', foreground='white')
        style.map('TButton', background=[('active', '#45a049')])
        style.configure('TLabel', font=('Helvetica Neue', 12), background="#f80d0d")

        self.frame_principal = ttk.Frame(self.root, padding=20, style='TFrame')
        self.frame_principal.pack(expand=True, fill='both')

        self.label_video = tk.Label(self.frame_principal, bg="black", bd=2, relief="sunken")
        self.label_video.pack(pady=10, fill='both', expand=True)

        self.frame_botones = ttk.Frame(self.frame_principal, padding=10, style='TFrame')
        self.frame_botones.pack(pady=15)

        self.btn_iniciar = ttk.Button(self.frame_botones, text="Iniciar Detección", command=self.iniciar, style='TButton')
        self.btn_iniciar.grid(row=0, column=0, padx=10, pady=5)

        self.btn_detener = ttk.Button(self.frame_botones, text="Detener", command=self.detener, state=tk.DISABLED, style='TButton')
        self.btn_detener.grid(row=0, column=1, padx=10, pady=5)

        self.btn_registrar = ttk.Button(self.frame_botones, text="Registrar Persona", command=self.registrar, state=tk.DISABLED, style='TButton')
        self.btn_registrar.grid(row=0, column=2, padx=10, pady=5)

        self.btn_ver_datos_imagenes = ttk.Button(self.frame_botones, text="Ver Datos con Imágenes", command=self.mostrar_datos_con_imagenes, style='TButton')
        self.btn_ver_datos_imagenes.grid(row=0, column=4, padx=10, pady=5)

        self.status_label = ttk.Label(self.root, text="Estado: Listo", anchor='w', font=('Helvetica Neue', 10), background='#c0c0c0', padding=5)
        self.status_label.pack(side='bottom', fill='x')

        self.cap = None
        self.running = False
        self.frame_anterior = None
        self.procesando = False
        self.ultimo_reconocimiento = 0
        self.nombre_reconocido = []

        self.inicializar_base_datos()
        self.datos_registrados = self.cargar_datos_registrados()

        self.root.protocol("WM_DELETE_WINDOW", self.cerrar)

    def inicializar_base_datos(self):
        try:
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
                    edad VARCHAR(255) NOT NULL,
                    rut VARCHAR(255) NOT NULL UNIQUE,
                    fecha VARCHAR(255) NOT NULL,
                    imagen LONGBLOB NOT NULL,
                    encoding LONGBLOB NOT NULL
                )
            """)
            self.conexion.commit()
        except mysql.connector.Error as err:
            print(f"❌ Error al conectar con la base de datos: {err}")

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

    def cerrar(self):
        self.detener()
        if self.conexion.is_connected():
            self.cursor.close()
            self.conexion.close()
        self.root.destroy()

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
            edad = edad_entry.get()
            rut = rut_entry.get()
            fecha = fecha_entry.get()

            if nombre and edad and rut and fecha:
                self.registrar_persona(nombre, edad, rut, fecha)
                ventana_registro.destroy()
            else:
                print("⚠️ Por favor, completa todos los campos.")

        ventana_registro = tk.Toplevel(self.root)
        ventana_registro.title("Registrar Persona")
        ventana_registro.geometry("400x300")

        for campo in ["Nombre", "Edad", "RUT", "Fecha (YYYY-MM-DD)"]:
            tk.Label(ventana_registro, text=campo + ":").pack(pady=5)
            entry = tk.Entry(ventana_registro)
            entry.pack(pady=5)
            if campo == "Nombre": nombre_entry = entry
            elif campo == "Edad": edad_entry = entry
            elif campo == "RUT": rut_entry = entry
            elif campo.startswith("Fecha"): fecha_entry = entry

        tk.Button(ventana_registro, text="Registrar", command=registrar_accion).pack(pady=10)

    def registrar_persona(self, nombre, edad, rut, fecha):
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
                        self.cursor.execute(
                            "INSERT INTO reconocimiento (nombre, edad, rut, fecha, imagen, encoding) VALUES (%s, %s, %s, %s, %s, %s)",
                            (nombre, edad, rut, fecha, imagen_bytes, encoding_bytes)
                        )
                        self.conexion.commit()
                        self.datos_registrados[nombre] = {
                            'encoding': encoding,
                            'edad': edad,
                            'rut': rut,
                            'fecha': fecha
                        }
                        print(f"✅ Persona registrada: {nombre}")
                    except mysql.connector.IntegrityError:
                        print("⚠️ El nombre o RUT ya están registrados.")
                else:
                    print("⚠️ No se pudo extraer encoding.")
            else:
                print("⚠️ No se detectó rostro.")
        else:
            print("❌ Error al capturar la imagen.")

    def cargar_datos_registrados(self):
        datos = {}
        self.cursor.execute("SELECT nombre, edad, rut, fecha, encoding FROM reconocimiento")
        for nombre, edad, rut, fecha, encoding_bytes in self.cursor.fetchall():
            encoding = np.frombuffer(encoding_bytes, dtype=np.float64)
            datos[nombre] = {
                'encoding': encoding,
                'edad': edad,
                'rut': rut,
                'fecha': fecha
            }
        return datos

    def extraer_encoding(self, rostro):
        rostro_rgb = cv2.cvtColor(rostro, cv2.COLOR_BGR2RGB)
        ubicaciones = face_recognition.face_locations(rostro_rgb)
        encodings = face_recognition.face_encodings(rostro_rgb, ubicaciones)
        return encodings[0] if encodings else None

    def detectar_rostro(self, frame):
        rostro_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ubicaciones = face_recognition.face_locations(rostro_rgb)
        if ubicaciones:
            top, right, bottom, left = ubicaciones[0]
            return frame[top:bottom, left:right]
        return None

    def reconocer_rostros(self, frame):
        rostros_encontrados, datos_reconocidos = [], []
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ubicaciones = face_recognition.face_locations(frame_rgb)
        encodings = face_recognition.face_encodings(frame_rgb, ubicaciones)

        enc_bd = [persona['encoding'] for persona in self.datos_registrados.values()]
        nombres_bd = list(self.datos_registrados.keys())

        for encoding, (top, right, bottom, left) in zip(encodings, ubicaciones):
            nombre = "Desconocido"
            info = None
            matches = face_recognition.compare_faces(enc_bd, encoding, tolerance=0.45)
            distances = face_recognition.face_distance(enc_bd, encoding)

            if matches:
                best_index = np.argmin(distances)
                if matches[best_index]:
                    nombre = nombres_bd[best_index]
                    info = self.datos_registrados[nombre]

            rostros_encontrados.append((top, right, bottom, left, nombre, info))
        return rostros_encontrados

    def detectar(self):
        if self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gris = cv2.GaussianBlur(gris, (21, 21), 0)

                if self.frame_anterior is None:
                    self.frame_anterior = gris
                else:
                    delta = cv2.absdiff(self.frame_anterior, gris)
                    thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
                    thresh = cv2.dilate(thresh, None, iterations=2)
                    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    movimiento = any(cv2.contourArea(c) > 1000 for c in contornos)
                    self.frame_anterior = gris

                    if movimiento and not self.procesando and (time.time() - self.ultimo_reconocimiento > 5):
                        self.procesando = True
                        frame_pequeno = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

                        def reconocimiento_async():
                            rostros = self.reconocer_rostros(frame_pequeno)
                            if rostros:
                                self.rostros_actuales = [(t*4, r*4, b*4, l*4, n, i) for (t, r, b, l, n, i) in rostros]
                                sonido = ALERTA_SONIDO_RECONOCIDO if any(n != "Desconocido" for (_, _, _, _, n, _) in self.rostros_actuales) else ALERTA_SONIDO_NO_RECONOCIDO
                                self.reproducir_sonido(sonido)
                            else:
                                self.rostros_actuales = []
                                self.reproducir_sonido(ALERTA_SONIDO_NO_RECONOCIDO)
                            self.ultimo_reconocimiento = time.time()
                            self.procesando = False

                        threading.Thread(target=reconocimiento_async, daemon=True).start()

                if hasattr(self, 'rostros_actuales'):
                    for (top, right, bottom, left, nombre, info) in self.rostros_actuales:
                        color = (0, 255, 0) if nombre != "Desconocido" else (0, 0, 255)
                        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

                        if nombre != "Desconocido" and info:
                            texto = f"{nombre} - {info['edad']} años\nRUT: {info['rut']}\nFecha: {info['fecha']}"
                        else:
                            texto = "ROSTRO NO REGISTRADO"

                        y_text = top - 10
                        for linea in texto.split('\n'):
                            cv2.putText(frame, linea, (left, y_text), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                            y_text -= 25

                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                imgtk = ImageTk.PhotoImage(Image.fromarray(img))
                self.label_video.imgtk = imgtk
                self.label_video.configure(image=imgtk)

            self.root.after(30, self.detectar)

    def mostrar_datos_con_imagenes(self):
        self.cursor.execute("SELECT nombre, edad, rut, fecha, imagen FROM reconocimiento")
        resultados = self.cursor.fetchall()

        ventana = tk.Toplevel(self.root)
        ventana.title("Datos con Imágenes")
        ventana.geometry("400x600")

        canvas = tk.Canvas(ventana)
        scrollbar = ttk.Scrollbar(ventana, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.imagenes_mostradas = []

        if resultados:
            for nombre, edad, rut, fecha, imagen_blob in resultados:
                imagen_pil = Image.open(BytesIO(imagen_blob)).resize((100, 100))
                imagen_tk = ImageTk.PhotoImage(imagen_pil)
                self.imagenes_mostradas.append(imagen_tk)

                frame_item = ttk.Frame(scrollable_frame, padding=5, relief="ridge")
                frame_item.pack(fill="x", pady=5)

                ttk.Label(frame_item, image=imagen_tk).pack(side="left")
                info_frame = ttk.Frame(frame_item)
                info_frame.pack(side="left", padx=10)

                for txt in [f"Nombre: {nombre}", f"Edad: {edad}", f"RUT: {rut}", f"Fecha: {fecha}"]:
                    ttk.Label(info_frame, text=txt).pack(anchor="w")
        else:
            ttk.Label(scrollable_frame, text="La base de datos está vacía.").pack(pady=20)

if __name__ == "__main__":
    root = tk.Tk()
    app = DeteccionMovimientoApp(root)
    root.mainloop()
