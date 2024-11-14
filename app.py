from waitress import serve
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, abort
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from math import ceil
from flask import make_response
import mysql.connector
import os
import time

app = Flask(__name__)
app.secret_key = 'datiles2044'
app.config['UPLOAD_FOLDER'] = '/uploads/'  # Carpeta raíz donde se guardarán los archivos
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg', 'xls', 'xlsx', 'csv', 'docx'}
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limitar a 16 MB
# Global database connection variables
mydb = None
mycursor = None

DB_HOST = "192.168.30.216"
DB_USER = "root"
DB_PASSWORD = "toor"
DB_NAME = "contratistas"

# Función para conectar a la base de datos MySQL con manejo de excepciones
def connect_to_db():
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            autocommit=True,
            connection_timeout=28800,  # Configura timeout alto para evitar desconexiones
            pool_name="mypool",  # Pool de conexiones para manejo eficiente
            pool_size=10  # Número de conexiones permitidas en el pool
        )
        if connection.is_connected():
            # print("Conexión exitosa a la base de datos")
            return connection
    except mysql.connector.Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None
    except Exception as general_error:
        print(f"Error inesperado al conectar a la base de datos: {general_error}")
        return None

# Función para reconectar con varios intentos
def connect_with_retry(retries=5, delay=5):
    for _ in range(retries):
        connection = connect_to_db()
        if connection:
            return connection
        print(f"Reintentando conexión en {delay} segundos...")
        time.sleep(delay)
    print("No se pudo conectar a la base de datos después de varios intentos.")
    return None

# Función para mantener la conexión activa (Keep-Alive)
def keep_connection_alive(connection, interval=60):
    while True:
        try:
            # Verificar conexión actual
            if not connection.is_connected():
                print("Conexión perdida. Intentando reconectar...")
                connection = connect_with_retry()  # Reintentar conexión
            else:
                # Realizar ping para mantener la conexión activa
                connection.ping(reconnect=True, attempts=3, delay=5)
                # print("Conexión verificada y activa.")
        except mysql.connector.Error as e:
            print(f"Error en keep-alive: {e}")
            connection = connect_with_retry()
        time.sleep(interval)

# Función para ejecutar consultas SQL con manejo de errores
def execute_query(connection, query, params=None, fetchone=False, commit=False):
    try:
        # Verificar si la conexión está activa
        if not connection.is_connected():
            connection = connect_with_retry()

        cursor = connection.cursor()  # Usamos diccionario para un mejor acceso a los resultados
        cursor.execute(query, params or ())  # Prevenir inyecciones SQL
        if commit:
            connection.commit()
        result = cursor.fetchone() if fetchone else cursor.fetchall()
        cursor.close()
        return result
    except mysql.connector.Error as err:
        print("Error MySQL:", err)
        if commit:
            connection.rollback()
        # Intentar reconectar si hay un error en la conexión
        if "MySQL server has gone away" in str(err):
            print("Intentando reconectar...")
            connection = connect_with_retry()
            return execute_query(connection, query, params, fetchone, commit)
        return None

# Decorador para asegurar la conexión a la base de datos
def ensure_db_connection(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Obtén la conexión antes de la ejecución
        db_connection = connect_with_retry()  # Aseguramos la conexión con reintentos
        if not db_connection:
            print("No se pudo establecer una conexión con la base de datos")
            return None  # Retorna None si no se conecta
        return f(db_connection, *args, **kwargs)
    return decorated_function



# Funciones  para manejar datos la base de datos

@app.template_filter('format_period')
def format_period(value):
    # Supone que el valor está en formato yyyy-mm-dd
    if value is None:
        return ''
    return value.strftime('%b-%Y')

# Registra el filtro personalizado en el ambiente de Jinja
app.jinja_env.filters['format_period'] = format_period

def convertir_fecha(fecha_str):
    try:
        return datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None  # Manejo de error si la fecha no es válida

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():  
    if 'usuario' not in session or session['rol'] != 'administrador':
        return redirect('/admin/login') 
    else:
        return render_template(
        'index.html',
        contratistas='',
        current_page=0,
        total_pages=0,
        page_size=0,
        search='')


# Conectar a la base de datos al inicio
mydb = connect_with_retry()
if mydb:
    mycursor = mydb.cursor()
else:
    raise Exception("No se pudo establecer la conexión con la base de datos.")

@app.route('/index_admin')
@login_required
def index_admin():
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    
    if 'alertas_mostradas' not in session:
        session['alertas_mostradas'] = False

    # Consulta para eventos no completados de la semana actual
    check_current_week_events_query = """
        SELECT COUNT(*) 
        FROM calendario 
        WHERE WEEK(fecha_evento, 1) = WEEK(CURDATE(), 1) 
        AND YEAR(fecha_evento) = YEAR(CURDATE()) 
        AND completado = 0;
    """
    eventos_semana_actual = execute_query(mydb, check_current_week_events_query, fetchone=True)[0]

    # Consulta para eventos anteriores no completados
    check_past_events_query = """
        SELECT COUNT(*) 
        FROM calendario 
        WHERE fecha_evento < CURDATE() 
        AND completado = 0;
    """
    eventos_pasados = execute_query(mydb, check_past_events_query, fetchone=True)[0]

    toasts = []

    if eventos_pasados > 0 and session['rol'] == 'administrador':
        toasts.append({
            'title': 'Eventos Pasados',
            'message': f'Hay eventos anteriores a la semana actual \n que no han sido completados.',
            'type': 'warning'
        })

    if eventos_semana_actual > 0 and session['rol'] == 'administrador':
        toasts.append({
            'title': 'Eventos de la Semana Actual',
            'message': f'Hay {eventos_semana_actual} eventos pendientes en esta semana.',
            'type': 'info'
        })

    session['alertas_mostradas'] = True

    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 6, type=int)
    search = request.args.get('search', '', type=str)
    categoria = request.args.get('categoria', 'VIVERO', type=str)

    search_query = "WHERE c.categoria = %s"
    search_values = [categoria]

    if session['rol'] != 'administrador':
        search_query += " AND c.habilitado = 1"

    if search:
        if search.isdigit():
            search_query += " AND c.cuit LIKE %s"
            search_values.append('%' + search + '%')
        else:
            search_query += " AND c.nombre LIKE %s"
            search_values.append('%' + search + '%')

    count_query = f"SELECT COUNT(*) FROM contratistas c {search_query}"
    total_count = execute_query(mydb, count_query, params=search_values, fetchone=True)[0]
    total_pages = (total_count + page_size - 1) // page_size

    offset = (page - 1) * page_size

    query = f"""
        SELECT c.id, c.nombre, c.cuit, c.habilitado,
        (SELECT COUNT(*) FROM personal p WHERE p.contratista_id = c.id AND p.baja IS NULL) AS empleados_count,
        (SELECT COUNT(*) FROM vehiculos v WHERE v.contratista_id = c.id) AS vehiculos_count,
        (SELECT COUNT(*) FROM cargas_sociales d WHERE d.contratista_id = c.id) AS documentos_count
        FROM contratistas c 
        {search_query}
        ORDER BY c.nombre ASC
        LIMIT %s OFFSET %s
    """
    search_values.extend([page_size, offset])
    contratistas = execute_query(mydb, query, params=search_values)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template(
            'contratistas_cards.html',
            contratistas=contratistas,
            current_page=page,
            total_pages=total_pages
        )

    return render_template(
        'index.html',
        contratistas=contratistas,
        current_page=page,
        total_pages=total_pages,
        page_size=page_size,
        search=search,
        categoria=categoria,
        toasts=toasts
    )

