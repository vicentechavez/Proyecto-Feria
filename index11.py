import os
import cv2
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import pygame
import time
import face_recognition
import numpy as np
import mysql.connector
from datetime import datetime
import io
import socket

# ==============================================================================
# --- CONFIGURACIÓN INICIAL Y CONSTANTES ---
# ==============================================================================
pygame.mixer.init()
ALERTA_SONIDO_RECONOCIDO = "confirmacion.mp3"
ALERTA_SONIDO_NO_RECONOCIDO = "error.mp3"
# La siguiente línea ya no es necesaria para guardar archivos, pero la mantenemos por si se quiere reactivar.
DESCONOCIDOS_FOTOS_DIR = "desconocidos_fotos" 
APP_LOG_FILE = "app_log.txt"

if not os.path.exists(DESCONOCIDOS_FOTOS_DIR):
    os.makedirs(DESCONOCIDOS_FOTOS_DIR)

class DeteccionMovimientoApp:
    # ==============================================================================
    # --- COLORES Y ESTILOS ---
    # ==============================================================================
    COLORES = {
        "fondo_principal": "#3c3c3c", "fondo_paneles": "#4a4a4b", "fondo_label_video": "black",
        "fondo_barra_estado": "#2a2a2b", "texto_barra_estado": "#e0e0e0", "boton_normal_bg": "#0095d5",
        "boton_normal_fg": "white", "boton_activo_bg": "#0078a8", "texto_titulo": "#ffffff",
        "texto_label": "#f0f0f0", "texto_cooldown": "#ffb74d", "texto_error": "#ef5350",
        "borde_widget": "#6e6e6f", "animacion_fondo": "#4a4a4b", "animacion_texto_nombre": "#ffffff",
        "borde_reconocido": (0, 255, 0), "borde_desconocido": (0, 0, 255)
    }
    FONT_PRINCIPAL = ('Segoe UI', 10)
    FONT_TITULO = ('Segoe UI', 12, 'bold')
    FONT_ESTADO = ('Segoe UI', 9)

    # ==============================================================================
    # --- 1. INICIALIZACIÓN Y CONFIGURACIÓN ---
    # ==============================================================================
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Reconocimiento Facial (Red)")
        self.root.geometry("1100x750")
        self.root.resizable(True, True)
        self.root.minsize(900, 650)
        self.root.configure(bg=self.COLORES["fondo_principal"])

        self.device_hostname = socket.gethostname()
        self.root.title(f"Sistema de Reconocimiento Facial (Red) - Dispositivo: {self.device_hostname}")

        self.configurar_estilos()
        self.crear_widgets()

        self.cap = None
        self.running = True
        self.detection_active = False
        self.procesando = False
        self.reloading_data_lock = threading.Lock()
        self.last_detection_time = {}
        self.recognition_timer = None
        self.face_detection_interval = 5
        self.cooldown_period = 60
        self.last_unknown_capture_time = 0
        self.unknown_capture_cooldown = 30
        self.last_notification_time = 0
        self.notification_cooldown = 300

        self.last_db_update_timestamp = None
        self.db_poll_interval = 5

        self.inicializar_base_datos_mysql()
        self._reload_data_from_db(is_initial_load=True)

        self.root.protocol("WM_DELETE_WINDOW", self.cerrar)

        self.ventana_animacion = None
        self.animacion_label = None
        self.nombre_reconocido_animacion = ""
        self.estado_animacion = "neutral"
        self.animacion_frame_idx = 0
        self.animacion_imagenes = self.cargar_imagenes_pixeladas()
        self.animacion_timer = None

        self.log_app_startup()
        threading.Thread(target=self._poll_database_for_updates, daemon=True).start()

    def configurar_estilos(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=self.COLORES["fondo_principal"])
        style.configure('Contenedor.TFrame', background=self.COLORES["fondo_paneles"])
        style.configure('TButton', font=self.FONT_PRINCIPAL, padding=10, background=self.COLORES["boton_normal_bg"], foreground=self.COLORES["boton_normal_fg"], bordercolor=self.COLORES["boton_normal_bg"], relief='flat')
        style.map('TButton', background=[('active', self.COLORES["boton_activo_bg"])], relief=[('pressed', 'sunken'), ('!pressed', 'flat')])
        style.configure('TLabel', font=self.FONT_PRINCIPAL, background=self.COLORES["fondo_paneles"], foreground=self.COLORES["texto_label"])
        style.configure('Titulo.TLabel', font=self.FONT_TITULO, foreground=self.COLORES["texto_titulo"], background=self.COLORES["fondo_paneles"])
        style.configure('Estado.TLabel', font=self.FONT_ESTADO, background=self.COLORES["fondo_barra_estado"], foreground=self.COLORES["texto_barra_estado"])
        style.configure('TLabelframe', background=self.COLORES["fondo_paneles"], bordercolor=self.COLORES["borde_widget"])
        style.configure('TLabelframe.Label', font=self.FONT_TITULO, foreground=self.COLORES["texto_titulo"], background=self.COLORES["fondo_paneles"])
        
        # --- NUEVOS ESTILOS PARA LA VENTANA DE REGISTRO ---
        color_fondo_registro = '#4d4d4d'
        color_texto_registro = 'white'
        color_borde_registro = '#6e6e6f' 
        color_seleccion_registro = '#3c3c3c'

        style.configure('Black.TLabel', background=color_fondo_registro, foreground=color_texto_registro, font=self.FONT_PRINCIPAL)
        style.configure('Black.TFrame', background=color_fondo_registro)
        style.configure('Black.TEntry', fieldbackground=color_fondo_registro, foreground=color_texto_registro, insertcolor=color_texto_registro, bordercolor=color_borde_registro)
        style.map('Black.TCombobox',
                  fieldbackground=[('readonly', color_fondo_registro)],
                  selectbackground=[('readonly', color_seleccion_registro)],
                  selectforeground=[('readonly', color_texto_registro)],
                  foreground=[('readonly', color_texto_registro)],
                  background=[('readonly', color_fondo_registro)])
        style.configure('Black.TCombobox', bordercolor=color_borde_registro)


    def crear_widgets(self):
        self.frame_principal = ttk.Frame(self.root, padding=15)
        self.frame_principal.pack(expand=True, fill='both')
        self.frame_principal.grid_columnconfigure(0, weight=3)
        self.frame_principal.grid_columnconfigure(1, weight=1)
        self.frame_principal.grid_rowconfigure(1, weight=1)

        panel_controles = ttk.LabelFrame(self.frame_principal, text="Controles", padding=15, style='TLabelframe')
        panel_controles.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 10))

        botones = {
            "Iniciar Detección": self.iniciar, "Detener": self.detener, "Registrar Persona": self.registrar,
            "Ver Personas": self.mostrar_personas_registradas, "Ver Historial": self.mostrar_historial_reconocimiento,
            "Modo Admin": self.mostrar_ventana_admin_login, "Ver Sospechosos": self.mostrar_ventana_sospechosos
        }
        for i, (texto, comando) in enumerate(botones.items()):
            btn = ttk.Button(panel_controles, text=texto, command=comando, style='TButton')
            btn.grid(row=0, column=i, padx=5, pady=5)
            if texto == "Detener": btn.config(state=tk.DISABLED)
            setattr(self, f"btn_{texto.lower().replace(' ', '_')}", btn)

        self.label_video = tk.Label(self.frame_principal, bg=self.COLORES["fondo_label_video"], bd=1, relief="sunken")
        self.label_video.grid(row=1, column=0, pady=10, padx=(0, 10), sticky='nsew')

        self.panel_datos = ttk.LabelFrame(self.frame_principal, text="Datos Reconocidos", padding=15, style='TLabelframe')
        self.panel_datos.grid(row=1, column=1, pady=10, padx=(10, 0), sticky='ns')
        self.labels_datos = {}
        campos_datos = ['Nombre Completo', 'Edad', 'RUT', 'Fecha de Nacimiento', 'Relación', 'Fecha de Registro']
        for campo in campos_datos:
            lbl = ttk.Label(self.panel_datos, text=f"{campo}: ---", wraplength=250)
            lbl.pack(anchor='w', pady=6)
            self.labels_datos[campo] = lbl
        self.label_cooldown_status = ttk.Label(self.panel_datos, text="", font=(self.FONT_PRINCIPAL[0], 9, 'italic'), foreground=self.COLORES["texto_cooldown"])
        self.label_cooldown_status.pack(anchor='w', pady=8)

        self.status_label = ttk.Label(self.root, text="Estado: Listo", anchor='w', padding=5, style='Estado.TLabel')
        self.status_label.pack(side='bottom', fill='x')

    # ==============================================================================
    # --- 4. GESTIÓN DE BASE DE DATOS Y SINCRONIZACIÓN ---
    # ==============================================================================
    def inicializar_base_datos_mysql(self):
        try:
            self.db_config = {
                "host": "192.168.1.122", "user": "ojodigital", "password": "feria2025",
                "database": "ojodigital", "charset": "utf8mb4", "use_unicode": True
            }
            self.conexion = mysql.connector.connect(**self.db_config)
            print("✅ MySQL inicializada y conectada.")
        except mysql.connector.Error as err:
            print(f"❌ Error MySQL: {err}")
            messagebox.showerror("Error de Base de Datos", f"No se pudo conectar a la base de datos MySQL.\nError: {err}")
            self.root.destroy()

    def _poll_database_for_updates(self):
        poll_conn = mysql.connector.connect(**self.db_config)
        poll_cursor = poll_conn.cursor(dictionary=True)
        
        while self.running:
            try:
                sql_heartbeat = "INSERT INTO dispositivos_activos (hostname, ultima_conexion) VALUES (%s, NOW()) ON DUPLICATE KEY UPDATE ultima_conexion = NOW()"
                poll_cursor.execute(sql_heartbeat, (self.device_hostname,))
                
                poll_cursor.execute("SELECT ultima_actualizacion FROM estado_sistema WHERE id = 1")
                result = poll_cursor.fetchone()
                
                if result:
                    current_db_timestamp = result['ultima_actualizacion']
                    if self.last_db_update_timestamp is None or current_db_timestamp > self.last_db_update_timestamp:
                        print(f"🔄 Se detectó un cambio en la base de datos. Recargando datos...")
                        self.last_db_update_timestamp = current_db_timestamp
                        self._reload_data_from_db()

                poll_conn.commit()
            except mysql.connector.Error as err:
                print(f"⚠️ Error en el sondeo de la BD: {err}. Intentando reconectar...")
                try:
                    poll_conn.close()
                    poll_conn = mysql.connector.connect(**self.db_config)
                    poll_cursor = poll_conn.cursor(dictionary=True)
                except mysql.connector.Error:
                    time.sleep(10)
            
            time.sleep(self.db_poll_interval)
        
        poll_conn.close()
        print("🛑 Sondeo de base de datos detenido.")

    def _update_system_status(self):
        cursor = None
        try:
            cursor = self.conexion.cursor()
            cursor.execute("UPDATE estado_sistema SET ultima_actualizacion = NOW() WHERE id = 1")
            self.conexion.commit()
        except mysql.connector.Error as err:
            print(f"❌ Error al actualizar el estado del sistema: {err}")
        finally:
            if cursor:
                cursor.close()

    def _reload_data_from_db(self, is_initial_load=False):
        with self.reloading_data_lock:
            if not is_initial_load:
                self.status_label.config(text="Estado: Sincronizando datos desde la red...")
            
            self.datos_registrados = self.cargar_datos_registrados_mysql()
            self.encodings_registrados = self.cargar_encodings_registrados()
            
            if not is_initial_load:
                 self.status_label.config(text="Estado: Sincronización completada.")
            print(f"✅ Datos recargados. {len(self.encodings_registrados)} rostros en memoria.")

    def cargar_datos_registrados_mysql(self):
        datos = {}
        cursor = None
        try:
            cursor = self.conexion.cursor(dictionary=True)
            cursor.execute("SELECT nombre_completo, fecha_nacimiento, edad, rut, relacion, fecha_registro, id_imagen FROM reconocimiento")
            for row in cursor.fetchall():
                datos[row['nombre_completo']] = {
                    'fecha_nacimiento': row['fecha_nacimiento'].strftime("%Y-%m-%d"), 'edad': row['edad'],
                    'rut': row['rut'], 'relacion': row['relacion'], 
                    'fecha_registro': row['fecha_registro'].strftime("%Y-%m-%d"),
                    'id_imagen': row['id_imagen']
                }
        except mysql.connector.Error as err:
            print(f"❌ Error cargando datos de personas desde MySQL: {err}")
        finally:
            if cursor:
                cursor.close()
        return datos

    def cargar_encodings_registrados(self):
        encodings = {}
        cursor = None
        try:
            cursor = self.conexion.cursor(dictionary=True)
            sql = "SELECT r.nombre_completo, i.encoding_data FROM reconocimiento r JOIN imagenes_reconocimiento i ON r.id_imagen = i.id"
            cursor.execute(sql)
            for row in cursor.fetchall():
                encoding = np.frombuffer(row['encoding_data'], dtype=np.float64)
                encodings[row['nombre_completo']] = encoding
        except mysql.connector.Error as err:
            print(f"❌ Error cargando encodings desde MySQL: {err}")
        finally:
            if cursor:
                cursor.close()
        return encodings

    def registrar_en_historial(self, nombre, rut, fecha_hora):
        cursor = None
        try:
            cursor = self.conexion.cursor()
            sql = "INSERT INTO historial_reconocimiento (nombre, rut, fecha_hora, dispositivo_id) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (nombre, rut, fecha_hora.strftime("%Y-%m-%d %H:%M:%S"), self.device_hostname))
            self.conexion.commit()
            print(f"✔️ Historial registrado: {nombre} ({rut}) desde {self.device_hostname}")
            self.status_label.config(text=f"Reconocido: {nombre} ({fecha_hora.strftime('%H:%M:%S')})")
        except mysql.connector.Error as err:
            print(f"❌ Error al insertar en historial: {err}")
        finally:
            if cursor:
                cursor.close()

    # ==============================================================================
    # --- 5. GESTIÓN DE REGISTRO DE PERSONAS ---
    # ==============================================================================
    def registrar_persona(self, nombre_completo, fecha_nacimiento, edad, rut, relacion, fecha_registro):
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
            time.sleep(1)
        ret, frame = self.cap.read()
        if not ret:
            self.status_label.config(text="Error: No se pudo capturar imagen.")
            return
        rostro = self.detectar_rostro(cv2.flip(frame, 1))
        if rostro is None:
            messagebox.showwarning("Registro Fallido", "No se detectó ningún rostro.")
            return
        encoding = self.extraer_encoding(rostro)
        if encoding is None:
            messagebox.showwarning("Registro Fallido", "No se pudo procesar el rostro.")
            return
        
        cursor = None
        try:
            cursor = self.conexion.cursor(dictionary=True)
            cursor.execute("SELECT COUNT(*) as count FROM reconocimiento WHERE rut = %s", (rut,))
            if cursor.fetchone()['count'] > 0:
                messagebox.showerror("Error de Registro", "El RUT ya está registrado.")
                return

            _, buffer_img = cv2.imencode('.jpg', rostro)
            imagen_data = buffer_img.tobytes()
            encoding_data = encoding.tobytes()

            sql_img = "INSERT INTO imagenes_reconocimiento (imagen_data, encoding_data) VALUES (%s, %s)"
            cursor.execute(sql_img, (imagen_data, encoding_data))
            new_id_imagen = cursor.lastrowid

            sql_rec = "INSERT INTO reconocimiento (nombre_completo, fecha_nacimiento, edad, rut, relacion, fecha_registro, id_imagen) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(sql_rec, (nombre_completo, fecha_nacimiento, edad, rut, relacion, fecha_registro, new_id_imagen))
            
            self.conexion.commit()
            
            self._update_system_status()
            self._reload_data_from_db()
            
            self.status_label.config(text=f"✅ Registrado: {nombre_completo}")
            messagebox.showinfo("Registro Exitoso", f"{nombre_completo} ha sido registrado.")

        except mysql.connector.Error as err:
            messagebox.showerror("Error de Registro en DB", f"Ocurrió un error de base de datos: {err}")
            self.conexion.rollback()
        except Exception as e:
            messagebox.showerror("Error de Registro", f"Ocurrió un error inesperado: {e}")
            self.conexion.rollback()
        finally:
            if cursor:
                cursor.close()

    # ==============================================================================
    # --- 6. PANELES DE VISUALIZACIÓN ---
    # ==============================================================================
    def mostrar_personas_registradas(self):
        ventana = tk.Toplevel(self.root)
        ventana.title("Personas Registradas (MySQL)")
        ventana.geometry("850x650")
        self.centrar_ventana(ventana, self.root)

        frame_superior = ttk.Frame(ventana, padding=5)
        frame_superior.pack(fill='x')
        
        ttk.Button(frame_superior, text="Recargar Datos", command=lambda: self._cargar_vista_personas(frame_contenido)).pack()

        canvas = tk.Canvas(ventana)
        scrollbar = ttk.Scrollbar(ventana, orient="vertical", command=canvas.yview)
        frame_contenido = ttk.Frame(canvas, padding=10)
        
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((0, 0), window=frame_contenido, anchor="nw")
        
        frame_contenido.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        self._cargar_vista_personas(frame_contenido)

    def _cargar_vista_personas(self, frame_destino):
        # Limpiar vista anterior
        for widget in frame_destino.winfo_children():
            widget.destroy()

        cursor = None
        try:
            cursor = self.conexion.cursor(dictionary=True)
            sql = "SELECT r.nombre_completo, r.rut, r.relacion, i.imagen_data FROM reconocimiento r JOIN imagenes_reconocimiento i ON r.id_imagen = i.id ORDER BY r.nombre_completo"
            cursor.execute(sql)
            
            personas = cursor.fetchall()
            if not personas:
                ttk.Label(frame_destino, text="No hay personas registradas en la base de datos.").pack()
                return

            for row_idx, row in enumerate(personas):
                frame_item = ttk.Frame(frame_destino, borderwidth=1, relief="solid", padding=5)
                frame_item.grid(row=row_idx // 4, column=row_idx % 4, padx=5, pady=5, sticky='nsew')
                
                img = Image.open(io.BytesIO(row['imagen_data']))
                img.thumbnail((100, 100), Image.LANCZOS)
                imgtk = ImageTk.PhotoImage(image=img)
                
                lbl_imagen = tk.Label(frame_item, image=imgtk)
                lbl_imagen.image = imgtk
                lbl_imagen.pack()
                
                ttk.Label(frame_item, text=f"Nombre: {row['nombre_completo']}", font=('Helvetica Neue', 9, 'bold')).pack(anchor='w')
                ttk.Label(frame_item, text=f"RUT: {row['rut']}", font=('Helvetica Neue', 9)).pack(anchor='w')
                ttk.Label(frame_item, text=f"Relación: {row['relacion']}", font=('Helvetica Neue', 9)).pack(anchor='w')
        except mysql.connector.Error as err:
            messagebox.showerror("Error de Carga", f"No se pudieron cargar las personas: {err}")
        finally:
            if cursor:
                cursor.close()

    # ==============================================================================
    # --- 7. PANEL DE ADMINISTRACIÓN ---
    # ==============================================================================
    def eliminar_persona(self):
        selected_item = self.tree_personas_admin.selection()
        if not selected_item:
            messagebox.showwarning("Sin Selección", "Selecciona una persona para eliminar.")
            return
        values = self.tree_personas_admin.item(selected_item, 'values')
        id_imagen, nombre, rut = values[0], values[1], values[2]

        if messagebox.askyesno("Confirmar", f"¿Eliminar a '{nombre}' (RUT: {rut})? Esto es permanente."):
            cursor = None
            try:
                cursor = self.conexion.cursor()
                cursor.execute("DELETE FROM imagenes_reconocimiento WHERE id = %s", (id_imagen,))
                self.conexion.commit()
                
                self._update_system_status()
                self._reload_data_from_db()

                messagebox.showinfo("Éxito", f"'{nombre}' ha sido eliminado de la base de datos.")
                self._cargar_personas_admin_treeview()
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"No se pudo eliminar de la base de datos: {err}")
                self.conexion.rollback()
            finally:
                if cursor:
                    cursor.close()

    # ==============================================================================
    # --- LÓGICA DE DETECCIÓN (UI Y PROCESAMIENTO) ---
    # ==============================================================================
    def iniciar(self):
        if self.detection_active: return
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened(): raise IOError("No se puede abrir la cámara web")
            self.detection_active = True
            self.btn_iniciar_detección.config(state=tk.DISABLED)
            self.btn_detener.config(state=tk.NORMAL)
            self.status_label.config(text="Estado: Detección iniciada")
            self.actualizar_video()
            self.iniciar_reconocimiento_periodico()
            self.mostrar_ventana_animacion()
        except IOError as e:
            messagebox.showerror("Error de Cámara", f"No se pudo acceder a la cámara: {e}")
            self.detener()

    def detener(self):
        if not self.detection_active: return
        self.detection_active = False
        if self.recognition_timer:
            self.recognition_timer.cancel()
            self.recognition_timer = None
        if self.cap: self.cap.release()
        self.label_video.config(image="")
        self.btn_iniciar_detección.config(state=tk.NORMAL)
        self.btn_detener.config(state=tk.DISABLED)
        self.status_label.config(text="Estado: Detenido")
        self.limpiar_datos_panel()
        self.last_detection_time = {}
        self.cerrar_ventana_animacion()

    def actualizar_video(self):
        if not self.detection_active: return
        ret, frame = self.cap.read()
        if ret:
            self.mostrar_frame(cv2.flip(frame, 1))
            self.root.after(30, self.actualizar_video)

    def iniciar_reconocimiento_periodico(self):
        if self.detection_active and not self.procesando:
            with self.reloading_data_lock:
                if self.cap and self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if ret:
                        threading.Thread(target=self.procesar_reconocimiento, args=(cv2.flip(frame, 1).copy(),), daemon=True).start()
        if self.detection_active:
            self.recognition_timer = threading.Timer(self.face_detection_interval, self.iniciar_reconocimiento_periodico)
            self.recognition_timer.start()

    def procesar_reconocimiento(self, frame):
        self.procesando = True
        try:
            with self.reloading_data_lock:
                if not self.encodings_registrados:
                    return
                resultados = self.reconocer_rostros(frame)
            
            current_time, now = time.time(), datetime.now()
            frame_to_display = frame.copy()
            if not resultados:
                self.estado_animacion = "neutral"
                self.limpiar_datos_panel()
            else:
                for nombre, (top, right, bottom, left) in resultados:
                    if nombre != "Desconocido":
                        color = self.COLORES["borde_reconocido"]
                        self.procesar_persona_reconocida(nombre, current_time, now)
                        break
                    else:
                        color = self.COLORES["borde_desconocido"]
                        self.procesar_persona_desconocida(frame, current_time, now)
                    cv2.rectangle(frame_to_display, (left, top), (right, bottom), color, 2)
                    cv2.putText(frame_to_display, nombre, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            self.mostrar_frame(frame_to_display)
        finally:
            self.procesando = False

    def procesar_persona_reconocida(self, nombre, current_time, now):
        if nombre not in self.last_detection_time or (current_time - self.last_detection_time.get(nombre, 0)) > self.cooldown_period:
            self.last_detection_time[nombre] = current_time
            rut_final = self.datos_registrados.get(nombre, {}).get('rut', 'N/A')
            self.registrar_en_historial(nombre, rut_final, now)
            self.sonar_confirmacion()
            self.nombre_reconocido_animacion, self.estado_animacion = nombre, "reconocido"
            self.mostrar_datos_panel(nombre)
        else:
            self.nombre_reconocido_animacion, self.estado_animacion = nombre, "cooldown"
            self.mostrar_datos_panel(nombre)
            self.label_cooldown_status.config(text="Enfriamiento Activo (1 min)", foreground=self.COLORES["texto_cooldown"])

    def reconocer_rostros(self, frame):
        resultados = []
        rgb_small_frame = cv2.cvtColor(cv2.resize(frame, (0, 0), fx=0.25, fy=0.25), cv2.COLOR_BGR2RGB)
        locs = face_recognition.face_locations(rgb_small_frame)
        encs = face_recognition.face_encodings(rgb_small_frame, locs)
        
        encodings_actuales = list(self.encodings_registrados.values())
        nombres_actuales = list(self.encodings_registrados.keys())

        for encoding, loc_small in zip(encs, locs):
            nombre_encontrado = "Desconocido"
            if nombres_actuales:
                matches = face_recognition.compare_faces(encodings_actuales, encoding, tolerance=0.5)
                if True in matches:
                    face_distances = face_recognition.face_distance(encodings_actuales, encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        nombre_encontrado = nombres_actuales[best_match_index]
            top, right, bottom, left = [c * 4 for c in loc_small]
            resultados.append((nombre_encontrado, (top, right, bottom, left)))
        return resultados

    # ==============================================================================
    # --- FUNCIONES AUXILIARES Y DE CIERRE ---
    # ==============================================================================
    def cerrar(self):
        print("Cerrando aplicación...")
        self.running = False
        self.detener()
        if hasattr(self, "conexion") and self.conexion.is_connected():
            self.conexion.close()
            print("✅ Conexión MySQL cerrada.")
        self.root.destroy()
        
    def mostrar_frame(self, frame):
        h, w, _ = frame.shape
        label_w, label_h = self.label_video.winfo_width(), self.label_video.winfo_height()
        if label_h <= 1 or label_w <= 1:
            self.label_video.after(100, lambda: self.mostrar_frame(frame))
            return
        scale = min(label_w / w, label_h / h)
        resized_frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
        img = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)))
        self.label_video.imgtk = img
        self.label_video.configure(image=img)

    def mostrar_datos_panel(self, nombre_completo):
        datos = self.datos_registrados.get(nombre_completo)
        if datos:
            self.labels_datos["Nombre Completo"].config(text=f"Nombre: {nombre_completo}")
            self.labels_datos["Edad"].config(text=f"Edad: {datos['edad']}")
            self.labels_datos["RUT"].config(text=f"RUT: {datos['rut']}")
            self.labels_datos["Fecha de Nacimiento"].config(text=f"F. Nac: {datos['fecha_nacimiento']}")
            self.labels_datos["Relación"].config(text=f"Relación: {datos['relacion']}")
            self.labels_datos["Fecha de Registro"].config(text=f"Registro: {datos['fecha_registro']}")
            self.label_cooldown_status.config(text="")

    def limpiar_datos_panel(self):
        for campo in self.labels_datos:
            self.labels_datos[campo].config(text=f"{campo.split(' ')[0]}: ---")
        self.label_cooldown_status.config(text="")

    def cargar_imagenes_pixeladas(self):
        imagenes = {}
        try:
            base_path = "caras_pixel"
            nombres_img = ["neutral.gif", "reconocido_1.png", "reconocido_2.png", "desconocido.png", "cooldown.png"]
            for nombre in nombres_img:
                key = nombre.split('.')[0]
                path = os.path.join(base_path, nombre)
                imagenes[key] = ImageTk.PhotoImage(Image.open(path).resize((150, 150), Image.LANCZOS))
        except Exception as e:
            messagebox.showerror("Error de Imagen", f"No se pudieron cargar las imágenes de animación: {e}")
        return imagenes

    def mostrar_ventana_animacion(self):
        if self.ventana_animacion and self.ventana_animacion.winfo_exists():
            self.ventana_animacion.lift()
            return
        self.ventana_animacion = tk.Toplevel(self.root)
        self.ventana_animacion.title("Estado")
        self.ventana_animacion.geometry("300x350")
        self.ventana_animacion.resizable(False, False)
        self.ventana_animacion.protocol("WM_DELETE_WINDOW", self.cerrar_ventana_animacion)
        self.ventana_animacion.configure(bg=self.COLORES["animacion_fondo"])
        frame_animacion = tk.Frame(self.ventana_animacion, bg=self.COLORES["animacion_fondo"])
        frame_animacion.pack(expand=True, fill='both')
        self.animacion_label = tk.Label(frame_animacion, bg=self.COLORES["animacion_fondo"])
        self.animacion_label.pack(pady=10)
        self.nombre_label_animacion = tk.Label(frame_animacion, text="Esperando...", font=(self.FONT_TITULO[0], 14, 'bold'), fg=self.COLORES["animacion_texto_nombre"], bg=self.COLORES["animacion_fondo"])
        self.nombre_label_animacion.pack(pady=5)
        self.actualizar_animacion_pixelada()
        self.centrar_ventana(self.ventana_animacion, self.root)

    def cerrar_ventana_animacion(self):
        if self.animacion_timer: self.ventana_animacion.after_cancel(self.animacion_timer)
        if self.ventana_animacion:
            self.ventana_animacion.destroy()
            self.ventana_animacion = None

    def actualizar_animacion_pixelada(self):
        if not self.ventana_animacion or not self.ventana_animacion.winfo_exists(): return
        img, texto_animacion = None, ""
        if self.estado_animacion == "neutral":
            img, texto_animacion = self.animacion_imagenes.get("neutral"), "Esperando..."
        elif self.estado_animacion == "reconocido":
            img = self.animacion_imagenes.get(f"reconocido_{self.animacion_frame_idx % 2 + 1}")
            self.animacion_frame_idx += 1
            texto_animacion = f"¡Hola, {self.nombre_reconocido_animacion}!"
        elif self.estado_animacion == "desconocido":
            img, texto_animacion = self.animacion_imagenes.get("desconocido"), "¡Persona Desconocida!"
        elif self.estado_animacion == "cooldown":
            img, texto_animacion = self.animacion_imagenes.get("cooldown"), f"{self.nombre_reconocido_animacion}\n(Enfriamiento)"
        if img:
            self.animacion_label.config(image=img)
            self.animacion_label.image = img
        self.nombre_label_animacion.config(text=texto_animacion)
        self.animacion_timer = self.ventana_animacion.after(200, self.actualizar_animacion_pixelada)

    def procesar_persona_desconocida(self, frame, current_time, now):
        self.estado_animacion = "desconocido"
        self.sonar_error()
        self.limpiar_datos_panel()
        if (current_time - self.last_unknown_capture_time) > self.unknown_capture_cooldown:
            self.last_unknown_capture_time = current_time
            # Guardar en base de datos en lugar de archivo local
            self.registrar_sospechoso_en_db(frame, now)
            self.notificar_persona_encargada(f"DB a las {now.strftime('%H:%M:%S')}")

    def registrar_sospechoso_en_db(self, frame, fecha_hora):
        cursor = None
        try:
            _, buffer_img = cv2.imencode('.jpg', frame)
            imagen_data = buffer_img.tobytes()
            
            cursor = self.conexion.cursor()
            sql = "INSERT INTO sospechosos (imagen_data, fecha_hora, dispositivo_id) VALUES (%s, %s, %s)"
            cursor.execute(sql, (imagen_data, fecha_hora.strftime("%Y-%m-%d %H:%M:%S"), self.device_hostname))
            self.conexion.commit()
            print(f"📸 Foto de sospechoso guardada en la base de datos desde {self.device_hostname}")
        except mysql.connector.Error as err:
            print(f"❌ Error al registrar sospechoso en DB: {err}")
            self.conexion.rollback()
        finally:
            if cursor:
                cursor.close()

    def detectar_rostro(self, frame):
        loc = face_recognition.face_locations(frame)
        return frame[loc[0][0]:loc[0][2], loc[0][3]:loc[0][1]] if loc else None

    def extraer_encoding(self, rostro):
        enc = face_recognition.face_encodings(cv2.cvtColor(rostro, cv2.COLOR_BGR2RGB), face_recognition.face_locations(cv2.cvtColor(rostro, cv2.COLOR_BGR2RGB)))
        return enc[0] if enc else None

    def registrar(self):
        ventana_registro = tk.Toplevel(self.root)
        ventana_registro.title("Registrar Persona")
        ventana_registro.geometry("400x400")
        ventana_registro.configure(bg='#4d4d4d')
        ventana_registro.transient(self.root)
        # No se usa grab_set() aquí para permitir la animación

        entradas = {}
        
        ttk.Label(ventana_registro, text="Nombre Completo:", style='Black.TLabel').pack(pady=5)
        entrada_nombre = ttk.Entry(ventana_registro, style='Black.TEntry')
        entrada_nombre.pack(pady=5, padx=20, fill='x')
        entradas["nombre_completo"] = entrada_nombre
        
        ttk.Label(ventana_registro, text="Fecha de Nacimiento:", style='Black.TLabel').pack(pady=5)
        frame_fecha = ttk.Frame(ventana_registro, style='Black.TFrame')
        frame_fecha.pack(pady=5, padx=20, fill='x')

        combo_dia = ttk.Combobox(frame_fecha, values=[f"{i:02d}" for i in range(1, 32)], width=5, state="readonly", style='Black.TCombobox')
        combo_dia.set("Día")
        combo_dia.pack(side=tk.LEFT, padx=2)
        entradas["dia_nacimiento"] = combo_dia

        combo_mes = ttk.Combobox(frame_fecha, values=[f"{i:02d}" for i in range(1, 13)], width=5, state="readonly", style='Black.TCombobox')
        combo_mes.set("Mes")
        combo_mes.pack(side=tk.LEFT, padx=2)
        entradas["mes_nacimiento"] = combo_mes

        current_year = datetime.now().year
        combo_anio = ttk.Combobox(frame_fecha, values=[str(i) for i in range(current_year, current_year - 100, -1)], width=7, state="readonly", style='Black.TCombobox')
        combo_anio.set("Año")
        combo_anio.pack(side=tk.LEFT, padx=2)
        entradas["anio_nacimiento"] = combo_anio
        
        ttk.Label(ventana_registro, text="RUT:", style='Black.TLabel').pack(pady=5)
        entrada_rut = ttk.Entry(ventana_registro, style='Black.TEntry')
        entrada_rut.pack(pady=5, padx=20, fill='x')
        entrada_rut.bind("<KeyRelease>", lambda e: self.formatear_rut(entrada_rut))
        entradas["rut"] = entrada_rut
        
        ttk.Label(ventana_registro, text="Relación:", style='Black.TLabel').pack(pady=5)
        combo_relacion = ttk.Combobox(ventana_registro, values=["Dueño", "Hijo", "Esposa", "Empleado", "Visita", "Otro"], state="readonly", style='Black.TCombobox')
        combo_relacion.set("Selecciona una opción")
        combo_relacion.pack(pady=5, padx=20, fill='x')
        entradas["relacion"] = combo_relacion
        
        def registrar_accion():
            try:
                fecha_nac_dt = datetime.strptime(f"{entradas['anio_nacimiento'].get()}-{entradas['mes_nacimiento'].get()}-{entradas['dia_nacimiento'].get()}", "%Y-%m-%d")
                rut = entradas["rut"].get().strip()
                if not self.validar_rut(rut): raise ValueError("RUT inválido.")
                nombre = entradas["nombre_completo"].get().strip()
                relacion = entradas["relacion"].get()
                if not all([nombre, relacion != "Selecciona una opción"]): raise ValueError("Campos incompletos.")
                edad = datetime.now().year - fecha_nac_dt.year - ((datetime.now().month, datetime.now().day) < (fecha_nac_dt.month, fecha_nac_dt.day))
                self.registrar_persona(nombre, fecha_nac_dt.strftime("%Y-%m-%d"), edad, rut, relacion, datetime.now().strftime("%Y-%m-%d"))
                ventana_registro.destroy()
            except ValueError as e:
                messagebox.showwarning("Datos Inválidos", str(e))
        
        ttk.Button(ventana_registro, text="Registrar", command=registrar_accion, style='TButton').pack(pady=15)
        
        # Iniciar la animación
        self.animar_desplazamiento_derecha(ventana_registro)


    def mostrar_historial_reconocimiento(self):
        ventana_historial = tk.Toplevel(self.root)
        ventana_historial.title("Historial de Reconocimiento")
        ventana_historial.geometry("700x500")
        self.centrar_ventana(ventana_historial, self.root)
        tree = ttk.Treeview(ventana_historial, columns=("Fecha", "Hora", "Nombre", "RUT", "Dispositivo"), show="headings")
        for col in ("Fecha", "Hora", "Nombre", "RUT", "Dispositivo"): tree.heading(col, text=col)
        tree.pack(expand=True, fill="both", padx=10, pady=10)
        cursor = None
        try:
            cursor = self.conexion.cursor(dictionary=True)
            cursor.execute("SELECT fecha_hora, nombre, rut, dispositivo_id FROM historial_reconocimiento ORDER BY fecha_hora DESC")
            for row in cursor.fetchall():
                tree.insert("", "end", values=(row['fecha_hora'].strftime("%Y-%m-%d"), row['fecha_hora'].strftime("%H:%M:%S"), row['nombre'], row['rut'], row.get('dispositivo_id', 'N/A')))
        except mysql.connector.Error as err:
            messagebox.showerror("Error de Historial", f"Error al cargar historial: {err}")
        finally:
            if cursor:
                cursor.close()

    def mostrar_ventana_admin_login(self):
        self.ventana_admin_login = tk.Toplevel(self.root)
        self.ventana_admin_login.title("Acceso Admin")
        self.ventana_admin_login.geometry("300x150")
        self.ventana_admin_login.transient(self.root)
        self.ventana_admin_login.grab_set()
        ttk.Label(self.ventana_admin_login, text="Contraseña:").pack(pady=10)
        self.admin_password_entry = ttk.Entry(self.ventana_admin_login, show="*")
        self.admin_password_entry.pack(pady=5, padx=20, fill='x')
        self.admin_password_entry.bind("<Return>", lambda e: self.verificar_admin_password())
        ttk.Button(self.ventana_admin_login, text="Ingresar", command=self.verificar_admin_password).pack(pady=10)
        self.centrar_ventana(self.ventana_admin_login, self.root)

    def verificar_admin_password(self):
        if self.admin_password_entry.get() == "12345":
            self.ventana_admin_login.destroy()
            self.mostrar_panel_admin()
        else:
            messagebox.showerror("Acceso Denegado", "Contraseña incorrecta.")
            self.admin_password_entry.delete(0, tk.END)

    def mostrar_panel_admin(self):
        self.ventana_admin = tk.Toplevel(self.root)
        self.ventana_admin.title("Panel de Administración")
        self.ventana_admin.geometry("900x600")
        self.ventana_admin.transient(self.root); self.ventana_admin.grab_set()
        frame_botones = ttk.Frame(self.ventana_admin, padding=10); frame_botones.pack(pady=5, fill='x')
        ttk.Button(frame_botones, text="Eliminar Persona", command=self.eliminar_persona).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Editar Persona", command=self.modificar_datos_persona).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Recargar Datos", command=self._cargar_personas_admin_treeview).pack(side=tk.LEFT, padx=5)
        cols = ("ID_Imagen", "Nombre", "RUT", "F. Nac", "Edad", "Relación", "F. Reg")
        self.tree_personas_admin = ttk.Treeview(self.ventana_admin, columns=cols, show="headings")
        for col in cols: self.tree_personas_admin.heading(col, text=col)
        self.tree_personas_admin.pack(expand=True, fill="both", padx=10, pady=10)
        self._cargar_personas_admin_treeview()
        self.ventana_admin.protocol("WM_DELETE_WINDOW", self.cerrar_panel_admin)
        self.centrar_ventana(self.ventana_admin, self.root)

    def cerrar_panel_admin(self):
        self.ventana_admin.destroy()

    def _cargar_personas_admin_treeview(self):
        for item in self.tree_personas_admin.get_children(): self.tree_personas_admin.delete(item)
        cursor = None
        try:
            cursor = self.conexion.cursor(dictionary=True)
            cursor.execute("SELECT id_imagen, nombre_completo, rut, fecha_nacimiento, edad, relacion, fecha_registro FROM reconocimiento ORDER BY nombre_completo")
            for row in cursor.fetchall():
                self.tree_personas_admin.insert("", "end", values=(row['id_imagen'], row['nombre_completo'], row['rut'], row['fecha_nacimiento'].strftime('%Y-%m-%d'), row['edad'], row['relacion'], row['fecha_registro'].strftime('%Y-%m-%d')))
        except mysql.connector.Error as err:
            messagebox.showerror("Error de Base de Datos", f"Error al cargar personas: {err}")
        finally:
            if cursor:
                cursor.close()

    def modificar_datos_persona(self):
        messagebox.showinfo("Función no implementada", "La modificación de datos aún no está completamente implementada.")

    def mostrar_ventana_sospechosos(self):
        ventana = tk.Toplevel(self.root)
        ventana.title("Sospechosos (desde MySQL)")
        ventana.geometry("850x650")
        self.centrar_ventana(ventana, self.root)

        frame_superior = ttk.Frame(ventana, padding=5)
        frame_superior.pack(fill='x')
        
        ttk.Button(frame_superior, text="Recargar Fotos", command=lambda: self._cargar_fotos_sospechosas_db(frame_contenido)).pack()

        canvas = tk.Canvas(ventana)
        scrollbar = ttk.Scrollbar(ventana, orient="vertical", command=canvas.yview)
        frame_contenido = ttk.Frame(canvas, padding=10)
        
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.create_window((0, 0), window=frame_contenido, anchor="nw")
        
        frame_contenido.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        self._cargar_fotos_sospechosas_db(frame_contenido)

    def _cargar_fotos_sospechosas_db(self, frame_contenido):
        for widget in frame_contenido.winfo_children():
            widget.destroy()
        
        cursor = None
        try:
            cursor = self.conexion.cursor(dictionary=True)
            cursor.execute("SELECT id, imagen_data, fecha_hora, dispositivo_id FROM sospechosos ORDER BY fecha_hora DESC")
            sospechosos = cursor.fetchall()

            if not sospechosos:
                ttk.Label(frame_contenido, text="No hay fotos de sospechosos en la base de datos.").pack(pady=20)
                return

            for idx, row in enumerate(sospechosos):
                item_frame = ttk.Frame(frame_contenido, padding=5, relief="solid", borderwidth=1)
                item_frame.grid(row=idx // 4, column=idx % 4, padx=10, pady=10, sticky='nsew')
                
                img = Image.open(io.BytesIO(row['imagen_data']))
                img.thumbnail((150, 150), Image.LANCZOS)
                imgtk = ImageTk.PhotoImage(img)
                
                lbl_img = tk.Label(item_frame, image=imgtk)
                lbl_img.image = imgtk
                lbl_img.pack(pady=5)
                
                fecha_hora_obj = row['fecha_hora']
                ttk.Label(item_frame, text=fecha_hora_obj.strftime("%d-%m-%Y %H:%M:%S")).pack()
                ttk.Label(item_frame, text=f"Dispositivo: {row.get('dispositivo_id', 'N/A')}", font=('Segoe UI', 8)).pack()
                
                if 'id' in row:
                    id_sospechoso_val = row['id']
                    ttk.Button(item_frame, text="Eliminar", command=lambda id_sospechoso=id_sospechoso_val, f=frame_contenido: self.eliminar_foto_sospechosa_db(id_sospechoso, f)).pack(pady=5)
                else:
                    print(f"Error de clave: La columna 'id' no se encontró en los datos del sospechoso. Columnas disponibles: {list(row.keys())}")
                    ttk.Button(item_frame, text="Eliminar (Error)", state="disabled").pack(pady=5)
        except mysql.connector.Error as err:
            messagebox.showerror("Error de Base de Datos", f"No se pudieron cargar los sospechosos: {err}")
        finally:
            if cursor:
                cursor.close()

    def eliminar_foto_sospechosa_db(self, id_sospechoso, frame_a_recargar):
        if messagebox.askyesno("Confirmar", f"¿Eliminar esta foto de la base de datos?"):
            cursor = None
            try:
                cursor = self.conexion.cursor()
                cursor.execute("DELETE FROM sospechosos WHERE id = %s", (id_sospechoso,))
                self.conexion.commit()
                self._cargar_fotos_sospechosas_db(frame_a_recargar)
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"No se pudo eliminar el registro de la base de datos: {err}")
                self.conexion.rollback()
            finally:
                if cursor:
                    cursor.close()

    def sonar_confirmacion(self):
        try:
            pygame.mixer.music.load(ALERTA_SONIDO_RECONOCIDO)
            pygame.mixer.music.play()
        except pygame.error as e: print(f"Error reproduciendo sonido de confirmación: {e}")

    def sonar_error(self):
        try:
            pygame.mixer.music.load(ALERTA_SONIDO_NO_RECONOCIDO)
            pygame.mixer.music.play()
        except pygame.error as e: print(f"Error reproduciendo sonido de error: {e}")

    def notificar_persona_encargada(self, image_info):
        current_time = time.time()
        if (current_time - self.last_notification_time) > self.notification_cooldown:
            mensaje = f"🚨 ALERTA: Rostro desconocido detectado. Registro guardado en: {image_info}"
            print(mensaje)
            messagebox.showwarning("Alerta de Seguridad", mensaje)
            self.last_notification_time = current_time
        else:
            print(f"DEBUG: Notificación de desconocido en cooldown.")

    def log_app_startup(self):
        try:
            with open(APP_LOG_FILE, "a") as f: f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Aplicación iniciada en dispositivo {self.device_hostname}.\n")
            
            cursor = self.conexion.cursor()
            cursor.execute("SELECT COUNT(*) FROM sospechosos")
            count = cursor.fetchone()[0]
            cursor.close()
            if count > 0:
                messagebox.showwarning("AVISO DE SEGURIDAD", f"¡Se han detectado {count} sospechosos no revisados en la base de datos!")
        except Exception as e: print(f"❌ Error en log de inicio: {e}")

    def centrar_ventana(self, ventana_hija, ventana_padre):
        ventana_hija.update_idletasks()
        x = ventana_padre.winfo_x() + (ventana_padre.winfo_width() // 2) - (ventana_hija.winfo_width() // 2)
        y = ventana_padre.winfo_y() + (ventana_padre.winfo_height() // 2) - (ventana_hija.winfo_height() // 2)
        ventana_hija.geometry(f"+{x}+{y}")

    def animar_desplazamiento_derecha(self, ventana, paso=15, delay=10):
        ventana.update_idletasks()
        
        # Posición final
        x_final = self.root.winfo_x() + self.root.winfo_width()
        y_pos = self.root.winfo_y()

        # Posición inicial (detrás del borde izquierdo de la ventana principal)
        x_actual = ventana.winfo_x()

        if x_actual < x_final:
            x_nuevo = x_actual + paso
            if x_nuevo > x_final:
                x_nuevo = x_final
            ventana.geometry(f"+{x_nuevo}+{y_pos}")
            self.root.after(delay, lambda: self.animar_desplazamiento_derecha(ventana, paso, delay))
        else:
            # Al terminar, la levantamos y la hacemos modal
            ventana.lift(self.root)
            ventana.grab_set()

    def formatear_rut(self, entry_widget):
        current_text = entry_widget.get().replace(".", "").replace("-", "").strip()
        if not all(c.isdigit() or (i == len(current_text) - 1 and c.upper() == 'K') for i, c in enumerate(current_text)): return
        body, dv = current_text[:-1], current_text[-1].upper()
        formatted_body = "".join(reversed([char + ("." if i > 0 and i % 3 == 0 else "") for i, char in enumerate(reversed(body))]))
        formatted_rut = f"{formatted_body}-{dv}" if body else current_text
        if entry_widget.get() != formatted_rut:
            entry_widget.delete(0, tk.END); entry_widget.insert(0, formatted_rut); entry_widget.icursor(tk.END)

    def validar_rut(self, rut_completo):
        rut_completo = rut_completo.upper().replace(".", "").replace("-", "").strip()
        if not (rut_completo[:-1].isdigit() and (rut_completo[-1].isdigit() or rut_completo[-1] == 'K')): return False
        cuerpo, dv = rut_completo[:-1], rut_completo[-1]
        try:
            dv_calculado = str(11 - sum(int(digit) * ((i % 6) + 2) for i, digit in enumerate(reversed(cuerpo))) % 11)
            if dv_calculado == '11': dv_calculado = '0'
            if dv_calculado == '10': dv_calculado = 'K'
            return dv == dv_calculado
        except ValueError:
            return False

if __name__ == "__main__":
    root = tk.Tk()
    app = DeteccionMovimientoApp(root)
    root.mainloop()
