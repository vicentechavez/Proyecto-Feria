# main.py
# Archivo principal para iniciar la aplicación de reconocimiento facial.

import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import threading
import time
from datetime import datetime
import os
import socket
import pygame
from PIL import Image, ImageTk
import numpy as np

# Importar nuestros módulos personalizados
import config
from database_handler import DatabaseHandler
import face_processor
import gui_manager

class MainApplication:
    def __init__(self, root):
        self.root = root
        self.device_hostname = socket.gethostname()
        self.root.title("Ojo Digital - Sistema de Reconocimiento")
        self.root.geometry("1200x750") # Ancho aumentado para el nuevo layout
        self.root.minsize(1000, 700)
        self.root.configure(bg=config.COLORES["fondo_principal"])

        pygame.mixer.init()

        try:
            self.db_handler = DatabaseHandler(config.DB_CONFIG)
        except Exception as e:
            messagebox.showerror("Error Crítico de Base de Datos", f"No se pudo conectar a MySQL.\nError: {e}")
            self.root.destroy()
            return

        # Atributos de estado...
        self.running = True
        self.detection_active = False
        self.procesando_frame = False
        self.datos_registrados = {}
        self.encodings_registrados = {}
        self.last_detection_time = {}
        self.cooldown_period = 60
        self.cap = None
        self.recognition_timer = None
        self.last_unknown_capture_time = 0
        self.unknown_capture_cooldown = 30

        self.configurar_estilos()
        self.crear_widgets_principales()
        self.reload_data_from_db()
        self.log_app_startup()

        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_aplicacion)

    def configurar_estilos(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Estilos generales
        style.configure('TFrame', background=config.COLORES["fondo_principal"])
        style.configure('Left.TFrame', background=config.COLORES["fondo_paneles"])
        style.configure('TLabel', font=config.FONT_PRINCIPAL, background=config.COLORES["fondo_paneles"], foreground=config.COLORES["texto_label"])
        style.configure('Titulo.TLabel', font=config.FONT_TITULO, foreground=config.COLORES["texto_titulo"], background=config.COLORES["fondo_paneles"])
        style.configure('Estado.TLabel', font=config.FONT_ESTADO, background=config.COLORES["fondo_barra_estado"], foreground=config.COLORES["texto_barra_estado"])
        style.configure('TLabelframe', background=config.COLORES["fondo_paneles"], bordercolor=config.COLORES["borde_widget"])
        style.configure('TLabelframe.Label', font=config.FONT_TITULO, foreground=config.COLORES["texto_titulo"], background=config.COLORES["fondo_paneles"])

        # Estilo para botones azules
        style.configure('Blue.TButton', font=config.FONT_PRINCIPAL, padding=10, background=config.COLORES["boton_normal_bg"], foreground=config.COLORES["boton_normal_fg"], borderwidth=0, relief='flat')
        style.map('Blue.TButton', background=[('active', config.COLORES["boton_activo_bg"])])

        # Estilo para botones verdes
        style.configure('Green.TButton', font=config.FONT_PRINCIPAL, padding=10, background=config.COLORES["boton_verde_bg"], foreground=config.COLORES["boton_verde_fg"], borderwidth=0, relief='flat')
        style.map('Green.TButton', background=[('active', config.COLORES["boton_verde_activo_bg"])])
        
        # Estilos para ventanas secundarias
        s_cfg = config.STYLE_CONFIG_VENTANA_SECUNDARIA
        style.configure(s_cfg['label_style'], background=s_cfg['bg'], foreground='white', font=config.FONT_PRINCIPAL)
        style.configure(s_cfg['frame_style'], background=s_cfg['bg'])
        style.configure(s_cfg['entry_style'], fieldbackground=s_cfg['bg'], foreground='white', insertcolor='white', bordercolor=config.COLORES["borde_widget"])
        style.map(s_cfg['combobox_style'],
                  fieldbackground=[('readonly', s_cfg['bg'])],
                  selectbackground=[('readonly', '#3c3c3c')],
                  selectforeground=[('readonly', 'white')],
                  foreground=[('readonly', 'white')])
        style.configure(s_cfg['combobox_style'], bordercolor=config.COLORES["borde_widget"])

    def crear_widgets_principales(self):
        # --- Layout Principal (Izquierda y Derecha) ---
        self.root.grid_columnconfigure(0, weight=1, minsize=250) # Panel Izquierdo
        self.root.grid_columnconfigure(1, weight=4)              # Panel Derecho
        self.root.grid_rowconfigure(0, weight=1)

        # --- Panel Izquierdo (Controles) ---
        left_panel = ttk.Frame(self.root, style='Left.TFrame', padding=(10, 20))
        left_panel.grid(row=0, column=0, sticky='nsew')
        left_panel.grid_rowconfigure(2, weight=1) # Espacio para empujar botones hacia arriba

        # Título
        app_title = tk.Label(left_panel, text="Ojo Digital", font=config.FONT_TITULO_APP, bg=config.COLORES["fondo_paneles"], fg=config.COLORES["texto_titulo"])
        app_title.pack(pady=(0, 20))

        # Panel de Estado de IA
        ia_status_frame = ttk.Frame(left_panel, style='Left.TFrame', padding=15)
        ia_status_frame.pack(fill='x', pady=10)
        ia_status_frame.configure(relief='solid', borderwidth=1)
        
        self.status_ia_title = tk.Label(ia_status_frame, text="ESTADO DE IA", font=config.FONT_TITULO, bg=config.COLORES["fondo_paneles"], fg=config.COLORES["texto_label"])
        self.status_ia_title.pack()
        self.status_ia_line1 = tk.Label(ia_status_frame, text="Inactivo", font=('Segoe UI', 14), bg=config.COLORES["fondo_paneles"], fg="#ff5555")
        self.status_ia_line1.pack()
        self.status_ia_line2 = tk.Label(ia_status_frame, text="", font=config.FONT_PRINCIPAL, bg=config.COLORES["fondo_paneles"], fg=config.COLORES["texto_label"])
        self.status_ia_line2.pack()

        # Panel de Herramientas
        tools_frame = ttk.Frame(left_panel, style='Left.TFrame', padding=(0, 20))
        tools_frame.pack(fill='x')

        ttk.Label(tools_frame, text="HERRAMIENTAS", font=config.FONT_TITULO, background=config.COLORES["fondo_paneles"]).pack(fill='x', pady=(10,5))
        
        self.btn_iniciar = ttk.Button(tools_frame, text="Iniciar Detección", command=self.iniciar_deteccion, style='Green.TButton')
        self.btn_iniciar.pack(fill='x', pady=4)
        self.btn_detener = ttk.Button(tools_frame, text="Detener", command=self.detener_deteccion, state=tk.DISABLED, style='Blue.TButton')
        self.btn_detener.pack(fill='x', pady=4)
        ttk.Button(tools_frame, text="Registrar Persona", command=self.show_registration_view, style='Blue.TButton').pack(fill='x', pady=4)
        ttk.Button(tools_frame, text="Ver Historial", command=self.show_history_view, style='Blue.TButton').pack(fill='x', pady=4)
        ttk.Button(tools_frame, text="Modo Admin", command=self.show_admin_login_view, style='Blue.TButton').pack(fill='x', pady=4)
        ttk.Button(tools_frame, text="Ver Sospechosos", command=self.show_suspects_view, style='Blue.TButton').pack(fill='x', pady=4)

        # --- Panel Derecho (Video y Datos) ---
        right_panel = ttk.Frame(self.root, style='TFrame', padding=15)
        right_panel.grid(row=0, column=1, sticky='nsew')
        right_panel.grid_columnconfigure(0, weight=3)
        right_panel.grid_columnconfigure(1, weight=1)
        right_panel.grid_rowconfigure(0, weight=1)

        self.label_video = tk.Label(right_panel, bg=config.COLORES["fondo_label_video"])
        self.label_video.grid(row=0, column=0, sticky='nsew', padx=(0, 10))

        self.panel_datos = ttk.LabelFrame(right_panel, text="Datos Reconocidos", padding=15)
        self.panel_datos.grid(row=0, column=1, sticky='nsew')
        
        self.labels_datos = {}
        campos = ['Nombre Completo', 'Edad', 'RUT', 'Fecha de Nacimiento', 'Relación', 'Fecha de Registro']
        for campo in campos:
            lbl = ttk.Label(self.panel_datos, text=f"{campo}: ---", wraplength=250)
            lbl.pack(anchor='w', pady=6)
            self.labels_datos[campo] = lbl
        self.label_cooldown_status = ttk.Label(self.panel_datos, text="", font=(config.FONT_PRINCIPAL[0], 9, 'italic'), foreground=config.COLORES["texto_cooldown"])
        self.label_cooldown_status.pack(anchor='w', pady=8)

        self.status_label = ttk.Label(self.root, text="Estado: Listo", anchor='w', padding=5, style='Estado.TLabel')
        self.status_label.grid(row=1, column=0, columnspan=2, sticky='ew')

    def reload_data_from_db(self):
        self.status_label.config(text="Estado: Sincronizando datos...")
        self.datos_registrados, self.encodings_registrados = self.db_handler.get_all_registered_data()
        self.db_handler.update_system_status()
        self.status_label.config(text=f"Estado: Listo. {len(self.encodings_registrados)} personas registradas.")
        print(f"✅ Datos recargados. {len(self.encodings_registrados)} rostros en memoria.")

    def iniciar_deteccion(self):
        if self.detection_active: return
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened(): raise IOError("No se puede abrir la cámara.")
            self.detection_active = True
            self.btn_iniciar.config(state=tk.DISABLED); self.btn_detener.config(state=tk.NORMAL)
            self.status_label.config(text="Estado: Detección activa.")
            
            # Actualizar panel de estado de IA
            self.status_ia_line1.config(text="Cámara Activa", fg="#55ff55")
            self.status_ia_line2.config(text="Modo: Reconocimiento")

            self.actualizar_video_loop()
            self.iniciar_reconocimiento_periodico()
        except IOError as e: messagebox.showerror("Error de Cámara", f"No se pudo acceder a la cámara: {e}")

    def detener_deteccion(self):
        if not self.detection_active: return
        self.detection_active = False
        if self.recognition_timer: self.recognition_timer.cancel()
        if self.cap: self.cap.release(); self.cap = None
        self.label_video.config(image=''); self.limpiar_datos_panel()
        self.btn_iniciar.config(state=tk.NORMAL); self.btn_detener.config(state=tk.DISABLED)
        self.status_label.config(text="Estado: Detenido.")

        # Restaurar panel de estado de IA
        self.status_ia_line1.config(text="Inactivo", fg="#ff5555")
        self.status_ia_line2.config(text="")

    def actualizar_video_loop(self):
        if not self.detection_active or not self.cap: return
        ret, frame = self.cap.read()
        if ret:
            frame_flipped = cv2.flip(frame, 1)
            self.mostrar_frame_en_ui(frame_flipped)
        self.root.after(30, self.actualizar_video_loop)

    def iniciar_reconocimiento_periodico(self):
        if not self.detection_active: return
        if not self.procesando_frame:
            threading.Thread(target=self.procesar_frame_para_reconocimiento, daemon=True).start()
        self.recognition_timer = threading.Timer(5.0, self.iniciar_reconocimiento_periodico)
        self.recognition_timer.start()

    def procesar_frame_para_reconocimiento(self):
        if not self.cap or not self.cap.isOpened(): return
        self.procesando_frame = True
        ret, frame = self.cap.read()
        if ret:
            frame_flipped = cv2.flip(frame, 1)
            results = face_processor.find_and_compare_faces(frame_flipped, self.encodings_registrados)
            
            if not results:
                self.root.after(0, self.limpiar_datos_panel)
            else:
                reconocido = next((r for r in results if r['name'] != "Desconocido"), None)
                if reconocido:
                    self.manejar_persona_reconocida(reconocido['name'])
                else:
                    self.manejar_persona_desconocida(frame_flipped)
        self.procesando_frame = False

    def manejar_persona_reconocida(self, nombre):
        current_time = time.time()
        if nombre not in self.last_detection_time or (current_time - self.last_detection_time.get(nombre, 0)) > self.cooldown_period:
            self.last_detection_time[nombre] = current_time
            rut = self.datos_registrados.get(nombre, {}).get('rut', 'N/A')
            self.db_handler.log_recognition(nombre, rut, self.device_hostname)
            self.play_sound(config.ALERTA_SONIDO_RECONOCIDO)
        
        self.root.after(0, self.mostrar_datos_panel, nombre)

    def manejar_persona_desconocida(self, frame):
        current_time = time.time()
        if (current_time - self.last_unknown_capture_time) > self.unknown_capture_cooldown:
            self.last_unknown_capture_time = current_time
            self.play_sound(config.ALERTA_SONIDO_NO_RECONOCIDO)
            
            _, buffer_img = cv2.imencode('.jpg', frame)
            self.db_handler.log_suspect(buffer_img.tobytes(), self.device_hostname)
            print("📸 Foto de sospechoso guardada en la base de datos.")
        
        self.root.after(0, self.limpiar_datos_panel)

    def mostrar_frame_en_ui(self, frame):
        try:
            h, w, _ = frame.shape
            label_w, label_h = self.label_video.winfo_width(), self.label_video.winfo_height()
            if label_h <= 1 or label_w <= 1: return
            
            scale = min(label_w / w, label_h / h)
            resized = cv2.resize(frame, (int(w * scale), int(h * scale)))
            img = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)))
            self.label_video.imgtk = img
            self.label_video.configure(image=img)
        except Exception as e:
            print(f"Error al mostrar frame: {e}")

    def mostrar_datos_panel(self, nombre):
        datos = self.datos_registrados.get(nombre)
        if datos:
            self.labels_datos["Nombre Completo"].config(text=f"Nombre: {nombre}")
            self.labels_datos["Edad"].config(text=f"Edad: {datos['edad']}")
            self.labels_datos["RUT"].config(text=f"RUT: {datos['rut']}")
            self.labels_datos["Fecha de Nacimiento"].config(text=f"F. Nac: {datos['fecha_nacimiento']}")
            self.labels_datos["Relación"].config(text=f"Relación: {datos['relacion']}")
            self.labels_datos["Fecha de Registro"].config(text=f"Registro: {datos['fecha_registro']}")
            en_cooldown = (time.time() - self.last_detection_time.get(nombre, 0)) < self.cooldown_period
            self.label_cooldown_status.config(text="Enfriamiento Activo" if en_cooldown else "")

    def limpiar_datos_panel(self):
        for campo, label in self.labels_datos.items():
            label.config(text=f"{campo.split(' ')[0]}: ---")
        self.label_cooldown_status.config(text="")

    def show_registration_view(self):
        is_cam_temp = not self.detection_active
        if is_cam_temp:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened(): messagebox.showerror("Error", "No se pudo abrir la cámara."); return
            time.sleep(1)
        
        gui_manager.show_registration_window(self.root, self.db_handler, self._get_face_for_registration, self.reload_data_from_db, config.STYLE_CONFIG_VENTANA_SECUNDARIA)
        
        if is_cam_temp: self.cap.release(); self.cap = None

    def _get_face_for_registration(self, get_frame_only=False):
        if not self.cap or not self.cap.isOpened():
            return (False, None) if get_frame_only else (None, None)
        
        ret, frame = self.cap.read()
        frame_flipped = cv2.flip(frame, 1)

        if get_frame_only:
            return ret, frame_flipped
        else:
            return face_processor.extract_face_encoding(frame_flipped) if ret else (None, None)

    def show_history_view(self):
        gui_manager.show_history_window(self.root, self.db_handler)

    def show_suspects_view(self):
        gui_manager.show_suspects_window(self.root, self.db_handler)

    def show_admin_login_view(self):
        gui_manager.show_admin_login_window(self.root, self.show_admin_panel_view)

    def show_admin_panel_view(self):
        gui_manager.show_admin_panel_window(self.root, self.db_handler, self.reload_data_from_db, config.STYLE_CONFIG_VENTANA_SECUNDARIA)

    def play_sound(self, sound_file):
        try:
            pygame.mixer.music.load(sound_file)
            pygame.mixer.music.play()
        except pygame.error as e:
            print(f"Error al reproducir sonido {sound_file}: {e}")

    def log_app_startup(self):
        count = self.db_handler.get_suspect_count()
        if count > 0:
            messagebox.showwarning("Aviso de Seguridad", f"¡Se han detectado {count} sospechosos no revisados!")

    def cerrar_aplicacion(self):
        if messagebox.askokcancel("Salir", "¿Estás seguro de que quieres salir?"):
            self.running = False
            self.detener_deteccion()
            self.db_handler.close()
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApplication(root)
    root.mainloop()