@app.route('/admin/contratistas')
def admin_contratistas():
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    if 'usuario' not in session or session['rol'] != 'administrador':
        return redirect('/admin/login')

    query = "SELECT * FROM contratistas Order By nombre"
    contratistas = execute_query(mydb, query)
    contratista_editado = 0
    return render_template('contratistas.html', contratistas=contratistas, contratista_editado=contratista_editado)

@app.route('/crear_contratista', methods=['POST'])
def crear_contratista():
    nombre = request.form['nombre']
    cuit = request.form['cuit']
    categoria = request.form['categoria']
    habilitado = 1 if 'habilitado' in request.form else 0

    sql = "INSERT INTO contratistas (nombre, cuit, categoria, Habilitado) VALUES (%s, %s, %s, %s)"
    val = (nombre, cuit, categoria, habilitado)
    execute_query(mydb, sql, params=val, commit=True)
    return jsonify({"message": "El contratista ha sido creado correctamente."}), 200

@app.route('/editar_contratista/<int:contratista_id>', methods=['POST'])
def editar_contratista(contratista_id):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    try:
        nombre = request.form['nombre']
        cuit = request.form['cuit']
        categoria = request.form['categoria']
        habilitado = 1 if 'habilitado' in request.form else 0

        sql = """
            UPDATE contratistas
            SET nombre = %s, cuit = %s, categoria = %s, habilitado = %s
            WHERE id = %s
        """
        val = (nombre, cuit, categoria, habilitado, contratista_id)
        execute_query(mydb, sql, params=val, commit=True)

        return jsonify({'message': 'Contratista actualizado correctamente'}), 200
    
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/eliminar_contratista/<int:contratista_id>', methods=['DELETE'])
def eliminar_contratista(contratista_id):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    try:
        sql = "DELETE FROM contratistas WHERE id = %s"
        val = (contratista_id,)
        execute_query(mydb, sql, params=val, commit=True)

        return jsonify({'message': 'Contratista eliminado correctamente'}), 200
    
    except Exception as e:
        return jsonify({'message': str(e)}), 500


# Ruta de Usuarios
@app.route('/admin/usuarios')
@login_required
def admin_usuarios():
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    # Obtener datos de usuarios desde la base de datos
    query = "SELECT * FROM login"
    usuarios = execute_query(mydb, query)
    return render_template('usuario.html', usuarios=usuarios)

@app.route('/usuarios')
def usuarios():
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    query = 'SELECT id, usuario, contrasena, rol FROM login'
    usuarios = execute_query(mydb, query)
    return render_template('usuario.html', usuarios=usuarios, usuario_editado=None)

@app.route('/crear_usuario', methods=['POST'])
def crear_usuario():
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    usuario = request.form['usuario']
    contrasena = request.form['contrasena']
    rol = request.form['rol']

    hashed_password = generate_password_hash(contrasena, method='pbkdf2:sha256')
    
    sql = 'INSERT INTO login (usuario, contrasena, rol) VALUES (%s, %s, %s)'
    val = (usuario, hashed_password, rol)
    execute_query(mydb, sql, params=val, commit=True)
    
    return jsonify({'message': 'Usuario creado exitosamente'})

