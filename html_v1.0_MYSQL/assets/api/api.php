<?php
// api.php

// --- 1. CONFIGURACIÓN DE LA BASE DE DATOS ---
$db_host = 'localhost';
$db_user = 'root';
$db_pass = ''; // La contraseña por defecto de XAMPP es vacía.
$db_name = 'ojodigital';

// --- 2. CABECERAS Y CONEXIÓN ---
// Permite peticiones desde cualquier origen (CORS). En producción, deberías restringirlo a tu dominio.
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json; charset=UTF-8");
header("Access-Control-Allow-Methods: POST");
header("Access-Control-Allow-Headers: Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With");

// Crear la conexión a la base de datos
$conn = new mysqli($db_host, $db_user, $db_pass, $db_name);

// Verificar la conexión
if ($conn->connect_error) {
    echo json_encode(['success' => false, 'message' => 'Error de conexión con la base de datos.']);
    exit();
}

// --- 3. GESTIÓN DE RUTAS (ACCIONES) ---
$action = isset($_GET['action']) ? $_GET['action'] : '';
$data = json_decode(file_get_contents("php://input"));

switch ($action) {
    case 'register':
        handle_register($conn, $data);
        break;
    case 'login':
        handle_login($conn, $data);
        break;
    case 'contact':
        handle_contact($conn, $data);
        break;
    default:
        echo json_encode(['success' => false, 'message' => 'Acción no válida.']);
        break;
}

$conn->close();

// --- 4. FUNCIONES PARA CADA ACCIÓN ---

function handle_register($conn, $data) {
    if (empty($data->email) || empty($data->password)) {
        echo json_encode(['success' => false, 'message' => 'Correo y contraseña son obligatorios.']);
        return;
    }

    $email = $data->email;
    // ¡Seguridad! Encriptar la contraseña antes de guardarla.
    $password_hash = password_hash($data->password, PASSWORD_BCRYPT);

    $sql = "INSERT INTO users (email, password) VALUES (?, ?)";
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("ss", $email, $password_hash);

    if ($stmt->execute()) {
        echo json_encode(['success' => true, 'message' => 'Usuario registrado exitosamente.']);
    } else {
        // Manejar error de correo duplicado
        if ($conn->errno == 1062) {
            echo json_encode(['success' => false, 'message' => 'El correo electrónico ya está registrado.']);
        } else {
            echo json_encode(['success' => false, 'message' => 'Error al registrar el usuario.']);
        }
    }
    $stmt->close();
}

function handle_login($conn, $data) {
    if (empty($data->email) || empty($data->password)) {
        echo json_encode(['success' => false, 'message' => 'Correo y contraseña son obligatorios.']);
        return;
    }

    $email = $data->email;
    $password = $data->password;

    $sql = "SELECT email, password FROM users WHERE email = ?";
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("s", $email);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($result->num_rows === 1) {
        $user = $result->fetch_assoc();
        // Verificar que la contraseña ingresada coincida con la encriptada
        if (password_verify($password, $user['password'])) {
            echo json_encode(['success' => true, 'message' => 'Inicio de sesión exitoso.', 'user' => ['email' => $user['email']]]);
        } else {
            echo json_encode(['success' => false, 'message' => 'Contraseña incorrecta.']);
        }
    } else {
        echo json_encode(['success' => false, 'message' => 'El usuario no existe.']);
    }
    $stmt->close();
}

function handle_contact($conn, $data) {
    if (empty($data->name) || empty($data->email) || empty($data->message)) {
        echo json_encode(['success' => false, 'message' => 'Todos los campos son obligatorios.']);
        return;
    }

    $name = $data->name;
    $email = $data->email;
    $message = $data->message;

    $sql = "INSERT INTO messages (name, email, message) VALUES (?, ?, ?)";
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("sss", $name, $email, $message);

    if ($stmt->execute()) {
        echo json_encode(['success' => true, 'message' => 'Mensaje enviado exitosamente.']);
    } else {
        echo json_encode(['success' => false, 'message' => 'Error al enviar el mensaje.']);
    }
    $stmt->close();
}
?>
