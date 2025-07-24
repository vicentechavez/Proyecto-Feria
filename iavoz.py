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
import sqlite3
from datetime import datetime

import speech_recognition as sr
import pyttsx3
import random
from googlesearch import search
import re
pygame.mixer.init()
ALERTA_SONIDO_RECONOCIDO = "confirmacion.mp3"  # Make sure this file exists in the same directory
ALERTA_SONIDO_NO_RECONOCIDO = "error.mp3"       # Make sure this file exists in the same directory

class DeteccionMovimientoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ojo Digital - Asistente y Reconocimiento Facial")
        self.root.geometry("1200x800") # Increased size to accommodate chat
        self.root.resizable(False, False)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#e0e0e0')
        style.configure('TButton', font=('Helvetica Neue', 10), padding=8, background='#4CAF50', foreground='white')
        style.map('TButton', background=[('active', '#45a049')])
        style.configure('TLabel', font=('Helvetica Neue', 12), background="#e0e0e0")
        style.configure('Chat.TLabel', font=('Helvetica Neue', 12), background="#ffffff", foreground="#333333")

        self.frame_principal = ttk.Frame(self.root, padding=20, style='TFrame')
        self.frame_principal.pack(expand=True, fill='both')
        self.frame_principal.grid_columnconfigure(0, weight=1) # Video
        self.frame_principal.grid_columnconfigure(1, weight=0) # Data Panel
        self.frame_principal.grid_columnconfigure(2, weight=0) # Chat Panel
        self.frame_principal.grid_rowconfigure(0, weight=1) # Video and panels
        self.frame_principal.grid_rowconfigure(1, weight=0) # Buttons

        self.label_video = tk.Label(self.frame_principal, bg="black", bd=2, relief="sunken")
        self.label_video.grid(row=0, column=0, pady=10, padx=10, sticky='nsew')

        self.panel_datos = ttk.LabelFrame(self.frame_principal, text="Datos Reconocidos", padding=10)
        self.panel_datos.grid(row=0, column=1, padx=10, pady=10, sticky='n')

        self.labels_datos = {}
        for campo in ['Nombre', 'Edad', 'RUT', 'Fecha']:
            lbl = ttk.Label(self.panel_datos, text=f"{campo}: ---")
            lbl.pack(anchor='w', pady=5)
            self.labels_datos[campo] = lbl

        self.voice_status_label = ttk.Label(self.panel_datos, text="Voz IA: Inactiva", font=('Helvetica Neue', 10, 'italic'), foreground="blue")
        self.voice_status_label.pack(anchor='w', pady=10)

        self.chat_panel = ttk.LabelFrame(self.frame_principal, text="Conversación con Ojo Digital", padding=10)
        self.chat_panel.grid(row=0, column=2, padx=10, pady=10, sticky='nsew')
        self.chat_panel.grid_rowconfigure(0, weight=1) # Chat history takes most space
        self.chat_panel.grid_columnconfigure(0, weight=1)

        self.chat_history = tk.Text(self.chat_panel, wrap='word', state='disabled', width=40, height=20, font=('Helvetica Neue', 10), bg="#f0f0f0")
        self.chat_history.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        chat_scroll = ttk.Scrollbar(self.chat_panel, command=self.chat_history.yview)
        chat_scroll.grid(row=0, column=2, sticky='ns')
        self.chat_history['yscrollcommand'] = chat_scroll.set

        self.chat_input = ttk.Entry(self.chat_panel, font=('Helvetica Neue', 10))
        self.chat_input.grid(row=1, column=0, padx=5, pady=5, sticky='ew')
        self.chat_input.bind("<Return>", self.send_chat_message) # Allow Enter key to send

        self.btn_send_chat = ttk.Button(self.chat_panel, text="Enviar", command=self.send_chat_message, style='TButton')
        self.btn_send_chat.grid(row=1, column=1, padx=5, pady=5, sticky='e')

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

        self.btn_ver_historial = ttk.Button(self.frame_botones, text="Ver Historial", command=self.mostrar_historial_reconocimiento, style='TButton')
        self.btn_ver_historial.grid(row=0, column=4, padx=10, pady=5)

        self.status_label = ttk.Label(self.root, text="Estado: Listo", anchor='w', font=('Helvetica Neue', 10), background='#c0c0c0', padding=5)
        self.status_label.pack(side='bottom', fill='x')

        self.cap = None
        self.running = False
        self.frame_anterior = None
        self.procesando_rostro = False
        self.last_detection_time = {}
        self.recognition_timer = None
        self.face_detection_interval = 5
        self.cooldown_period = 60

        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        self.voice_listening_thread = None
        self.voice_active = False
        self.configure_voice_engine()

        self.inicializar_base_datos_mysql()
        self.inicializar_base_datos_local()
        self.datos_registrados = self.cargar_datos_registrados_mysql()
        self.encodings_registrados = self.cargar_encodings_registrados()

        self.root.protocol("WM_DELETE_WINDOW", self.cerrar)

        # Start listening for wake word immediately upon app launch
        self.voice_active = True
        self._resume_voice_listening() # Ensures the wake word listener starts

        # Play welcome message after UI is set up and voice engine is configured
        self.root.after(100, lambda: self.speak_and_chat(
            "Bienvenido al sistema Ojo Digital. Estoy lista para asistirte."
        ))

    def configure_voice_engine(self):
        """Configures the pyttsx3 engine, trying to use a Spanish voice."""
        voices = self.engine.getProperty('voices')
        if not voices:
            print("¡ADVERTENCIA: No se encontraron voces en tu sistema para pyttsx3!")
            print("Asegúrate de tener voces TTS instaladas (e.g., Microsoft SAPI for Windows, eSpeak for Linux).")
            self.append_to_chat("Ojo Digital", "Advertencia: No se encontraron voces en mi sistema. No podré hablar.")
        else:
            spanish_voice_found = False
            for voice in voices:
                if "es-ES" in voice.languages or "es_ES" in voice.id.lower():
                    self.engine.setProperty('voice', voice.id)
                    print(f"Usando voz en español para IA: {voice.name}")
                    spanish_voice_found = True
                    break
            if not spanish_voice_found:
                self.engine.setProperty('voice', voices[0].id)
                print(f"No se encontró voz en español, usando la voz predeterminada: {voices[0].name}")

    def append_to_chat(self, sender, message):
        """Appends a message to the chat history Text widget."""
        self.chat_history.config(state='normal')
        if sender == "Ojo Digital" and message.startswith("Encontré esto:"):
            # If it's a web search result, format it as a clickable link
            link_url = message.replace("Encontré esto: ", "").strip()
            self.chat_history.insert(tk.END, f"{sender}: ")
            self.chat_history.insert(tk.END, "Encontré esto: ", "link")
            self.chat_history.insert(tk.END, f"{link_url}\n", "link_text")
            self.chat_history.tag_config("link_text", foreground="blue", underline=1)
            self.chat_history.tag_bind("link_text", "<Button-1>", lambda e, url=link_url: self._open_link(url))
        else:
            self.chat_history.insert(tk.END, f"{sender}: {message}\n")
        self.chat_history.config(state='disabled')
        self.chat_history.see(tk.END) # Scroll to the bottom

    def _open_link(self, url):
        """Opens a given URL in the default web browser."""
        import webbrowser
        webbrowser.open_new_tab(url)

    def send_chat_message(self, event=None):
        """Sends a message from the chat input and processes it."""
        user_input = self.chat_input.get().strip()
        if user_input:
            self.append_to_chat("Tú", user_input)
            self.chat_input.delete(0, tk.END) # Clear input field

            # Process the command in a separate thread to keep UI responsive
            threading.Thread(target=self._process_chat_command_threaded, args=(user_input,)).start()
        else:
            self.speak_and_chat("No puedo procesar un comando vacío.")


    def _process_chat_command_threaded(self, user_input):
        """Helper to process chat commands in a thread."""
        response_text = self.process_ai_command(user_input)
        self.speak_and_chat(response_text)


    def speak_and_chat(self, text, sender="Ojo Digital"):
        """Function for the AI to 'speak' and display in chat."""
        self.append_to_chat(sender, text)
        print(f"IA dice: {text}")
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Error al reproducir voz: {e}")

    def speak(self, text):
        """Function for the AI to 'speak' the given text (used where chat update is not strictly needed)."""
        print(f"IA dice: {text}")
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Error al reproducir voz: {e}")

    def listen_for_command(self):
        """
        Function to listen to the user through the microphone and convert it to text.
        This is the 'active listening mode' for voice commands.
        """
        with sr.Microphone() as source:
            self.voice_status_label.config(text="Voz IA: Escuchando...")
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=6, phrase_time_limit=8)
            except sr.WaitTimeoutError:
                self.voice_status_label.config(text="Voz IA: Inactiva")
                return ""
            except Exception as e:
                self.voice_status_label.config(text="Voz IA: Error de micrófono")
                print(f"Error al escuchar comando: {e}")
                return ""

            try:
                self.voice_status_label.config(text="Voz IA: Reconociendo...")
                text = self.recognizer.recognize_google(audio, language="es-ES")
                print(f"Tú (IA Voz) dijiste: {text}")
                # Append user's voice input to chat
                self.append_to_chat("Tú (Voz)", text)
                self.voice_status_label.config(text="Voz IA: Lista")
                return text
            except sr.UnknownValueError:
                self.voice_status_label.config(text="Voz IA: No te entendí")
                self.speak_and_chat("Lo siento, no pude entender lo que dijiste.")
                return ""
            except sr.RequestError as e:
                self.voice_status_label.config(text="Voz IA: Error de servicio")
                self.speak_and_chat(f"Error en el servicio de reconocimiento de voz. Por favor, revisa tu conexión a internet.")
                print(f"Error en el servicio de reconocimiento de voz; {e}")
                return ""

    def listen_for_wake_word(self):
        """
        Continuously listens for a wake word to start voice interaction.
        """
        while self.voice_active:
            with sr.Microphone() as source:
                self.voice_status_label.config(text="Voz IA: Esperando comando (Di 'Hola asistente' o 'Ojo digital')")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5) # Faster adjustment
                try:
                    audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=4) # Listen continuously, short phrase limit for wake word
                except Exception as e:
                    print(f"Error al escuchar wake word: {e}")
                    time.sleep(1) # Wait a bit before retrying
                    continue

                try:
                    text = self.recognizer.recognize_google(audio, language="es-ES").lower()
                    print(f"Escuchado (wake word): {text}")
                    if "hola asistente" in text or "ojo digital" in text:
                        self.speak_and_chat("Dime.")
                        self.process_voice_command_loop() # Start the conversation loop
                except sr.UnknownValueError:
                    pass # Ignore if wake word is not understood
                except sr.RequestError as e:
                    print(f"Error en el servicio de reconocimiento de voz para wake word; {e}")
                time.sleep(0.1) # Small pause to not overload CPU

    def process_voice_command_loop(self):
        """Loop for continuous interaction with the voice AI."""
        while self.voice_active:
            user_input = self.listen_for_command()
            if user_input:
                response_text = self.process_ai_command(user_input)
                # speak_and_chat is already called within process_ai_command/speak_and_chat itself
                self.speak_and_chat(response_text)
                if any(phrase in user_input.lower() for phrase in ["adiós", "hasta luego", "chao", "cierra la conversación"]):
                    self.voice_status_label.config(text="Voz IA: Inactiva")
                    break # Exit the conversation loop
            else:
                self.speak_and_chat("No te escuché. ¿Necesitas algo más?")
                break # Exit the loop if no voice is detected

    def _resume_voice_listening(self):
        """Helper to ensure voice listening thread is running if voice_active is True."""
        if self.voice_active and (self.voice_listening_thread is None or not self.voice_listening_thread.is_alive()):
            self.voice_listening_thread = threading.Thread(target=self.listen_for_wake_word)
            self.voice_listening_thread.daemon = True # Allow the thread to close with the main app
            self.voice_listening_thread.start()

    def get_weather(self):
        now = datetime.now()
        current_hour = now.hour
        location = "Talagante, Región Metropolitana, Chile"

        weather_phrases = [
            f"En {location} son las {current_hour} y {now.minute} minutos. El cielo está despejado. Te deseo un excelente día.",
            f"La hora actual en {location} es {current_hour} con {now.minute} minutos. La temperatura es agradable. ¡Disfruta tu día!",
            f"Actualmente en {location} son las {current_hour} y {now.minute}. No hay nubes a la vista. ¿Hay algo más en lo que pueda ayudarte?",
            f"El tiempo en {location} ahora mismo es soleado y la hora es {current_hour}:{now.minute:02d}. Que tengas un día espléndido.",
            f"Son las {current_hour}:{now.minute:02d} en {location}. El pronóstico indica un día sin lluvias. ¡Aprovecha el día!"
        ]
        return random.choice(weather_phrases)

    def perform_calculation(self, command):
        command = command.lower()
        num_map = {
            'cero': 0, 'uno': 1, 'dos': 2, 'tres': 3, 'cuatro': 4,
            'cinco': 5, 'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9,
            'diez': 10, 'once': 11, 'doce': 12, 'trece': 13, 'catorce': 14,
            'quince': 15, 'dieciséis': 16, 'diecisiete': 17, 'dieciocho': 18, 'diecinueve': 19,
            'veinte': 20, 'treinta': 30, 'cuarenta': 40, 'cincuenta': 50,
            'sesenta': 60, 'setenta': 70, 'ochenta': 80, 'noventa': 90,
            'cien': 100
        }

        for word, digit in num_map.items():
            command = command.replace(word, str(digit))

        patterns = {
            'suma': r'(\d+)\s*(mas|\+|más)\s*(\d+)',
            'resta': r'(\d+)\s*(menos|-)\s*(\d+)',
            'multiplicacion': r'(\d+)\s*(por|x|\*)\s*(\d+)',
            'division': r'(\d+)\s*(dividido por|dividido entre|/)\s*(\d+)'
        }

        for op_name, pattern in patterns.items():
            match = re.search(pattern, command)
            if match:
                try:
                    num1 = float(match.group(1))
                    num2 = float(match.group(3))

                    if op_name == 'suma':
                        result = num1 + num2
                        return f"La suma de {num1} más {num2} es {result}."
                    elif op_name == 'resta':
                        result = num1 - num2
                        return f"La resta de {num1} menos {num2} es {result}."
                    elif op_name == 'multiplicacion':
                        result = num1 * num2
                        return f"La multiplicación de {num1} por {num2} es {result}."
                    elif op_name == 'division':
                        if num2 == 0:
                            return "No se puede dividir por cero."
                        result = num1 / num2
                        return f"La división de {num1} dividido por {num2} es {result}."
                except ValueError:
                    return "No pude entender los números para la operación."
                except Exception as e:
                    return f"Hubo un error al realizar la operación: {e}"

        return "No pude realizar esa operación. Intenta con 'cuánto es 5 más 3' o '20 dividido entre 4'."

    def tell_joke(self):
        jokes = [
            "¿Qué le dice un semáforo a otro semáforo? No me mires que me pongo rojo.",
            "¿Cuál es el colmo de un jardinero? Que deje a su mujer plantada.",
            "¿Qué hace una abeja en el gimnasio? ¡Zumba!",
            "¿Por qué el sol no fue a la universidad? Porque ya tiene millones de grados.",
            "¿Qué le dijo un pato a otro pato? Estamos empatados.",
            "¿Qué hace una taza de café en el gimnasio? ¡Se pone fuerte!",
            "¿Cuál es el último mono? El que cierra la puerta.",
            "¿Qué le dice un cable a otro cable? Somos inseparables."
        ]
        return random.choice(jokes)

    def search_web(self, query):
        self.speak_and_chat("Buscando en la web...")
        try:
            for url in search(query, num_results=1, lang="es"):
                return f"Encontré esto: {url}"
            return "No encontré nada relevante en la web."
        except Exception as e:
            return f"Lo siento, no pude realizar la búsqueda web en este momento: {e}. Quizás no hay conexión a internet o el servicio no está disponible."

    def process_ai_command(self, command):
        """
        Function to process the user's command and generate a voice AI response.
        """
        command = command.lower()

        if "hola" in command or "qué tal" in command:
            greetings = ["¡Hola! ¿En qué puedo ayudarte hoy?", "¿Qué tal? Dime en qué te sirvo.", "Saludos, estoy aquí para asistirte.", "¡Hola! Un placer verte. ¿Qué necesitas?"]
            return random.choice(greetings)
        elif "cómo estás" in command or "qué tal estás" in command:
            states = ["Estoy funcionando perfectamente, gracias por preguntar. ¿Y tú cómo te sientes?", "Me encuentro muy bien, lista para ayudarte.", "Excelente, como siempre. ¿Necesitas algo?", "Estoy genial, gracias. ¿En qué te puedo ser útil?"]
            return random.choice(states)
        elif any(phrase in command for phrase in ["adiós", "hasta luego", "chao", "cierra la conversación"]):
            farewells = ["¡Hasta luego! Que tengas un día excelente.", "¡Adiós! Fue un placer ayudarte.", "Nos vemos. No dudes en llamarme si me necesitas.", "Que tengas un buen día. ¡Hasta la próxima!", "Desconexión exitosa. ¡Hasta pronto!"]
            return random.choice(farewells)
        elif "qué hora es" in command or "la hora" in command:
            now = datetime.now()
            return f"Son las {now.hour} horas y {now.minute} minutos."
        elif "qué día es hoy" in command or "la fecha de hoy" in command:
            today = datetime.now()
            return f"Hoy es {today.strftime('%A %d de %B del %Y')}."
        elif "qué tiempo hace" in command or "cómo está el clima" in command or "el clima" in command:
            return self.get_weather()
        elif "quién eres" in command or "cuál es tu nombre" in command:
            return "Soy Ojo Digital, tu asistente de voz y reconocimiento facial, programada para ayudarte en lo que necesites."
        elif "gracias" in command or "te lo agradezco" in command:
            thanks_responses = ["De nada, estoy para servirte.", "Es un placer ayudarte.", "Para eso estoy.", "Cuando quieras.", "No hay de qué.", "El placer es mío."]
            return random.choice(thanks_responses)
        elif "qué haces" in command or "a qué te dedicas" in command or "ayuda" in command or "qué puedes hacer" in command:
            help_message = (
                "Puedo decirte la hora y fecha, contarte un chiste, hacer cálculos simples, o buscar información en la web. "
                "También puedo responder a saludos y despedidas. Además, asisto con la detección y reconocimiento facial. "
                "Aquí tienes una lista de comandos que puedes usar:\n"
                "- **'Hola'** o **'Qué tal'**: Para saludar.\n"
                "- **'Cómo estás'**: Para preguntar por mi estado.\n"
                "- **'Qué hora es'** o **'La hora'**: Para saber la hora actual.\n"
                "- **'Qué día es hoy'** o **'La fecha de hoy'**: Para saber la fecha.\n"
                "- **'Qué tiempo hace'** o **'El clima'**: Para información del tiempo.\n"
                "- **'Quién eres'** o **'Cuál es tu nombre'**: Para conocerme.\n"
                "- **'Cuéntame un chiste'** o **'Un chiste'**: Para escuchar un chiste.\n"
                "- **'Cuánto es [número] más [número]'** (o resta, multiplica, divide): Para cálculos.\n"
                "- **'Busca [algo]'** o **'Qué es [algo]'** o **'Quién es [alguien]'**: Para buscar en la web.\n"
                "- **'Adiós'** o **'Hasta luego'** o **'Chao'**: Para despedirte."
            )
            return help_message
        elif "cuéntame un chiste" in command or "un chiste" in command:
            return self.tell_joke()
        elif "cuánto es" in command or "calcula" in command or "suma" in command or "resta" in command or "multiplica" in command or "divide" in command:
            return self.perform_calculation(command)
        elif "busca" in command or "búscame" in command or "qué es" in command or "quién es" in command:
            query = ""
            if "busca" in command:
                query = command.split("busca", 1)[1].strip()
            elif "búscame" in command:
                query = command.split("búscame", 1)[1].strip()
            elif "qué es" in command:
                query = command.split("qué es", 1)[1].strip()
            elif "quién es" in command:
                query = command.split("quién es", 1)[1].strip()

            if query:
                return self.search_web(query)
            else:
                return "No sé qué quieres que busque. Por favor, dime qué quieres buscar."
        else:
            unknown_responses = [
                "Lo siento, no entendí tu comando. ¿Podrías repetirlo?",
                "No comprendí eso. ¿Podrías decirlo de otra manera?",
                "Hmm, parece que no capté eso. Inténtalo de nuevo, por favor.",
                "Disculpa, ¿podrías ser más específico?",
                "No estoy segura de qué quieres. Si necesitas ayuda, di 'ayuda'.",
                "Mi vocabulario es limitado en este momento. ¿Hay algo más de lo que pueda hablar?",
                "Podría ser que no tengo una respuesta para eso. Intenta con algo diferente.",
                "¿Podrías reformular tu pregunta? No estoy segura de haberla captado."
            ]
            return random.choice(unknown_responses)

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

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS pruebAron (
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
            messagebox.showerror("Error de Base de Datos", f"No se pudo conectar a la base de datos MySQL: {err}\nAsegúrate de que el servidor MySQL esté corriendo y los datos de conexión sean correctos.")
            # Consider exiting or disabling DB features if connection fails

    def cargar_datos_registrados_mysql(self):
        datos = {}
        if not hasattr(self, 'cursor') or (hasattr(self, 'conexion') and not self.conexion.is_connected()):
            return datos # Return empty if DB not connected
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
        # Pause voice listening during registration pop-up
        self.voice_status_label.config(text="Voz IA: Pausada para registro")
        temp_voice_active = self.voice_active
        self.voice_active = False # Temporarily disable voice listening

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
                messagebox.showwarning("Campos Incompletos", "Por favor, completa todos los campos para registrar a la persona.")
            # Resume voice listening after registration attempt
            self.voice_active = temp_voice_active
            self._resume_voice_listening() # Call the new helper method here!

        ventana_registro = tk.Toplevel(self.root)
        ventana_registro.title("Registrar Persona")
        ventana_registro.geometry("400x280")
        ventana_registro.transient(self.root)
        ventana_registro.grab_set()

        campos = ["nombre", "edad", "rut"]
        entradas = {}

        for i, campo in enumerate(campos):
            ttk.Label(ventana_registro, text=campo.capitalize() + ":").pack(pady=5)
            entrada = ttk.Entry(ventana_registro)
            entrada.pack(pady=5, padx=20, fill='x')
            entradas[campo] = entrada

        ttk.Button(ventana_registro, text="Registrar", command=registrar_accion, style='TButton').pack(pady=15)

        ventana_registro.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (ventana_registro.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (ventana_registro.winfo_height() // 2)
        ventana_registro.geometry(f"+{x}+{y}")

        ventana_registro.protocol("WM_DELETE_WINDOW", lambda: [
            ventana_registro.destroy(),
            setattr(self, 'voice_active', temp_voice_active),
            self._resume_voice_listening() # Call the new helper method here too!
        ])

    def registrar_persona(self, nombre, edad, rut, fecha):
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
            time.sleep(1) # Give camera a moment to warm up if just opened
        ret, frame = self.cap.read()
        if not ret:
            self.status_label.config(text="Error: No se pudo capturar imagen de la cámara.")
            self.speak_and_chat("Error: No se pudo capturar una imagen para el registro.")
            return
        frame_flipped = cv2.flip(frame, 1)
        rostro = self.detectar_rostro(frame_flipped)
        if rostro is None:
            self.status_label.config(text="⚠️ No se detectó rostro para registrar.")
            self.speak_and_chat("No se detectó ningún rostro en el encuadre. Asegúrate de que tu cara esté visible.")
            messagebox.showwarning("Registro Fallido", "No se detectó ningún rostro en el encuadre. Asegúrate de que tu cara esté visible.")
            return
        encoding = self.extraer_encoding(rostro)
        if encoding is None:
            self.status_label.config(text="⚠️ No se pudo extraer encoding del rostro.")
            self.speak_and_chat("No se pudo procesar el rostro para el reconocimiento. Intenta de nuevo.")
            messagebox.showwarning("Registro Fallido", "No se pudo procesar el rostro para el reconocimiento. Intenta de nuevo.")
            return
        try:
            self.cursor.execute("SELECT COUNT(*) FROM reconocimiento WHERE nombre = %s OR rut = %s", (nombre, rut))
            if self.cursor.fetchone()[0] > 0:
                self.status_label.config(text=f"❌ Error: Nombre o RUT ya registrados.")
                self.speak_and_chat("El nombre o RUT ya están registrados en la base de datos.")
                messagebox.showerror("Error de Registro", "El nombre o RUT ya están registrados en la base de datos.")
                return
        except mysql.connector.Error as err:
            print(f"❌ Error al verificar duplicados en MySQL: {err}")
            self.speak_and_chat("Ocurrió un error al verificar datos duplicados en la base de datos.")
            messagebox.showerror("Error de Base de Datos", "Ocurrió un error al verificar datos duplicados.")
            return
        try:
            self.cursor_local.execute("INSERT INTO personas (imagen_archivo) VALUES (?)", ('temp',))
            self.db_local.commit()
            new_id = self.cursor_local.lastrowid
            nombre_archivo_imagen = f"imagenes/id_{new_id}.jpg"
            nombre_archivo_encoding = f"imagenes/id_{new_id}_encoding.npy"
            cv2.imwrite(nombre_archivo_imagen, rostro)
            np.save(nombre_archivo_encoding, encoding)
            self.cursor_local.execute("UPDATE personas SET imagen_archivo = ? WHERE id = ?", (nombre_archivo_imagen, new_id))
            self.db_local.commit()
            self.cursor.execute(
                "INSERT INTO reconocimiento (nombre, edad, rut, fecha, id_imagen) VALUES (%s, %s, %s, %s, %s)",
                (nombre, edad, rut, fecha, new_id)
            )
            self.conexion.commit()
            self.datos_registrados[nombre] = {
                'edad': edad,
                'rut': rut,
                'fecha': fecha,
                'id_imagen': new_id
            }
            self.encodings_registrados[nombre] = encoding
            self.status_label.config(text=f"✅ Registrado: {nombre}")
            self.speak_and_chat(f"{nombre} ha sido registrado exitosamente.")
            print(f"✅ Registrado {nombre} con imagen ID {new_id}")
            messagebox.showinfo("Registro Exitoso", f"{nombre} ha sido registrado exitosamente.")
        except mysql.connector.Error as e:
            print(f"❌ Error al registrar en MySQL: {e}")
            self.status_label.config(text=f"❌ Error al registrar en MySQL.")
            self.speak_and_chat(f"Error al registrar a {nombre} en la base de datos.")
            messagebox.showerror("Error de Base de Datos", f"Error al registrar la persona en MySQL: {e}")
            if 'new_id' in locals() and os.path.exists(nombre_archivo_imagen):
                os.remove(nombre_archivo_imagen)
            if 'new_id' in locals() and os.path.exists(nombre_archivo_encoding):
                os.remove(nombre_archivo_encoding)
            self.cursor_local.execute("DELETE FROM personas WHERE id = ?", (new_id,))
            self.db_local.commit()

    def detectar_rostro(self, frame):
        loc = face_recognition.face_locations(frame)
        if not loc:
            return None
        t, r, b, l = loc[0]
        return frame[t:b, l:r]

    def extraer_encoding(self, rostro):
        rgb = cv2.cvtColor(rostro, cv2.COLOR_BGR2RGB)
        # Ensure that face_encodings receives a list of locations, even if there's only one
        encodings = face_recognition.face_encodings(rgb, known_face_locations=[(0, rostro.shape[1], rostro.shape[0], 0)])
        if encodings:
            return encodings[0]
        return None

    def iniciar(self):
        if not self.running:
            self.running = True
            self.btn_iniciar.config(state=tk.DISABLED)
            self.btn_detener.config(state=tk.NORMAL)
            self.btn_registrar.config(state=tk.NORMAL)
            self.status_label.config(text="Estado: Detección iniciada")
            self.speak_and_chat("Detección de movimiento y reconocimiento facial iniciada.")
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.status_label.config(text="Error: No se pudo abrir la cámara.")
                self.speak_and_chat("Error: No se pudo acceder a la cámara. Por favor, verifica que no esté en uso.")
                messagebox.showerror("Error de Cámara", "No se pudo acceder a la cámara. Asegúrate de que no esté en uso por otra aplicación.")
                self.detener()
                return
            self.update_frame()
            # Start voice listening thread if not already active
            self.voice_active = True
            self._resume_voice_listening()

    def detener(self):
        if self.running:
            self.running = False
            self.btn_iniciar.config(state=tk.NORMAL)
            self.btn_detener.config(state=tk.DISABLED)
            self.btn_registrar.config(state=tk.DISABLED)
            self.status_label.config(text="Estado: Detenido")
            self.speak_and_chat("Detección detenida.")
            if self.cap:
                self.cap.release()
            self.label_video.config(image='')
            # Stop voice listening
            self.voice_active = False
            self.voice_status_label.config(text="Voz IA: Inactiva")


    def update_frame(self):
        if self.running:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1) # Mirror the frame for a more intuitive view
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)

                if self.frame_anterior is None:
                    self.frame_anterior = gray
                    self.root.after(10, self.update_frame)
                    return

                diferencia = cv2.absdiff(self.frame_anterior, gray)
                _, umbral = cv2.threshold(diferencia, 25, 255, cv2.THRESH_BINARY)
                umbral = cv2.dilate(umbral, None, iterations=2)
                contornos, _ = cv2.findContours(umbral.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                movimiento_detectado = False
                for contorno in contornos:
                    if cv2.contourArea(contorno) < 5000: # Minimum area to consider it motion
                        continue
                    (x, y, w, h) = cv2.boundingRect(contorno)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    movimiento_detectado = True

                self.frame_anterior = gray

                if movimiento_detectado and not self.procesando_rostro:
                    self.procesando_rostro = True
                    # Debounce face recognition to run every X seconds per person
                    self.root.after(100, lambda: threading.Thread(target=self._recognize_faces_threaded, args=(frame.copy(),)).start())

                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                imgtk = ImageTk.PhotoImage(image=img)
                self.label_video.imgtk = imgtk
                self.label_video.config(image=imgtk)

            self.root.after(10, self.update_frame)

    def _recognize_faces_threaded(self, frame_to_process):
        try:
            face_locations = face_recognition.face_locations(frame_to_process)
            face_encodings = face_recognition.face_encodings(frame_to_process, face_locations)

            current_time = time.time()
            found_a_match = False

            for face_encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):
                matches = face_recognition.compare_faces(list(self.encodings_registrados.values()), face_encoding, tolerance=0.5)
                name = "Desconocido"
                known_names = list(self.encodings_registrados.keys())

                face_distances = face_recognition.face_distance(list(self.encodings_registrados.values()), face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_names[best_match_index]
                    found_a_match = True

                    # Cooldown logic per person
                    if name not in self.last_detection_time or \
                       (current_time - self.last_detection_time[name] > self.cooldown_period):
                        self.last_detection_time[name] = current_time
                        self.actualizar_datos_reconocidos(name)
                        self.reproducir_alerta(ALERTA_SONIDO_RECONOCIDO)
                        self.guardar_historial_reconocimiento(name, self.datos_registrados.get(name, {}).get('rut', 'N/A'))
                        self.speak_and_chat(f"Persona reconocida: {name}")

                elif not found_a_match: # Only play unknown sound if no known faces are detected in this pass
                    # General cooldown for unknown detections to avoid constant alerts
                    if "Desconocido" not in self.last_detection_time or \
                       (current_time - self.last_detection_time["Desconocido"] > self.cooldown_period):
                        self.last_detection_time["Desconocido"] = current_time
                        self.actualizar_datos_reconocidos("Desconocido")
                        self.reproducir_alerta(ALERTA_SONIDO_NO_RECONOCIDO)
                        self.guardar_historial_reconocimiento("Desconocido", "N/A")
                        self.speak_and_chat("Persona desconocida detectada.")

        except Exception as e:
            print(f"Error en el hilo de reconocimiento facial: {e}")
        finally:
            self.procesando_rostro = False # Reset flag regardless of outcome

    def actualizar_datos_reconocidos(self, nombre_persona):
        if nombre_persona != "Desconocido" and nombre_persona in self.datos_registrados:
            datos = self.datos_registrados[nombre_persona]
            self.labels_datos['Nombre'].config(text=f"Nombre: {nombre_persona}")
            self.labels_datos['Edad'].config(text=f"Edad: {datos['edad']}")
            self.labels_datos['RUT'].config(text=f"RUT: {datos['rut']}")
            self.labels_datos['Fecha'].config(text=f"Fecha: {datos['fecha']}")
        else:
            self.labels_datos['Nombre'].config(text=f"Nombre: {nombre_persona}")
            self.labels_datos['Edad'].config(text="Edad: ---")
            self.labels_datos['RUT'].config(text="RUT: ---")
            self.labels_datos['Fecha'].config(text="Fecha: ---")

    def reproducir_alerta(self, archivo_sonido):
        try:
            pygame.mixer.music.load(archivo_sonido)
            pygame.mixer.music.play()
        except pygame.error as e:
            print(f"Error al reproducir sonido: {e}")

    def guardar_historial_reconocimiento(self, nombre, rut):
        try:
            fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "INSERT INTO pruebAron (nombre, rut, fecha_hora) VALUES (%s, %s, %s)",
                (nombre, rut, fecha_hora)
            )
            self.conexion.commit()
            print(f"Historial guardado: {nombre} - {rut} - {fecha_hora}")
        except mysql.connector.Error as err:
            print(f"❌ Error al guardar historial en MySQL: {err}")

    def mostrar_datos_locales(self):
        ventana_datos = tk.Toplevel(self.root)
        ventana_datos.title("Datos Registrados Localmente")
        ventana_datos.geometry("800x600")
        ventana_datos.transient(self.root)
        ventana_datos.grab_set()

        frame_listado = ttk.Frame(ventana_datos, padding=10)
        frame_listado.pack(expand=True, fill='both')

        columns = ("ID", "Nombre", "Edad", "RUT", "Fecha")
        tree = ttk.Treeview(frame_listado, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor='center')
        tree.pack(expand=True, fill='both')

        try:
            self.cursor.execute("SELECT id_imagen, nombre, edad, rut, fecha FROM reconocimiento ORDER BY nombre")
            for id_imagen, nombre, edad, rut, fecha in self.cursor.fetchall():
                tree.insert("", tk.END, values=(id_imagen, nombre, edad, rut, fecha))
        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"No se pudo cargar los datos de MySQL: {err}")
            ventana_datos.destroy()
            return

        def mostrar_imagen(event):
            selected_item = tree.focus()
            if not selected_item:
                return
            item_values = tree.item(selected_item, 'values')
            if not item_values:
                return
            id_imagen = item_values[0]
            nombre_persona = item_values[1]
            ruta_imagen = f"imagenes/id_{id_imagen}.jpg"

            if os.path.exists(ruta_imagen):
                img_window = tk.Toplevel(ventana_datos)
                img_window.title(f"Imagen de {nombre_persona}")
                img_window.transient(ventana_datos)
                
                try:
                    img = Image.open(ruta_imagen)
                    # Resize image to fit, max height 400
                    max_height = 400
                    if img.height > max_height:
                        ratio = max_height / img.height
                        img = img.resize((int(img.width * ratio), max_height), Image.LANCZOS)
                    
                    img_tk = ImageTk.PhotoImage(img)
                    lbl_img = tk.Label(img_window, image=img_tk)
                    lbl_img.image = img_tk # Keep a reference!
                    lbl_img.pack(padx=10, pady=10)
                except Exception as e:
                    tk.Label(img_window, text=f"Error al cargar imagen: {e}").pack(padx=10, pady=10)
            else:
                messagebox.showerror("Error", f"No se encontró la imagen para el ID {id_imagen} en {ruta_imagen}")

        tree.bind("<Double-1>", mostrar_imagen)

    def mostrar_historial_reconocimiento(self):
        ventana_historial = tk.Toplevel(self.root)
        ventana_historial.title("Historial de Reconocimiento")
        ventana_historial.geometry("800x600")
        ventana_historial.transient(self.root)
        ventana_historial.grab_set()

        frame_listado = ttk.Frame(ventana_historial, padding=10)
        frame_listado.pack(expand=True, fill='both')

        columns = ("ID", "Nombre", "RUT", "Fecha y Hora")
        tree = ttk.Treeview(frame_listado, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor='center')
        tree.pack(expand=True, fill='both')

        try:
            self.cursor.execute("SELECT id, nombre, rut, fecha_hora FROM pruebAron ORDER BY fecha_hora DESC")
            for id_reg, nombre, rut, fecha_hora in self.cursor.fetchall():
                tree.insert("", tk.END, values=(id_reg, nombre, rut, fecha_hora))
        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"No se pudo cargar el historial de MySQL: {err}")
            ventana_historial.destroy()
            return

    def cerrar(self):
        self.running = False
        self.voice_active = False # Ensure voice thread stops
        if self.cap:
            self.cap.release()
        if hasattr(self, 'conexion') and self.conexion.is_connected():
            self.cursor.close()
            self.conexion.close()
            print("❌ Conexión MySQL cerrada.")
        if hasattr(self, 'db_local'):
            self.cursor_local.close()
            self.db_local.close()
            print("❌ Conexión SQLite cerrada.")
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = DeteccionMovimientoApp(root)
    root.mainloop()