@app.route('/editar_usuario/<int:id>', methods=['POST'])
def editar_usuario(id):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    usuario = request.form['usuario']
    contrasena = request.form['contrasena']
    rol = request.form['rol']

    hashed_password = generate_password_hash(contrasena, method='pbkdf2:sha256')
    
    sql = 'UPDATE login SET usuario = %s, contrasena = %s, rol = %s WHERE id = %s'
    val = (usuario, hashed_password, rol, id)
    execute_query(mydb, sql, params=val, commit=True)
    
    return jsonify({'message': 'Usuario actualizado exitosamente'})

@app.route('/eliminar_usuario/<int:id>', methods=['DELETE'])
def eliminar_usuario(id):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    sql = 'DELETE FROM login WHERE id = %s'
    val = (id,)
    execute_query(mydb, sql, params=val, commit=True)

    return jsonify({'message': 'Usuario eliminado exitosamente'})


# Ruta de Calendario

@app.route('/calendario')
@login_required
def calendario():
    return render_template('calendario.html')

@app.route('/obtener_eventos')
@login_required
def obtener_eventos():
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    start = request.args.get('start')
    end = request.args.get('end')
    
    sql = """
    SELECT c.id, c.contratista_id, cont.nombre, c.fecha_evento, c.descripcion_evento, c.tipo_evento, c.completado 
    FROM calendario c
    JOIN contratistas cont ON c.contratista_id = cont.id
    WHERE c.fecha_evento BETWEEN %s AND %s
    """
    eventos = execute_query(mydb, sql, params=(start, end))
    
    eventos_formateados = []
    for evento in eventos:
        eventos_formateados.append({
            'id': evento[0],
            'title': f"{evento[2]}: {evento[5]}",
            'start': evento[3].isoformat(),
            'extendedProps': {
                'contratista_id': evento[1],
                'contratista_nombre': evento[2],
                'description': evento[4],
                'type': evento[5],
                'completed': evento[6]  # Asegúrate de que este campo esté en tu consulta SQL
            },
            'classNames': ['completed'] if evento[6] else []  # Agrega la clase CSS si está completado
        })

    return jsonify(eventos_formateados)

@app.route('/crear_evento', methods=['POST'])
@login_required
def crear_evento():
    if session['rol'] != 'administrador':
        return jsonify({'error': 'No tienes permisos para realizar esta acción'}), 403
    
    data = request.json
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    sql = """
    INSERT INTO calendario (contratista_id, fecha_evento, descripcion_evento, tipo_evento, completado) 
    VALUES (%s, %s, %s, %s, %s)
    """
    valores = (data['contratista_id'], data['fecha_evento'], data['descripcion_evento'], data['tipo_evento'], data['completed'])

    execute_query(mydb, sql, params=valores, commit=True)
    
    return jsonify({'message': 'Evento creado correctamente', 'id': mycursor.lastrowid})

@app.route('/actualizar_evento/<int:evento_id>', methods=['PUT'])
@login_required
def actualizar_evento(evento_id):
    if session['rol'] != 'administrador':
        return jsonify({'error': 'No tienes permisos para realizar esta acción'}), 403
    
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    data = request.json
    sql = """
    UPDATE calendario 
    SET contratista_id = %s, fecha_evento = %s, descripcion_evento = %s, tipo_evento = %s, completado = %s 
    WHERE id = %s
    """
    valores = (data['contratista_id'], data['fecha_evento'], data['descripcion_evento'], data['tipo_evento'], data['completed'], evento_id)

    execute_query(mydb, sql, params=valores, commit=True)
    
    return jsonify({'message': 'Evento actualizado correctamente'})

@app.route('/eliminar_evento/<int:evento_id>', methods=['DELETE'])
@login_required
def eliminar_evento(evento_id):
    if session['rol'] != 'administrador':
        return jsonify({'error': 'No tienes permisos para realizar esta acción'}), 403
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    sql = "DELETE FROM calendario WHERE id = %s"
    execute_query(mydb, sql, params=(evento_id,), commit=True)
    
    return jsonify({'message': 'Evento eliminado correctamente'})

@app.route('/obtener_contratistas')
@login_required
def obtener_contratistas():
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    sql = "SELECT id, nombre FROM contratistas ORDER BY nombre"
    contratistas = execute_query(mydb, sql)
    return jsonify([{'id': c[0], 'nombre': c[1]} for c in contratistas])


# # Ruta de Login
@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['usuario']
        password = request.form['contrasena']        
        # Verificar las credenciales del usuario
        if not ensure_db_connection(mydb):
            return render_template('error.html', message='Error de conexión con la base de datos')
        sql = "SELECT * FROM login WHERE usuario = %s"
        user = execute_query(mydb, sql, params=(username,), fetchone=True)
        
        if user and check_password_hash(user[2], password):
            session['usuario'] = user[1]
            session['rol'] = user[3]
            return jsonify({'status': 'success', 'redirect': url_for('index_admin')})
        else:
            return jsonify({'status': 'error', 'message': 'Nombre de usuario o contraseña incorrectos'})
    
    return render_template('login.html')

