import customtkinter as ctk
import configparser
import logging
import os
import sys
import asyncio
import queue
import threading
import json
import tempfile
import base64
import io
import time
from tkinter import messagebox
from PIL import Image, ImageTk
import cv2
import face_recognition
import numpy as np
import mysql.connector

# Importaciones para la funcionalidad de voz y audio
from vosk import Model, KaldiRecognizer
import sounddevice as sd
import soundfile as sf
import edge_tts
import google.generativeai as genai

# --- CONFIGURACIÓN INICIAL ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')

# --- ESTADOS DEL ASISTENTE ---
class AsistenteEstado:
    ESPERANDO = "Esperando..."
    ESCUCHANDO = "Escuchando..."
    PENSANDO = "Pensando..."
    HABLANDO = "Hablando..."
    DETECTANDO = "Detección Activa"

# --- CLASE DE ESTADO COMPARTIDO ---
class EstadoCompartido:
    def __init__(self):
        self.ultima_persona_vista = "Nadie"
        self.personas_en_frame = []
        self.desconocidos_count = 0
        self.lock = threading.Lock()

    def actualizar_deteccion(self, personas, desconocidos):
        with self.lock:
            self.personas_en_frame = personas
            self.desconocidos_count = desconocidos
            if personas:
                self.ultima_persona_vista = personas[0]['Nombre Completo']
            elif desconocidos > 0:
                self.ultima_persona_vista = f"{desconocidos} persona(s) desconocida(s)"
            else:
                self.ultima_persona_vista = "Nadie"

