# filename: setup_database_final.py

import mysql.connector
import os

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
    Configura la base de datos MySQL creando y/o alterando tablas si es necesario.
    - Se conecta a la base de datos.
    - Crea la tabla 'imagenes_reconocimiento' para almacenar datos binarios (fotos y encodings).
    - Crea el resto de las tablas del sistema.
    - Asegura que la tabla 'reconocimiento' tenga la clave foránea correcta.
    """
    conn = None
    try:
        # Conectar a MySQL (sin especificar la base de datos al principio)
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()
        db_name = DB_CONFIG['database']

        # Crear la base de datos si no existe
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE {db_name}")
        print(f"Conectado a la base de datos '{db_name}'.")

        print("Creando/verificando tablas...")

        # --- Tabla para almacenar las imágenes y encodings ---
        # Usamos LONGBLOB para imágenes por si son de alta resolución.
        # Usamos BLOB para los encodings, que tienen un tamaño fijo y más pequeño.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS imagenes_reconocimiento (
                id INT AUTO_INCREMENT PRIMARY KEY,
                imagen_data LONGBLOB NOT NULL,
                encoding_data BLOB NOT NULL
            )
        """)
        print(" -> Tabla 'imagenes_reconocimiento' creada/verificada.")

        # --- Tabla de Reconocimiento (Personas) ---
        # id_imagen ahora será una clave foránea.
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
                    ON DELETE SET NULL
            )
        """)
        print(" -> Tabla 'reconocimiento' creada/verificada.")

        # --- Tabla de Historial ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historial_reconocimiento (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(255) NOT NULL,
                rut VARCHAR(15) NOT NULL,
                fecha_hora DATETIME NOT NULL
            )
        """)
        print(" -> Tabla 'historial_reconocimiento' creada/verificada.")
        
        # --- Otras tablas del sistema (Clientes, Dispositivos, etc.) ---
        # (Se mantienen las otras tablas que ya tenías)
        other_tables = {
            "Clientes": """
                CREATE TABLE IF NOT EXISTS Clientes (
                    cliente_id INT AUTO_INCREMENT PRIMARY KEY, nombre VARCHAR(100) NOT NULL, direccion VARCHAR(200),
                    telefono VARCHAR(20), correo VARCHAR(100), fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "Dispositivos": """
                CREATE TABLE IF NOT EXISTS Dispositivos (
                    dispositivo_id INT AUTO_INCREMENT PRIMARY KEY, cliente_id INT, tipo_dispositivo VARCHAR(50),
                    modelo VARCHAR(50), fecha_instalacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                    estado ENUM('Activo', 'Inactivo') DEFAULT 'Activo', FOREIGN KEY (cliente_id) REFERENCES Clientes(cliente_id)
                )
            """,
            # ... (puedes añadir el resto de tus tablas aquí si lo deseas)
        }

        for table_name, table_sql in other_tables.items():
            try:
                print(f" -> Creando tabla '{table_name}' si no existe...")
                cursor.execute(table_sql)
            except mysql.connector.Error as err:
                print(f"    -> Error al crear tabla {table_name}: {err}")


        conn.commit()
        print("\n✅ ¡Base de datos configurada exitosamente!")

    except mysql.connector.Error as e:
        print(f"❌ Error al conectar o configurar la base de datos: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    # Crear carpetas necesarias para archivos que no van a la DB
    if not os.path.exists("desconocidos_fotos"):
        os.makedirs("desconocidos_fotos")
    
    setup_database()

