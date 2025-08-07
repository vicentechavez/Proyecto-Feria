# face_processor.py
# Este módulo contiene toda la lógica de procesamiento facial con face_recognition.

import face_recognition
import numpy as np
import cv2

def extract_face_encoding(frame):
    """
    Detecta el rostro más grande en un frame, lo recorta y extrae su encoding.
    Devuelve el encoding y la imagen del rostro recortado.
    """
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    locs = face_recognition.face_locations(rgb_frame)
    if not locs:
        return None, None  # No se encontró rostro

    # Encuentra el rostro más grande basado en el área del cuadro delimitador
    main_face_loc = max(locs, key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]))
    
    top, right, bottom, left = main_face_loc
    face_image = frame[top:bottom, left:right]
    
    encodings = face_recognition.face_encodings(rgb_frame, [main_face_loc])
    return encodings[0] if encodings else None, face_image

def find_and_compare_faces(frame, known_encodings_dict, tolerance=0.5):
    """
    Busca todos los rostros en un frame, los compara con una lista de encodings conocidos
    y devuelve una lista de resultados con nombres y ubicaciones.
    """
    if not known_encodings_dict:
        return []

    # Redimensiona el frame para un procesamiento más rápido
    rgb_small_frame = cv2.cvtColor(cv2.resize(frame, (0, 0), fx=0.25, fy=0.25), cv2.COLOR_BGR2RGB)
    
    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    known_names = list(known_encodings_dict.keys())
    known_encodings = list(known_encodings_dict.values())
    
    results = []
    for encoding, loc in zip(face_encodings, face_locations):
        matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=tolerance)
        name = "Desconocido"

        if True in matches:
            # Encuentra el mejor match basado en la distancia (menor es mejor)
            face_distances = face_recognition.face_distance(known_encodings, encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_names[best_match_index]
        
        # Escala la ubicación de vuelta al tamaño original del frame
        top, right, bottom, left = [c * 4 for c in loc]
        results.append({'name': name, 'location': (top, right, bottom, left)})
        
    return results