# --- CLASE PRINCIPAL DE LA APLICACIÓN ---
class AppIntegrada(ctk.CTk):
    def __init__(self, estado_compartido):
        super().__init__()
        self.estado_compartido = estado_compartido
        self.title("Asistente de Vigilancia Inteligente")
        self.geometry("1200x800")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # --- CONFIGURACIÓN DE LA ESTRUCTURA (GRID) ---
        self.grid_columnconfigure(0, weight=2) # Columna para video y log
        self.grid_columnconfigure(1, weight=1) # Columna para datos y controles
        self.grid_rowconfigure(0, weight=1)    # Fila principal

        # --- INICIALIZACIÓN DE COMPONENTES ---
        self.modelo_gemini, self.palabra_clave = self.cargar_configuracion()
        self.chat_session = None
        self.loop = asyncio.new_event_loop()
        self.interrupcion_habla = asyncio.Event()
        self.hilo_deteccion = None
        self.deteccion_activa = threading.Event()

        self.crear_widgets()
        
        if self.modelo_gemini:
            if not self.verificar_microfono(): return
            self.iniciar_motor_vosk()

        self.protocol("WM_DELETE_WINDOW", self.al_cerrar)

    def crear_widgets(self):
        """Crea todos los elementos de la interfaz gráfica."""
        # --- FRAME IZQUIERDO (VIDEO Y LOG) ---
        left_frame = ctk.CTkFrame(self)
        left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        left_frame.grid_rowconfigure(0, weight=3) # Más espacio para el video
        left_frame.grid_rowconfigure(1, weight=2) # Espacio para el log
        left_frame.grid_columnconfigure(0, weight=1)

        self.label_video = ctk.CTkLabel(left_frame, text="La detección está detenida.", font=ctk.CTkFont(size=20))
        self.label_video.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.text_area = ctk.CTkTextbox(left_frame, font=ctk.CTkFont(size=14), wrap="word")
        self.text_area.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # --- FRAME DERECHO (CONTROLES Y DATOS) ---
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        # Controles del asistente
        asistente_controls_frame = ctk.CTkFrame(right_frame)
        asistente_controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.start_button = ctk.CTkButton(asistente_controls_frame, text="Iniciar Asistente", command=self.iniciar_asistente_thread)
        self.start_button.pack(pady=5, fill="x")
        self.status_label = ctk.CTkLabel(asistente_controls_frame, text="Estado: Esperando", font=ctk.CTkFont(size=16, weight="bold"))
        self.status_label.pack(pady=5)
        
        # Controles de detección
        detection_controls_frame = ctk.CTkFrame(right_frame)
        detection_controls_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.btn_iniciar_deteccion = ctk.CTkButton(detection_controls_frame, text="Iniciar Detección", command=self.iniciar_deteccion)
        self.btn_iniciar_deteccion.pack(pady=5, fill="x")
        self.btn_detener_deteccion = ctk.CTkButton(detection_controls_frame, text="Detener Detección", command=self.detener_deteccion, state="disabled")
        self.btn_detener_deteccion.pack(pady=5, fill="x")

        # Panel de datos reconocidos
        self.panel_datos = ctk.CTkFrame(right_frame)
        self.panel_datos.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.labels_datos = {}
        for campo in ['Nombre Completo', 'Edad', 'RUT', 'Fecha de Nacimiento', 'Relación', 'Fecha de Registro']:
            lbl = ctk.CTkLabel(self.panel_datos, text=f"{campo}: ---")
            lbl.pack(anchor='w', pady=2)
            self.labels_datos[campo] = lbl
        
        # Chat de texto
        chat_frame = ctk.CTkFrame(right_frame)
        chat_frame.grid(row=3, column=0, padx=10, pady=10, sticky="sew")
        chat_frame.grid_columnconfigure(0, weight=1)
        self.chat_entry = ctk.CTkEntry(chat_frame, placeholder_text="Escribe tu petición aquí...")
        self.chat_entry.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        self.chat_entry.bind("<Return>", self.enviar_texto_handler)
        self.send_button = ctk.CTkButton(chat_frame, text="Enviar", command=self.enviar_texto_handler, width=80)
        self.send_button.grid(row=0, column=1)

    # --- MÉTODOS DE CONFIGURACIÓN Y CONTROL ---
    def cargar_configuracion(self):
        try:
            config = configparser.ConfigParser()
            config.read('config.ini')
            api_key = config['GEMINI']['API_KEY']
            palabra_clave = config['ASISTENTE']['PALABRA_CLAVE']
            if 'TU_CLAVE_API' in api_key:
                self.mostrar_error_fatal("La clave API no ha sido configurada.")
                return None, None
            genai.configure(api_key=api_key)
            modelo = genai.GenerativeModel('gemini-1.5-flash-latest')
            return modelo, palabra_clave
        except Exception as e:
            self.mostrar_error_fatal(f"Error en config.ini: {e}")
            return None, None

    def verificar_microfono(self):
        try:
            if not any(d['max_input_channels'] > 0 for d in sd.query_devices()):
                self.mostrar_error_fatal("No se encontró ningún micrófono.")
                return False
            return True
        except Exception as e:
            self.mostrar_error_fatal(f"No se pudo acceder al micrófono: {e}")
            return False

    def mostrar_error_fatal(self, mensaje):
        logging.critical(mensaje)
        messagebox.showerror("Error Crítico", mensaje)
        self.after(100, self.destroy)

    def actualizar_estado(self, estado):
        self.status_label.configure(text=f"Estado: {estado}")
        logging.info(f"Nuevo estado: {estado}")

    def agregar_texto_log(self, emisor, texto):
        self.text_area.insert("end", f"{emisor}:\n{texto}\n\n")
        self.text_area.see("end")
    
    def al_cerrar(self):
        logging.info("Cerrando aplicación...")
        self.deteccion_activa.clear()
        if self.hilo_deteccion: self.hilo_deteccion.join()
        if self.loop.is_running(): self.loop.call_soon_threadsafe(self.loop.stop)
        self.destroy()

    # --- MÉTODOS DE DETECCIÓN FACIAL (EJECUTADOS EN UN HILO) ---
    def iniciar_deteccion(self):
        self.deteccion_activa.set()
        self.hilo_deteccion = threading.Thread(target=self.bucle_deteccion_facial, daemon=True)
        self.hilo_deteccion.start()
        self.btn_iniciar_deteccion.configure(state="disabled")
        self.btn_detener_deteccion.configure(state="normal")

    def detener_deteccion(self):
        self.deteccion_activa.clear()
        self.btn_iniciar_deteccion.configure(state="normal")
        self.btn_detener_deteccion.configure(state="disabled")
        self.label_video.configure(image=None, text="La detección está detenida.")
        logging.info("Detección detenida por el usuario.")

    def bucle_deteccion_facial(self):
        # Esta función se ejecuta en un hilo separado para no bloquear la GUI
        try:
            db_connection = mysql.connector.connect(host="localhost", user="root", password="", database="reconocimiento_facial")
            cursor = db_connection.cursor(dictionary=True)
            logging.info("Conexión a MySQL establecida para el hilo de detección.")
        except Exception as e:
            logging.error(f"No se pudo conectar a la base de datos MySQL: {e}")
            self.after(0, lambda: self.btn_iniciar_deteccion.configure(state="normal"))
            return

        encodings_registrados, datos_registrados = self.cargar_datos_mysql(cursor)
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logging.error("No se pudo abrir la cámara.")
            return

        while self.deteccion_activa.is_set():
            ret, frame = cap.read()
            if not ret: break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            personas_en_frame = []
            desconocidos_count = 0

            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                coincidencias = face_recognition.compare_faces(encodings_registrados, face_encoding)
                nombre = "Desconocido"
                datos_persona = None

                if True in coincidencias:
                    first_match_index = coincidencias.index(True)
                    datos_persona = datos_registrados[first_match_index]
                    nombre = datos_persona['Nombre Completo']
                    personas_en_frame.append(datos_persona)
                else:
                    desconocidos_count += 1

                # Dibujar rectángulos y nombres en el frame
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
                cv2.putText(frame, nombre, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)

            # Actualizar estado compartido
            self.estado_compartido.actualizar_deteccion(personas_en_frame, desconocidos_count)
            self.after(0, self.actualizar_panel_datos, datos_persona if personas_en_frame else None)

            # Mostrar video en la GUI
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            imgtk = ctk.CTkImage(light_image=img, dark_image=img, size=(640, 480))
            self.label_video.configure(image=imgtk, text="")
            
            time.sleep(0.05) # Pequeña pausa para no sobrecargar la CPU

        cap.release()
        cursor.close()
        db_connection.close()
        logging.info("Cámara y conexión a DB cerradas.")

    def cargar_datos_mysql(self, cursor):
        cursor.execute("SELECT * FROM personas")
        personas = cursor.fetchall()
        encodings = [np.frombuffer(p['face_encoding'], dtype=np.float64) for p in personas]
        return encodings, personas

    def actualizar_panel_datos(self, datos):
        if datos:
            for campo, valor in datos.items():
                label_text = campo.replace("_", " ").title()
                if label_text in self.labels_datos:
                    self.labels_datos[label_text].configure(text=f"{label_text}: {valor}")
        else:
            for campo, label in self.labels_datos.items():
                label.configure(text=f"{campo}: ---")

    # --- MÉTODOS DEL ASISTENTE DE VOZ (ASÍNCRONOS) ---
    def iniciar_asistente_thread(self):
        self.start_button.configure(state="disabled", text="Asistente Activo")
        threading.Thread(target=self.iniciar_loop_asincrono, name="AsyncLoopThread", daemon=True).start()
    
    def iniciar_loop_asincrono(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.bucle_principal_asistente())
        except Exception as e:
            logging.error(f"Error en el bucle principal del asistente: {e}")

    async def bucle_principal_asistente(self):
        if self.modelo_gemini:
            self.chat_session = self.modelo_gemini.start_chat(history=[])
            await self.hablar("Hola, soy tu asistente de vigilancia. Puedes preguntarme sobre lo que veo.")

        while True:
            texto_usuario = await self.escuchar()
            if texto_usuario:
                if "adiós" in texto_usuario.lower() or "salir" in texto_usuario.lower():
                    await self.hablar("Ha sido un placer. ¡Hasta pronto!")
                    break
                await self.procesar_peticion_ia(texto_usuario)
        self.al_cerrar()

    def iniciar_motor_vosk(self):
        try:
            modelo_path = "vosk-model-small-es-0.42"
            if not os.path.exists(modelo_path):
                raise FileNotFoundError("La carpeta del modelo Vosk no se encontró.")
            self.modelo_vosk = Model(modelo_path)
            logging.info("Modelo Vosk cargado.")
        except Exception as e:
            self.mostrar_error_fatal(f"No se pudo cargar el modelo Vosk: {e}")

    async def escuchar(self):
        self.actualizar_estado(AsistenteEstado.ESCUCHANDO)
        q = queue.Queue()
        def callback(indata, frames, time, status):
            if status: logging.warning(status)
            q.put(bytes(indata))
        
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16', channels=1, callback=callback):
            reconocedor = KaldiRecognizer(self.modelo_vosk, 16000)
            while True:
                data = q.get()
                if reconocedor.AcceptWaveform(data):
                    resultado = json.loads(reconocedor.Result())
                    if resultado['text']:
                        self.agregar_texto_log("Tú", resultado['text'])
                        return resultado['text']
                await asyncio.sleep(0.01)

    def enviar_texto_handler(self, event=None):
        texto = self.chat_entry.get()
        if texto:
            self.agregar_texto_log("Tú (texto)", texto)
            self.chat_entry.delete(0, "end")
            asyncio.run_coroutine_threadsafe(self.procesar_peticion_ia(texto), self.loop)

    async def procesar_peticion_ia(self, texto_usuario):
        # Comandos especiales para acceder a los datos de la cámara
        if any(p in texto_usuario.lower() for p in ["quién está ahí", "a quién ves", "qué ves"]):
            with self.estado_compartido.lock:
                respuesta = f"Actualmente estoy viendo a {self.estado_compartido.ultima_persona_vista}."
            await self.hablar(respuesta)
        elif any(p in texto_usuario.lower() for p in ["hay desconocidos", "algún extraño"]):
            with self.estado_compartido.lock:
                if self.estado_compartido.desconocidos_count > 0:
                    respuesta = f"Sí, he detectado a {self.estado_compartido.desconocidos_count} persona(s) desconocida(s)."
                else:
                    respuesta = "No, no veo a ninguna persona desconocida en este momento."
            await self.hablar(respuesta)
        else:
            # Si no es un comando especial, se envía a Gemini
            await self.pensar_y_responder_gemini(texto_usuario)

    async def pensar_y_responder_gemini(self, texto_usuario):
        self.actualizar_estado(AsistenteEstado.PENSANDO)
        try:
            respuesta_stream = await self.chat_session.send_message_async(texto_usuario, stream=True)
            await self.hablar_en_stream(respuesta_stream)
        except Exception as e:
            logging.error(f"Error al obtener respuesta de Gemini: {e}")
            await self.hablar("Lo siento, he tenido un problema para conectarme con la IA.")

    async def hablar(self, texto_completo):
        self.actualizar_estado(AsistenteEstado.HABLANDO)
        self.agregar_texto_log("IA", texto_completo)
        await self.hablar_fragmento(texto_completo)
        self.actualizar_estado(AsistenteEstado.ESPERANDO)

    async def hablar_en_stream(self, stream_iterator):
        self.actualizar_estado(AsistenteEstado.HABLANDO)
        texto_completo = ""
        oracion_actual = ""
        try:
            async for chunk in stream_iterator:
                texto_chunk = chunk.text
                texto_completo += texto_chunk
                oracion_actual += texto_chunk
                if '.' in oracion_actual or '?' in oracion_actual or '!' in oracion_actual:
                    if oracion_actual.strip():
                        await self.hablar_fragmento(oracion_actual.strip())
                    oracion_actual = ""
            if oracion_actual.strip():
                await self.hablar_fragmento(oracion_actual.strip())
            if texto_completo: self.agregar_texto_log("IA", texto_completo)
        except Exception as e:
            logging.error(f"Error durante el stream de TTS: {e}")
        finally:
            self.actualizar_estado(AsistenteEstado.ESPERANDO)

    async def hablar_fragmento(self, texto):
        try:
            communicate = edge_tts.Communicate(texto, "es-ES-ElviraNeural", rate="+25%")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                temp_filename = f.name
            await communicate.save(temp_filename)
            data, samplerate = sf.read(temp_filename)
            sd.play(data, samplerate)
            sd.wait()
            os.remove(temp_filename)
        except Exception as e:
            logging.error(f"Error al hablar fragmento: {e}")

# --- PUNTO DE ENTRADA ---
if __name__ == "__main__":
    estado_compartido = EstadoCompartido()
    app = AppIntegrada(estado_compartido)
    app.mainloop()
