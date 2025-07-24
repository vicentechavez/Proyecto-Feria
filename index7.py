import os
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
import sqlite3
from datetime import datetime

pygame.mixer.init()
ALERTA_SONIDO_RECONOCIDO = "confirmacion.mp3"
ALERTA_SONIDO_NO_RECONOCIDO = "error.mp3"

class DeteccionMovimientoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Detector de Movimiento y Reconocimiento Facial")
        self.root.geometry("1000x700")
        self.root.resizable(False, False)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#e0e0e0')
        style.configure('TButton', font=('Helvetica Neue', 10), padding=8, background='#4CAF50', foreground='white')
        style.map('TButton', background=[('active', '#45a049')])
        style.configure('TLabel', font=('Helvetica Neue', 12), background="#e0e0e0")

        self.frame_principal = ttk.Frame(self.root, padding=20, style='TFrame')
        self.frame_principal.pack(expand=True, fill='both')

        # Video
        self.label_video = tk.Label(self.frame_principal, bg="black", bd=2, relief="sunken")
        self.label_video.grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky='nsew')

        # Panel lateral de datos
        self.panel_datos = ttk.LabelFrame(self.frame_principal, text="Datos Reconocidos", padding=10)
        self.panel_datos.grid(row=0, column=2, padx=10, pady=10, sticky='n')

        self.labels_datos = {}
        for campo in ['Nombre', 'Edad', 'RUT', 'Fecha']:
            lbl = ttk.Label(self.panel_datos, text=f"{campo}: ---")
            lbl.pack(anchor='w', pady=5)
            self.labels_datos[campo] = lbl

        # Botones
        self.frame_botones = ttk.Frame(self.frame_principal, padding=10, style='TFrame')
        self.frame_botones.grid(row=1, column=0, columnspan=3, pady=10)

        self.btn_iniciar = ttk.Button(self.frame_botones, text="Iniciar Detección", command=self.iniciar, style='TButton')
        self.btn_iniciar.grid(row=0, column=0, padx=10, pady=5)

        self.btn_detener = ttk.Button(self.frame_botones, text="Detener", command=self.detener, state=tk.DISABLED, style='TButton')
        self.btn_detener.grid(row=0, column=1, padx=10, pady=5)

        self.btn_registrar = ttk.Button(self.frame_botones, text="Registrar Persona", command=self.registrar, state=tk.DISABLED, style='TButton')
        self.btn_registrar.grid(row=0, column=2, padx=10, pady=5)

        self.btn_ver_datos_imagenes = ttk.Button(self.frame_botones, text="Ver Datos Locales", command=self.mostrar_datos_locales, style='TButton')
        self.btn_ver_datos_imagenes.grid(row=0, column=3, padx=10, pady=5)

        self.status_label = ttk.Label(self.root, text="Estado: Listo", anchor='w', font=('Helvetica Neue', 10), background='#c0c0c0', padding=5)
        self.status_label.pack(side='bottom', fill='x')

        self.cap = None
        self.running = False
        self.frame_anterior = None
        self.procesando = False
        self.last_detection_time = {} # To store the last detection time for each person

        # Timer for periodic face recognition
        self.recognition_timer = None
        self.face_detection_interval = 5 # seconds
        self.cooldown_period = 60 # seconds (1 minute)

        self.inicializar_base_datos_mysql()
        self.inicializar_base_datos_local()
        self.datos_registrados = self.cargar_datos_registrados_mysql()
        self.encodings_registrados = self.cargar_encodings_registrados()

        self.root.protocol("WM_DELETE_WINDOW", self.cerrar)

    def inicializar_base_datos_mysql(self):
        try:
            self.conexion = mysql.connector.connect(
                host="192.168.1.122",
                user="ojodigital",
                password="feria2025",
                database="ojodigital",
                charset="utf8",
                use_unicode=True
            )
            self.cursor = self.conexion.cursor()
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS reconocimiento (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(255) NOT NULL,
                    edad VARCHAR(255) NOT NULL,
                    rut VARCHAR(255) NOT NULL,
                    fecha VARCHAR(255) NOT NULL,
                    id_imagen INT NOT NULL,
                    UNIQUE (nombre),
                    UNIQUE (rut)
                );
            """)
            self.conexion.commit()
            print("✅ MySQL inicializada.")
        except mysql.connector.Error as err:
            print("❌ Error MySQL:", err)

    def cargar_datos_registrados_mysql(self):
        datos = {}
        try:
            self.cursor.execute("SELECT nombre, edad, rut, fecha, id_imagen FROM reconocimiento")
            for nombre, edad, rut, fecha, id_imagen in self.cursor.fetchall():
                datos[nombre] = {
                    'edad': edad,
                    'rut': rut,
                    'fecha': fecha,
                    'id_imagen': id_imagen
                }
        except mysql.connector.Error as err:
            print("❌ Error cargando datos MySQL:", err)
        return datos

    def cargar_encodings_registrados(self):
        encodings = {}
        for nombre, datos in self.datos_registrados.items():
            path_encoding = f"imagenes/id_{datos['id_imagen']}_encoding.npy"
            if os.path.exists(path_encoding):
                encoding = np.load(path_encoding)
                encodings[nombre] = encoding
            else:
                print(f"⚠️ No se encontró encoding para {nombre}")
        return encodings

    def inicializar_base_datos_local(self):
        if not os.path.exists("imagenes"):
            os.makedirs("imagenes")
        self.db_local = sqlite3.connect("base_datos.db")
        self.cursor_local = self.db_local.cursor()
        self.cursor_local.execute("""
        CREATE TABLE IF NOT EXISTS personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imagen_archivo TEXT NOT NULL
        )
        """)
        self.db_local.commit()
        print("✅ SQLite inicializada.")

    def registrar(self):
        def registrar_accion():
            nombre = entradas["nombre"].get().strip()
            edad = entradas["edad"].get().strip()
            rut = entradas["rut"].get().strip()
            fecha = datetime.now().strftime("%Y-%m-%d")
            if nombre and edad and rut:
                self.registrar_persona(nombre, edad, rut, fecha)
                ventana_registro.destroy()
            else:
                print("⚠️ Completa todos los campos.")

        ventana_registro = tk.Toplevel(self.root)
        ventana_registro.title("Registrar Persona")
        ventana_registro.geometry("400x250")

        campos = ["nombre", "edad", "rut"]
        entradas = {}

        for campo in campos:
            ttk.Label(ventana_registro, text=campo.capitalize() + ":").pack(pady=5)
            entrada = ttk.Entry(ventana_registro)
            entrada.pack(pady=5)
            entradas[campo] = entrada

        ttk.Button(ventana_registro, text="Registrar", command=registrar_accion).pack(pady=10)

    def registrar_persona(self, nombre, edad, rut, fecha):
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
        ret, frame = self.cap.read()
        if ret:
            rostro = self.detectar_rostro(frame)
            if rostro is None:
                print("⚠️ No se detectó rostro.")
                return
            encoding = self.extraer_encoding(rostro)
            if encoding is None:
                print("⚠️ No se pudo extraer encoding.")
                return

            self.cursor_local.execute("INSERT INTO personas (imagen_archivo) VALUES ('temp')")
            self.db_local.commit()
            new_id = self.cursor_local.lastrowid
            nombre_archivo = f"imagenes/id_{new_id}.jpg"
            cv2.imwrite(nombre_archivo, rostro)
            np.save(f"imagenes/id_{new_id}_encoding.npy", encoding)

            self.cursor_local.execute("UPDATE personas SET imagen_archivo = ? WHERE id = ?", (nombre_archivo, new_id))
            self.db_local.commit()

            try:
                self.cursor.execute(
                    "INSERT INTO reconocimiento (nombre, edad, rut, fecha, id_imagen) VALUES (%s,%s,%s,%s,%s)",
                    (nombre, edad, rut, fecha, new_id))
                self.conexion.commit()
                self.datos_registrados[nombre] = {
                    'edad': edad,
                    'rut': rut,
                    'fecha': fecha,
                    'id_imagen': new_id
                }
                self.encodings_registrados[nombre] = encoding
                self.status_label.config(text=f"Registrado: {nombre}")
                print(f"✅ Registrado {nombre} con imagen ID {new_id}")
            except mysql.connector.IntegrityError as e:
                print("❌ Error al registrar en MySQL:", e)
                self.cursor_local.execute("DELETE FROM personas WHERE id = ?", (new_id,))
                self.db_local.commit()

    def detectar_rostro(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        loc = face_recognition.face_locations(rgb)
        if not loc:
            return None
        t, r, b, l = loc[0]
        return frame[t:b, l:r]

    def extraer_encoding(self, rostro):
        rgb = cv2.cvtColor(rostro, cv2.COLOR_BGR2RGB)
        loc = face_recognition.face_locations(rgb)
        enc = face_recognition.face_encodings(rgb, loc)
        return enc[0] if enc else None

    def reconocer_rostros(self, frame):
        resultados = []
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locs = face_recognition.face_locations(rgb)
        encs = face_recognition.face_encodings(rgb, locs)

        for encoding, loc in zip(encs, locs):
            nombre_encontrado = "Desconocido"
            for nombre, known_encoding in self.encodings_registrados.items():
                matches = face_recognition.compare_faces([known_encoding], encoding, tolerance=0.5)
                if matches[0]:
                    nombre_encontrado = nombre
                    break
            resultados.append((nombre_encontrado, loc))
        return resultados

    def sonar_confirmacion(self):
        pygame.mixer.music.load(ALERTA_SONIDO_RECONOCIDO)
        pygame.mixer.music.play()

    def sonar_error(self):
        pygame.mixer.music.load(ALERTA_SONIDO_NO_RECONOCIDO)
        pygame.mixer.music.play()

    def actualizar_video(self):
        if not self.running:
            return
        ret, frame = self.cap.read()
        if not ret:
            self.status_label.config(text="Error accediendo a cámara.")
            return

        # Flip the frame horizontally (mirror effect)
        frame = cv2.flip(frame, 1)

        gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gris = cv2.GaussianBlur(gris, (21, 21), 0)

        if self.frame_anterior is None:
            self.frame_anterior = gris
            self.mostrar_frame(frame)
        else:
            diff = cv2.absdiff(self.frame_anterior, gris)
            umbral = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
            umbral = cv2.dilate(umbral, None, iterations=2)
            cnts, _ = cv2.findContours(umbral.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            movimiento_detectado = any(cv2.contourArea(c) > 5000 for c in cnts)

            # Removed the direct call to procesar_reconocimiento here.
            # It will now be called by the timer.

            self.frame_anterior = gris
            self.mostrar_frame(frame)

        self.root.after(30, self.actualizar_video)

    def iniciar_reconocimiento_periodico(self):
        if self.running and not self.procesando:
            # Capture a fresh frame for processing
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.flip(frame, 1) # Ensure consistency with displayed frame
                    threading.Thread(target=self.procesar_reconocimiento, args=(frame.copy(),)).start()
        # Schedule the next recognition
        if self.running:
            self.recognition_timer = threading.Timer(self.face_detection_interval, self.iniciar_reconocimiento_periodico)
            self.recognition_timer.start()

    def procesar_reconocimiento(self, frame):
        self.procesando = True
        try:
            resultados = self.reconocer_rostros(frame)
            rostro_reconocido_actual = False
            nombre_final = None
            current_time = time.time()

            for nombre, (top, right, bottom, left) in resultados:
                color = (0, 255, 0) if nombre != "Desconocido" else (0, 0, 255)
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.putText(frame, nombre, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

                if nombre != "Desconocido":
                    # Check cooldown for the recognized person
                    if nombre not in self.last_detection_time or \
                       (current_time - self.last_detection_time[nombre]) > self.cooldown_period:
                        rostro_reconocido_actual = True
                        nombre_final = nombre
                        self.last_detection_time[nombre] = current_time # Update last detection time
                        break # Only process the first recognized person

            if rostro_reconocido_actual:
                self.sonar_confirmacion()
                self.mostrar_datos_panel(nombre_final)
            else:
                self.limpiar_datos_panel() # Clear panel if no new recognition or if cooldown is active

            self.mostrar_frame(frame)
        finally:
            self.procesando = False

    def mostrar_datos_panel(self, nombre):
        datos = self.datos_registrados.get(nombre)
        if datos:
            self.labels_datos["Nombre"].config(text=f"Nombre: {nombre}")
            self.labels_datos["Edad"].config(text=f"Edad: {datos['edad']}")
            self.labels_datos["RUT"].config(text=f"RUT: {datos['rut']}")
            self.labels_datos["Fecha"].config(text=f"Fecha: {datos['fecha']}")

    def limpiar_datos_panel(self):
        for campo in self.labels_datos:
            self.labels_datos[campo].config(text=f"{campo}: ---")

    def mostrar_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.label_video.imgtk = imgtk
        self.label_video.configure(image=imgtk)

    def iniciar(self):
        self.cap = cv2.VideoCapture(0)
        self.running = True
        self.btn_iniciar.config(state=tk.DISABLED)
        self.btn_detener.config(state=tk.NORMAL)
        self.btn_registrar.config(state=tk.NORMAL)
        self.status_label.config(text="Estado: Detección iniciada")
        self.actualizar_video()
        # Start the periodic face recognition timer
        self.iniciar_reconocimiento_periodico()


    def detener(self):
        self.running = False
        if self.recognition_timer:
            self.recognition_timer.cancel() # Stop the timer
            self.recognition_timer = None
        if self.cap:
            self.cap.release()
        self.label_video.config(image="")
        self.btn_iniciar.config(state=tk.NORMAL)
        self.btn_detener.config(state=tk.DISABLED)
        self.btn_registrar.config(state=tk.DISABLED)
        self.status_label.config(text="Estado: Detenido")

    def mostrar_datos_locales(self):
        self.cursor_local.execute("SELECT id, imagen_archivo FROM personas")
        filas = self.cursor_local.fetchall()
        ventana = tk.Toplevel(self.root)
        ventana.title("Datos Locales de Imágenes")
        for i, (id_p, archivo) in enumerate(filas):
            ttk.Label(ventana, text=f"ID: {id_p} | Archivo: {archivo}").pack()

    def cerrar(self):
        self.detener()
        if hasattr(self, "conexion") and self.conexion.is_connected():
            self.cursor.close()
            self.conexion.close()
        if hasattr(self, "db_local"):
            self.db_local.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DeteccionMovimientoApp(root)
    root.mainloop()