<?php
/**
 * api.php
 *
 * API para gestionar usuarios (registro, login) y mensajes de contacto.
 * Versión profesional con manejo de errores, validación y seguridad mejorada.
 */

// --- 1. CONFIGURACIÓN DE LA APLICACIÓN ---
// Constantes para la conexión a la base de datos y reglas de negocio.
define('DB_HOST', 'localhost');
define('DB_USER', 'root');
define('DB_PASS', ''); // Contraseña de la base de datos (vacía por defecto en XAMPP).
define('DB_NAME', 'ojodigital');
define('PASSWORD_MIN_LENGTH', 8);


// --- 2. HELPERS Y CONFIGURACIÓN INICIAL ---

/**
 * Envía una respuesta JSON estandarizada y termina la ejecución del script.
 *
 * @param bool $success Indica si la operación fue exitosa.
 * @param string $message Mensaje descriptivo.
 * @param array|null $data Datos adicionales para enviar en la respuesta, se anidarán bajo la clave "data".
 * @param int $statusCode Código de estado HTTP (ej. 200 OK, 400 Bad Request).
 * @return void
 */
function sendJsonResponse(bool $success, string $message, ?array $data = null, int $statusCode = 200): void
{
    header("Content-Type: application/json; charset=UTF-8");
    http_response_code($statusCode);
    
    $response = ['success' => $success, 'message' => $message];
    if ($data !== null) {
        $response['data'] = $data;
    }
    
    echo json_encode($response);
    exit();
}

// Configurar cabeceras para CORS (Cross-Origin Resource Sharing).
// ¡IMPORTANTE! En producción, restringir el origen a tu dominio: header("Access-Control-Allow-Origin: https://tudominio.com");
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With");

// Gestionar peticiones pre-vuelo (OPTIONS) para la verificación de CORS.
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Forzar que la API solo acepte peticiones POST para mayor seguridad.
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    sendJsonResponse(false, 'Método no permitido. Solo se aceptan peticiones POST.', null, 405);
}

// Habilitar el reporte de excepciones para errores de MySQLi.
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);


// --- 3. EJECUCIÓN PRINCIPAL ---

// Conexión a la base de datos.
try {
    $conn = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);
    $conn->set_charset("utf8mb4");
} catch (mysqli_sql_exception $e) {
    // Error crítico: no se pudo conectar a la base de datos.
    sendJsonResponse(false, 'Error de conexión con la base de datos.', null, 500);
}

// Obtener los datos JSON de la petición y la acción de la URL.
$data = json_decode(file_get_contents("php://input"));
$action = $_GET['action'] ?? '';

// Router simple para dirigir la petición a la función correspondiente.
switch ($action) {
    case 'register':
        handleRegister($conn, $data);
        break;
    case 'login':
        handleLogin($conn, $data);
        break;
    case 'contact':
        handleContact($conn, $data);
        break;
    default:
        sendJsonResponse(false, 'Acción no válida proporcionada.', null, 400);
        break;
}

// Cerrar la conexión al final del script.
$conn->close();


// --- 4. FUNCIONES LÓGICAS (HANDLERS) ---

/**
 * Gestiona el registro de un nuevo usuario.
 * Valida los datos, comprueba duplicados y los inserta en la base de datos.
 *
 * @param mysqli $conn La conexión a la base de datos.
 * @param object|null $data Los datos decodificados de la petición JSON.
 * @return void
 */
function handleRegister(mysqli $conn, ?object $data): void
{
    if (!isset($data->email) || !isset($data->password)) {
        sendJsonResponse(false, 'El correo y la contraseña son obligatorios.', null, 400);
    }

    $email = trim($data->email);
    $password = trim($data->password);

    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        sendJsonResponse(false, 'El formato del correo electrónico no es válido.', null, 400);
    }

    if (strlen($password) < PASSWORD_MIN_LENGTH) {
        sendJsonResponse(false, 'La contraseña debe tener al menos ' . PASSWORD_MIN_LENGTH . ' caracteres.', null, 400);
    }

    $password_hash = password_hash($password, PASSWORD_BCRYPT);

    try {
        $stmt = $conn->prepare("INSERT INTO users (email, password) VALUES (?, ?)");
        $stmt->bind_param("ss", $email, $password_hash);
        $stmt->execute();
        $stmt->close();
        
        sendJsonResponse(true, 'Usuario registrado exitosamente.', null, 201);
    } catch (mysqli_sql_exception $e) {
        // Código de error 1062 = Entrada duplicada (email ya existe).
        if ($e->getCode() == 1062) {
            sendJsonResponse(false, 'El correo electrónico ya está registrado.', null, 409); // 409 Conflict
        } else {
            sendJsonResponse(false, 'Error interno al registrar el usuario.', null, 500);
        }
    }
}

/**
 * Gestiona el inicio de sesión de un usuario.
 * Verifica las credenciales y devuelve los datos del usuario si son correctas.
 *
 * @param mysqli $conn La conexión a la base de datos.
 * @param object|null $data Los datos decodificados de la petición JSON.
 * @return void
 */
function handleLogin(mysqli $conn, ?object $data): void
{
    if (empty($data->email) || empty($data->password)) {
        sendJsonResponse(false, 'El correo y la contraseña son obligatorios.', null, 400);
    }

    $email = trim($data->email);
    $password = trim($data->password);

    try {
        $stmt = $conn->prepare("SELECT email, password FROM users WHERE email = ?");
        $stmt->bind_param("s", $email);
        $stmt->execute();
        $result = $stmt->get_result();

        if ($result->num_rows === 1) {
            $user = $result->fetch_assoc();
            if (password_verify($password, $user['password'])) {
                // Éxito: se devuelve el email del usuario anidado en una clave "user".
                $userData = ['user' => ['email' => $user['email']]];
                sendJsonResponse(true, 'Inicio de sesión exitoso.', $userData);
            } else {
                sendJsonResponse(false, 'Credenciales incorrectas.', null, 401); // 401 Unauthorized
            }
        } else {
            sendJsonResponse(false, 'Credenciales incorrectas.', null, 401);
        }
        $stmt->close();
    } catch (mysqli_sql_exception $e) {
        sendJsonResponse(false, 'Error interno del servidor.', null, 500);
    }
}

/**
 * Gestiona el envío de un mensaje de contacto.
 * Valida los datos y los inserta en la tabla de mensajes.
 *
 * @param mysqli $conn La conexión a la base de datos.
 * @param object|null $data Los datos decodificados de la petición JSON.
 * @return void
 */
function handleContact(mysqli $conn, ?object $data): void
{
    if (empty($data->name) || empty($data->email) || empty($data->message)) {
        sendJsonResponse(false, 'Todos los campos (nombre, email, mensaje) son obligatorios.', null, 400);
    }

    $name = trim(strip_tags($data->name));
    $email = trim($data->email);
    $message = trim(strip_tags($data->message));

    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        sendJsonResponse(false, 'El formato del correo electrónico no es válido.', null, 400);
    }

    try {
        $stmt = $conn->prepare("INSERT INTO messages (name, email, message) VALUES (?, ?, ?)");
        $stmt->bind_param("sss", $name, $email, $message);
        $stmt->execute();
        $stmt->close();

        sendJsonResponse(true, 'Mensaje enviado exitosamente.');
    } catch (mysqli_sql_exception $e) {
        sendJsonResponse(false, 'Error al enviar el mensaje.', null, 500);
    }
}
?>