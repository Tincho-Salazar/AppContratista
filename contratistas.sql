-- --------------------------------------------------------
-- Host:                         192.168.30.216
-- Versión del servidor:         10.4.6-MariaDB - mariadb.org binary distribution
-- SO del servidor:              Win64
-- HeidiSQL Versión:             12.3.0.6589
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Volcando estructura de base de datos para contratistas
CREATE DATABASE IF NOT EXISTS `contratistas` /*!40100 DEFAULT CHARACTER SET latin1 */;
USE `contratistas`;

-- Volcando estructura para tabla contratistas.calendario
CREATE TABLE IF NOT EXISTS `calendario` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `contratista_id` int(11) DEFAULT NULL,
  `fecha_evento` date DEFAULT NULL,
  `descripcion_evento` text DEFAULT NULL,
  `tipo_evento` varchar(255) DEFAULT NULL,
  `completado` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `contratista_id` (`contratista_id`),
  CONSTRAINT `calendario_ibfk_1` FOREIGN KEY (`contratista_id`) REFERENCES `contratistas` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=latin1;

-- Volcando datos para la tabla contratistas.calendario: ~0 rows (aproximadamente)
REPLACE INTO `calendario` (`id`, `contratista_id`, `fecha_evento`, `descripcion_evento`, `tipo_evento`, `completado`) VALUES
	(9, 1, '2024-09-14', 'presentacion de comprobantes', 'documentos', 1);

-- Volcando estructura para tabla contratistas.cargas_sociales
CREATE TABLE IF NOT EXISTS `cargas_sociales` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `contratista_id` int(11) DEFAULT NULL,
  `fecha_entrega` date DEFAULT NULL,
  `periodo` date DEFAULT NULL,
  `pago_931` tinyint(1) DEFAULT NULL,
  `uatre` tinyint(1) DEFAULT NULL,
  `iva` tinyint(1) DEFAULT NULL,
  `pago_sepelio` tinyint(1) DEFAULT NULL,
  `f_931_afip` tinyint(1) DEFAULT NULL,
  `obra_social` tinyint(1) DEFAULT NULL,
  `personal_afectado` int(11) DEFAULT NULL,
  `rc_sueldos` tinyint(1) DEFAULT NULL,
  `altas` tinyint(1) DEFAULT NULL,
  `bajas` tinyint(1) DEFAULT NULL,
  `art` tinyint(1) DEFAULT NULL,
  `s_vida` tinyint(1) DEFAULT NULL,
  `poliza_vida` tinyint(1) DEFAULT NULL,
  `tk_pago_vida` tinyint(1) DEFAULT NULL,
  `remun_bruta` decimal(10,2) DEFAULT NULL,
  `prom_s_931` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `contratista_id` (`contratista_id`),
  CONSTRAINT `cargas_sociales_ibfk_1` FOREIGN KEY (`contratista_id`) REFERENCES `contratistas` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=latin1;

-- Volcando datos para la tabla contratistas.cargas_sociales: ~3 rows (aproximadamente)
REPLACE INTO `cargas_sociales` (`id`, `contratista_id`, `fecha_entrega`, `periodo`, `pago_931`, `uatre`, `iva`, `pago_sepelio`, `f_931_afip`, `obra_social`, `personal_afectado`, `rc_sueldos`, `altas`, `bajas`, `art`, `s_vida`, `poliza_vida`, `tk_pago_vida`, `remun_bruta`, `prom_s_931`) VALUES
	(4, 17, '2024-08-09', '2024-08-01', 1, 1, 1, 1, 1, 1, NULL, 1, 1, 1, 1, 1, 1, 1, 2678976.00, 937567.00),
	(5, 14, '2024-08-15', '2024-08-01', 1, 1, 1, 1, 1, 1, NULL, 1, 1, 1, 1, 1, 1, 1, 2678976.00, 937567.00),
	(6, 7, '2024-09-14', '2024-09-01', 1, 0, 0, 0, 0, 0, NULL, 0, 0, 0, 0, 0, 0, 0, NULL, NULL);