@app.route('/admin/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        new_username = request.form['new_usuario']
        new_password = request.form['new_contrasena']
        hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
        rol = 'usuario'
        if not ensure_db_connection(mydb):
            return render_template('error.html', message='Error de conexión con la base de datos')
        # Insertar nuevo usuario en la base de datos con el rol
        sql = "INSERT INTO login (usuario, contrasena, rol) VALUES (%s, %s, %s)"
        execute_query(mydb, sql, params=(new_username, hashed_password, rol), commit=True)
        
        # Retorna un JSON con un mensaje de éxito
        return jsonify({"message": "Registro exitoso"}), 200
    
    return render_template('register.html')




@app.route('/logout')
def logout():
    session.pop('usuario', None)
    session.clear()  # Limpiar toda la sesión
    # flash('Has cerrado sesión exitosamente', 'success')
    return redirect(url_for('login'))  

# Ruta de Empleados 
@app.route('/admin/empleados/<int:contratista_id>')
@login_required
def admin_empleados(contratista_id):   
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    nombre_contratista = obtener_valor("SELECT nombre FROM contratistas WHERE id = %s", (contratista_id,))
    
    sql = """
    SELECT id, contratista_id, cuil_dni, nombre, puesto, alta, baja, sueldo_general FROM personal 
    WHERE contratista_id = %s ORDER BY alta DESC
    """
    empleados = execute_query(mydb, sql, params=(contratista_id,))

    # Organiza por año
    empleados_por_ano = {}
    for empleado in empleados:
        empleado = list(empleado)  # Convertir la tupla a una lista
        fecha_alta = empleado[5]  # fecha_alta        
        fecha_baja = empleado[6]
        if fecha_alta:
            try:
                fecha_alta_formateada = fecha_alta.strftime('%d/%m/%Y')
                empleado[5] = fecha_alta_formateada
                ano = fecha_alta.year
            except ValueError:
                ano = 'Desconocido'
        else:
            ano = 'Desconocido'

        if fecha_baja:
            try:
                fecha_baja_formateada = fecha_baja.strftime('%d/%m/%Y')
                empleado[6] = fecha_baja_formateada
            except ValueError:
                empleado[6] = 'Fecha inválida'

        if ano not in empleados_por_ano:
            empleados_por_ano[ano] = []
        empleados_por_ano[ano].append(tuple(empleado))  # Convertir la lista de vuelta a una tupla si es necesario        

    return render_template('empleados.html', empleados_por_ano=empleados_por_ano, contratista_id=contratista_id, nombre_contratista=nombre_contratista)

@app.route('/crear_empleado/<int:contratista_id>', methods=['POST'])
def crear_empleado(contratista_id):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    data = request.form

    sql = """
        INSERT INTO personal (contratista_id, cuil_dni, nombre, puesto, alta, sueldo_general)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    try:
        execute_query(mydb, sql, params=(contratista_id, data['cuil_dni'], data['nombre'], data['puesto'], data['alta'], data['sueldo_general']), commit=True)
        return jsonify({"message": "Empleado creado correctamente."}), 200
    except mysql.connector.Error as err:
        print("Error MySQL:", err)
        return jsonify({"error": "Error al crear empleado."}), 500

@app.route('/editar_empleado/<int:empleado_id>', methods=['POST'])
def editar_empleado(empleado_id):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    data = request.form

    sql = """
        UPDATE personal
        SET cuil_dni=%s, nombre=%s, puesto=%s, alta=%s, sueldo_general=%s
        WHERE id=%s
    """

    try:
        execute_query(mydb, sql, params=(data['cuil_dni'], data['nombre'], data['puesto'], data['alta'], data['sueldo_general'], empleado_id), commit=True)
        return jsonify({"message": "Empleado actualizado correctamente."}), 200
    except mysql.connector.Error as err:
        print("Error MySQL:", err)
        return jsonify({"error": "Error al actualizar empleado."}), 500

@app.route('/eliminar_empleado/<int:empleado_id>', methods=['DELETE'])
def eliminar_empleado(empleado_id):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    sql = "DELETE FROM personal WHERE id=%s"

    try:
        execute_query(mydb, sql, params=(empleado_id,), commit=True)
        return jsonify({"message": "Empleado eliminado correctamente."}), 200
    except mysql.connector.Error as err:
        print("Error MySQL:", err)
        return jsonify({"error": "Error al eliminar empleado."}), 500

@app.route('/obtener_empleado/<int:empleado_id>', methods=['GET'])
def obtener_empleado(empleado_id):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    sql = """
    SELECT id, contratista_id, cuil_dni, nombre, puesto, DATE_FORMAT(alta, '%d/%m/%Y') as alta, 
           DATE_FORMAT(baja, '%d/%m/%Y') as baja, sueldo_general 
    FROM personal WHERE id=%s
    """
    empleado = execute_query(mydb, sql, params=(empleado_id,), fetchone=True)
    
    if empleado:          
        return jsonify({"empleado": {
            "id": empleado[0],
            "contratista_id": empleado[1],
            "cuil_dni": empleado[2],
            "nombre": empleado[3],
            "puesto": empleado[4],
            "alta": empleado[5],
            "baja": empleado[6],
            "sueldo_general": empleado[7]
        }}), 200
    else:
        return jsonify({"error": "Empleado no encontrado"}), 404

   
# Ruta de Vehiculo
@app.route('/admin/vehiculos/<int:contratista_id>')
@login_required
def admin_vehiculos(contratista_id):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    nombre_contratista = obtener_valor("SELECT nombre FROM contratistas WHERE id = %s", (contratista_id,))

    # Consulta combinada para obtener vehículos y personal asignado
    sql = """
    SELECT v.id, v.contratista_id, v.Unidad, v.patente, v.poliza, v.revision_tecnica_desde, v.revision_tecnica_hasta, 
           v.pago, v.vigencia, p.nombre AS conductor, vp.carnet_conducir, vp.vigencia AS vigencia_carnet, vp.habilitado,
           vp.id as conductorId
    FROM vehiculos v
    LEFT JOIN vehiculos_personal vp ON v.id = vp.vehiculo_id
    LEFT JOIN personal p ON vp.personal_id = p.id
    WHERE v.contratista_id = %s
    ORDER BY v.id DESC
    """

    vehiculos = execute_query(mydb, sql, params=(contratista_id,))

    # Organiza por año (basado en la póliza)
    vehiculos_por_ano = {}
    for vehiculo in vehiculos:
        vehiculo = list(vehiculo)  # Convertir la tupla a una lista
        poliza = vehiculo[4]
        ano = 'Desconocido'

        if poliza:
            try:
                ano = poliza.year
                vehiculo[4] = poliza.strftime('%d/%m/%Y')
            except ValueError:
                vehiculo[4] = 'Fecha inválida'

        # Formatear otras fechas y habilitado
        for i in range(5, 9):
            if vehiculo[i]:
                try:
                    vehiculo[i] = vehiculo[i].strftime('%d/%m/%Y')
                except ValueError:
                    vehiculo[i] = 'Fecha inválida'

        if vehiculo[11]:  # Vigencia carnet
            try:
                vehiculo[11] = vehiculo[11].strftime('%d/%m/%Y')
            except ValueError:
                vehiculo[11] = 'Fecha inválida'

        vehiculo[12] = 'Sí' if vehiculo[12] else 'No'  # Habilitado

        if ano not in vehiculos_por_ano:
            vehiculos_por_ano[ano] = []
        vehiculos_por_ano[ano].append(tuple(vehiculo))  # Convertir la lista de vuelta a una tupla si es necesario

    return render_template('vehiculos.html', vehiculos_por_ano=vehiculos_por_ano, contratista_id=contratista_id,
                           nombre_contratista=nombre_contratista)


@app.route('/crear_vehiculo/<int:contratista_id>', methods=['POST'])
def crear_vehiculo(contratista_id):
    data = request.form
    sql_vehiculo = """
        INSERT INTO vehiculos (contratista_id, Unidad, patente, poliza, revision_tecnica_desde, revision_tecnica_hasta, pago, vigencia)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    sql_personal = """
        INSERT INTO vehiculos_personal (vehiculo_id, personal_id, carnet_conducir, vigencia, habilitado)
        VALUES (%s, %s, %s, %s, %s)
    """
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')

    try:
        # Convertir las fechas a formato datetime si están presentes
        poliza = convertir_fecha(data.get('poliza'))
        revision_desde = convertir_fecha(data.get('revision_desde'))
        revision_hasta = convertir_fecha(data.get('revision_hasta'))
        pago = convertir_fecha(data.get('pago'))
        vigencia = convertir_fecha(data.get('vigencia'))

        # Convertir el campo habilitado a un valor entero (0 o 1)
        habilitado = data.get('habilitado')
        
        # Crear un cursor persistente
        cursor = mydb.cursor()
        # Ejecutar la consulta SQL con los datos proporcionados y el contratista_id de la URL
        
        # Insertar el vehículo
        execute_query(mydb, sql_vehiculo, params=(
            contratista_id, data['unidad'], data['patente'], poliza,
            revision_desde, revision_hasta, pago, vigencia
        ), commit=True)
       # Obtener el ID del último vehículo insertado usando SELECT MAX(id)
        cursor.execute("SELECT MAX(id) FROM vehiculos")
        vehiculo_id = cursor.fetchone()[0]  # Recuperar el ID del vehículo
        # Insertar el personal asignado al vehículo
        execute_query(mydb, sql_personal, params=(
            vehiculo_id, data['conductor'], data['carnet'], vigencia,
            habilitado
        ), commit=True)
        cursor.close()

        return jsonify({"message": "Vehículo creado correctamente."}), 200
    except mysql.connector.Error as err:
        print("Error MySQL:", err)
        return jsonify({"error": "Error al crear vehículo."}), 500
    except Exception as e:
        print("Error general:", e)
        return jsonify({"error": "Error desconocido al crear vehículo."}), 500

@app.route('/editar_vehiculo/<int:vehiculo_id>', methods=['POST'])
def editar_vehiculo(vehiculo_id):
    conductor_id = request.args.get('conductor_id')  # Obtener el conductor_id actual (conductorId en vehiculos_personal)
    data = request.form
    print(data,"Conductor :",conductor_id)
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')

    sql_vehiculo = """
        UPDATE vehiculos
        SET Unidad=%s, patente=%s, poliza=%s, revision_tecnica_desde=%s, revision_tecnica_hasta=%s, pago=%s, vigencia=%s
        WHERE id=%s
    """

    sql_personal = """
        UPDATE vehiculos_personal
        SET personal_id=%s, carnet_conducir=%s, vigencia=%s, habilitado=%s
        WHERE id=%s
    """

    try:
        # Convertir las fechas a formato datetime si están presentes
        poliza = convertir_fecha(data.get('poliza'))
        revision_desde = convertir_fecha(data.get('revision_desde'))
        revision_hasta = convertir_fecha(data.get('revision_hasta'))
        pago = convertir_fecha(data.get('pago'))
        vigencia = convertir_fecha(data.get('vigencia'))

        # Actualizar el vehículo
        execute_query(mydb, sql_vehiculo, params=(
            data['unidad'], data['patente'], poliza,
            revision_desde, revision_hasta, pago, vigencia, vehiculo_id
        ), commit=True)

        # Solo actualizar en vehiculos_personal si conductor_id existe
        if conductor_id:
            execute_query(mydb, sql_personal, params=(
                data['conductor'], data['carnet'], vigencia,
                1 if data.get('habilitado') == '1' else 0, conductor_id
            ), commit=True)

        return jsonify({"message": "Vehículo actualizado correctamente."}), 200
    except mysql.connector.Error as err:
        mydb.rollback()
        print("Error MySQL:", err)
        return jsonify({"error": "Error al actualizar vehículo."}), 500

@app.route('/eliminar_vehiculo/<int:vehiculo_id>', methods=['DELETE'])
def eliminar_vehiculo(vehiculo_id):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    sql = "DELETE FROM vehiculos WHERE id=%s"

    try:
        execute_query(mydb, sql, params=(vehiculo_id,), commit=True)
        return jsonify({"message": "Vehículo eliminado correctamente."}), 200
    except mysql.connector.Error as err:
        print("Error MySQL:", err)
        return jsonify({"error": "Error al eliminar vehículo."}), 500

@app.route('/obtener_vehiculo/<int:vehiculo_id>', methods=['GET'])
def obtener_vehiculo(vehiculo_id):
    conductor_id = request.args.get('conductor_id')  # Obtiene el parámetro conductor_id de la URL si está presente

    sql = """
    SELECT v.id, v.contratista_id, v.Unidad, v.patente, v.poliza, 
           v.revision_tecnica_desde, v.revision_tecnica_hasta, v.pago, 
           p.nombre AS conductor, vp.carnet_conducir, vp.vigencia, vp.habilitado,
           vp.id as conductorId
    FROM vehiculos v
    LEFT JOIN vehiculos_personal vp ON v.id = vp.vehiculo_id
    LEFT JOIN personal p ON vp.personal_id = p.id
    WHERE v.id = %s
    """
    print(vehiculo_id,)
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')

    # Si conductor_id está presente, ajusta la consulta para incluirlo
    if conductor_id:
        sql += " AND vp.id = %s"
        params = (vehiculo_id, conductor_id)
    else:
        params = (vehiculo_id,)

    vehiculo = execute_query(mydb, sql, params=params, fetchone=True)
    
    if vehiculo:
        vehiculo = list(vehiculo)
        poliza = vehiculo[4]
        tecnica_desde = vehiculo[5]
        tecnica_hasta = vehiculo[6]
        pago = vehiculo[7]
        vigencia = vehiculo[10]

        def format_date(date_value):
            try:
                return date_value.strftime('%Y-%m-%d')
            except AttributeError:
                return 'Fecha inválida'

        vehiculo[4] = format_date(poliza)
        vehiculo[5] = format_date(tecnica_desde)
        vehiculo[6] = format_date(tecnica_hasta)
        vehiculo[7] = format_date(pago)
        vehiculo[10] = format_date(vigencia)
        return jsonify({"vehiculo": {
            "id": vehiculo[0],
            "contratista_id": vehiculo[1],
            "unidad": vehiculo[2],
            "patente": vehiculo[3],
            "poliza": vehiculo[4],
            "revision_tecnica_desde": vehiculo[5],
            "revision_tecnica_hasta": vehiculo[6],
            "pago": vehiculo[7],
            "conductor": vehiculo[8],
            "carnet_conducir": vehiculo[9],
            "vigencia": vehiculo[10],
            "habilitado": vehiculo[11],
            "conductorId": vehiculo[12]
        }}), 200
    else:
        return jsonify({"error": "Vehículo no encontrado"}), 404

@app.route('/obtener_personal_asignado/<int:contratista_id>', methods=['GET'])
def obtener_personal_asignado(contratista_id):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    sql = "SELECT id, nombre FROM personal WHERE contratista_id = %s"
    personal_asignado = execute_query(mydb, sql, params=(contratista_id,))

    # Convertir los resultados en un formato de lista de diccionarios
    personal_list = [{'id': p[0], 'nombre': p[1]} for p in personal_asignado]
    
    return jsonify(personal_list)


# Ruta de documentos
@app.route('/admin/documentos/<int:contratista_id>')
@login_required
def admin_documentos(contratista_id):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    sql_documentos = """
        SELECT * FROM cargas_sociales WHERE contratista_id = %s
        ORDER BY fecha_entrega DESC
    """
    documentos = execute_query(mydb, sql_documentos, params=(contratista_id,))

    nombre_contratista = obtener_valor("SELECT nombre FROM contratistas WHERE id = %s", (contratista_id,))

    # Organiza por año
    documentos_por_ano = {}
    for documento in documentos:
        ano = documento[2].year  # fecha_entrega
        if ano not in documentos_por_ano:
            documentos_por_ano[ano] = []
        documentos_por_ano[ano].append(documento)

    return render_template('documentos.html', documentos_por_ano=documentos_por_ano, contratista_id=contratista_id, nombre_contratista=nombre_contratista)


@app.route('/crear_documento/<int:contratista_id>', methods=['POST'])
def crear_documento(contratista_id):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    data = request.form.to_dict()
    data['contratista_id'] = contratista_id
    
    # Convertir el campo 'periodo' de yyyy-MM a yyyy-MM-dd
    if 'periodo' in data and data['periodo']:
        data['periodo'] = f"{data['periodo']}-01"
    else:
        data['periodo'] = None

    # Convertir valores de checkboxes de '1' o '0' a booleanos
    boolean_fields = [
        'pago_931', 'uatre', 'iva', 'pago_sepelio', 'f_931_afip', 'obra_social', 
        'rc_sueldos', 'altas', 'bajas', 'art', 's_vida', 'poliza_vida', 'tk_pago_vida'
    ]
    
    for field in boolean_fields:
        data[field] = int(data.get(field, 0))
    
    # Asegurar que otros campos estén presentes y establecer valores predeterminados si es necesario
    other_fields = ['personal_afectado', 'remun_bruta', 'prom_s_931']
    for field in other_fields:
        data[field] = data.get(field) or None
    
    sql = """
        INSERT INTO cargas_sociales (
            contratista_id, fecha_entrega, periodo, pago_931, uatre, iva, 
            pago_sepelio, f_931_afip, obra_social, personal_afectado, 
            rc_sueldos, altas, bajas, art, s_vida, poliza_vida, 
            tk_pago_vida, remun_bruta, prom_s_931
        ) VALUES (
            %(contratista_id)s, %(fecha_entrega)s, %(periodo)s, %(pago_931)s, 
            %(uatre)s, %(iva)s, %(pago_sepelio)s, %(f_931_afip)s, %(obra_social)s, 
            %(personal_afectado)s, %(rc_sueldos)s, %(altas)s, %(bajas)s, %(art)s, 
            %(s_vida)s, %(poliza_vida)s, %(tk_pago_vida)s, %(remun_bruta)s, %(prom_s_931)s
        )
    """
    
    try:
        execute_query(mydb, sql, params=data, commit=True)
        return jsonify({"message": "Documento creado correctamente."}), 200
    except mysql.connector.Error as err:
        print("Error MySQL:", err)
        return jsonify({"error": "Error al crear documento."}), 500
    except Exception as e:
        print("Error general:", e)
        return jsonify({"error": "Error desconocido al crear documento."}), 500


@app.route('/editar_documento/<int:documento_id>', methods=['POST'])
def editar_documento(documento_id):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    try:
        data = request.form.to_dict()

        # Convertir el campo 'periodo' de yyyy-MM a yyyy-MM-dd
        if 'periodo' in data and data['periodo']:
            data['periodo'] = f"{data['periodo']}-01"
        else:
            data['periodo'] = None

        # Convertir campos booleanos de '1' o '0' a booleanos
        boolean_fields = [
            'pago_931', 'uatre', 'iva', 'pago_sepelio', 'f_931_afip', 'obra_social', 
            'rc_sueldos', 'altas', 'bajas', 'art', 's_vida', 'poliza_vida', 'tk_pago_vida'
        ]
        
        for field in boolean_fields:
            data[field] = int(data.get(field, 0))
        
        # Asegurar que otros campos estén presentes y establecer valores predeterminados si es necesario
        other_fields = ['personal_afectado', 'remun_bruta', 'prom_s_931']
        for field in other_fields:
            data[field] = data.get(field) or None
        
        sql = """
            UPDATE cargas_sociales SET
                contratista_id = %(contratista_id)s,
                fecha_entrega = %(fecha_entrega)s,
                periodo = %(periodo)s,
                pago_931 = %(pago_931)s,
                uatre = %(uatre)s,
                iva = %(iva)s,
                pago_sepelio = %(pago_sepelio)s,
                f_931_afip = %(f_931_afip)s,
                obra_social = %(obra_social)s,
                personal_afectado = %(personal_afectado)s,
                rc_sueldos = %(rc_sueldos)s,
                altas = %(altas)s,
                bajas = %(bajas)s,
                art = %(art)s,
                s_vida = %(s_vida)s,
                poliza_vida = %(poliza_vida)s,
                tk_pago_vida = %(tk_pago_vida)s,
                remun_bruta = %(remun_bruta)s,
                prom_s_931 = %(prom_s_931)s
            WHERE id = %(id)s
        """
        data['id'] = documento_id
        execute_query(mydb, sql, params=data, commit=True)
        return jsonify({"message": "Documento actualizado correctamente."}), 200
    except mysql.connector.Error as err:
        mydb.rollback()
        print("Error MySQL:", err)
        return jsonify({"error": "Error al actualizar documento."}), 500
    except Exception as e:
        mydb.rollback()
        print("Error general:", e)
        return jsonify({"error": "Error desconocido al actualizar documento."}), 500


@app.route('/eliminar_documento/<int:documento_id>', methods=['DELETE'])
def eliminar_documento(documento_id):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    sql = "DELETE FROM cargas_sociales WHERE id = %s"
    try:
        execute_query(mydb, sql, params=(documento_id,), commit=True)
        return jsonify({"message": "Documento eliminado correctamente."}), 200
    except mysql.connector.Error as err:
        print("Error MySQL:", err)
        return jsonify({"error": "Error al eliminar documento."}), 500


@app.route('/obtener_documento/<int:documento_id>', methods=['GET'])
def obtener_documento(documento_id):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    sql = """
    SELECT id, contratista_id, fecha_entrega, periodo, pago_931, uatre, iva, 
           pago_sepelio, f_931_afip, obra_social, personal_afectado, rc_sueldos, 
           altas, bajas, art, s_vida, poliza_vida, tk_pago_vida, remun_bruta, prom_s_931 
    FROM cargas_sociales WHERE id=%s
    """
    documento = execute_query(mydb, sql, params=(documento_id,), fetchone=True)
    
    if documento:
        documento = list(documento)
        fecha_entrega = documento[2]

        if fecha_entrega:
            try:
                fecha_formateada = fecha_entrega.strftime('%Y-%m-%d')
                documento[2] = fecha_formateada
            except ValueError:
                documento[2] = 'Fecha inválida'

        periodo = documento[3]
        if periodo:
            try:
                periodo_formateado = periodo.strftime('%Y-%m')
                documento[3] = periodo_formateado
            except ValueError:
                documento[3] = 'Fecha inválida'        

        return jsonify({"documento": {
            "id": documento[0],
            "contratista_id": documento[1],
            "fecha_entrega": documento[2],
            "periodo": documento[3],
            "pago_931": documento[4],
            "uatre": documento[5],
            "iva": documento[6],
            "pago_sepelio": documento[7],
            "f_931_afip": documento[8],
            "obra_social": documento[9],
            "personal_afectado": documento[10],
            "rc_sueldos": documento[11],
            "altas": documento[12],
            "bajas": documento[13],
            "art": documento[14],
            "s_vida": documento[15],
            "poliza_vida": documento[16],
            "tk_pago_vida": documento[17],
            "remun_bruta": documento[18],
            "prom_s_931": documento[19]
        }}), 200
    else:
        return jsonify({"error": "Documento no encontrado"}), 404  


@app.route('/ver_documentos/<contratista_id>')
def ver_documentos(contratista_id):
    # Obtén la ruta base del contratista
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], contratista_id)
    
    # Lista de años disponibles
    years = []
    
    # Diccionario para almacenar los documentos encontrados
    documentos_por_año = {}
    
    # Recorrer los años disponibles en las carpetas
    if os.path.exists(base_path):
        for year in os.listdir(base_path):
            year_path = os.path.join(base_path, year)
            if os.path.isdir(year_path):
                years.append(year)
                documentos_por_año[year] = []
                
                # Recorrer los tipos de documentos
                for document_type in os.listdir(year_path):
                    document_path = os.path.join(year_path, document_type)
                    if os.path.isdir(document_path):
                        # Obtener los archivos dentro de cada tipo de documento
                        documentos_por_año[year].append(document_type)
    
    # Lista de documentos permitidos (Extraídos del select en documentos.html)
    documentos_permitidos = [
        'pago_931', 'uatre', 'iva', 'pago_sepelio', 'f_931_afip', 'obra_social', 
        'rc_sueldos', 'altas', 'bajas', 'art', 's_vida', 'poliza_vida', 'tk_pago_vida'
    ]
    
    return render_template(
        'ver_documentos.html', 
        contratista_id=contratista_id,  # Se pasa el ID del contratista
        years=years, 
        documentos_por_año=documentos_por_año, 
        documentos_permitidos=documentos_permitidos
    )


