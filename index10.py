import os
import cv2
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
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

# Directorio para guardar fotos de desconocidos
DESCONOCIDOS_FOTOS_DIR = "desconocidos_fotos"
if not os.path.exists(DESCONOCIDOS_FOTOS_DIR):
    os.makedirs(DESCONOCIDOS_FOTOS_DIR)

# Archivo de log de la aplicación
APP_LOG_FILE = "app_log.txt"

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

        # Updated labels for the side panel - AÑADIDA 'Relación'
        self.labels_datos = {}
        for campo in ['Nombre Completo', 'Edad', 'RUT', 'Fecha de Nacimiento', 'Relación', 'Fecha de Registro']:
            lbl = ttk.Label(self.panel_datos, text=f"{campo}: ---")
            lbl.pack(anchor='w', pady=5)
            self.labels_datos[campo] = lbl
        
        # New label for cooldown status
        self.label_cooldown_status = ttk.Label(self.panel_datos, text="", font=('Helvetica Neue', 10, 'italic'), foreground='orange')
        self.label_cooldown_status.pack(anchor='w', pady=5)


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

        # --- NUEVO BOTÓN PARA MODO ADMIN ---
        self.btn_admin_mode = ttk.Button(self.frame_botones, text="Modo Admin", command=self.mostrar_ventana_admin_login, style='TButton')
        self.btn_admin_mode.grid(row=0, column=5, padx=10, pady=5)
        # --- FIN NUEVO BOTÓN ---
        # --- NUEVO BOTÓN PARA VER SOSPECHOSOS ---
        self.btn_ver_sospechosos = ttk.Button(self.frame_botones, text="Ver Sospechosos", command=self.mostrar_ventana_sospechosos, style='TButton')
        self.btn_ver_sospechosos.grid(row=0, column=6, padx=10, pady=5)
        # --- FIN NUEVO BOTÓN ---

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

        # Cooldown para capturar fotos de desconocidos y notificaciones
        self.last_unknown_capture_time = 0
        self.unknown_capture_cooldown = 30 # segundos entre capturas de desconocidos
        self.last_notification_time = 0
        self.notification_cooldown = 300 # segundos (5 minutos) entre notificaciones al encargado

        self.inicializar_base_datos_mysql()
        self.inicializar_base_datos_local()
        self.datos_registrados = self.cargar_datos_registrados_mysql()
        self.encodings_registrados = self.cargar_encodings_registrados()

        self.root.protocol("WM_DELETE_WINDOW", self.cerrar)

        # Nueva ventana para la animación de caras pixeladas
        self.ventana_animacion = None
        self.animacion_label = None
        self.nombre_reconocido_animacion = ""
        self.estado_animacion = "neutral" # "neutral", "reconocido", "desconocido", "cooldown"
        self.animacion_frame_idx = 0
        self.animacion_imagenes = self.cargar_imagenes_pixeladas() # Asegúrate de que esta línea esté presente
        self.animacion_timer = None # Para el loop de la animación de la cara pixelada

        # Registro y aviso al iniciar la app
        self.log_app_startup()


    def cargar_imagenes_pixeladas(self):
        imagenes = {}
        try:
            # Asegúrate de que estas rutas sean correctas y que las imágenes existan
            # en la carpeta 'caras_pixel'
            imagenes["neutral"] = ImageTk.PhotoImage(Image.open("caras_pixel/neutral.gif").resize((150, 150), Image.LANCZOS))
            imagenes["reconocido_1"] = ImageTk.PhotoImage(Image.open("caras_pixel/reconocido_1.png").resize((150, 150), Image.LANCZOS))
            imagenes["reconocido_2"] = ImageTk.PhotoImage(Image.open("caras_pixel/reconocido_2.png").resize((150, 150), Image.LANCZOS))
            imagenes["desconocido"] = ImageTk.PhotoImage(Image.open("caras_pixel/desconocido.png").resize((150, 150), Image.LANCZOS))
            imagenes["cooldown"] = ImageTk.PhotoImage(Image.open("caras_pixel/cooldown.png").resize((150, 150), Image.LANCZOS)) # Carga una imagen específica para cooldown
        except FileNotFoundError as e:
            print(f"Error: Asegúrate de que las imágenes pixeladas estén en la carpeta 'caras_pixel'. {e}")
            messagebox.showerror("Error de Imagen", "No se encontraron las imágenes pixeladas. Crea una carpeta 'caras_pixel' y coloca las imágenes allí (neutral.gif, reconocido_1.png, reconocido_2.png, desconocido.png, cooldown.png).")
            return {}
        except Exception as e:
            print(f"Error cargando imágenes pixeladas: {e}")
            messagebox.showerror("Error de Imagen", f"Error al cargar las imágenes pixeladas: {e}")
            return {}
        return imagenes

    def mostrar_ventana_animacion(self):
        if self.ventana_animacion is not None and self.ventana_animacion.winfo_exists():
            self.ventana_animacion.lift() # Bring to front if already open
            return

        self.ventana_animacion = tk.Toplevel(self.root)
        self.ventana_animacion.title("Estado de Reconocimiento")
        self.ventana_animacion.geometry("300x350")
        self.ventana_animacion.resizable(False, False)
        self.ventana_animacion.protocol("WM_DELETE_WINDOW", self.cerrar_ventana_animacion)

        frame_animacion = ttk.Frame(self.ventana_animacion, padding=10)
        frame_animacion.pack(expand=True, fill='both')

        self.animacion_label = tk.Label(frame_animacion, bg="lightblue")
        self.animacion_label.pack(pady=10)

        self.nombre_label_animacion = ttk.Label(frame_animacion, text="Esperando...", font=('Helvetica Neue', 14, 'bold'))
        self.nombre_label_animacion.pack(pady=5)
        
        # Iniciar la animación
        self.actualizar_animacion_pixelada()

        # Centrar la ventana
        self.ventana_animacion.update_idletasks()
        x = self.root.winfo_x() + self.root.winfo_width()
        y = self.root.winfo_y()
        self.ventana_animacion.geometry(f"+{x}+{y}")

    def cerrar_ventana_animacion(self):
        if self.animacion_timer:
            self.ventana_animacion.after_cancel(self.animacion_timer)
        if self.ventana_animacion:
            self.ventana_animacion.destroy()
            self.ventana_animacion = None

    def actualizar_animacion_pixelada(self):
        if not self.ventana_animacion or not self.ventana_animacion.winfo_exists():
            return

        img = None # Inicializar img a None
        if self.estado_animacion == "neutral":
            img = self.animacion_imagenes.get("neutral")
            self.nombre_label_animacion.config(text="Esperando...")
        elif self.estado_animacion == "reconocido":
            # Si hay múltiples frames para "reconocido", itera a través de ellos
            img_key = f"reconocido_{self.animacion_frame_idx % 2 + 1}" # Alterna entre 'reconocido_1' y 'reconocido_2'
            img = self.animacion_imagenes.get(img_key)
            self.animacion_frame_idx += 1
            self.nombre_label_animacion.config(text=f"¡Hola, {self.nombre_reconocido_animacion}!")
        elif self.estado_animacion == "desconocido":
            img = self.animacion_imagenes.get("desconocido")
            self.nombre_label_animacion.config(text="¡Quién eres!")
        elif self.estado_animacion == "cooldown": # Nuevo estado
            img = self.animacion_imagenes.get("cooldown")
            self.nombre_label_animacion.config(text=f"{self.nombre_reconocido_animacion}\n(Enfriamiento)")


        if img:
            self.animacion_label.config(image=img)
            self.animacion_label.image = img # Important: Keep a reference!

        # Schedule next update
        self.animacion_timer = self.ventana_animacion.after(200, self.actualizar_animacion_pixelada) # Update every 200ms

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
            
            # Table for recognized people's details - MODIFIED to include 'relacion'
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS reconocimiento (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre_completo VARCHAR(255) NOT NULL,
                    fecha_nacimiento DATE NOT NULL,
                    edad INT NOT NULL,
                    rut VARCHAR(255) NOT NULL,
                    relacion VARCHAR(50) NOT NULL, -- NUEVA COLUMNA
                    fecha_registro DATE NOT NULL,
                    id_imagen INT NOT NULL,
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
            # MODIFIED query to fetch new columns including 'relacion'
            self.cursor.execute("SELECT nombre_completo, fecha_nacimiento, edad, rut, relacion, fecha_registro, id_imagen FROM reconocimiento")
            for nombre_completo, fecha_nacimiento, edad, rut, relacion, fecha_registro, id_imagen in self.cursor.fetchall():
                datos[nombre_completo] = { 
                    'fecha_nacimiento': fecha_nacimiento.strftime("%Y-%m-%d"), # Convert date object to string for consistency
                    'edad': edad,
                    'rut': rut,
                    'relacion': relacion, # NUEVA COLUMNA
                    'fecha_registro': fecha_registro.strftime("%Y-%m-%d"),
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
            nombre_completo = entradas["nombre_completo"].get().strip()
            
            # --- MODIFICACIÓN PARA FECHA DE NACIMIENTO (MENÚS DESPLEGABLES) ---
            dia = entradas["dia_nacimiento"].get()
            mes = entradas["mes_nacimiento"].get()
            anio = entradas["anio_nacimiento"].get()

            if dia == "Día" or mes == "Mes" or anio == "Año":
                tk.messagebox.showwarning("Campos Incompletos", "Por favor, selecciona el día, mes y año de nacimiento.")
                return

            try:
                # Intenta crear un objeto datetime para validar que es una fecha real
                fecha_nacimiento_dt = datetime.strptime(f"{anio}-{mes}-{dia}", "%Y-%m-%d")
            except ValueError:
                tk.messagebox.showwarning("Formato de Fecha Inválido", "Por favor, selecciona una fecha de nacimiento válida (ej: 30 de Febrero no es válido).")
                return

            fecha_nacimiento_str = f"{anio}-{mes}-{dia}"
            # --- FIN MODIFICACIÓN FECHA ---

            rut = entradas["rut"].get().strip() # Obtener el RUT, que ya debería estar formateado por formatear_rut

            # --- NUEVA VALIDACIÓN DE RUT ---
            if not self.validar_rut(rut):
                tk.messagebox.showwarning("RUT Inválido", "El RUT ingresado no es válido. Por favor, verifícalo.")
                return
            # --- FIN NUEVA VALIDACIÓN DE RUT ---

            # --- NUEVA ENTRADA PARA RELACIÓN ---
            relacion = entradas["relacion"].get().strip()
            if relacion == "Selecciona una opción": # Valor por defecto del combobox
                tk.messagebox.showwarning("Campo Incompleto", "Por favor, selecciona la relación.")
                return
            # --- FIN NUEVA ENTRADA RELACIÓN ---
            
            if nombre_completo and fecha_nacimiento_str and rut and relacion: # Asegurarse de que 'relacion' también esté presente
                # Calculate age (esta parte ya la tenías)
                today = datetime.now()
                edad = today.year - fecha_nacimiento_dt.year - ((today.month, today.day) < (fecha_nacimiento_dt.month, fecha_nacimiento_dt.day))
                
                fecha_registro = today.strftime("%Y-%m-%d")

                self.registrar_persona(nombre_completo, fecha_nacimiento_dt.strftime("%Y-%m-%d"), edad, rut, relacion, fecha_registro) # Pasar 'relacion'
                ventana_registro.destroy()
            else:
                print("⚠️ Completa todos los campos.")
                tk.messagebox.showwarning("Campos Incompletos", "Por favor, completa todos los campos para registrar a la persona.")

        ventana_registro = tk.Toplevel(self.root)
        ventana_registro.title("Registrar Persona")
        ventana_registro.geometry("400x400") # Aumentado para acomodar el nuevo campo
        ventana_registro.transient(self.root)
        ventana_registro.grab_set()

        # MODIFIED fields
        campos = ["nombre_completo"] # Solo nombre completo aquí, fecha y rut se manejan aparte
        etiquetas = {
            "nombre_completo": "Nombre Completo (ej: Juan Perez):"
        }
        entradas = {}

        for campo in campos:
            ttk.Label(ventana_registro, text=etiquetas[campo]).pack(pady=5)
            entrada = ttk.Entry(ventana_registro)
            entrada.pack(pady=5, padx=20, fill='x')
            entradas[campo] = entrada
        
        # --- NUEVAS ENTRADAS PARA FECHA DE NACIMIENTO (MENÚS DESPLEGABLES) ---
        ttk.Label(ventana_registro, text="Fecha de Nacimiento (Día/Mes/Año):").pack(pady=5)

        frame_fecha = ttk.Frame(ventana_registro)
        frame_fecha.pack(pady=5, padx=20, fill='x')

        # Día
        dias = [str(i).zfill(2) for i in range(1, 32)] # 01, 02, ..., 31
        combo_dia = ttk.Combobox(frame_fecha, values=dias, width=5, state="readonly")
        combo_dia.set("Día") # Texto inicial
        combo_dia.pack(side=tk.LEFT, padx=2)
        entradas["dia_nacimiento"] = combo_dia

        # Mes
        meses = [str(i).zfill(2) for i in range(1, 13)] # 01, 02, ..., 12
        combo_mes = ttk.Combobox(frame_fecha, values=meses, width=5, state="readonly")
        combo_mes.set("Mes") # Texto inicial
        combo_mes.pack(side=tk.LEFT, padx=2)
        entradas["mes_nacimiento"] = combo_mes

        # Año (ajusta el rango de años según tus necesidades)
        current_year = datetime.now().year
        anios = [str(i) for i in range(current_year, current_year - 100, -1)] # Desde el año actual hasta 100 años atrás
        combo_anio = ttk.Combobox(frame_fecha, values=anios, width=7, state="readonly")
        combo_anio.set("Año") # Texto inicial
        combo_anio.pack(side=tk.LEFT, padx=2)
        entradas["anio_nacimiento"] = combo_anio
        # --- FIN NUEVAS ENTRADAS FECHA ---

        # --- NUEVA ENTRADA PARA RUT (CON FORMATO AUTOMÁTICO) ---
        ttk.Label(ventana_registro, text="RUT:").pack(pady=5)
        entrada_rut = ttk.Entry(ventana_registro)
        entrada_rut.pack(pady=5, padx=20, fill='x')
        entrada_rut.bind("<KeyRelease>", lambda event: self.formatear_rut(entrada_rut))
        entradas["rut"] = entrada_rut # Asegúrate de que esta línea esté después del bind
        # --- FIN NUEVA ENTRADA RUT ---

        # --- NUEVA ENTRADA PARA RELACIÓN ---
        ttk.Label(ventana_registro, text="Relación:").pack(pady=5)
        opciones_relacion = ["Dueño", "Hijo", "Esposa", "Empleado", "Visita", "Otro"]
        combo_relacion = ttk.Combobox(ventana_registro, values=opciones_relacion, state="readonly")
        combo_relacion.set("Selecciona una opción") # Texto inicial
        combo_relacion.pack(pady=5, padx=20, fill='x')
        entradas["relacion"] = combo_relacion
        # --- FIN NUEVA ENTRADA RELACIÓN ---
        
        ttk.Button(ventana_registro, text="Registrar", command=registrar_accion, style='TButton').pack(pady=15)
        
        # Centrar la ventana
        ventana_registro.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (ventana_registro.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (ventana_registro.winfo_height() // 2)
        ventana_registro.geometry(f"+{x}+{y}")


    def registrar_persona(self, nombre_completo, fecha_nacimiento, edad, rut, relacion, fecha_registro): # Añadido 'relacion'
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

        # Check for RUT uniqueness
        try:
            self.cursor.execute("SELECT COUNT(*) FROM reconocimiento WHERE rut = %s", (rut,))
            if self.cursor.fetchone()[0] > 0:
                self.status_label.config(text=f"❌ Error: RUT '{rut}' ya registrado.")
                tk.messagebox.showerror("Error de Registro", "El RUT ya está registrado en la base de datos. Cada RUT debe ser único.")
                return
        except mysql.connector.Error as err:
            print(f"❌ Error al verificar RUT duplicado en MySQL: {err}")
            self.status_label.config(text=f"❌ Error DB al verificar RUT.")
            tk.messagebox.showerror("Error de Base de Datos", "Ocurrió un error al verificar el RUT duplicado.")
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

            # Now insert into MySQL - MODIFIED to include fecha_nacimiento, edad and relacion
            self.cursor.execute(
                "INSERT INTO reconocimiento (nombre_completo, fecha_nacimiento, edad, rut, relacion, fecha_registro, id_imagen) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (nombre_completo, fecha_nacimiento, edad, rut, relacion, fecha_registro, new_id) # Añadido 'relacion'
            )
            self.conexion.commit()
            
            # Update in-memory data - MODIFIED
            self.datos_registrados[nombre_completo] = { 
                'fecha_nacimiento': fecha_nacimiento,
                'edad': edad,
                'rut': rut,
                'relacion': relacion, # NUEVA COLUMNA
                'fecha_registro': fecha_registro,
                'id_imagen': new_id
            }
            self.encodings_registrados[nombre_completo] = encoding 
            
            self.status_label.config(text=f"✅ Registrado: {nombre_completo}")
            print(f"✅ Registrado {nombre_completo} con imagen ID {new_id}")
            tk.messagebox.showinfo("Registro Exitoso", f"{nombre_completo} ha sido registrado exitosamente.")

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
        # face_recognition expects RGB
        loc = face_recognition.face_locations(frame) 
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
            nombre_reconocido_actual = None # Para saber si se reconoció a ALGUIEN en este ciclo
            rut_final = None 
            current_time = time.time()
            now = datetime.now() 

            frame_to_display = frame.copy() 

            reconocido_y_registrado_en_este_ciclo = False # Flag para saber si se reconoció y se registró (no en cooldown)

            if resultados: # Si se detectó al menos una cara
                for nombre, (top, right, bottom, left) in resultados:
                    color = (0, 255, 0) if nombre != "Desconocido" else (0, 0, 255)
                    cv2.rectangle(frame_to_display, (left, top), (right, bottom), color, 2)
                    cv2.putText(frame_to_display, nombre, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

                    if nombre != "Desconocido":
                        nombre_reconocido_actual = nombre # Se reconoció a alguien
                        
                        # Check cooldown for the recognized person
                        if nombre not in self.last_detection_time or \
                           (current_time - self.last_detection_time[nombre]) > self.cooldown_period:
                            
                            self.last_detection_time[nombre] = current_time # Update last detection time
                            
                            # Get RUT and relacion from registered data for logging and display
                            if nombre in self.datos_registrados:
                                rut_final = self.datos_registrados[nombre]['rut']
                                relacion_final = self.datos_registrados[nombre]['relacion'] # Obtener la relación
                                
                            # Insert into historical log
                            try:
                                self.cursor.execute(
                                    "INSERT INTO historial_reconocimiento (nombre, rut, fecha_hora) VALUES (%s, %s, %s)",
                                    (nombre_reconocido_actual, rut_final, now.strftime("%Y-%m-%d %H:%M:%S"))
                                )
                                self.conexion.commit()
                                print(f"✔️ Historial registrado: {nombre_reconocido_actual} ({rut_final}) a las {now.strftime('%H:%M:%S')}")
                                self.status_label.config(text=f"Reconocido: {nombre_reconocido_actual} ({now.strftime('%H:%M:%S')})")
                                self.sonar_confirmacion()
                                reconocido_y_registrado_en_este_ciclo = True
                            except mysql.connector.Error as err:
                                print(f"❌ Error al insertar en historial: {err}")
                                self.status_label.config(text=f"Error al registrar historial para {nombre_reconocido_actual}.")
                            
                            # Actualizar la animación y el nombre en la ventana secundaria
                            self.nombre_reconocido_animacion = nombre_reconocido_actual
                            self.estado_animacion = "reconocido"
                            self.mostrar_datos_panel(nombre_reconocido_actual)
                            break # Salir del bucle for si se reconoció a alguien y se registró
                        else:
                            # La persona fue reconocida pero está en cooldown
                            self.nombre_reconocido_animacion = nombre # Mantener el nombre de la persona en cooldown
                            self.estado_animacion = "cooldown" # Nuevo estado para la animación
                            self.mostrar_datos_panel(nombre) # Actualizar panel con datos
                            self.label_cooldown_status.config(text="Enfriamiento Activo (1 min)", foreground='orange')
                            print(f"DEBUG: {nombre} reconocido, pero en cooldown.")
                            break # Salir del bucle for, ya hemos encontrado una persona en cooldown
                    else: # Si el nombre es "Desconocido"
                        self.estado_animacion = "desconocido"
                        self.sonar_error()
                        self.limpiar_datos_panel()
                        self.label_cooldown_status.config(text="") # Limpiar el mensaje de cooldown

                        # --- CAPTURA Y NOTIFICACIÓN DE ROSTROS DESCONOCIDOS ---
                        if (current_time - self.last_unknown_capture_time) > self.unknown_capture_cooldown:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = os.path.join(DESCONOCIDOS_FOTOS_DIR, f"desconocido_{timestamp}.jpg")
                            cv2.imwrite(filename, frame) # Guarda el frame completo con el rostro desconocido
                            print(f"📸 Foto de desconocido guardada: {filename}")
                            self.last_unknown_capture_time = current_time
                            self.notificar_persona_encargada(filename) # Notificar con la ruta de la imagen
                        # --- FIN CAPTURA Y NOTIFICACIÓN ---
            else:
                # No se detectó ninguna cara
                self.estado_animacion = "neutral"
                self.limpiar_datos_panel()
                self.label_cooldown_status.config(text="") # Limpiar el mensaje de cooldown


            self.mostrar_frame(frame_to_display)
        finally:
            self.procesando = False

    def notificar_persona_encargada(self, image_path):
        current_time = time.time()
        if (current_time - self.last_notification_time) > self.notification_cooldown:
            mensaje = f"🚨 ALERTA: Rostro desconocido detectado en la entrada. Foto guardada en: {image_path}"
            print(mensaje)
            tk.messagebox.showwarning("Alerta de Seguridad", mensaje)
            self.last_notification_time = current_time
        else:
            print(f"DEBUG: Notificación de desconocido en cooldown. Última notificación hace {int(current_time - self.last_notification_time)} segundos.")


    def mostrar_datos_panel(self, nombre_completo):
        datos = self.datos_registrados.get(nombre_completo)
        if datos:
            self.labels_datos["Nombre Completo"].config(text=f"Nombre Completo: {nombre_completo}")
            self.labels_datos["Edad"].config(text=f"Edad: {datos['edad']}")
            self.labels_datos["RUT"].config(text=f"RUT: {datos['rut']}")
            self.labels_datos["Fecha de Nacimiento"].config(text=f"Fecha de Nacimiento: {datos['fecha_nacimiento']}")
            self.labels_datos["Relación"].config(text=f"Relación: {datos['relacion']}") # Mostrar 'Relación'
            self.labels_datos["Fecha de Registro"].config(text=f"Fecha de Registro: {datos['fecha_registro']}")
            # Limpiar el mensaje de cooldown si se muestra información de una persona
            self.label_cooldown_status.config(text="")


    def limpiar_datos_panel(self):
        # MODIFIED labels to clear
        self.labels_datos["Nombre Completo"].config(text="Nombre Completo: ---")
        self.labels_datos["Edad"].config(text="Edad: ---")
        self.labels_datos["RUT"].config(text="RUT: ---")
        self.labels_datos["Fecha de Nacimiento"].config(text="Fecha de Nacimiento: ---")
        self.labels_datos["Relación"].config(text="Relación: ---") # Limpiar 'Relación'
        self.labels_datos["Fecha de Registro"].config(text="Fecha de Registro: ---")
        self.label_cooldown_status.config(text="") # Asegurarse de limpiar también este mensaje

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
            # Mostrar la ventana de animación al iniciar la detección
            self.mostrar_ventana_animacion()
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
        # Cerrar la ventana de animación al detener
        self.cerrar_ventana_animacion()


    # --- Modificaciones para recargar datos locales ---
    def _cargar_datos_locales_en_ventana(self, frame_contenido, canvas, mysql_data_by_id_imagen):
        # Limpia el contenido actual del frame_contenido
        for widget in frame_contenido.winfo_children():
            widget.destroy()

        row_idx = 0
        col_idx = 0
        max_cols = 4 # Number of images per row

        self.cursor_local.execute("SELECT id, imagen_archivo FROM personas")
        filas_local = self.cursor_local.fetchall()

        for id_p, archivo_local in filas_local:
            nombre_completo = "Nombre Desconocido"
            edad = "---"
            rut = "---"
            fecha_nacimiento = "---"
            relacion = "---" # NUEVA VARIABLE
            fecha_registro = "---"

            if id_p in mysql_data_by_id_imagen:
                nombre_completo, fecha_nacimiento, edad, rut, relacion, fecha_registro = mysql_data_by_id_imagen[id_p] # Obtener 'relacion'

            frame_item = ttk.Frame(frame_contenido, borderwidth=1, relief="solid", padding=5)
            frame_item.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky='nsew')
            
            frame_contenido.grid_columnconfigure(col_idx, weight=1)

            imgtk = None
            if os.path.exists(archivo_local):
                try:
                    img = Image.open(archivo_local)
                    img.thumbnail((100, 100), Image.LANCZOS) # Resize for display
                    imgtk = ImageTk.PhotoImage(image=img)
                except Exception as e:
                    print(f"Error cargando imagen {archivo_local}: {e}")
                    lbl_imagen = ttk.Label(frame_item, text="Imagen Corrupta", foreground="red")
                    lbl_imagen.pack()
            else:
                lbl_imagen = ttk.Label(frame_item, text="No Image File", foreground="gray")
                lbl_imagen.pack()

            if imgtk:
                lbl_imagen = tk.Label(frame_item, image=imgtk)
                lbl_imagen.image = imgtk # Keep a reference!
                lbl_imagen.pack()

            ttk.Label(frame_item, text=f"Nombre: {nombre_completo}", font=('Helvetica Neue', 9, 'bold')).pack(pady=1, anchor='w')
            ttk.Label(frame_item, text=f"Edad: {edad}", font=('Helvetica Neue', 9)).pack(pady=1, anchor='w')
            ttk.Label(frame_item, text=f"RUT: {rut}", font=('Helvetica Neue', 9)).pack(pady=1, anchor='w')
            ttk.Label(frame_item, text=f"F. Nacimiento: {fecha_nacimiento}", font=('Helvetica Neue', 9)).pack(pady=1, anchor='w')
            ttk.Label(frame_item, text=f"Relación: {relacion}", font=('Helvetica Neue', 9)).pack(pady=1, anchor='w') # Mostrar 'Relación'
            ttk.Label(frame_item, text=f"F. Registro: {fecha_registro}", font=('Helvetica Neue', 9)).pack(pady=1, anchor='w')
            ttk.Label(frame_item, text=f"ID Local: {id_p}", font=('Helvetica Neue', 8, 'italic')).pack(pady=1, anchor='w')

            col_idx += 1
            if col_idx >= max_cols:
                col_idx = 0
                row_idx += 1

        frame_contenido.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

    def mostrar_datos_locales(self):
        ventana = tk.Toplevel(self.root)
        ventana.title("Datos de Personas Registradas (Local)")
        ventana.geometry("800x600")
        ventana.transient(self.root)
        ventana.grab_set()

        # Frame for buttons
        frame_botones_locales = ttk.Frame(ventana)
        frame_botones_locales.pack(pady=5)

        # Container for content
        canvas = tk.Canvas(ventana)
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(ventana, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion = canvas.bbox("all")))

        frame_contenido = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=frame_contenido, anchor="nw")

        # Create a reverse lookup for MySQL data: id_imagen -> (nombre_completo, fecha_nacimiento, edad, rut, relacion, fecha_registro)
        mysql_data_by_id_imagen = {}
        try:
            self.cursor.execute("SELECT nombre_completo, fecha_nacimiento, edad, rut, relacion, fecha_registro, id_imagen FROM reconocimiento")
            for nombre_completo, fecha_nacimiento, edad, rut, relacion, fecha_registro, id_imagen in self.cursor.fetchall():
                mysql_data_by_id_imagen[id_imagen] = (nombre_completo, fecha_nacimiento.strftime("%Y-%m-%d"), edad, rut, relacion, fecha_registro.strftime("%Y-%m-%d"))
        except mysql.connector.Error as err:
            print(f"❌ Error al cargar datos para mostrar en local: {err}")
        
        # Initial load
        self._cargar_datos_locales_en_ventana(frame_contenido, canvas, mysql_data_by_id_imagen)

        # Reload button for local data
        btn_recargar = ttk.Button(frame_botones_locales, text="Recargar Datos", 
                                  command=lambda: self._cargar_datos_locales_en_ventana(frame_contenido, canvas, mysql_data_by_id_imagen))
        btn_recargar.pack(padx=10)


        # Centrar la ventana
        ventana.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (ventana.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (ventana.winfo_height() // 2)
        ventana.geometry(f"+{x}+{y}")

    # --- Modificaciones para recargar historial ---
    def _cargar_historial_en_treeview(self, tree):
        # Limpia los datos actuales del treeview
        for item in tree.get_children():
            tree.delete(item)
            
        try:
            self.cursor.execute("SELECT fecha_hora, nombre, rut FROM historial_reconocimiento ORDER BY fecha_hora DESC")
            for fecha_hora, nombre, rut in self.cursor.fetchall():
                fecha_str = fecha_hora.strftime("%Y-%m-%d")
                hora_str = fecha_hora.strftime("%H:%M:%S") 
                tree.insert("", "end", values=(fecha_str, hora_str, nombre, rut))
        except mysql.connector.Error as err:
            print(f"❌ Error al cargar historial: {err}")
            messagebox.showerror("Error de Historial", f"Error al cargar historial: {err}")


    def mostrar_historial_reconocimiento(self):
        ventana_historial = tk.Toplevel(self.root)
        ventana_historial.title("Historial de Reconocimiento")
        ventana_historial.geometry("700x500")
        ventana_historial.transient(self.root) # Make it appear on top of the main window
        ventana_historial.grab_set() # Make it modal

        # Frame for buttons (top of the window)
        frame_botones_historial = ttk.Frame(ventana_historial)
        frame_botones_historial.pack(pady=5)

        # Button to refresh history
        btn_recargar_historial = ttk.Button(frame_botones_historial, text="Recargar Historial")
        btn_recargar_historial.pack(padx=10) # Pack it first, then configure command

        # Treeview for displaying history
        tree = ttk.Treeview(ventana_historial, columns=("Fecha", "Hora", "Nombre", "RUT"), show="headings")
        tree.heading("Fecha", text="Fecha (AAAA-MM-DD)")
        tree.heading("Hora", text="Hora (HH:MM:SS)")
        tree.heading("Nombre", text="Nombre")
        tree.heading("RUT", text="RUT")
        tree.column("Fecha", width=150, anchor="center")
        tree.column("Hora", width=120, anchor="center")
        tree.column("Nombre", width=200, anchor="center")
        tree.column("RUT", width=150, anchor="center")
        tree.pack(expand=True, fill="both", padx=10, pady=10)

        # Configure the command after tree is defined
        btn_recargar_historial.config(command=lambda: self._cargar_historial_en_treeview(tree))


        # Scrollbar
        scrollbar = ttk.Scrollbar(ventana_historial, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Initial load of history
        self._cargar_historial_en_treeview(tree)
        
        # Centrar la ventana
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
        
    def formatear_rut(self, entry_widget):
        current_text = entry_widget.get()
        
        # 1. Limpiar el texto: remover puntos, guiones y espacios
        clean_rut = current_text.replace(".", "").replace("-", "").strip()
        
        # 2. Validar que solo contenga dígitos y la letra 'K' al final (opcional, pero recomendado para un RUT)
        # Esto permite que 'K' solo sea el último carácter
        if not all(c.isdigit() or (i == len(clean_rut) - 1 and c.upper() == 'K') for i, c in enumerate(clean_rut)):
            # Aquí podrías agregar un feedback visual o simplemente no formatear caracteres no válidos
            return

        formatted_rut = ""
        rut_len = len(clean_rut)

        if rut_len > 1:
            # Separar el dígito verificador
            body = clean_rut[:-1]
            dv = clean_rut[-1].upper() # Asegurar que el DV sea mayúscula

            # Formatear el cuerpo con puntos
            for i, char in enumerate(reversed(body)):
                if i > 0 and i % 3 == 0:
                    formatted_rut = "." + formatted_rut
                formatted_rut = char + formatted_rut
            
            # Unir el cuerpo formateado con el dígito verificador
            formatted_rut = formatted_rut + "-" + dv
        elif rut_len == 1:
            formatted_rut = clean_rut # Si solo hay un carácter, no formatear aún
        else:
            formatted_rut = "" # Si no hay caracteres, dejar vacío

        # Actualizar el widget de entrada solo si el formato ha cambiado para evitar bucles infinitos
        if entry_widget.get() != formatted_rut:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, formatted_rut)

        # Mover el cursor al final de la entrada
        entry_widget.icursor(tk.END)

    def validar_rut(self, rut_completo):
        rut_completo = rut_completo.upper().replace(".", "").replace("-", "").strip()

        if not rut_completo:
            return False

        # Verifica que el cuerpo sean dígitos y el DV sea dígito o 'K'
        if not (rut_completo[:-1].isdigit() and (rut_completo[-1].isdigit() or rut_completo[-1] == 'K')):
            return False

        cuerpo = rut_completo[:-1]
        dv = rut_completo[-1]

        # Calcular dígito verificador esperado
        suma = 0
        multiplo = 2
        for i in reversed(cuerpo):
            suma += int(i) * multiplo
            multiplo += 1
            if multiplo == 8:
                multiplo = 2

        dv_calculado = 11 - (suma % 11)
        
        if dv_calculado == 11:
            dv_final = '0'
        elif dv_calculado == 10:
            dv_final = 'K'
        else:
            dv_final = str(dv_calculado)

        return dv_final == dv

    def mostrar_ventana_admin_login(self):
        # Crea una nueva ventana de nivel superior para el login
        self.ventana_admin_login = tk.Toplevel(self.root)
        self.ventana_admin_login.title("Acceso Admin")
        self.ventana_admin_login.geometry("300x150")
        # Hace que la ventana de login aparezca encima de la ventana principal
        self.ventana_admin_login.transient(self.root)
        # Hace que la ventana de login sea modal (bloquea la interacción con la ventana principal)
        self.ventana_admin_login.grab_set() 

        # Etiqueta y campo de entrada para la contraseña
        ttk.Label(self.ventana_admin_login, text="Contraseña de Administrador:").pack(pady=10)
        # show="*" oculta los caracteres de la contraseña
        self.admin_password_entry = ttk.Entry(self.ventana_admin_login, show="*") 
        self.admin_password_entry.pack(pady=5, padx=20, fill='x')
        # Permite presionar Enter para intentar iniciar sesión
        self.admin_password_entry.bind("<Return>", lambda event: self.verificar_admin_password()) 

        # Botón para verificar la contraseña
        ttk.Button(self.ventana_admin_login, text="Ingresar", command=self.verificar_admin_password, style='TButton').pack(pady=10)

        # Centrar la ventana de login en relación con la ventana principal
        self.ventana_admin_login.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (self.ventana_admin_login.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (self.ventana_admin_login.winfo_height() // 2)
        self.ventana_admin_login.geometry(f"+{x}+{y}")

    def verificar_admin_password(self):
        password = self.admin_password_entry.get()
        ADMIN_PASSWORD = "12345" # Contraseña de ejemplo. ¡Considera usar un método más seguro en producción!

        if password == ADMIN_PASSWORD:
            self.ventana_admin_login.destroy() # Cierra la ventana de login
            tk.messagebox.showinfo("Acceso Correcto", "¡Bienvenido, Administrador!")
            self.mostrar_panel_admin() # Llama a la función para mostrar el panel de administración
        else:
            tk.messagebox.showerror("Acceso Denegado", "Contraseña incorrecta. Inténtalo de nuevo.")
            self.admin_password_entry.delete(0, tk.END) # Limpia el campo de contraseña para reintentar

    def mostrar_panel_admin(self):
        self.ventana_admin = tk.Toplevel(self.root)
        self.ventana_admin.title("Panel de Administración")
        self.ventana_admin.geometry("900x600")
        self.ventana_admin.transient(self.root)
        self.ventana_admin.grab_set()

        # Frame para botones de administración
        frame_admin_botones = ttk.Frame(self.ventana_admin, padding=10)
        frame_admin_botones.pack(pady=5, fill='x')

        ttk.Label(frame_admin_botones, text="Gestión de Personas:", font=('Helvetica Neue', 12, 'bold')).pack(side=tk.LEFT, padx=10)

        self.btn_eliminar_persona = ttk.Button(frame_admin_botones, text="Eliminar Persona", command=self.eliminar_persona, style='TButton')
        self.btn_eliminar_persona.pack(side=tk.LEFT, padx=5)

        self.btn_editar_persona = ttk.Button(frame_admin_botones, text="Editar Persona", command=self.modificar_datos_persona, style='TButton')
        self.btn_editar_persona.pack(side=tk.LEFT, padx=5)

        self.btn_recargar_admin = ttk.Button(frame_admin_botones, text="Recargar Datos", command=self._cargar_personas_admin_treeview, style='TButton')
        self.btn_recargar_admin.pack(side=tk.LEFT, padx=5)

        # Treeview para mostrar los datos de las personas - AÑADIDA 'Relación'
        self.tree_personas_admin = ttk.Treeview(self.ventana_admin, columns=("ID_Imagen", "Nombre Completo", "RUT", "Fecha Nacimiento", "Edad", "Relación", "Fecha Registro"), show="headings")
        self.tree_personas_admin.heading("ID_Imagen", text="ID Local")
        self.tree_personas_admin.heading("Nombre Completo", text="Nombre Completo")
        self.tree_personas_admin.heading("RUT", text="RUT")
        self.tree_personas_admin.heading("Fecha Nacimiento", text="F. Nacimiento")
        self.tree_personas_admin.heading("Edad", text="Edad")
        self.tree_personas_admin.heading("Relación", text="Relación") # NUEVA COLUMNA
        self.tree_personas_admin.heading("Fecha Registro", text="F. Registro")

        # Ajustar anchos de columna
        self.tree_personas_admin.column("ID_Imagen", width=80, anchor="center")
        self.tree_personas_admin.column("Nombre Completo", width=200, anchor="w")
        self.tree_personas_admin.column("RUT", width=120, anchor="center")
        self.tree_personas_admin.column("Fecha Nacimiento", width=120, anchor="center")
        self.tree_personas_admin.column("Edad", width=60, anchor="center")
        self.tree_personas_admin.column("Relación", width=100, anchor="center") # NUEVA COLUMNA
        self.tree_personas_admin.column("Fecha Registro", width=120, anchor="center")

        self.tree_personas_admin.pack(expand=True, fill="both", padx=10, pady=10)

        # Scrollbar para el Treeview
        scrollbar_admin = ttk.Scrollbar(self.ventana_admin, orient="vertical", command=self.tree_personas_admin.yview)
        self.tree_personas_admin.configure(yscrollcommand=scrollbar_admin.set)
        scrollbar_admin.pack(side="right", fill="y")

        # Cargar los datos iniciales en el Treeview
        self._cargar_personas_admin_treeview()

        # Centrar la ventana
        self.ventana_admin.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (self.ventana_admin.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (self.ventana_admin.winfo_height() // 2)
        self.ventana_admin.geometry(f"+{x}+{y}")

        # Configurar el protocolo de cierre para recargar datos al cerrar
        self.ventana_admin.protocol("WM_DELETE_WINDOW", self.cerrar_panel_admin)

    def cerrar_panel_admin(self):
        # Recargar datos en la aplicación principal si es necesario
        self.datos_registrados = self.cargar_datos_registrados_mysql()
        self.encodings_registrados = self.cargar_encodings_registrados()
        self.limpiar_datos_panel() # Limpiar el panel de datos reconocidos
        self.ventana_admin.destroy()

    def _cargar_personas_admin_treeview(self):
        # Limpia los datos actuales del treeview
        for item in self.tree_personas_admin.get_children():
            self.tree_personas_admin.delete(item)
            
        try:
            # Obtener datos de MySQL - AÑADIDA 'relacion'
            self.cursor.execute("SELECT id_imagen, nombre_completo, rut, fecha_nacimiento, edad, relacion, fecha_registro FROM reconocimiento ORDER BY nombre_completo ASC")
            for id_imagen, nombre_completo, rut, fecha_nacimiento, edad, relacion, fecha_registro in self.cursor.fetchall():
                # Formatear fechas para mostrar
                fecha_nac_str = fecha_nacimiento.strftime("%Y-%m-%d") if fecha_nacimiento else "N/A"
                fecha_reg_str = fecha_registro.strftime("%Y-%m-%d") if fecha_registro else "N/A"
                self.tree_personas_admin.insert("", "end", values=(id_imagen, nombre_completo, rut, fecha_nac_str, edad, relacion, fecha_reg_str)) # Añadida 'relacion'
        except mysql.connector.Error as err:
            print(f"❌ Error al cargar datos para el panel de administración: {err}")
            messagebox.showerror("Error de Base de Datos", f"Error al cargar datos de personas: {err}")

    def eliminar_persona(self):
        selected_item = self.tree_personas_admin.selection()
        if not selected_item:
            tk.messagebox.showwarning("Eliminar Persona", "Por favor, selecciona una persona de la lista para eliminar.")
            return

        # Obtener los datos de la fila seleccionada
        values = self.tree_personas_admin.item(selected_item, 'values')
        id_imagen = values[0] # ID Local
        nombre_completo = values[1]
        rut = values[2]

        confirm = tk.messagebox.askyesno(
            "Confirmar Eliminación",
            f"¿Estás seguro de que quieres eliminar a '{nombre_completo}' (RUT: {rut}) y todos sus datos asociados?"
        )

        if confirm:
            try:
                # 1. Eliminar de MySQL
                self.cursor.execute("DELETE FROM reconocimiento WHERE rut = %s", (rut,))
                self.conexion.commit()

                # 2. Eliminar de SQLite
                self.cursor_local.execute("DELETE FROM personas WHERE id = ?", (id_imagen,))
                self.db_local.commit()

                # 3. Eliminar archivos de imagen y encoding
                imagen_path = f"imagenes/id_{id_imagen}.jpg"
                encoding_path = f"imagenes/id_{id_imagen}_encoding.npy"
                if os.path.exists(imagen_path):
                    os.remove(imagen_path)
                    print(f"✔️ Imagen eliminada: {imagen_path}")
                if os.path.exists(encoding_path):
                    os.remove(encoding_path)
                    print(f"✔️ Encoding eliminado: {encoding_path}")

                # 4. Actualizar datos en memoria
                if nombre_completo in self.datos_registrados:
                    del self.datos_registrados[nombre_completo]
                if nombre_completo in self.encodings_registrados:
                    del self.encodings_registrados[nombre_completo]

                tk.messagebox.showinfo("Eliminación Exitosa", f"'{nombre_completo}' ha sido eliminado exitosamente.")
                self._cargar_personas_admin_treeview() # Recargar la tabla del admin
                self.limpiar_datos_panel() # Limpiar el panel de datos si la persona eliminada estaba mostrándose
                self.last_detection_time = {k:v for k,v in self.last_detection_time.items() if k != nombre_completo} # Limpiar cooldown
            except mysql.connector.Error as err:
                print(f"❌ Error al eliminar en MySQL: {err}")
                tk.messagebox.showerror("Error de Base de Datos", f"Error al eliminar la persona en MySQL: {err}")
            except sqlite3.Error as err:
                print(f"❌ Error al eliminar en SQLite: {err}")
                tk.messagebox.showerror("Error de Base de Datos", f"Error al eliminar la persona en SQLite: {err}")
            except Exception as e:
                print(f"❌ Error inesperado al eliminar: {e}")
                tk.messagebox.showerror("Error", f"Ocurrió un error inesperado al eliminar: {e}")

    def modificar_datos_persona(self):
        selected_item = self.tree_personas_admin.selection()
        if not selected_item:
            tk.messagebox.showwarning("Modificar Datos", "Por favor, selecciona una persona de la lista para editar.")
            return

        # Obtener todos los datos de la fila seleccionada en el panel de admin
        values = self.tree_personas_admin.item(selected_item, 'values')
        id_imagen = values[0]
        nombre_actual = values[1]
        rut_actual = values[2]
        fecha_nac_actual_str = values[3]
        relacion_actual = values[5]
        fecha_reg_actual_str = values[6]

        # --- Ventana para solicitar los nuevos datos ---
        ventana_modificar = tk.Toplevel(self.ventana_admin)
        ventana_modificar.title("Editar Datos de Persona")
        ventana_modificar.geometry("400x500") # Aumentamos la altura para los nuevos campos
        ventana_modificar.transient(self.ventana_admin)
        ventana_modificar.grab_set()

        ttk.Label(ventana_modificar, text=f"Editando a: {nombre_actual}", wraplength=350, font=('Helvetica Neue', 10, 'bold')).pack(pady=10)

        # --- Frame para todos los campos de entrada ---
        frame_campos = ttk.Frame(ventana_modificar)
        frame_campos.pack(pady=10, padx=20, fill='x', expand=True)

        # 1. Editor de Nombre
        ttk.Label(frame_campos, text="Nombre Completo:").pack(anchor='w')
        entry_nuevo_nombre = ttk.Entry(frame_campos)
        entry_nuevo_nombre.pack(fill='x', pady=5)
        entry_nuevo_nombre.insert(0, nombre_actual)

        # 2. Editor de RUT (AÑADIDO)
        ttk.Label(frame_campos, text="RUT:").pack(anchor='w', pady=(10, 0))
        entry_nuevo_rut = ttk.Entry(frame_campos)
        entry_nuevo_rut.pack(fill='x', pady=5)
        entry_nuevo_rut.insert(0, rut_actual)
        # Aplicar formato automático al RUT mientras se escribe
        entry_nuevo_rut.bind("<KeyRelease>", lambda event: self.formatear_rut(entry_nuevo_rut))

        # 3. Editor de Fecha de Nacimiento
        ttk.Label(frame_campos, text="Fecha de Nacimiento:").pack(anchor='w', pady=(10, 0))
        frame_fecha = ttk.Frame(frame_campos)
        frame_fecha.pack(fill='x', pady=5)

        anio_actual, mes_actual, dia_actual = map(int, fecha_nac_actual_str.split('-'))

        dias = [str(i).zfill(2) for i in range(1, 32)]
        combo_dia = ttk.Combobox(frame_fecha, values=dias, width=5, state="readonly")
        combo_dia.set(str(dia_actual).zfill(2))
        combo_dia.pack(side=tk.LEFT, padx=2)

        meses = [str(i).zfill(2) for i in range(1, 13)]
        combo_mes = ttk.Combobox(frame_fecha, values=meses, width=5, state="readonly")
        combo_mes.set(str(mes_actual).zfill(2))
        combo_mes.pack(side=tk.LEFT, padx=2)

        current_year = datetime.now().year
        anios = [str(i) for i in range(current_year, current_year - 100, -1)]
        combo_anio = ttk.Combobox(frame_fecha, values=anios, width=7, state="readonly")
        combo_anio.set(str(anio_actual))
        combo_anio.pack(side=tk.LEFT, padx=2)

        # 4. Editor de Relación
        ttk.Label(frame_campos, text="Relación:").pack(anchor='w', pady=(10, 0))
        opciones_relacion = ["Dueño", "Hijo", "Esposa", "Empleado", "Visita", "Otro"]
        combo_relacion = ttk.Combobox(frame_campos, values=opciones_relacion, state="readonly")
        if relacion_actual in opciones_relacion:
            combo_relacion.set(relacion_actual)
        else:
            combo_relacion.set(opciones_relacion[0])
        combo_relacion.pack(fill='x', pady=5)


        def guardar_cambios():
            # --- Obtener y validar todos los campos ---
            nuevo_nombre = entry_nuevo_nombre.get().strip()
            if not nuevo_nombre:
                tk.messagebox.showwarning("Campo Vacío", "El nombre no puede estar vacío.", parent=ventana_modificar)
                return

            nuevo_rut = entry_nuevo_rut.get().strip()
            if not self.validar_rut(nuevo_rut):
                tk.messagebox.showwarning("RUT Inválido", "El RUT ingresado no es válido. Por favor, verifícalo.", parent=ventana_modificar)
                return
            
            try:
                nueva_fecha_dt = datetime.strptime(f"{combo_anio.get()}-{combo_mes.get()}-{combo_dia.get()}", "%Y-%m-%d")
                nueva_fecha_str = nueva_fecha_dt.strftime("%Y-%m-%d")
            except ValueError:
                tk.messagebox.showwarning("Fecha Inválida", "La fecha de nacimiento seleccionada no es válida.", parent=ventana_modificar)
                return

            nueva_relacion = combo_relacion.get()
            
            # --- Recalcular la edad ---
            today = datetime.now()
            nueva_edad = today.year - nueva_fecha_dt.year - ((today.month, today.day) < (nueva_fecha_dt.month, nueva_fecha_dt.day))

            try:
                # 1. Actualizar en MySQL. Usamos el RUT actual para encontrar el registro.
                self.cursor.execute(
                    "UPDATE reconocimiento SET nombre_completo = %s, rut = %s, fecha_nacimiento = %s, edad = %s, relacion = %s WHERE rut = %s",
                    (nuevo_nombre, nuevo_rut, nueva_fecha_str, nueva_edad, nueva_relacion, rut_actual) # Se usa rut_actual para el WHERE
                )
                self.conexion.commit()

                # 2. Actualizar datos en memoria (diccionarios)
                # Como el nombre y el RUT pueden cambiar, es más seguro eliminar la entrada antigua y crear una nueva.
                encoding_persona = self.encodings_registrados.pop(nombre_actual, None)
                tiempo_cooldown = self.last_detection_time.pop(nombre_actual, None)
                self.datos_registrados.pop(nombre_actual, None)

                # Crear nueva entrada con los datos actualizados
                self.datos_registrados[nuevo_nombre] = {
                    'fecha_nacimiento': nueva_fecha_str,
                    'edad': nueva_edad,
                    'rut': nuevo_rut,
                    'relacion': nueva_relacion,
                    'fecha_registro': fecha_reg_actual_str,
                    'id_imagen': id_imagen
                }
                if encoding_persona is not None:
                    self.encodings_registrados[nuevo_nombre] = encoding_persona
                if tiempo_cooldown is not None:
                    self.last_detection_time[nuevo_nombre] = tiempo_cooldown

                tk.messagebox.showinfo("Datos Modificados", f"Los datos de '{nombre_actual}' han sido actualizados exitosamente.", parent=self.ventana_admin)
                
                # Recargar la tabla del admin y cerrar ventana
                self._cargar_personas_admin_treeview()
                self.limpiar_datos_panel()
                ventana_modificar.destroy()

            except mysql.connector.Error as err:
                # Manejar el error de RUT duplicado
                if err.errno == 1062: # 1062 es el código de error para "Duplicate entry"
                    tk.messagebox.showerror("Error de Duplicado", f"El RUT '{nuevo_rut}' ya está registrado. Por favor, ingrese uno diferente.", parent=ventana_modificar)
                else:
                    print(f"❌ Error al modificar datos en MySQL: {err}")
                    tk.messagebox.showerror("Error de Base de Datos", f"Error al modificar los datos en MySQL: {err}", parent=ventana_modificar)

        ttk.Button(ventana_modificar, text="Guardar Cambios", command=guardar_cambios, style='TButton').pack(side="bottom", pady=20)

        # Centrar la ventana de modificar
        ventana_modificar.update_idletasks()
        x = self.ventana_admin.winfo_x() + (self.ventana_admin.winfo_width() // 2) - (ventana_modificar.winfo_width() // 2)
        y = self.ventana_admin.winfo_y() + (self.ventana_admin.winfo_height() // 2) - (ventana_modificar.winfo_height() // 2)
        ventana_modificar.geometry(f"+{x}+{y}")
        
    def log_app_startup(self):
        """Registra el inicio de la aplicación y revisa si hay desconocidos."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{now}] Aplicación iniciada.\n"
        try:
            # Mantiene el registro del inicio en el archivo de log
            with open(APP_LOG_FILE, "a") as f:
                f.write(log_message)
            print(f"Log de inicio de app guardado en {APP_LOG_FILE}")

            # Verifica si la carpeta de desconocidos existe y si contiene archivos
            if os.path.exists(DESCONOCIDOS_FOTOS_DIR) and os.listdir(DESCONOCIDOS_FOTOS_DIR):
                # Si hay archivos, muestra la alerta de persona sospechosa
                tk.messagebox.showwarning("AVISO DE SEGURIDAD", "¡PERSONA SOSPECHOSA AVISTADA!")
            # Si no hay archivos, la aplicación se inicia silenciosamente sin mensaje emergente.

        except Exception as e:
            print(f"❌ Error al escribir en el archivo de log o verificar desconocidos: {e}")
            tk.messagebox.showerror("Error de Inicio", f"No se pudo registrar el inicio de la aplicación: {e}")

    def mostrar_ventana_sospechosos(self):
        """Crea y muestra la ventana para visualizar y gestionar las fotos de desconocidos."""
        ventana = tk.Toplevel(self.root)
        ventana.title("Personas Sospechosas / Desconocidas")
        ventana.geometry("800x600")
        ventana.transient(self.root)
        ventana.grab_set()

        # Frame superior para botones de acción
        frame_botones_top = ttk.Frame(ventana)
        frame_botones_top.pack(pady=10, fill='x')

        # Contenedor principal con scroll
        canvas = tk.Canvas(ventana)
        scrollbar = ttk.Scrollbar(ventana, orient="vertical", command=canvas.yview)
        frame_contenido = ttk.Frame(canvas)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.create_window((0, 0), window=frame_contenido, anchor="nw")

        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        frame_contenido.bind("<Configure>", on_frame_configure)
        
        # Botón para recargar el contenido
        btn_recargar = ttk.Button(frame_botones_top, text="Recargar Fotos",
                                  command=lambda: self._cargar_fotos_sospechosas(frame_contenido))
        btn_recargar.pack(padx=10)

        # Carga inicial de las fotos
        self._cargar_fotos_sospechosas(frame_contenido)
        
        # Centrar la ventana
        ventana.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (ventana.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (ventana.winfo_height() // 2)
        ventana.geometry(f"+{x}+{y}")

    def _cargar_fotos_sospechosas(self, frame_contenido):
        """Limpia el frame y carga las imágenes de la carpeta de desconocidos."""
        # Limpiar contenido anterior
        for widget in frame_contenido.winfo_children():
            widget.destroy()

        if not os.path.exists(DESCONOCIDOS_FOTOS_DIR) or not os.listdir(DESCONOCIDOS_FOTOS_DIR):
            ttk.Label(frame_contenido, text="No se han registrado personas sospechosas.", font=('Helvetica Neue', 14)).pack(pady=20)
            return

        image_files = sorted([f for f in os.listdir(DESCONOCIDOS_FOTOS_DIR) if f.endswith(('.jpg', '.png'))], reverse=True)
        
        max_cols = 4
        for idx, filename in enumerate(image_files):
            row = idx // max_cols
            col = idx % max_cols
            
            path_completo = os.path.join(DESCONOCIDOS_FOTOS_DIR, filename)

            item_frame = ttk.Frame(frame_contenido, padding=5, relief="solid", borderwidth=1)
            item_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            try:
                img = Image.open(path_completo)
                img.thumbnail((150, 150), Image.LANCZOS)
                imgtk = ImageTk.PhotoImage(img)

                lbl_img = tk.Label(item_frame, image=imgtk)
                lbl_img.image = imgtk # Guardar referencia
                lbl_img.pack(pady=5)

                # Extraer fecha y hora del nombre del archivo
                timestamp_str = filename.replace("desconocido_", "").replace(".jpg", "")
                try:
                    fecha_hora_obj = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    fecha_legible = fecha_hora_obj.strftime("%d-%m-%Y %H:%M:%S")
                    ttk.Label(item_frame, text=fecha_legible, font=('Helvetica Neue', 9)).pack()
                except ValueError:
                    ttk.Label(item_frame, text=filename, font=('Helvetica Neue', 8)).pack()
                
                btn_eliminar = ttk.Button(item_frame, text="Eliminar",
                                          command=lambda p=path_completo: self.eliminar_foto_sospechosa(p, frame_contenido))
                btn_eliminar.pack(pady=5)

            except Exception as e:
                print(f"Error al cargar la imagen {filename}: {e}")
                lbl_error = ttk.Label(item_frame, text=f"Error al cargar:\n{filename}", foreground="red")
                lbl_error.pack()

    def eliminar_foto_sospechosa(self, path_a_eliminar, frame_a_recargar):
        """Elimina un archivo de foto de un sospechoso y recarga la vista."""
        filename = os.path.basename(path_a_eliminar)
        confirm = tk.messagebox.askyesno(
            "Confirmar Eliminación",
            f"¿Estás seguro de que quieres eliminar permanentemente la foto '{filename}'?",
            parent=frame_a_recargar.winfo_toplevel() # Asegura que el messagebox aparezca al frente
        )

        if confirm:
            try:
                os.remove(path_a_eliminar)
                print(f"✔️ Foto de sospechoso eliminada: {path_a_eliminar}")
                # Recargar las fotos para actualizar la ventana
                self._cargar_fotos_sospechosas(frame_a_recargar)
            except Exception as e:
                print(f"❌ Error al eliminar la foto {path_a_eliminar}: {e}")
                tk.messagebox.showerror("Error de Eliminación", f"No se pudo eliminar el archivo: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DeteccionMovimientoApp(root)
    root.mainloop()
