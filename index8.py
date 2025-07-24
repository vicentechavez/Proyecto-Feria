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

# Initialize pygame mixer for sound alerts
pygame.mixer.init()
ALERTA_SONIDO_RECONOCIDO = "confirmacion.mp3" # Make sure this file exists in the same directory
ALERTA_SONIDO_NO_RECONOCIDO = "error.mp3"     # Make sure this file exists in the same directory

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

        # Video display area
        self.label_video = tk.Label(self.frame_principal, bg="black", bd=2, relief="sunken")
        self.label_video.grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky='nsew')

        # Side panel for recognized data
        self.panel_datos = ttk.LabelFrame(self.frame_principal, text="Datos Reconocidos", padding=10)
        self.panel_datos.grid(row=0, column=2, padx=10, pady=10, sticky='n')

        self.labels_datos = {}
        for campo in ['Nombre', 'Edad', 'RUT', 'Fecha']:
            lbl = ttk.Label(self.panel_datos, text=f"{campo}: ---")
            lbl.pack(anchor='w', pady=5)
            self.labels_datos[campo] = lbl

        # Buttons frame
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

        # New button for showing history
        self.btn_ver_historial = ttk.Button(self.frame_botones, text="Ver Historial", command=self.mostrar_historial_reconocimiento, style='TButton')
        self.btn_ver_historial.grid(row=0, column=4, padx=10, pady=5)

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
            
            # Table for recognized people's details
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
            
            # New table for recognition history
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS historial_reconocimiento (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(255) NOT NULL,
                    rut VARCHAR(255) NOT NULL,
                    fecha_hora DATETIME NOT NULL
                );
            """)

            self.conexion.commit()
            print("✅ MySQL inicializada y tablas verificadas.")
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
                print(f"⚠️ No se encontró encoding para {nombre} en {path_encoding}")
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
                tk.messagebox.showwarning("Campos Incompletos", "Por favor, completa todos los campos para registrar a la persona.")

        ventana_registro = tk.Toplevel(self.root)
        ventana_registro.title("Registrar Persona")
        ventana_registro.geometry("400x280") # Increased height for better spacing
        ventana_registro.transient(self.root) # Make it appear on top of the main window
        ventana_registro.grab_set() # Make it modal

        campos = ["nombre", "edad", "rut"]
        entradas = {}

        for i, campo in enumerate(campos):
            ttk.Label(ventana_registro, text=campo.capitalize() + ":").pack(pady=5)
            entrada = ttk.Entry(ventana_registro)
            entrada.pack(pady=5, padx=20, fill='x')
            entradas[campo] = entrada
        
        ttk.Button(ventana_registro, text="Registrar", command=registrar_accion, style='TButton').pack(pady=15)
        
        # Center the window
        ventana_registro.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (ventana_registro.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (ventana_registro.winfo_height() // 2)
        ventana_registro.geometry(f"+{x}+{y}")


    def registrar_persona(self, nombre, edad, rut, fecha):
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
            # Give camera a moment to warm up if just opened
            time.sleep(1) 
        
        ret, frame = self.cap.read()
        if not ret:
            self.status_label.config(text="Error: No se pudo capturar imagen de la cámara.")
            return
        
        # Flip the frame for consistency, as it's flipped in actual video stream
        frame_flipped = cv2.flip(frame, 1)

        rostro = self.detectar_rostro(frame_flipped)
        if rostro is None:
            self.status_label.config(text="⚠️ No se detectó rostro para registrar.")
            tk.messagebox.showwarning("Registro Fallido", "No se detectó ningún rostro en el encuadre. Asegúrate de que tu cara esté visible.")
            return
            
        encoding = self.extraer_encoding(rostro)
        if encoding is None:
            self.status_label.config(text="⚠️ No se pudo extraer encoding del rostro.")
            tk.messagebox.showwarning("Registro Fallido", "No se pudo procesar el rostro para el reconocimiento. Intenta de nuevo.")
            return

        # Check if the name or RUT already exists in MySQL
        try:
            self.cursor.execute("SELECT COUNT(*) FROM reconocimiento WHERE nombre = %s OR rut = %s", (nombre, rut))
            if self.cursor.fetchone()[0] > 0:
                self.status_label.config(text=f"❌ Error: Nombre o RUT ya registrados.")
                tk.messagebox.showerror("Error de Registro", "El nombre o RUT ya están registrados en la base de datos.")
                return
        except mysql.connector.Error as err:
            print(f"❌ Error al verificar duplicados en MySQL: {err}")
            tk.messagebox.showerror("Error de Base de Datos", "Ocurrió un error al verificar datos duplicados.")
            return

        # Insert into local SQLite first to get an ID for the image file
        try:
            self.cursor_local.execute("INSERT INTO personas (imagen_archivo) VALUES (?)", ('temp',))
            self.db_local.commit()
            new_id = self.cursor_local.lastrowid
            
            # Save the image and encoding with the new ID
            nombre_archivo_imagen = f"imagenes/id_{new_id}.jpg"
            nombre_archivo_encoding = f"imagenes/id_{new_id}_encoding.npy"
            cv2.imwrite(nombre_archivo_imagen, rostro)
            np.save(nombre_archivo_encoding, encoding)

            self.cursor_local.execute("UPDATE personas SET imagen_archivo = ? WHERE id = ?", (nombre_archivo_imagen, new_id))
            self.db_local.commit()

            # Now insert into MySQL
            self.cursor.execute(
                "INSERT INTO reconocimiento (nombre, edad, rut, fecha, id_imagen) VALUES (%s, %s, %s, %s, %s)",
                (nombre, edad, rut, fecha, new_id)
            )
            self.conexion.commit()
            
            # Update in-memory data
            self.datos_registrados[nombre] = {
                'edad': edad,
                'rut': rut,
                'fecha': fecha,
                'id_imagen': new_id
            }
            self.encodings_registrados[nombre] = encoding
            
            self.status_label.config(text=f"✅ Registrado: {nombre}")
            print(f"✅ Registrado {nombre} con imagen ID {new_id}")
            tk.messagebox.showinfo("Registro Exitoso", f"{nombre} ha sido registrado exitosamente.")

        except mysql.connector.Error as e:
            print(f"❌ Error al registrar en MySQL: {e}")
            self.status_label.config(text=f"❌ Error al registrar en MySQL.")
            tk.messagebox.showerror("Error de Base de Datos", f"Error al registrar la persona en MySQL: {e}")
            # Clean up local files if MySQL registration fails
            if 'new_id' in locals() and os.path.exists(nombre_archivo_imagen):
                os.remove(nombre_archivo_imagen)
            if 'new_id' in locals() and os.path.exists(nombre_archivo_encoding):
                os.remove(nombre_archivo_encoding)
            self.cursor_local.execute("DELETE FROM personas WHERE id = ?", (new_id,))
            self.db_local.commit()

    def detectar_rostro(self, frame):
        # Convert to grayscale for faster face detection if not using face_recognition's internal RGB conversion
        # rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # face_recognition expects RGB
        loc = face_recognition.face_locations(frame) # face_recognition handles internal conversion
        if not loc:
            return None
        # Return the first detected face (top, right, bottom, left)
        t, r, b, l = loc[0]
        return frame[t:b, l:r]

    def extraer_encoding(self, rostro):
        rgb = cv2.cvtColor(rostro, cv2.COLOR_BGR2RGB)
        loc = face_recognition.face_locations(rgb)
        enc = face_recognition.face_encodings(rgb, loc)
        return enc[0] if enc else None

    def reconocer_rostros(self, frame):
        resultados = []
        # Resize frame for faster processing (optional, but good for real-time)
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        locs = face_recognition.face_locations(rgb_small_frame)
        encs = face_recognition.face_encodings(rgb_small_frame, locs)

        for encoding, loc_small in zip(encs, locs):
            # Scale back up face locations to the original frame size
            top, right, bottom, left = [coord * 4 for coord in loc_small]
            
            nombre_encontrado = "Desconocido"
            
            # Compare with known encodings
            if self.encodings_registrados: # Ensure there are registered encodings to compare against
                known_face_encodings_list = list(self.encodings_registrados.values())
                known_face_names_list = list(self.encodings_registrados.keys())

                matches = face_recognition.compare_faces(known_face_encodings_list, encoding, tolerance=0.5)
                face_distances = face_recognition.face_distance(known_face_encodings_list, encoding)
                
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    nombre_encontrado = known_face_names_list[best_match_index]
            
            resultados.append((nombre_encontrado, (top, right, bottom, left)))
        return resultados

    def sonar_confirmacion(self):
        try:
            pygame.mixer.music.load(ALERTA_SONIDO_RECONOCIDO)
            pygame.mixer.music.play()
        except pygame.error as e:
            print(f"Error reproduciendo sonido de confirmación: {e}")

    def sonar_error(self):
        try:
            pygame.mixer.music.load(ALERTA_SONIDO_NO_RECONOCIDO)
            pygame.mixer.music.play()
        except pygame.error as e:
            print(f"Error reproduciendo sonido de error: {e}")

    def actualizar_video(self):
        if not self.running:
            return
        ret, frame = self.cap.read()
        if not ret:
            self.status_label.config(text="Error: No se pudo acceder a la cámara.")
            return

        # Flip the frame horizontally (mirror effect)
        frame = cv2.flip(frame, 1)

        # Draw any existing recognized faces from the last recognition cycle if they're still in view
        # This part is illustrative; actual drawing happens in procesar_reconocimiento
        # For a truly responsive display, you'd want to draw based on real-time detections,
        # but for periodic recognition, drawing only during `procesar_reconocimiento` is fine.
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.label_video.imgtk = imgtk
        self.label_video.configure(image=imgtk)

        self.root.after(30, self.actualizar_video) # Update video stream approx. every 30ms (33 FPS)

    def iniciar_reconocimiento_periodico(self):
        if self.running and not self.procesando:
            # Capture a fresh frame for processing (already flipped in actualizar_video)
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.flip(frame, 1) # Ensure consistency with displayed frame
                    # Process recognition in a separate thread to avoid freezing UI
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
            rut_final = None # To store the RUT for the history
            current_time = time.time()
            now = datetime.now() # Get current datetime for timestamp

            frame_to_display = frame.copy() # Make a copy to draw on for display

            for nombre, (top, right, bottom, left) in resultados:
                color = (0, 255, 0) if nombre != "Desconocido" else (0, 0, 255)
                cv2.rectangle(frame_to_display, (left, top), (right, bottom), color, 2)
                cv2.putText(frame_to_display, nombre, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

                if nombre != "Desconocido":
                    # Check cooldown for the recognized person
                    if nombre not in self.last_detection_time or \
                       (current_time - self.last_detection_time[nombre]) > self.cooldown_period:
                        
                        rostro_reconocido_actual = True
                        nombre_final = nombre
                        self.last_detection_time[nombre] = current_time # Update last detection time

                        # Get RUT from registered data for logging
                        if nombre in self.datos_registrados:
                            rut_final = self.datos_registrados[nombre]['rut']
                            
                        # Insert into historical log
                        try:
                            # Using now.strftime for consistent string format in DB
                            self.cursor.execute(
                                "INSERT INTO historial_reconocimiento (nombre, rut, fecha_hora) VALUES (%s, %s, %s)",
                                (nombre_final, rut_final, now.strftime("%Y-%m-%d %H:%M:%S"))
                            )
                            self.conexion.commit()
                            print(f"✔️ Historial registrado: {nombre_final} ({rut_final}) a las {now.strftime('%H:%M:%S')}")
                            self.status_label.config(text=f"Reconocido: {nombre_final} ({now.strftime('%H:%M:%S')})")
                        except mysql.connector.Error as err:
                            print(f"❌ Error al insertar en historial: {err}")
                            self.status_label.config(text=f"Error al registrar historial para {nombre_final}.")
                        
                        # Once a recognized person is found and logged (if within cooldown), stop processing for this frame
                        break 

            # Update the UI with the processed frame and recognition data
            if rostro_reconocido_actual:
                self.sonar_confirmacion()
                self.mostrar_datos_panel(nombre_final)
            else:
                self.limpiar_datos_panel() # Clear panel if no new recognition or if cooldown is active
                self.sonar_error() # Play error sound if no recognized face or all are in cooldown

            self.mostrar_frame(frame_to_display) # Display the frame with bounding boxes
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
        # Resize image to fit the label, maintaining aspect ratio
        img.thumbnail((self.label_video.winfo_width(), self.label_video.winfo_height()), Image.LANCZOS)
        imgtk = ImageTk.PhotoImage(image=img)
        self.label_video.imgtk = imgtk
        self.label_video.configure(image=imgtk)

    def iniciar(self):
        if self.running: # Prevent starting if already running
            return
        try:
            self.cap = cv2.VideoCapture(0) # 0 for default camera
            if not self.cap.isOpened():
                raise IOError("Cannot open webcam")
            self.running = True
            self.btn_iniciar.config(state=tk.DISABLED)
            self.btn_detener.config(state=tk.NORMAL)
            self.btn_registrar.config(state=tk.NORMAL)
            self.status_label.config(text="Estado: Detección iniciada")
            self.actualizar_video()
            # Start the periodic face recognition timer
            self.iniciar_reconocimiento_periodico()
        except IOError as e:
            self.status_label.config(text=f"Error: {e}. No se pudo iniciar la cámara.")
            tk.messagebox.showerror("Error de Cámara", f"No se pudo acceder a la cámara: {e}\nAsegúrate de que no esté en uso por otra aplicación.")
            self.detener() # Reset buttons if camera fails to start

    def detener(self):
        if not self.running: # Prevent stopping if already stopped
            return
        self.running = False
        if self.recognition_timer:
            self.recognition_timer.cancel() # Stop the timer
            self.recognition_timer = None
        if self.cap:
            self.cap.release()
        self.label_video.config(image="") # Clear video display
        self.btn_iniciar.config(state=tk.NORMAL)
        self.btn_detener.config(state=tk.DISABLED)
        self.btn_registrar.config(state=tk.DISABLED)
        self.status_label.config(text="Estado: Detenido")
        self.limpiar_datos_panel()
        self.last_detection_time = {} # Clear cooldown times

    def mostrar_datos_locales(self):
        ventana = tk.Toplevel(self.root)
        ventana.title("Datos de Personas Registradas (Local)")
        ventana.geometry("800x600")
        ventana.transient(self.root)
        ventana.grab_set()

        canvas = tk.Canvas(ventana)
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(ventana, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion = canvas.bbox("all")))

        frame_contenido = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=frame_contenido, anchor="nw")

        row_idx = 0
        col_idx = 0
        max_cols = 4 # Number of images per row

        self.cursor_local.execute("SELECT id, imagen_archivo FROM personas")
        filas_local = self.cursor_local.fetchall()

        # Create a reverse lookup for MySQL data: id_imagen -> (nombre, edad, rut, fecha)
        mysql_data_by_id_imagen = {data['id_imagen']: (name, data['edad'], data['rut'], data['fecha']) 
                                   for name, data in self.datos_registrados.items()}

        for id_p, archivo_local in filas_local:
            nombre = "Nombre Desconocido"
            edad = "---"
            rut = "---"
            fecha = "---"

            if id_p in mysql_data_by_id_imagen:
                nombre, edad, rut, fecha = mysql_data_by_id_imagen[id_p]

            frame_item = ttk.Frame(frame_contenido, borderwidth=1, relief="solid", padding=5)
            frame_item.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky='nsew')
            
            # Ensure the frame expands with columns
            frame_contenido.grid_columnconfigure(col_idx, weight=1)

            imgtk = None
            if os.path.exists(archivo_local):
                try:
                    img = Image.open(archivo_local)
                    img.thumbnail((100, 100), Image.LANCZOS) # Resize for display
                    imgtk = ImageTk.PhotoImage(image=img)
                except Exception as e:
                    print(f"Error cargando imagen {archivo_local}: {e}")
                    # Placeholder if image fails to load
                    lbl_imagen = ttk.Label(frame_item, text="Imagen Corrupta", foreground="red")
                    lbl_imagen.pack()
            else:
                # Placeholder if image file does not exist
                lbl_imagen = ttk.Label(frame_item, text="No Image File", foreground="gray")
                lbl_imagen.pack()

            if imgtk:
                lbl_imagen = tk.Label(frame_item, image=imgtk)
                lbl_imagen.image = imgtk # Keep a reference!
                lbl_imagen.pack()

            ttk.Label(frame_item, text=f"Nombre: {nombre}", font=('Helvetica Neue', 9, 'bold')).pack(pady=1, anchor='w')
            ttk.Label(frame_item, text=f"Edad: {edad}", font=('Helvetica Neue', 9)).pack(pady=1, anchor='w')
            ttk.Label(frame_item, text=f"RUT: {rut}", font=('Helvetica Neue', 9)).pack(pady=1, anchor='w')
            ttk.Label(frame_item, text=f"ID Local: {id_p}", font=('Helvetica Neue', 8, 'italic')).pack(pady=1, anchor='w')

            col_idx += 1
            if col_idx >= max_cols:
                col_idx = 0
                row_idx += 1

        frame_contenido.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

        # Center the window
        ventana.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (ventana.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (ventana.winfo_height() // 2)
        ventana.geometry(f"+{x}+{y}")

    def mostrar_historial_reconocimiento(self):
        ventana_historial = tk.Toplevel(self.root)
        ventana_historial.title("Historial de Reconocimiento")
        ventana_historial.geometry("700x500")
        ventana_historial.transient(self.root) # Make it appear on top of the main window
        ventana_historial.grab_set() # Make it modal

        # Treeview for displaying history
        tree = ttk.Treeview(ventana_historial, columns=("Hora", "Nombre", "RUT"), show="headings")
        tree.heading("Hora", text="Hora (HH:MM:SS)")
        tree.heading("Nombre", text="Nombre")
        tree.heading("RUT", text="RUT")
        tree.column("Hora", width=150, anchor="center")
        tree.column("Nombre", width=200, anchor="center")
        tree.column("RUT", width=150, anchor="center")
        tree.pack(expand=True, fill="both", padx=10, pady=10)

        # Scrollbar
        scrollbar = ttk.Scrollbar(ventana_historial, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        try:
            self.cursor.execute("SELECT fecha_hora, nombre, rut FROM historial_reconocimiento ORDER BY fecha_hora DESC")
            for fecha_hora, nombre, rut in self.cursor.fetchall():
                # Format the datetime object to just HH-MM-SS
                # fecha_hora is typically returned as a datetime object by mysql.connector
                hora_str = fecha_hora.strftime("%H:%M:%S") 
                tree.insert("", "end", values=(hora_str, nombre, rut))
        except mysql.connector.Error as err:
            print(f"❌ Error al cargar historial: {err}")
            ttk.Label(ventana_historial, text=f"Error al cargar historial: {err}", foreground="red").pack()
        
        # Center the window
        ventana_historial.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (ventana_historial.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (ventana_historial.winfo_height() // 2)
        ventana_historial.geometry(f"+{x}+{y}")


    def cerrar(self):
        self.detener()
        if hasattr(self, "conexion") and self.conexion.is_connected():
            self.cursor.close()
            self.conexion.close()
            print("✅ Conexión MySQL cerrada.")
        if hasattr(self, "db_local"):
            self.db_local.close()
            print("✅ Conexión SQLite cerrada.")
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DeteccionMovimientoApp(root)
    root.mainloop()