# filename: setup_database_final.py

import mysql.connector
import os
from datetime import datetime

# --- Configuración de la Base de Datos MySQL ---
# Asegúrate de que estos datos son correctos para tu servidor MySQL
DB_CONFIG = {
    'host': '192.168.1.122',
    'user': 'ojodigital',
    'password': 'feria2025',
    'database': 'ojodigital',
    'charset': 'utf8mb4',
    'use_unicode': True
}

def setup_database():
    """
    Configura la base de datos MySQL para un entorno multi-dispositivo.
    - Crea tablas para el registro de personas, imágenes y historial.
    - Crea la tabla 'estado_sistema' para rastrear la última actualización y sincronizar clientes.
    - Crea la tabla 'dispositivos_activos' para monitorear los clientes conectados.
    """
    conn = None
    try:
        # Conectar a MySQL para crear la base de datos si es necesario
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()
        db_name = DB_CONFIG['database']

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE {db_name}")
        print(f"Conectado a la base de datos '{db_name}'.")

        print("Creando/verificando tablas para el sistema de reconocimiento...")

        # --- Tabla para almacenar las imágenes y encodings ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS imagenes_reconocimiento (
                id INT AUTO_INCREMENT PRIMARY KEY,
                imagen_data LONGBLOB NOT NULL,
                encoding_data BLOB NOT NULL
            )
        """)
        print(" -> Tabla 'imagenes_reconocimiento' creada/verificada.")

        # --- Tabla de Reconocimiento (Personas) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reconocimiento (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre_completo VARCHAR(255) NOT NULL,
                fecha_nacimiento DATE NOT NULL,
                edad INT NOT NULL,
                rut VARCHAR(15) NOT NULL UNIQUE,
                relacion VARCHAR(50) NOT NULL,
                fecha_registro DATE NOT NULL,
                id_imagen INT,
                INDEX (id_imagen),
                FOREIGN KEY (id_imagen)
                    REFERENCES imagenes_reconocimiento(id)
                    ON DELETE CASCADE
            )
        """)
        print(" -> Tabla 'reconocimiento' creada/verificada.")

        # --- Tabla de Historial ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historial_reconocimiento (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(255) NOT NULL,
                rut VARCHAR(15) NOT NULL,
                fecha_hora DATETIME NOT NULL,
                dispositivo_id VARCHAR(100)
            )
        """)
        print(" -> Tabla 'historial_reconocimiento' creada/verificada.")

        # --- Tabla para Sincronización de Clientes ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS estado_sistema (
                id INT PRIMARY KEY DEFAULT 1,
                ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        print(" -> Tabla 'estado_sistema' creada/verificada.")
        
        # Insertar la fila inicial para el estado del sistema si no existe
        cursor.execute("INSERT IGNORE INTO estado_sistema (id) VALUES (1)")


        # --- Tabla para Monitorear Dispositivos Activos ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dispositivos_activos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hostname VARCHAR(255) NOT NULL UNIQUE,
                ultima_conexion TIMESTAMP
            )
        """)
        print(" -> Tabla 'dispositivos_activos' creada/verificada.")


        conn.commit()
        print("\n✅ ¡Base de datos configurada exitosamente para operación en red!")

    except mysql.connector.Error as e:
        print(f"❌ Error al conectar o configurar la base de datos: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    if not os.path.exists("desconocidos_fotos"):
        os.makedirs("desconocidos_fotos")
    
    setup_database()
