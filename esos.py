import mysql.connector
import tkinter as tk
from PIL import Image, ImageTk
import io
import numpy as np
import cv2

# Conexión a la base de datos
conexion = mysql.connector.connect(
    host="192.168.1.122",
    user="ojodigital",
    password="feria2025",
    database="ojodigital"
)

cursor = conexion.cursor()
cursor.execute("SELECT nombre, imagen FROM reconocimiento")
registros = cursor.fetchall()

# Crear ventana Tkinter
root = tk.Tk()
root.title("Imágenes Registradas en la Base de Datos")

# Crear un canvas con scrollbar si hay muchas imágenes
canvas = tk.Canvas(root, width=800, height=600)
scroll_y = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
frame = tk.Frame(canvas)

# Mostrar imágenes
for i, (nombre, imagen_blob) in enumerate(registros):
    np_array = np.frombuffer(imagen_blob, np.uint8)
    imagen_cv = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

    if imagen_cv is not None:
        imagen_rgb = cv2.cvtColor(imagen_cv, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(imagen_rgb)
        img_pil = img_pil.resize((200, 200))  # Tamaño fijo
        imgtk = ImageTk.PhotoImage(img_pil)

        label_img = tk.Label(frame, image=imgtk)
        label_img.image = imgtk  # Referencia para que no se borre
        label_img.grid(row=i, column=0, padx=10, pady=10)

        label_text = tk.Label(frame, text=nombre, font=("Arial", 12))
        label_text.grid(row=i, column=1, padx=10)

    else:
        print(f"⚠️ No se pudo mostrar la imagen de {nombre}")

# Configurar canvas y scroll
canvas.create_window((0, 0), window=frame, anchor='nw')
canvas.update_idletasks()
canvas.configure(scrollregion=canvas.bbox('all'), yscrollcommand=scroll_y.set)
canvas.pack(side='left', fill='both', expand=True)
scroll_y.pack(side='right', fill='y')

root.mainloop()
cursor.close()
conexion.close()