@app.route('/ver_documento/<contratista_id>/<year>/<documento>')
def ver_documento(contratista_id, year, documento):
    # Construir la ruta base
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], contratista_id, year, documento)
    
    # Verificar si es un directorio
    if os.path.isdir(base_path):
        # Listar los archivos dentro del directorio
        files = os.listdir(base_path)
        if files:
            # Seleccionar el primer archivo del directorio
            file_path = os.path.join(base_path, files[0])
        else:
            return "No se encontraron archivos en el directorio.", 404
    else:
        file_path = base_path  # Asumir que es un archivo

    # Verificar si la ruta es un archivo válido
    if os.path.isfile(file_path):
        return send_file(file_path)
    else:
        return "Archivo no encontrado o la ruta es incorrecta.", 404



# Funciones para subir archivos a carpeta
# Función para verificar si el archivo tiene una extensión permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/upload_file', methods=['POST'])
def upload_file():
    # Verificar si el archivo está presente en la solicitud
    if 'archivo' not in request.files:
        flash('No se ha seleccionado ningún archivo', 'danger')
        return redirect(request.url)
    
    file = request.files['archivo']
    
    # Verificar si se ha seleccionado un archivo
    if file.filename == '':
        flash('No se ha seleccionado ningún archivo', 'danger')
        return redirect(request.url)

    # Verificar si el archivo tiene una extensión permitida
    if file and allowed_file(file.filename):
        try:
            # Obtener los datos del formulario
            codigo_contratista = request.form['contratista_id']
            document_type = request.form['tipo_documento']
            upload_date = request.form['upload_date']

            # Asegurarse de que los campos obligatorios están presentes
            if not codigo_contratista or not document_type or not upload_date:
                flash('Datos del formulario incompletos', 'danger')
                return redirect(request.url)

            # Crear directorios basados en el código de contratista, año y tipo de documento
            year = datetime.strptime(upload_date, '%Y-%m-%d').strftime('%Y')
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], codigo_contratista, year, document_type)

            # Crear directorio si no existe
            os.makedirs(save_path, exist_ok=True)

            # Guardar el archivo
            file.save(os.path.join(save_path, file.filename))
            
            flash('Archivo subido exitosamente', 'success')
            return redirect(url_for('index'))
        
        except Exception as e:
            flash(f'Error al subir el archivo: {str(e)}', 'danger')
            return redirect(request.url)
    else:
        flash('Archivo no permitido o inválido', 'danger')
        return redirect(request.url)


def obtener_valor(consulta,parametro):
    if not ensure_db_connection(mydb):
        return render_template('error.html', message='Error de conexión con la base de datos')
    
    mycursor.execute(consulta,parametro)    
    # Obtener el resultado de la consulta
    resultado = mycursor.fetchone()
    
    if resultado:
        return resultado[0]  # Retorna el valor del primer campo encontrado
    else:
        return None  # Retorna None si no se encontraron resultados



if __name__ == '__main__':
    # db_connection = connect_with_retry()
    # Usa únicamente Waitress para correr el servidor
    app.run(debug=True)
    # serve(app, host='0.0.0.0', port=8000)
