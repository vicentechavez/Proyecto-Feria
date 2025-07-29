import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
from datetime import datetime
import csv

# Función: mostrar ventana de registro y ocultar bienvenida
def mostrar_registro():
    ventana_inicio.pack_forget()
    ventana_registro.pack(fill="both", expand=True)

# Función: registrar datos (sin cámara activada)
def registrar_rostro():
    nombre = entry_nombre.get().strip()
    edad = entry_edad.get().strip()
    rut = entry_rut.get().strip()
    fecha_nac = entry_fecha.get().strip()
    fecha_ingreso = datetime.now().strftime("%Y-%m-%d")

    if not nombre or not edad or not rut or not fecha_nac:
        messagebox.showwarning("Campos incompletos", "Por favor completa todos los campos.")
        return
    if not edad.isdigit():
        messagebox.showerror("Edad inválida", "La edad debe ser un número.")
        return

    # Guardar datos en CSV
    with open("registro_datos.csv", mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([nombre, edad, rut, fecha_nac, fecha_ingreso])

    messagebox.showinfo("Registro exitoso", f"{nombre} registrado correctamente.")
    limpiar_campos()

# Limpiar campos del formulario
def limpiar_campos():
    entry_nombre.delete(0, tk.END)
    entry_edad.delete(0, tk.END)
    entry_rut.delete(0, tk.END)
    entry_fecha.delete(0, tk.END)

# Cerrar aplicación
def cerrar_app():
    root.destroy()

# Colores bonitos sin negro ni blanco
color_bg = "#F0E5D8"   # beige claro
color_fg = "#6B4226"   # marrón oscuro

root = tk.Tk()
root.title("Sistema de Registro Facial")
root.geometry("700x600")
root.configure(bg=color_bg)
root.protocol("WM_DELETE_WINDOW", cerrar_app)

# ─── VENTANA DE INICIO CON FONDO IMAGEN ───
ventana_inicio = tk.Frame(root, width=700, height=600)
ventana_inicio.pack_propagate(False)  # Evita que el tamaño cambie según widgets
ventana_inicio.pack(fill="both", expand=True)

# Cargar la imagen de fondo
# Cambia "fondo_bienvenida.jpg" por el nombre de tu archivo de imagen
imagen_fondo = Image.open("fondo inicio.jpg")  # <-- MODIFICA AQUÍ EL NOMBRE DE TU IMAGEN
imagen_fondo = imagen_fondo.resize((700, 600), Image.ANTIALIAS)
imagen_fondo_tk = ImageTk.PhotoImage(imagen_fondo)

# Label para mostrar la imagen y ponerla de fondo
label_fondo = tk.Label(ventana_inicio, image=imagen_fondo_tk)
label_fondo.place(x=0, y=0, relwidth=1, relheight=1)

# Widgets encima del fondo
label_bienvenida = tk.Label(
    ventana_inicio,
    text="Bienvenido al Sistema de Registro Facial",
    font=("Arial", 20, "bold"),
    fg=color_fg,
    bg="#FFFFFFB0"  # Fondo semitransparente para mejorar lectura
)
label_bienvenida.pack(pady=30)

btn_ir_registro = tk.Button(
    ventana_inicio,
    text="Iniciar Registro",
    command=mostrar_registro,
    bg="#D4A373",
    fg="white",
    font=("Arial", 16, "bold"),
    activebackground="#B5838D",
    activeforeground="white",
    padx=20,
    pady=10,
    relief="raised",
    bd=3
)
btn_ir_registro.pack(pady=20)

# ─── VENTANA DE REGISTRO ───
ventana_registro = tk.Frame(root, bg=color_bg)

# Formulario
form_frame = tk.Frame(ventana_registro, bg=color_bg)
form_frame.pack(pady=10)

tk.Label(form_frame, text="Nombre:", bg=color_bg, fg=color_fg).grid(row=0, column=0, sticky="e", pady=5)
entry_nombre = tk.Entry(form_frame, bg="#D4A373", fg="white", width=30)
entry_nombre.grid(row=0, column=1, pady=5)

tk.Label(form_frame, text="Edad:", bg=color_bg, fg=color_fg).grid(row=1, column=0, sticky="e", pady=5)
entry_edad = tk.Entry(form_frame, bg="#D4A373", fg="white", width=30)
entry_edad.grid(row=1, column=1, pady=5)

tk.Label(form_frame, text="RUT:", bg=color_bg, fg=color_fg).grid(row=2, column=0, sticky="e", pady=5)
entry_rut = tk.Entry(form_frame, bg="#D4A373", fg="white", width=30)
entry_rut.grid(row=2, column=1, pady=5)

tk.Label(form_frame, text="Fecha de nacimiento:", bg=color_bg, fg=color_fg).grid(row=3, column=0, sticky="e", pady=5)
entry_fecha = tk.Entry(form_frame, bg="#D4A373", fg="white", width=30)
entry_fecha.grid(row=3, column=1, pady=5)

btn_registrar = tk.Button(
    ventana_registro,
    text="Registrar",
    command=registrar_rostro,
    bg="#6B4226",
    fg="white",
    font=("Arial", 14, "bold"),
    padx=10,
    pady=5
)
btn_registrar.pack(pady=20)

root.mainloop()
