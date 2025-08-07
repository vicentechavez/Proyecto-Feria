# database_handler.py
# Este módulo centraliza todas las operaciones con la base de datos MySQL.

import mysql.connector
import numpy as np
from datetime import datetime

class DatabaseHandler:
    def __init__(self, db_config):
        """Inicializa la conexión a la base de datos."""
        self.config = db_config
        self.connection = None
        self.connect()

    def connect(self):
        """Establece la conexión con la base de datos."""
        try:
            self.connection = mysql.connector.connect(**self.config)
            print("✅ Conexión a MySQL establecida.")
        except mysql.connector.Error as err:
            print(f"❌ Error de conexión a MySQL: {err}")
            raise err

    def reconnect(self):
        """Intenta reconectar si la conexión se pierde."""
        print("⚠️ Intentando reconectar a la base de datos...")
        try:
            if self.connection and self.connection.is_connected():
                self.connection.close()
            self.connect()
            return True
        except mysql.connector.Error as err:
            print(f"❌ Fallo en la reconexión: {err}")
            return False

    def _execute_query(self, query, params=None, fetch=None, dictionary=False):
        """
        Ejecuta una consulta de forma segura, manejando reconexiones.
        fetch: puede ser 'one', 'all', o None para sentencias DML.
        """
        try:
            if not self.connection or not self.connection.is_connected():
                if not self.reconnect():
                    return None # No se pudo reconectar

            cursor = self.connection.cursor(dictionary=dictionary)
            cursor.execute(query, params or ())
            
            if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                self.connection.commit()
                last_row_id = cursor.lastrowid
                cursor.close()
                return last_row_id

            if fetch == 'one':
                result = cursor.fetchone()
            elif fetch == 'all':
                result = cursor.fetchall()
            else:
                result = None # No se esperaba un resultado
            
            cursor.close()
            return result
        except mysql.connector.Error as err:
            print(f"❌ Error en consulta: {err}. Consulta: {query[:100]}...")
            return None

    def get_all_registered_data(self):
        """Obtiene todos los datos y encodings de las personas registradas para el reconocimiento."""
        sql = """
            SELECT r.nombre_completo, r.fecha_nacimiento, r.edad, r.rut, r.relacion, 
                   r.fecha_registro, r.id_imagen, i.encoding_data 
            FROM reconocimiento r JOIN imagenes_reconocimiento i ON r.id_imagen = i.id
        """
        rows = self._execute_query(sql, fetch='all', dictionary=True)
        datos, encodings = {}, {}
        if not rows: return datos, encodings

        for row in rows:
            nombre = row['nombre_completo']
            datos[nombre] = {
                'fecha_nacimiento': row['fecha_nacimiento'].strftime("%Y-%m-%d"),
                'edad': row['edad'], 'rut': row['rut'], 'relacion': row['relacion'],
                'fecha_registro': row['fecha_registro'].strftime("%Y-%m-%d"),
                'id_imagen': row['id_imagen']
            }
            encodings[nombre] = np.frombuffer(row['encoding_data'], dtype=np.float64)
        return datos, encodings

    def get_data_for_admin_panel(self):
        """Obtiene los datos de todas las personas para el panel de administración."""
        sql = "SELECT id_imagen, nombre_completo, rut, fecha_nacimiento, edad, relacion, fecha_registro FROM reconocimiento ORDER BY nombre_completo"
        return self._execute_query(sql, fetch='all', dictionary=True)

    def get_recognition_history(self):
        """Obtiene el historial de reconocimientos."""
        sql = "SELECT fecha_hora, nombre, rut, dispositivo_id FROM historial_reconocimiento ORDER BY fecha_hora DESC"
        return self._execute_query(sql, fetch='all', dictionary=True)

    def get_suspects(self):
        """Obtiene todas las imágenes y datos de sospechosos."""
        sql = "SELECT id, imagen_data, fecha_hora, dispositivo_id FROM sospechosos ORDER BY fecha_hora DESC"
        return self._execute_query(sql, fetch='all', dictionary=True)

    def register_person(self, nombre, fecha_nac, edad, rut, relacion, fecha_reg, img_data, encoding_data):
        """Registra una nueva persona en la base de datos."""
        sql_img = "INSERT INTO imagenes_reconocimiento (imagen_data, encoding_data) VALUES (%s, %s)"
        id_imagen = self._execute_query(sql_img, (img_data, encoding_data))

        sql_rec = "INSERT INTO reconocimiento (nombre_completo, fecha_nacimiento, edad, rut, relacion, fecha_registro, id_imagen) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        self._execute_query(sql_rec, (nombre, fecha_nac, edad, rut, relacion, fecha_reg, id_imagen))

    def update_person(self, id_imagen, nombre, fecha_nac, edad, relacion):
        """Actualiza los datos de una persona existente."""
        sql = "UPDATE reconocimiento SET nombre_completo = %s, fecha_nacimiento = %s, edad = %s, relacion = %s WHERE id_imagen = %s"
        self._execute_query(sql, (nombre, fecha_nac, edad, relacion, id_imagen))

    def delete_person(self, id_imagen):
        """Elimina a una persona y su imagen asociada. La FK en la BD se encarga del resto."""
        sql = "DELETE FROM imagenes_reconocimiento WHERE id = %s"
        self._execute_query(sql, (id_imagen,))

    def delete_suspect(self, id_sospechoso):
        """Elimina una foto de un sospechoso."""
        sql = "DELETE FROM sospechosos WHERE id = %s"
        self._execute_query(sql, (id_sospechoso,))

    def log_recognition(self, nombre, rut, dispositivo):
        """Registra un evento de reconocimiento en el historial."""
        sql = "INSERT INTO historial_reconocimiento (nombre, rut, fecha_hora, dispositivo_id) VALUES (%s, %s, %s, %s)"
        self._execute_query(sql, (nombre, rut, datetime.now(), dispositivo))

    def log_suspect(self, frame_data, dispositivo):
        """Guarda la imagen de un sospechoso en la base de datos."""
        sql = "INSERT INTO sospechosos (imagen_data, fecha_hora, dispositivo_id) VALUES (%s, %s, %s)"
        self._execute_query(sql, (frame_data, datetime.now(), dispositivo))

    def check_rut_exists(self, rut):
        """Verifica si un RUT ya está registrado."""
        sql = "SELECT COUNT(*) as count FROM reconocimiento WHERE rut = %s"
        result = self._execute_query(sql, (rut,), fetch='one', dictionary=True)
        return result['count'] > 0 if result else False

    def get_suspect_count(self):
        """Cuenta cuántos sospechosos no revisados hay."""
        sql = "SELECT COUNT(*) as count FROM sospechosos"
        result = self._execute_query(sql, fetch='one', dictionary=True)
        return result['count'] if result else 0

    def update_system_status(self):
        """Actualiza la marca de tiempo del sistema para sincronización entre clientes."""
        sql = "UPDATE estado_sistema SET ultima_actualizacion = NOW() WHERE id = 1"
        self._execute_query(sql)

    def close(self):
        """Cierra la conexión a la base de datos."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("🔌 Conexión a MySQL cerrada.")
