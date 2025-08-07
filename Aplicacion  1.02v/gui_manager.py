# gui_manager.py
# Este módulo se encarga de crear y gestionar todas las ventanas de la UI.

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from PIL import Image, ImageTk
import io
import config # Para la contraseña de admin
import cv2 # Necesario para la preview de la cámara

# --- Funciones de Utilidad ---
def validar_rut(rut_completo):
    rut_completo = rut_completo.upper().replace(".", "").replace("-", "").strip()
    if not (rut_completo[:-1].isdigit() and (rut_completo[-1].isdigit() or rut_completo[-1] == 'K')): return False
    cuerpo, dv = rut_completo[:-1], rut_completo[-1]
    try:
        dv_calculado = str(11 - sum(int(digit) * ((i % 6) + 2) for i, digit in enumerate(reversed(cuerpo))) % 11)
        if dv_calculado == '11': dv_calculado = '0'
        if dv_calculado == '10': dv_calculado = 'K'
        return dv == dv_calculado
    except ValueError: return False

def formatear_rut_entry(entry_widget):
    current_text = entry_widget.get().replace(".", "").replace("-", "").strip()
    # FIX: Añadir una comprobación para un string vacío para prevenir el IndexError
    if not current_text:
        return
    if not all(c.isdigit() or (i == len(current_text) - 1 and c.upper() == 'K') for i, c in enumerate(current_text)): return
    body, dv = current_text[:-1], current_text[-1].upper()
    formatted_body = "".join(reversed([char + ("." if i > 0 and i % 3 == 0 else "") for i, char in enumerate(reversed(body))]))
    formatted_rut = f"{formatted_body}-{dv}" if body else current_text
    if entry_widget.get() != formatted_rut:
        entry_widget.delete(0, tk.END); entry_widget.insert(0, formatted_rut); entry_widget.icursor(tk.END)

