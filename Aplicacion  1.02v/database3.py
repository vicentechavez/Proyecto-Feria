# filename: setup_database_final.py

import mysql.connector
import os

# --- Configuración de la Base de Datos MySQL ---
DB_CONFIG = {
    'host': '192.168.1.122',
    'user': 'ojodigital',
    'password': 'feria2025',
    'database': 'ojodigital',
    'charset': 'utf8',
    'use_unicode': True
}

def setup_database():
    """
    Configura la base de datos MySQL creando tablas si no existen.
    - Se conecta a la base de datos especificada.
    - Crea todas las tablas necesarias utilizando CREATE TABLE IF NOT EXISTS.
    """
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        db_name = DB_CONFIG['database']
        print(f"Conectado a la base de datos '{db_name}'.")

        print("Creando tablas si no existen...")

        tables = {
            "reconocimiento": """
                CREATE TABLE IF NOT EXISTS reconocimiento (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre_completo VARCHAR(255) NOT NULL,
                    fecha_nacimiento DATE NOT NULL,
                    edad INT NOT NULL,
                    rut VARCHAR(255) NOT NULL UNIQUE,
                    relacion VARCHAR(50) NOT NULL,
                    fecha_registro DATE NOT NULL,
                    id_imagen INT NOT NULL
                )
            """,
            "historial_reconocimiento": """
                CREATE TABLE IF NOT EXISTS historial_reconocimiento (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(255) NOT NULL,
                    rut VARCHAR(255) NOT NULL,
                    fecha_hora DATETIME NOT NULL
                )
            """,
            "Clientes": """
                CREATE TABLE IF NOT EXISTS Clientes (
                    cliente_id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL,
                    direccion VARCHAR(200),
                    telefono VARCHAR(20),
                    correo VARCHAR(100),
                    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "Dispositivos": """
                CREATE TABLE IF NOT EXISTS Dispositivos (
                    dispositivo_id INT AUTO_INCREMENT PRIMARY KEY,
                    cliente_id INT,
                    tipo_dispositivo VARCHAR(50),
                    modelo VARCHAR(50),
                    fecha_instalacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                    estado ENUM('Activo', 'Inactivo') DEFAULT 'Activo',
                    FOREIGN KEY (cliente_id) REFERENCES Clientes(cliente_id)
                )
            """,
            "PlanesSeguridad": """
                CREATE TABLE IF NOT EXISTS PlanesSeguridad (
                    plan_id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre_plan VARCHAR(100),
                    descripcion TEXT,
                    precio DECIMAL(12, 2),
                    tipo_plan ENUM('Básico', 'Avanzado', 'Premium')
                )
            """,
            "ClientesPlanes": """
                CREATE TABLE IF NOT EXISTS ClientesPlanes (
                    cliente_id INT,
                    plan_id INT,
                    fecha_inicio DATE,
                    fecha_fin DATE,
                    PRIMARY KEY(cliente_id, plan_id),
                    FOREIGN KEY (cliente_id) REFERENCES Clientes(cliente_id),
                    FOREIGN KEY (plan_id) REFERENCES PlanesSeguridad(plan_id)
                )
            """,
            "Monitoreo": """
                CREATE TABLE IF NOT EXISTS Monitoreo (
                    monitoreo_id INT AUTO_INCREMENT PRIMARY KEY,
                    dispositivo_id INT,
                    fecha_monitoreo DATETIME DEFAULT CURRENT_TIMESTAMP,
                    estado ENUM('Normal', 'Alerta', 'Fallo') DEFAULT 'Normal',
                    FOREIGN KEY (dispositivo_id) REFERENCES Dispositivos(dispositivo_id)
                )
            """,
            "Pagos": """
                CREATE TABLE IF NOT EXISTS Pagos (
                    pago_id INT AUTO_INCREMENT PRIMARY KEY,
                    cliente_id INT,
                    monto DECIMAL(12, 2),
                    fecha_pago DATE,
                    metodo_pago ENUM('Tarjeta', 'Transferencia', 'Efectivo', 'Otros'),
                    FOREIGN KEY (cliente_id) REFERENCES Clientes(cliente_id)
                )
            """,
            "HistorialDispositivos": """
                CREATE TABLE IF NOT EXISTS HistorialDispositivos (
                    historial_id INT AUTO_INCREMENT PRIMARY KEY,
                    dispositivo_id INT,
                    fecha_accion DATETIME DEFAULT CURRENT_TIMESTAMP,
                    accion VARCHAR(255),
                    descripcion TEXT,
                    FOREIGN KEY (dispositivo_id) REFERENCES Dispositivos(dispositivo_id)
                )
            """,
            "HistorialPagos": """
                CREATE TABLE IF NOT EXISTS HistorialPagos (
                    historial_pago_id INT AUTO_INCREMENT PRIMARY KEY,
                    cliente_id INT,
                    monto DECIMAL(10, 2),
                    fecha_pago DATE,
                    metodo_pago ENUM('Tarjeta', 'Transferencia', 'Efectivo', 'Otros'),
                    FOREIGN KEY (cliente_id) REFERENCES Clientes(cliente_id)
                )
            """,
            "Empresa": """
                CREATE TABLE IF NOT EXISTS Empresa (
                    empresa_id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre_empresa VARCHAR(255) NOT NULL,
                    direccion VARCHAR(255),
                    telefono VARCHAR(20),
                    correo VARCHAR(100),
                    fecha_fundacion DATE,
                    descripcion TEXT,
                    sitio_web VARCHAR(255),
                    estado_empresa ENUM('Activo', 'Inactivo', 'Suspendido') DEFAULT 'Activo'
                )
            """,
            "Sospechoso": """
                CREATE TABLE sospechosos (
                    sospechoso_id INT AUTO_INCREMENT PRIMARY KEY,
                    imagen_data LONGBLOB NOT NULL,
                    fecha_hora DATETIME NOT NULL,
                    dispositivo_id VARCHAR(255)
                )
            """
        }
        
        for table_name, table_sql in tables.items():
            try:
                print(f" -> Creando tabla '{table_name}' si no existe...")
                cursor.execute(table_sql)
            except mysql.connector.Error as err:
                print(f"    -> Error al crear tabla {table_name}: {err}")

        conn.commit()
        print("\n✅ ¡Base de datos configurada exitosamente! Se han creado o verificado todas las tablas.")

    except mysql.connector.Error as e:
        print(f"❌ Error al conectar o configurar la base de datos: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    # Crear carpetas necesarias si no existen
    if not os.path.exists("imagenes_registradas"):
        os.makedirs("imagenes_registradas")
    if not os.path.exists("encodings_registrados"):
        os.makedirs("encodings_registrados")
    if not os.path.exists("sospechosos_fotos"):
        os.makedirs("sospechosos_fotos")
    
    setup_database()