-- Volcando estructura para tabla contratistas.contratistas
CREATE TABLE IF NOT EXISTS `contratistas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(255) NOT NULL,
  `cuit` varchar(20) NOT NULL,
  `categoria` enum('VIVERO','FORESTAL','INDUSTRIA','TRANSPORTISTA','YERBA','SECADERO','CERFOAR') NOT NULL,
  `Habilitado` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=62 DEFAULT CHARSET=latin1;

-- Volcando datos para la tabla contratistas.contratistas: ~61 rows (aproximadamente)
REPLACE INTO `contratistas` (`id`, `nombre`, `cuit`, `categoria`, `Habilitado`) VALUES
	(1, 'Ventilacion Teva ', '20000000001', 'VIVERO', 1),
	(2, 'Barboza Julio Aire Ac. ', '20000000001', 'FORESTAL', 1),
	(3, 'Bloch e Hijos ', '20000000001', 'INDUSTRIA', 1),
	(4, 'Lopez Francisco Solano ', '20000000001', 'TRANSPORTISTA', 1),
	(5, 'Bridge Hydrogen ', '20000000001', 'YERBA', 1),
	(6, 'Fracalossi Walter ', '20000000001', 'SECADERO', 1),
	(7, 'Binder Rulemanes ', '20000000001', 'VIVERO', 1),
	(8, 'Alecrin Gruber ', '20000000001', 'FORESTAL', 1),
	(9, 'Forestal Garuape ', '20000000001', 'INDUSTRIA', 1),
	(10, 'Gottert ', '20000000001', 'TRANSPORTISTA', 1),
	(11, 'Toledo Roberto E ', '20000000001', 'YERBA', 1),
	(12, 'Ingelect SRL', '20000000001', 'SECADERO', 1),
	(13, 'Kevin Tesari TyD', '20000000001', 'VIVERO', 1),
	(14, 'Aguilera Carlos ', '20000000001', 'FORESTAL', 1),
	(15, 'Ing laboral y ambi.', '20000000001', 'INDUSTRIA', 1),
	(16, 'Lavatruc', '20000000001', 'TRANSPORTISTA', 1),
	(17, 'Acevedo Gladys', '20000000001', 'YERBA', 0),
	(18, 'Roman Daniel ', '20000000001', 'SECADERO', 1),
	(19, 'Fedian Jerkovich', '20000000001', 'VIVERO', 1),
	(20, 'Alvez', '20000000001', 'FORESTAL', 1),
	(21, 'Kurten Carchano', '20000000001', 'INDUSTRIA', 1),
	(22, 'Martin Binder', '20000000001', 'TRANSPORTISTA', 1),
	(23, 'Ingenieria Norte ZARZA', '20000000001', 'YERBA', 1),
	(24, 'Frio Tecnica Eldorado', '20000000001', 'SECADERO', 1),
	(25, 'ElectroLuz', '20000000001', 'VIVERO', 1),
	(26, 'SPI Bascula y Balanza', '20000000001', 'FORESTAL', 1),
	(27, 'DSI Sgroppo y Marchke', '20000000001', 'INDUSTRIA', 1),
	(28, 'Ftal y Ganaderia Indumarca', '20000000001', 'TRANSPORTISTA', 1),
	(29, 'Aumer ', '20000000001', 'YERBA', 1),
	(30, 'Benitez Manuel', '20000000001', 'SECADERO', 1),
	(31, 'JM Stema Constivo', '20000000001', 'VIVERO', 1),
	(32, 'Luty Ramiro', '20000000001', 'FORESTAL', 1),
	(33, 'Garcia Agustin Arsenio ', '20000000001', 'INDUSTRIA', 1),
	(34, 'Toledo Rodolfo ', '20000000001', 'TRANSPORTISTA', 1),
	(35, 'El Cerrito ', '20000000001', 'YERBA', 1),
	(36, 'VIP Benitez Guillermo', '20000000001', 'SECADERO', 1),
	(37, 'Caisa', '20000000001', 'VIVERO', 1),
	(38, 'Const. Esper Gonzalez Natalia ', '20000000001', 'FORESTAL', 1),
	(39, 'Gonzalez Hugo ', '20000000001', 'INDUSTRIA', 1),
	(40, 'Mecanalisis ', '20000000001', 'TRANSPORTISTA', 1),
	(41, 'Rhema', '20000000001', 'YERBA', 1),
	(42, 'Hormicon', '20000000001', 'SECADERO', 1),
	(43, 'San Cayetano ', '20000000001', 'VIVERO', 1),
	(44, 'Mids', '20000000001', 'FORESTAL', 1),
	(45, 'Faccio W', '20000000001', 'INDUSTRIA', 1),
	(46, 'Dionisia Correa ', '20000000001', 'TRANSPORTISTA', 1),
	(47, 'EFO Ingenieria', '20000000001', 'YERBA', 1),
	(48, 'Rios Roman ', '20000000001', 'SECADERO', 1),
	(49, 'Rabiolo Francisco ', '20000000001', 'VIVERO', 1),
	(50, 'Ayala Yiyo ', '20000000001', 'FORESTAL', 1),
	(51, 'Gruber Guillermo  ', '20000000001', 'INDUSTRIA', 1),
	(52, 'Forestal Garuhape', '20000000001', 'TRANSPORTISTA', 1),
	(53, 'Chatarra Trans Avenida', '20000000001', 'YERBA', 1),
	(54, 'Tamet', '20000000001', 'SECADERO', 1),
	(55, 'Borja Juan Pablo ', '20000000001', 'VIVERO', 1),
	(56, 'Canta Emiliano ', '20000000001', 'FORESTAL', 1),
	(57, 'Gonzalez Juan de Dios ', '20000000001', 'INDUSTRIA', 1),
	(58, 'Serv. Ind. Fluidodinamicos ', '20000000001', 'TRANSPORTISTA', 1),
	(59, 'Tymaq SRL ', '20000000001', 'YERBA', 1),
	(60, 'GS Ensayo y Servicio ', '20000000001', 'SECADERO', 1),
	(61, 'Grupo Silva ', '20000000001', 'VIVERO', 1);

-- Volcando estructura para tabla contratistas.login
CREATE TABLE IF NOT EXISTS `login` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `usuario` varchar(50) DEFAULT NULL,
  `contrasena` varchar(255) DEFAULT NULL,
  `rol` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=latin1;

-- Volcando datos para la tabla contratistas.login: ~5 rows (aproximadamente)
REPLACE INTO `login` (`id`, `usuario`, `contrasena`, `rol`) VALUES
	(1, 'tincho', 'pbkdf2:sha256:600000$2zItyEJ1jsRA0yIN$92f17462faef8b879b439f5250ddb16ed07d2743873f156be6fab6ccdda08b93', 'administrador'),
	(4, 'admin', 'pbkdf2:sha256:600000$ciRv2hKPpx5ABAFX$a06d4f5947fd291f13724e497286a0135f4b5dcdcfc50c444626bd02b0835be5', 'administrador'),
	(10, 'Juliana', 'pbkdf2:sha256:600000$nsbJwr7s10toE9MZ$c75a8a4b8b0baaad835f9462fc207be0d38a40f58e2f1b469dd3a4b09e422c3b', 'administrador'),
	(11, 'vigilancia', 'pbkdf2:sha256:600000$U1DLRFBvJAwkNcDn$17670c0a7e1132e95f77347c626e6a4e13e6567771c85d0facc8d50eaa440b7f', 'usuario'),
	(22, 'carlos', 'pbkdf2:sha256:600000$TpHDAvPxxpCMoGbx$ce8b8ec14562649820545e4e55dc5a13326be45bb7eb7e5c767e08b4fe9455c2', 'usuario');

-- Volcando estructura para tabla contratistas.personal
CREATE TABLE IF NOT EXISTS `personal` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `contratista_id` int(11) DEFAULT NULL,
  `cuil_dni` varchar(20) DEFAULT NULL,
  `nombre` varchar(255) DEFAULT NULL,
  `puesto` varchar(255) DEFAULT NULL,
  `alta` date DEFAULT NULL,
  `baja` date DEFAULT NULL,
  `sueldo_general` decimal(10,2) DEFAULT NULL,
  `enero` decimal(10,2) DEFAULT NULL,
  `febrero` decimal(10,2) DEFAULT NULL,
  `marzo` decimal(10,2) DEFAULT NULL,
  `abril` decimal(10,2) DEFAULT NULL,
  `mayo` decimal(10,2) DEFAULT NULL,
  `junio` decimal(10,2) DEFAULT NULL,
  `julio` decimal(10,2) DEFAULT NULL,
  `agosto` decimal(10,2) DEFAULT NULL,
  `septiembre` decimal(10,2) DEFAULT NULL,
  `octubre` decimal(10,2) DEFAULT NULL,
  `noviembre` decimal(10,2) DEFAULT NULL,
  `diciembre` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `contratista_id` (`contratista_id`),
  CONSTRAINT `personal_ibfk_1` FOREIGN KEY (`contratista_id`) REFERENCES `contratistas` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=latin1;

-- Volcando datos para la tabla contratistas.personal: ~0 rows (aproximadamente)

-- Volcando estructura para tabla contratistas.vehiculos
CREATE TABLE IF NOT EXISTS `vehiculos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `contratista_id` int(11) DEFAULT NULL,
  `Unidad` varchar(255) DEFAULT NULL,
  `patente` varchar(10) DEFAULT NULL,
  `poliza` date DEFAULT NULL,
  `revision_tecnica_desde` date DEFAULT NULL,
  `revision_tecnica_hasta` date DEFAULT NULL,
  `pago` date DEFAULT NULL,
  `vigencia` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `contratista_id` (`contratista_id`),
  CONSTRAINT `vehiculos_ibfk_1` FOREIGN KEY (`contratista_id`) REFERENCES `contratistas` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=latin1;

-- Volcando datos para la tabla contratistas.vehiculos: ~1 rows (aproximadamente)

-- Volcando estructura para tabla contratistas.vehiculos_personal
CREATE TABLE IF NOT EXISTS `vehiculos_personal` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `vehiculo_id` int(11) NOT NULL,
  `personal_id` int(11) NOT NULL,
  `carnet_conducir` varchar(255) DEFAULT NULL,
  `vigencia` date DEFAULT NULL,
  `habilitado` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `vehiculo_id` (`vehiculo_id`),
  KEY `personal_id` (`personal_id`),
  CONSTRAINT `vehiculos_personal_ibfk_1` FOREIGN KEY (`vehiculo_id`) REFERENCES `vehiculos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `vehiculos_personal_ibfk_2` FOREIGN KEY (`personal_id`) REFERENCES `personal` (`id`) ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=latin1;

-- Volcando datos para la tabla contratistas.vehiculos_personal: ~1 rows (aproximadamente)

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