def centrar_ventana(ventana_hija, ventana_padre):
    ventana_hija.update_idletasks()
    x = ventana_padre.winfo_x() + (ventana_padre.winfo_width() // 2) - (ventana_hija.winfo_width() // 2)
    y = ventana_padre.winfo_y() + (ventana_padre.winfo_height() // 2) - (ventana_hija.winfo_height() // 2)
    ventana_hija.geometry(f"+{x}+{y}")

# --- Ventana de Captura con Countdown ---
def show_capture_window(parent, face_capture_func, on_capture_complete):
    capture_window = tk.Toplevel(parent)
    capture_window.title("Preparando Captura")
    capture_window.geometry("640x580")
    capture_window.transient(parent)
    capture_window.grab_set()
    centrar_ventana(capture_window, parent)
    capture_window.configure(bg="black")

    video_label = tk.Label(capture_window, bg="black")
    video_label.pack(pady=10)

    message_label = tk.Label(capture_window, text="¡Prepárate!", font=("Segoe UI", 20, "bold"), fg="white", bg="black")
    message_label.pack(pady=10)

    countdown_label = tk.Label(capture_window, text="", font=("Segoe UI", 40, "bold"), fg="yellow", bg="black")
    countdown_label.pack(pady=10)

    is_running = True

    def update_video_feed():
        if not is_running: return
        ret, frame = face_capture_func(get_frame_only=True)
        if ret:
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            imgtk = ImageTk.PhotoImage(image=img)
            video_label.imgtk = imgtk
            video_label.configure(image=imgtk)
        capture_window.after(15, update_video_feed)

    def run_countdown(count):
        nonlocal is_running
        if not is_running: return
        
        if count > 0:
            message_label.config(text="Sonríe para el registro...")
            countdown_label.config(text=str(count))
            capture_window.after(1000, lambda: run_countdown(count - 1))
        else:
            countdown_label.config(text="¡Listo!", fg="lightgreen")
            message_label.config(text="Procesando...")
            capture_window.update()
            
            # Captura final
            encoding, face_image = face_capture_func()
            on_capture_complete(encoding, face_image)
            
            is_running = False
            capture_window.destroy()

    def on_close():
        nonlocal is_running
        is_running = False
        on_capture_complete(None, None) # Señal de cancelación
        capture_window.destroy()

    capture_window.protocol("WM_DELETE_WINDOW", on_close)
    
    update_video_feed()
    run_countdown(3)


# --- Ventana de Registro ---
def show_registration_window(parent, db_handler, face_capture_func, on_success_callback, style_config):
    """Muestra la ventana para registrar una nueva persona."""
    
    ventana_registro = tk.Toplevel(parent)
    ventana_registro.title("Registrar Persona")
    ventana_registro.geometry("400x400")
    ventana_registro.configure(bg=style_config['bg'])
    ventana_registro.transient(parent)
    ventana_registro.grab_set()
    centrar_ventana(ventana_registro, parent)

    entradas = {}

    def start_registration_process():
        try:
            # Validar datos primero
            nombre = entradas["nombre_completo"].get().strip()
            rut = entradas["rut"].get().strip()
            relacion = entradas["relacion"].get()
            
            if not all([nombre, relacion != "Selecciona una opción", rut]): raise ValueError("Todos los campos son obligatorios.")
            if not validar_rut(rut): raise ValueError("El RUT ingresado no es válido.")
            if db_handler.check_rut_exists(rut): raise ValueError("El RUT ya está registrado.")

            # Ocultar ventana de registro y mostrar la de captura
            ventana_registro.withdraw()
            show_capture_window(parent, face_capture_func, continue_registration)

        except ValueError as e:
            messagebox.showwarning("Datos Inválidos", str(e), parent=ventana_registro)

    def continue_registration(encoding, face_image):
        # Esta función se ejecuta cuando la ventana de captura se cierra
        if encoding is None or face_image is None:
            print("Registro cancelado por el usuario.")
            ventana_registro.destroy() # Cerrar la ventana de registro si se cancela la captura
            return

        try:
            nombre = entradas["nombre_completo"].get().strip()
            rut = entradas["rut"].get().strip()
            relacion = entradas["relacion"].get()
            fecha_nac_dt = datetime.strptime(f"{entradas['anio_nacimiento'].get()}-{entradas['mes_nacimiento'].get()}-{entradas['dia_nacimiento'].get()}", "%Y-%m-%d")

            _, buffer_img = cv2.imencode('.jpg', face_image)
            img_data = buffer_img.tobytes()
            encoding_data = encoding.tobytes()
            
            edad = datetime.now().year - fecha_nac_dt.year - ((datetime.now().month, datetime.now().day) < (fecha_nac_dt.month, fecha_nac_dt.day))
            
            db_handler.register_person(nombre, fecha_nac_dt.strftime("%Y-%m-%d"), edad, rut, relacion, datetime.now().strftime("%Y-%m-%d"), img_data, encoding_data)
            
            messagebox.showinfo("Registro Exitoso", f"{nombre} ha sido registrado.", parent=parent)
            ventana_registro.destroy()
            on_success_callback()

        except Exception as e:
            messagebox.showerror("Error Inesperado", f"Ocurrió un error durante el registro final: {e}", parent=parent)
            ventana_registro.destroy()


    # Widgets de la ventana de registro
    ttk.Label(ventana_registro, text="Nombre Completo:", style=style_config['label_style']).pack(pady=5)
    entrada_nombre = ttk.Entry(ventana_registro, style=style_config['entry_style'])
    entrada_nombre.pack(pady=5, padx=20, fill='x')
    entradas["nombre_completo"] = entrada_nombre
    
    ttk.Label(ventana_registro, text="Fecha de Nacimiento:", style=style_config['label_style']).pack(pady=5)
    frame_fecha = ttk.Frame(ventana_registro, style=style_config['frame_style'])
    frame_fecha.pack(pady=5, padx=20, fill='x')
    
    combo_dia = ttk.Combobox(frame_fecha, values=[f"{i:02d}" for i in range(1, 32)], width=5, state="readonly", style=style_config['combobox_style']); combo_dia.set("Día"); combo_dia.pack(side=tk.LEFT, padx=2)
    entradas["dia_nacimiento"] = combo_dia
    combo_mes = ttk.Combobox(frame_fecha, values=[f"{i:02d}" for i in range(1, 13)], width=5, state="readonly", style=style_config['combobox_style']); combo_mes.set("Mes"); combo_mes.pack(side=tk.LEFT, padx=2)
    entradas["mes_nacimiento"] = combo_mes
    current_year = datetime.now().year
    combo_anio = ttk.Combobox(frame_fecha, values=[str(i) for i in range(current_year, current_year - 100, -1)], width=7, state="readonly", style=style_config['combobox_style']); combo_anio.set("Año"); combo_anio.pack(side=tk.LEFT, padx=2)
    entradas["anio_nacimiento"] = combo_anio
    
    ttk.Label(ventana_registro, text="RUT:", style=style_config['label_style']).pack(pady=5)
    entrada_rut = ttk.Entry(ventana_registro, style=style_config['entry_style'])
    entrada_rut.pack(pady=5, padx=20, fill='x')
    entrada_rut.bind("<KeyRelease>", lambda e: formatear_rut_entry(entrada_rut))
    entradas["rut"] = entrada_rut
    
    ttk.Label(ventana_registro, text="Relación:", style=style_config['label_style']).pack(pady=5)
    combo_relacion = ttk.Combobox(ventana_registro, values=["Dueño", "Hijo", "Esposa", "Empleado", "Visita", "Otro"], state="readonly", style=style_config['combobox_style'])
    combo_relacion.set("Selecciona una opción")
    combo_relacion.pack(pady=5, padx=20, fill='x')
    entradas["relacion"] = combo_relacion
    
    ttk.Button(ventana_registro, text="Continuar a Captura de Foto", command=start_registration_process, style='Green.TButton').pack(pady=15)

# --- Ventana de Edición de Persona ---
def show_edit_person_window(parent, db_handler, person_data, on_success_callback, style_config):
    id_imagen, nombre, rut, fecha_nac_str, _, relacion, _ = person_data

    ventana_editar = tk.Toplevel(parent)
    ventana_editar.title(f"Editando a {nombre}")
    ventana_editar.geometry("400x380")
    ventana_editar.configure(bg=style_config['bg'])
    ventana_editar.transient(parent)
    ventana_editar.grab_set()
    centrar_ventana(ventana_editar, parent)

    entradas = {}

    def _save_changes():
        try:
            nombre_nuevo = entradas["nombre_completo"].get().strip()
            relacion_nueva = entradas["relacion"].get()

            if not nombre_nuevo or relacion_nueva == "Selecciona una opción":
                raise ValueError("El nombre y la relación no pueden estar vacíos.")

            fecha_nac_str_nueva = f"{entradas['anio_nacimiento'].get()}-{entradas['mes_nacimiento'].get()}-{entradas['dia_nacimiento'].get()}"
            fecha_nac_dt_nueva = datetime.strptime(fecha_nac_str_nueva, "%Y-%m-%d")
            
            edad_nueva = datetime.now().year - fecha_nac_dt_nueva.year - ((datetime.now().month, datetime.now().day) < (fecha_nac_dt_nueva.month, fecha_nac_dt_nueva.day))

            db_handler.update_person(id_imagen, nombre_nuevo, fecha_nac_dt_nueva.strftime('%Y-%m-%d'), edad_nueva, relacion_nueva)
            db_handler.update_system_status()
            on_success_callback()

            ventana_editar.destroy()
            messagebox.showinfo("Éxito", "Los datos han sido actualizados.", parent=parent)

        except ValueError as e:
            messagebox.showerror("Error de Datos", str(e), parent=ventana_editar)
        except Exception as e:
            messagebox.showerror("Error Inesperado", f"No se pudo actualizar el registro: {e}", parent=ventana_editar)

    # Widgets
    ttk.Label(ventana_editar, text="Nombre Completo:", style=style_config['label_style']).pack(pady=(10, 2))
    entrada_nombre = ttk.Entry(ventana_editar, style=style_config['entry_style'])
    entrada_nombre.pack(pady=2, padx=20, fill='x')
    entrada_nombre.insert(0, nombre)
    entradas["nombre_completo"] = entrada_nombre

    ttk.Label(ventana_editar, text=f"RUT: {rut} (No editable)", style=style_config['label_style']).pack(pady=(10, 2))

    ttk.Label(ventana_editar, text="Fecha de Nacimiento:", style=style_config['label_style']).pack(pady=(10, 2))
    frame_fecha = ttk.Frame(ventana_editar, style=style_config['frame_style'])
    frame_fecha.pack(pady=2, padx=20, fill='x', expand=True)

    try:
        fecha_dt = datetime.strptime(fecha_nac_str, '%Y-%m-%d')
        dia_actual, mes_actual, anio_actual = f"{fecha_dt.day:02d}", f"{fecha_dt.month:02d}", str(fecha_dt.year)
    except (ValueError, TypeError):
        dia_actual, mes_actual, anio_actual = "Día", "Mes", "Año"

    combo_dia = ttk.Combobox(frame_fecha, values=[f"{i:02d}" for i in range(1, 32)], width=5, state="readonly", style=style_config['combobox_style']); combo_dia.set(dia_actual); combo_dia.pack(side=tk.LEFT, padx=2, expand=True)
    entradas["dia_nacimiento"] = combo_dia
    combo_mes = ttk.Combobox(frame_fecha, values=[f"{i:02d}" for i in range(1, 13)], width=5, state="readonly", style=style_config['combobox_style']); combo_mes.set(mes_actual); combo_mes.pack(side=tk.LEFT, padx=2, expand=True)
    entradas["mes_nacimiento"] = combo_mes
    current_year = datetime.now().year
    combo_anio = ttk.Combobox(frame_fecha, values=[str(i) for i in range(current_year, current_year - 100, -1)], width=7, state="readonly", style=style_config['combobox_style']); combo_anio.set(anio_actual); combo_anio.pack(side=tk.LEFT, padx=2, expand=True)
    entradas["anio_nacimiento"] = combo_anio

    ttk.Label(ventana_editar, text="Relación:", style=style_config['label_style']).pack(pady=(10, 2))
    combo_relacion = ttk.Combobox(ventana_editar, values=["Dueño", "Hijo", "Esposa", "Empleado", "Visita", "Otro"], state="readonly", style=style_config['combobox_style'])
    combo_relacion.set(relacion)
    combo_relacion.pack(pady=2, padx=20, fill='x')
    entradas["relacion"] = combo_relacion

    ttk.Button(ventana_editar, text="Guardar Cambios", command=_save_changes, style='Green.TButton').pack(pady=20)


# --- Ventana de Login de Admin ---
def show_admin_login_window(parent, on_success_callback):
    ventana_login = tk.Toplevel(parent)
    ventana_login.title("Acceso Admin")
    ventana_login.geometry("300x150")
    ventana_login.transient(parent)
    ventana_login.grab_set()
    centrar_ventana(ventana_login, parent)

    def verificar():
        if entry_pass.get() == config.ADMIN_PASSWORD:
            ventana_login.destroy()
            on_success_callback()
        else:
            messagebox.showerror("Acceso Denegado", "Contraseña incorrecta.", parent=ventana_login)

    ttk.Label(ventana_login, text="Contraseña:").pack(pady=10)
    entry_pass = ttk.Entry(ventana_login, show="*")
    entry_pass.pack(pady=5, padx=20, fill='x')
    entry_pass.bind("<Return>", lambda e: verificar())
    ttk.Button(ventana_login, text="Ingresar", command=verificar, style='Blue.TButton').pack(pady=10)

# --- Panel de Administración ---
def show_admin_panel_window(parent, db_handler, on_data_changed_callback, style_config):
    ventana_admin = tk.Toplevel(parent)
    ventana_admin.title("Panel de Administración")
    ventana_admin.geometry("900x600")
    ventana_admin.transient(parent)
    ventana_admin.grab_set()
    centrar_ventana(ventana_admin, parent)

    def cargar_datos():
        for item in tree.get_children(): tree.delete(item)
        personas = db_handler.get_data_for_admin_panel()
        if personas:
            for p in personas:
                tree.insert("", "end", values=(p['id_imagen'], p['nombre_completo'], p['rut'], p['fecha_nacimiento'].strftime('%Y-%m-%d'), p['edad'], p['relacion'], p['fecha_registro'].strftime('%Y-%m-%d')))

    def eliminar_persona():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Sin Selección", "Selecciona una persona para eliminar.", parent=ventana_admin)
            return
        
        values = tree.item(selected_item, 'values')
        id_imagen, nombre = values[0], values[1]
        if messagebox.askyesno("Confirmar", f"¿Eliminar a '{nombre}'? Esta acción es permanente.", parent=ventana_admin):
            db_handler.delete_person(id_imagen)
            db_handler.update_system_status()
            on_data_changed_callback()
            cargar_datos()
            messagebox.showinfo("Éxito", f"'{nombre}' ha sido eliminado.", parent=ventana_admin)

    def editar_persona():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Sin Selección", "Por favor, selecciona una persona para editar.", parent=ventana_admin)
            return
        
        person_data = tree.item(selected_item, 'values')
        # Llamar a la nueva ventana de edición
        show_edit_person_window(ventana_admin, db_handler, person_data, 
                                lambda: [on_data_changed_callback(), cargar_datos()], 
                                style_config)


    frame_botones = ttk.Frame(ventana_admin, padding=10)
    frame_botones.pack(fill='x')
    ttk.Button(frame_botones, text="Eliminar Persona", command=eliminar_persona, style='Blue.TButton').pack(side=tk.LEFT, padx=5)
    ttk.Button(frame_botones, text="Editar Persona", command=editar_persona, style='Blue.TButton').pack(side=tk.LEFT, padx=5)
    ttk.Button(frame_botones, text="Recargar", command=cargar_datos, style='Blue.TButton').pack(side=tk.LEFT, padx=5)

    cols = ("ID_Imagen", "Nombre", "RUT", "F. Nac", "Edad", "Relación", "F. Reg")
    tree = ttk.Treeview(ventana_admin, columns=cols, show="headings")
    for col in cols: tree.heading(col, text=col)
    tree.pack(expand=True, fill="both", padx=10, pady=10)
    
    cargar_datos()

# --- Ventana de Historial ---
def show_history_window(parent, db_handler):
    ventana_historial = tk.Toplevel(parent)
    ventana_historial.title("Historial de Reconocimiento")
    ventana_historial.geometry("700x500")
    centrar_ventana(ventana_historial, parent)
    
    tree = ttk.Treeview(ventana_historial, columns=("Fecha", "Hora", "Nombre", "RUT", "Dispositivo"), show="headings")
    for col in ("Fecha", "Hora", "Nombre", "RUT", "Dispositivo"): tree.heading(col, text=col)
    tree.pack(expand=True, fill="both", padx=10, pady=10)
    
    historial = db_handler.get_recognition_history()
    if historial:
        for row in historial:
            tree.insert("", "end", values=(row['fecha_hora'].strftime("%Y-%m-%d"), row['fecha_hora'].strftime("%H:%M:%S"), row['nombre'], row['rut'], row.get('dispositivo_id', 'N/A')))

# --- Ventana de Sospechosos ---
def show_suspects_window(parent, db_handler):
    ventana = tk.Toplevel(parent)
    ventana.title("Galería de Sospechosos")
    ventana.geometry("850x650")
    centrar_ventana(ventana, parent)

    canvas = tk.Canvas(ventana)
    scrollbar = ttk.Scrollbar(ventana, orient="vertical", command=canvas.yview)
    frame_contenido = ttk.Frame(canvas, padding=10)
    
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.create_window((0, 0), window=frame_contenido, anchor="nw")
    frame_contenido.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    def cargar_fotos():
        for widget in frame_contenido.winfo_children(): widget.destroy()
        sospechosos = db_handler.get_suspects()
        if not sospechosos:
            ttk.Label(frame_contenido, text="No hay fotos de sospechosos.").pack()
            return

        for idx, row in enumerate(sospechosos):
            item_frame = ttk.Frame(frame_contenido, padding=5, relief="solid", borderwidth=1)
            item_frame.grid(row=idx // 4, column=idx % 4, padx=10, pady=10)
            
            img = Image.open(io.BytesIO(row['imagen_data']))
            img.thumbnail((150, 150), Image.LANCZOS)
            imgtk = ImageTk.PhotoImage(img)
            
            lbl_img = tk.Label(item_frame, image=imgtk); lbl_img.image = imgtk; lbl_img.pack(pady=5)
            ttk.Label(item_frame, text=row['fecha_hora'].strftime("%d-%m-%Y %H:%M:%S")).pack()
            ttk.Label(item_frame, text=f"Dispositivo: {row.get('dispositivo_id', 'N/A')}", font=('Segoe UI', 8)).pack()
            
            def eliminar_accion(id_sospechoso=row['id']):
                if messagebox.askyesno("Confirmar", "¿Eliminar esta foto?", parent=ventana):
                    db_handler.delete_suspect(id_sospechoso)
                    cargar_fotos()

            ttk.Button(item_frame, text="Eliminar", command=eliminar_accion, style='Blue.TButton').pack(pady=5)
    
    cargar_fotos()
