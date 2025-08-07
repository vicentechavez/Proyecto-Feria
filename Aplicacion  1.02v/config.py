# config.py
# Este archivo almacena todas las configuraciones y constantes de la aplicación.

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
DB_CONFIG = {
    "host": "192.168.1.122",
    "user": "ojodigital",
    "password": "feria2025",
    "database": "ojodigital",
    "charset": "utf8mb4",
    "use_unicode": True
}

# --- CONSTANTES DE LA APLICACIÓN ---
ALERTA_SONIDO_RECONOCIDO = "confirmacion.mp3"
ALERTA_SONIDO_NO_RECONOCIDO = "error.mp3"
APP_LOG_FILE = "app_log.txt"
ADMIN_PASSWORD = "12345"  # Contraseña para el panel de administración

# --- NUEVA PALETA DE COLORES (ESTILO MODERNO) ---
COLORES = {
    "fondo_principal": "#2d2d2d",  # Un gris oscuro para el fondo
    "fondo_paneles": "#3c3c3c",    # Un gris ligeramente más claro para paneles
    "fondo_label_video": "black",
    "fondo_barra_estado": "#1e1e1e",
    "texto_barra_estado": "#e0e0e0",
    "boton_normal_bg": "#0078d4",  # Azul estándar para botones
    "boton_normal_fg": "white",
    "boton_activo_bg": "#005a9e",  # Azul más oscuro al presionar
    "boton_verde_bg": "#107c10",   # Verde para botones especiales (como Iniciar)
    "boton_verde_fg": "white",
    "boton_verde_activo_bg": "#0d630d",
    "texto_titulo": "#ffffff",
    "texto_label": "#f0f0f0",
    "texto_cooldown": "#ffb74d",
    "texto_error": "#ef5350",
    "borde_widget": "#555555",
    "animacion_fondo": "#4a4a4b",
    "animacion_texto_nombre": "#ffffff",
    "borde_reconocido": (0, 255, 0),
    "borde_desconocido": (0, 0, 255)
}

# --- FUENTES ---
FONT_PRINCIPAL = ('Segoe UI', 10)
FONT_TITULO_APP = ('Segoe UI', 24, 'bold') # Fuente para el título "Ojo Digital"
FONT_TITULO = ('Segoe UI', 12, 'bold')
FONT_ESTADO = ('Segoe UI', 9)

# --- ESTILOS PARA VENTANAS SECUNDARIAS ---
STYLE_CONFIG_VENTANA_SECUNDARIA = {
    'bg': '#3c3c3c', # Fondo oscuro también para ventanas secundarias
    'label_style': 'Dark.TLabel',
    'entry_style': 'Dark.TEntry',
    'combobox_style': 'Dark.TCombobox',
    'frame_style': 'Dark.TFrame'
}
