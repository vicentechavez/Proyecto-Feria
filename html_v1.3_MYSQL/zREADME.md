🚀 Ojo Digital - Plataforma de Vigilancia Inteligente
¡Bienvenido a Ojo Digital! Esta es una guía completa para instalar, configurar y ejecutar el proyecto en tu entorno de desarrollo local.

📝 Requisitos Previos
Para que el proyecto sea completamente funcional (incluyendo inicio de sesión, registro y formularios), necesitas un servidor local. Recomendamos XAMPP.

XAMPP: Un entorno de desarrollo gratuito que incluye:

Servidor web Apache.

Gestor de base de datos MariaDB (MySQL).

Intérprete de PHP.

Enlace de Descarga: 👉 Descargar XAMPP

⚙️ Pasos para la Instalación
Sigue estas instrucciones en orden para una configuración exitosa.

1. 📦 Instalar XAMPP
Descarga e instala la versión más reciente de XAMPP usando el enlace anterior.

Puedes mantener las opciones de instalación por defecto.

2. 🗂️ Mover los Archivos del Proyecto
Navega a la carpeta de instalación de XAMPP (normalmente C:\xampp en Windows).

Localiza la subcarpeta htdocs. Esta es la raíz de tu servidor web local.

Copia todos los archivos y carpetas del proyecto (index.html, assets/, etc.) y pégalos directamente dentro de htdocs.

3. 🖥️ Iniciar el Servidor Local
Abre el Panel de Control de XAMPP.

Inicia los dos servicios requeridos para el proyecto:

Haz clic en Start junto a Apache.

Haz clic en Start junto a MySQL.

Ambos módulos deben mostrarse con un fondo verde, indicando que están activos.

4. 🗃️ Crear la Base de Datos
Con los servicios corriendo, abre tu navegador y ve a http://localhost/phpmyadmin/.

Paso A: Crear la Base de Datos

En el menú izquierdo, haz clic en "Nueva".

Nombre de la base de datos: Escribe ojodigital (exactamente).

Cotejamiento: Selecciona utf8mb4_general_ci.

Haz clic en "Crear".

Paso B: Crear las Tablas (users y messages)

Selecciona la base de datos ojodigital en el menú izquierdo.

Ve a la pestaña "SQL".

Copia y pega el siguiente código en el área de texto:

CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `messages` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `message` text NOT NULL,
  `sent_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

Haz clic en "Continuar" para ejecutar la consulta. Deberías ver un mensaje de éxito.

▶️ Ejecutar el Proyecto
Con la configuración completa, solo necesitas:

Verificar que Apache y MySQL sigan corriendo en el panel de XAMPP.

Abrir tu navegador web.

Ir a la dirección: http://localhost/

¡Y listo! La página de inicio de Ojo Digital debería cargarse y ser 100% funcional.

📂 Estructura del Proyecto
/
|-- assets/
|   |-- css/         # Hojas de estilo
|   |-- img/         # Imágenes y logos
|   |-- js/          # Scripts de JavaScript
|   |-- api/
|       |-- api.php  # Lógica del backend
|
|-- index.html       # Página de inicio
|-- contacto.html
|-- galeria.html
|-- historia.html
|-- pago.html
|-- gracias.html
|-- servicios.html
|-- zREADME.md       # Este archivo

🔍 Solución de Problemas Comunes
Error "No se puede conectar con la base de datos":

Asegúrate de que MySQL esté corriendo en XAMPP.

Verifica que el nombre de la base de datos sea ojodigital.

El archivo api.php asume que la contraseña del usuario root de MySQL está vacía. Si has configurado una contraseña, debes actualizarla en api.php.

Apache no se inicia:

Este problema suele ser por un conflicto de puertos (normalmente el puerto 80). Aplicaciones como Skype o algunas impresoras pueden usarlo.

En XAMPP, ve a Config > Apache (httpd.conf) y cambia la línea Listen 80 a Listen 8080. Guarda el archivo y reinicia Apache. Ahora podrás acceder al proyecto desde http://localhost:8080/.