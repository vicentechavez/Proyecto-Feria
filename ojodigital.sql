
CREATE TABLE Clientes (
    cliente_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    direccion VARCHAR(200),
    telefono VARCHAR(20),
    correo VARCHAR(100),
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Dispositivos (
    dispositivo_id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT,
    tipo_dispositivo VARCHAR(50),
    modelo VARCHAR(50),
    fecha_instalacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    estado ENUM('Activo', 'Inactivo') DEFAULT 'Activo',
    FOREIGN KEY (cliente_id) REFERENCES Clientes(cliente_id)
);

CREATE TABLE PlanesSeguridad (
    plan_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_plan VARCHAR(100),
    descripcion TEXT,
    precio DECIMAL(12, 2),
    tipo_plan ENUM('Básico', 'Avanzado', 'Premium')
);

CREATE TABLE ClientesPlanes (
    cliente_id INT,
    plan_id INT,
    fecha_inicio DATE,
    fecha_fin DATE,
    PRIMARY KEY(cliente_id, plan_id),
    FOREIGN KEY (cliente_id) REFERENCES Clientes(cliente_id),
    FOREIGN KEY (plan_id) REFERENCES PlanesSeguridad(plan_id)
);

CREATE TABLE Monitoreo (
    monitoreo_id INT AUTO_INCREMENT PRIMARY KEY,
    dispositivo_id INT,
    fecha_monitoreo DATETIME DEFAULT CURRENT_TIMESTAMP,
    estado ENUM('Normal', 'Alerta', 'Fallo') DEFAULT 'Normal',
    FOREIGN KEY (dispositivo_id) REFERENCES Dispositivos(dispositivo_id)
);

CREATE TABLE Pagos (
    pago_id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT,
    monto DECIMAL(12, 2),
    fecha_pago DATE,
    metodo_pago ENUM('Tarjeta', 'Transferencia', 'Efectivo', 'Otros'),
    FOREIGN KEY (cliente_id) REFERENCES Clientes(cliente_id)
);
CREATE TABLE HistorialDispositivos (
    historial_id INT AUTO_INCREMENT PRIMARY KEY,
    dispositivo_id INT,
    fecha_accion DATETIME DEFAULT CURRENT_TIMESTAMP,
    accion VARCHAR(255),
    descripcion TEXT,
    FOREIGN KEY (dispositivo_id) REFERENCES Dispositivos(dispositivo_id)
);
CREATE TABLE HistorialPagos (
    historial_pago_id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT,
    monto DECIMAL(10, 2),
    fecha_pago DATE,
    metodo_pago ENUM('Tarjeta', 'Transferencia', 'Efectivo', 'Otros'),
    FOREIGN KEY (cliente_id) REFERENCES Clientes(cliente_id)
    );
    CREATE TABLE Empresa (
    empresa_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_empresa VARCHAR(255) NOT NULL,
    direccion VARCHAR(255),
    telefono VARCHAR(20),
    correo VARCHAR(100),
    fecha_fundacion DATE,
    descripcion TEXT,
    sitio_web VARCHAR(255),
    estado_empresa ENUM('Activo', 'Inactivo', 'Suspendido') DEFAULT 'Activo'
);
CREATE TABLE IF NOT EXISTS reconocimiento (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL UNIQUE,
    imagen LONGBLOB NOT NULL,
    encoding LONGBLOB NOT NULL
);


