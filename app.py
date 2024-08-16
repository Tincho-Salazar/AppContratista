from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, abort
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import mysql.connector
import os


app = Flask(__name__)
app.secret_key = 'datiles2044'
app.config['UPLOAD_FOLDER'] = '/uploads/'  # Carpeta raíz donde se guardarán los archivos
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg', 'xls', 'xlsx', 'csv', 'docx'}

# Conectar a la base de datos
mydb = mysql.connector.connect(
    host="192.168.30.216",
    # host="127.0.0.1",
    user="root",
    password="toor",
    database="contratistas"
)

# Crear cursor
mycursor = mydb.cursor()


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
        return datetime.strptime(fecha_str, '%Y-%m-%d') if fecha_str else None
    except ValueError:
        print(f"Error al convertir la fecha: {fecha_str}")
        return None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/prueba')
def prueba():
    return render_template('prueba.html')

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


# Ruta de Contratistas
@app.route('/index_admin')
@login_required
def index_admin():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 6, type=int)
    search = request.args.get('search', '', type=str)

    search_query = ""
    search_values = []
 # Verificar si el rol del usuario no es administrador
    if session['rol'] != 'administrador':
        search_query += " WHERE c.habilitado = 1"

    # Añadir la búsqueda por CUIT o nombre
    if search:
        if search.isdigit():
            if search_query:
                search_query += " AND c.cuit LIKE %s"
            else:
                search_query = " WHERE c.cuit LIKE %s"
            search_values.append('%' + search + '%')
        else:
            if search_query:
                search_query += " AND c.nombre LIKE %s"
            else:
                search_query = " WHERE c.nombre LIKE %s"
            search_values.append('%' + search + '%')

    # Contar el total de resultados para la paginación
    count_query = f"SELECT COUNT(*) FROM contratistas c {search_query}"
    mycursor.execute(count_query, search_values)
    total_count = mycursor.fetchone()[0]
    total_pages = (total_count + page_size - 1) // page_size

    offset = (page - 1) * page_size

    query = f"""
        SELECT c.id, c.nombre, c.cuit, c.habilitado,
        (SELECT COUNT(*) FROM personal p WHERE p.contratista_id = c.id AND p.baja IS NULL) AS empleados_count,
        (SELECT COUNT(*) FROM vehiculos v WHERE v.contratista_id = c.id AND v.habilitado = 1) AS vehiculos_count,
        (SELECT COUNT(*) FROM cargas_sociales d WHERE d.contratista_id = c.id) AS documentos_count
        FROM contratistas c 
        {search_query}
        ORDER BY c.nombre ASC
        LIMIT %s OFFSET %s
    """
    search_values.extend([page_size, offset])
    mycursor.execute(query, search_values)
    contratistas = mycursor.fetchall()
    # print(contratistas)

    return render_template(
        'index.html',
        contratistas=contratistas,
        current_page=page,
        total_pages=total_pages,
        page_size=page_size,
        search=search
    )

@app.route('/admin/contratistas')
def admin_contratistas():
    if 'usuario' not in session or session['rol'] != 'administrador':
        return redirect('/admin/login')
    
    mycursor.execute("SELECT * FROM contratistas Order By nombre")
    contratistas = mycursor.fetchall()
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
    mycursor.execute(sql, val)
    mydb.commit()
    return jsonify({"message": "El contratista ha sido creado correctamente."}), 200
    # return redirect('/admin/contratistas')

@app.route('/editar_contratista/<int:contratista_id>', methods=['POST'])
def editar_contratista(contratista_id):
    try:
        nombre = request.form['nombre']
        cuit = request.form['cuit']
        categoria = request.form['categoria']
        habilitado = 1 if 'habilitado' in request.form else 0

        # Ejecutar la actualización en la base de datos
        sql = """
            UPDATE contratistas
            SET nombre = %s, cuit = %s, categoria = %s, habilitado = %s
            WHERE id = %s
        """
        val = (nombre, cuit, categoria, habilitado, contratista_id)
        mycursor.execute(sql, val)

        # Confirmar los cambios
        mydb.commit()

        return jsonify({'message': 'Contratista actualizado correctamente'}), 200
    
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/eliminar_contratista/<int:contratista_id>', methods=['DELETE'])
def eliminar_contratista(contratista_id):
    try:
        # Ejecutar la eliminación en la base de datos
        sql = "DELETE FROM contratistas WHERE id = %s"
        val = (contratista_id,)
        mycursor.execute(sql, val)

        # Confirmar los cambios
        mydb.commit()

        return jsonify({'message': 'Contratista eliminado correctamente'}), 200
    
    except Exception as e:
        return jsonify({'message': str(e)}), 500


# Ruta de Usuarios
@app.route('/admin/usuarios')
@login_required
def admin_usuarios():    
    # Obtener datos de usuarios desde la base de datos
    mycursor.execute("SELECT * FROM login")
    usuarios = mycursor.fetchall()
    return render_template('usuario.html', usuarios=usuarios)

@app.route('/usuarios')
def usuarios():
    mycursor.execute('SELECT id, usuario, contrasena, rol FROM login')
    usuarios = mycursor.fetchall()
    return render_template('usuario.html', usuarios=usuarios, usuario_editado=None)

@app.route('/crear_usuario', methods=['POST'])
def crear_usuario():
    usuario = request.form['usuario']
    contrasena = request.form['contrasena']
    rol = request.form['rol']

    hashed_password = generate_password_hash(contrasena, method='pbkdf2:sha256')
    
    sql = 'INSERT INTO login (usuario, contrasena, rol) VALUES (%s, %s, %s)'
    val = (usuario, hashed_password, rol)
    mycursor.execute(sql, val)
    mydb.commit()
    
    return jsonify({'message': 'Usuario creado exitosamente'})

@app.route('/editar_usuario/<int:id>', methods=['POST'])
def editar_usuario(id):
    usuario = request.form['usuario']
    contrasena = request.form['contrasena']
    rol = request.form['rol']

    hashed_password = generate_password_hash(contrasena, method='pbkdf2:sha256')
    
    sql = 'UPDATE login SET usuario = %s, contrasena = %s, rol = %s WHERE id = %s'
    val = (usuario, hashed_password, rol, id)
    mycursor.execute(sql, val)
    mydb.commit()
    
    return jsonify({'message': 'Usuario actualizado exitosamente'})

@app.route('/eliminar_usuario/<int:id>', methods=['DELETE'])
def eliminar_usuario(id):
    sql = 'DELETE FROM login WHERE id = %s'
    val = (id,)
    mycursor.execute(sql, val)
    mydb.commit()

    return jsonify({'message': 'Usuario eliminado exitosamente'})


# Ruta de Calendario
@app.route('/admin/calendario')
@login_required
def admin_calendario():
    return render_template('admin_calendario.html')

# Ruta de Login
@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['usuario']
        password = request.form['contrasena']        
        rol = ""
        # Verificar las credenciales del usuario
        mycursor.execute("SELECT * FROM login WHERE usuario = %s", (username,))
        user = mycursor.fetchone()
        
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
        
        # Insertar nuevo usuario en la base de datos
        mycursor.execute("INSERT INTO login (usuario, contrasena, rol) VALUES (%s, %s, 'user')", (new_username, hashed_password))
        mydb.commit()
        flash('Registro exitoso', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Has cerrado sesión exitosamente', 'success')
    return redirect(url_for('login'))  

# Ruta de Empleados 
@app.route('/admin/empleados/<int:contratista_id>')
@login_required
def admin_empleados(contratista_id):   
    nombre_contratista=obtener_valor("SELECT nombre FROM contratistas WHERE id = %s", (contratista_id,))
    mycursor.execute("""
    SELECT id, contratista_id, cuil_dni, nombre, puesto, alta, baja, sueldo_general FROM personal 
    WHERE contratista_id = %s ORDER BY alta DESC
""", (contratista_id,))
    empleados = mycursor.fetchall()

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
    data = request.form

    # Consulta SQL para insertar en la tabla personal
    sql = """
        INSERT INTO personal (contratista_id, cuil_dni, nombre, puesto, alta, sueldo_general)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    try:
        # Ejecutar la consulta SQL con los datos proporcionados y el contratista_id de la URL
        mycursor.execute(sql, (contratista_id, data['cuil_dni'], data['nombre'], data['puesto'], data['alta'], data['sueldo_general']))
        mydb.commit()

        return jsonify({"message": "Empleado creado correctamente."}), 200
    except mysql.connector.Error as err:
        print("Error MySQL:", err)  # Imprimir el error en la consola para depurar
        return jsonify({"error": "Error al crear empleado."}), 500

@app.route('/editar_empleado/<int:empleado_id>', methods=['POST'])
def editar_empleado(empleado_id):
    data = request.form

    # Consulta SQL para actualizar en la tabla personal
    sql = """
        UPDATE personal
        SET cuil_dni=%s, nombre=%s, puesto=%s, alta=%s, sueldo_general=%s
        WHERE id=%s
    """

    try:
        # Ejecutar la consulta SQL con los datos proporcionados y el empleado_id de la URL
        mycursor.execute(sql, (data['cuil_dni'], data['nombre'], data['puesto'], data['alta'], data['sueldo_general'], empleado_id))
        mydb.commit()

        return jsonify({"message": "Empleado actualizado correctamente."}), 200
    except mysql.connector.Error as err:
        print("Error MySQL:", err)  # Imprimir el error en la consola para depurar
        return jsonify({"error": "Error al actualizar empleado."}), 500

@app.route('/eliminar_empleado/<int:empleado_id>', methods=['DELETE'])
def eliminar_empleado(empleado_id):
    sql = "DELETE FROM personal WHERE id=%s"

    try:
        # Ejecutar la consulta SQL con el empleado_id de la URL
        mycursor.execute(sql, (empleado_id,))
        mydb.commit()

        return jsonify({"message": "Empleado eliminado correctamente."}), 200
    except mysql.connector.Error as err:
        print("Error MySQL:", err)  # Imprimir el error en la consola para depurar
        return jsonify({"error": "Error al eliminar empleado."}), 500

@app.route('/obtener_empleado/<int:empleado_id>', methods=['GET'])
def obtener_empleado(empleado_id):
    sql = "SELECT id,contratista_id,cuil_dni,nombre,puesto,DATE_FORMAT(alta, '%d/%m/%Y') as alta,DATE_FORMAT(baja, '%d/%m/%Y') as baja,sueldo_general FROM personal WHERE id=%s"
    mycursor.execute(sql, (empleado_id,))
    empleado = mycursor.fetchone()
    
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
    nombre_contratista=obtener_valor("SELECT nombre FROM contratistas WHERE id = %s", (contratista_id,))
    mycursor.execute("""
        SELECT id, contratista_id, Unidad, patente, poliza, revision_tecnica_desde, revision_tecnica_hasta, pago, conductor, carnet_conducir, vigencia, habilitado
        FROM vehiculos
        WHERE contratista_id = %s
        ORDER BY id DESC
    """, (contratista_id,))
    vehiculos = mycursor.fetchall()

    # Organiza por año
    vehiculos_por_ano = {}
    for vehiculo in vehiculos:
        vehiculo = list(vehiculo)  # Convertir la tupla a una lista
        poliza=vehiculo[4] 
        tecnica_desde=vehiculo[5] 
        tecnica_hasta=vehiculo[6] 
        pago=vehiculo[7] 
        vigencia=vehiculo[10] 
        # for i in range(4, 11):  # Indices de las fechas en la tabla vehiculos        
        if poliza:
            try:
                fecha_formateada = poliza.strftime('%d/%m/%Y')
                vehiculo[4] = fecha_formateada
                ano=poliza.year
            except ValueError:
                vehiculo[4] = 'Fecha inválida'
        else:
            ano ='Desconocido'

        if tecnica_desde:
            try:
                fecha_formateada = tecnica_desde.strftime('%d/%m/%Y')
                vehiculo[5] = fecha_formateada
            except ValueError:
                vehiculo[5] = 'Fecha inválida'
        if tecnica_hasta:
            try:
                fecha_formateada = tecnica_hasta.strftime('%d/%m/%Y')
                vehiculo[6] = fecha_formateada
            except ValueError:
                vehiculo[6] = 'Fecha inválida'
        if pago:
            try:
                fecha_formateada = pago.strftime('%d/%m/%Y')
                vehiculo[7] = fecha_formateada
            except ValueError:
                vehiculo[7] = 'Fecha inválida'
        if vigencia:
            try:
                fecha_formateada = vigencia.strftime('%d/%m/%Y')
                vehiculo[10] = fecha_formateada
            except ValueError:
                vehiculo[10] = 'Fecha inválida'

        if ano not in vehiculos_por_ano:
            vehiculos_por_ano[ano] = []
        vehiculos_por_ano[ano].append(tuple(vehiculo))  # Convertir la lista de vuelta a una tupla si es necesario

    return render_template('vehiculos.html', vehiculos_por_ano=vehiculos_por_ano, contratista_id=contratista_id, nombre_contratista=nombre_contratista)

@app.route('/crear_vehiculo/<int:contratista_id>', methods=['POST'])
def crear_vehiculo(contratista_id):
    data = request.form    
    
    # Consulta SQL para insertar en la tabla vehiculos
    sql = """
        INSERT INTO vehiculos (contratista_id, Unidad, patente, poliza, revision_tecnica_desde, revision_tecnica_hasta, pago, conductor, carnet_conducir, vigencia, habilitado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    try:
        # Convertir las fechas a formato datetime si están presentes
        poliza = datetime.strptime(data['poliza'], '%Y-%m-%d') if data.get('poliza') else None
        revision_desde = datetime.strptime(data['revision_desde'], '%Y-%m-%d') if data.get('revision_desde') else None
        revision_hasta = datetime.strptime(data['revision_hasta'], '%Y-%m-%d') if data.get('revision_hasta') else None
        pago = datetime.strptime(data['pago'], '%Y-%m-%d') if data.get('pago') else None
        vigencia = datetime.strptime(data['vigencia'], '%Y-%m-%d') if data.get('vigencia') else None

        # Convertir el campo habilitado a un valor entero (0 o 1)
        habilitado = 1 if data.get('habilitado') == 'on' else 0

        # Ejecutar la consulta SQL con los datos proporcionados y el contratista_id de la URL
        mycursor.execute(sql, (
            contratista_id, data['unidad'], data['patente'], poliza, revision_desde, revision_hasta, pago,
            data['conductor'], data['carnet'], vigencia, habilitado
        ))
        mydb.commit()

        return jsonify({"message": "Vehículo creado correctamente."}), 200
    except mysql.connector.Error as err:
        print("Error MySQL:", err)  # Imprimir el error en la consola para depurar
        return jsonify({"error": "Error al crear vehículo."}), 500
    except Exception as e:
        print("Error general:", e)  # Imprimir cualquier otro error
        return jsonify({"error": "Error desconocido al crear vehículo."}), 500


@app.route('/editar_vehiculo/<int:vehiculo_id>', methods=['POST'])
def editar_vehiculo(vehiculo_id):
    data = request.form

    # Consulta SQL para actualizar en la tabla vehiculos
    sql = """
        UPDATE vehiculos
        SET Unidad=%s, patente=%s, poliza=%s, revision_tecnica_desde=%s, revision_tecnica_hasta=%s, pago=%s, conductor=%s, carnet_conducir=%s, vigencia=%s, habilitado=%s
        WHERE id=%s
    """    
    try:
        # Convertir las fechas a formato datetime si están presentes
        # poliza = datetime.strptime(data['poliza'], '%Y-%m-%d') if data['poliza'] else None
        # revision_desde = datetime.strptime(data['revision_tecnica_desde'], '%Y-%m-%d') if data['revision_tecnica_desde'] else None
        # revision_hasta = datetime.strptime(data['revision_tecnica_hasta'], '%Y-%m-%d') if data['revision_tecnica_hasta'] else None
        # pago = datetime.strptime(data['pago'], '%Y-%m-%d') if data['pago'] else None
        # vigencia = datetime.strptime(data['vigencia'], '%Y-%m-%d') if data['vigencia'] else None
        poliza = convertir_fecha(data.get('poliza'))
        revision_desde = convertir_fecha(data.get('revision_tecnica_desde'))
        revision_hasta = convertir_fecha(data.get('revision_tecnica_hasta'))
        pago = convertir_fecha(data.get('pago'))
        vigencia = convertir_fecha(data.get('vigencia'))

        # Ejecutar la consulta SQL con los datos proporcionados y el vehiculo_id de la URL
        mycursor.execute(sql, (
            data['unidad'], data['patente'], poliza, revision_desde, revision_hasta, pago,
            data['conductor'], data['carnet'], vigencia, data['habilitado'], vehiculo_id
        ))
        mydb.commit()

        return jsonify({"message": "Vehículo actualizado correctamente."}), 200
    except mysql.connector.Error as err:
        print("Error MySQL:", err)  # Imprimir el error en la consola para depurar
        return jsonify({"error": "Error al actualizar vehículo."}), 500

@app.route('/eliminar_vehiculo/<int:vehiculo_id>', methods=['DELETE'])
def eliminar_vehiculo(vehiculo_id):
    sql = "DELETE FROM vehiculos WHERE id=%s"

    try:
        # Ejecutar la consulta SQL con el vehiculo_id de la URL
        mycursor.execute(sql, (vehiculo_id,))
        mydb.commit()

        return jsonify({"message": "Vehículo eliminado correctamente."}), 200
    except mysql.connector.Error as err:
        print("Error MySQL:", err)  # Imprimir el error en la consola para depurar
        return jsonify({"error": "Error al eliminar vehículo."}), 500

@app.route('/obtener_vehiculo/<int:vehiculo_id>', methods=['GET'])
def obtener_vehiculo(vehiculo_id):
    sql = "SELECT id, contratista_id, Unidad, patente, poliza, revision_tecnica_desde, revision_tecnica_hasta, pago, conductor, carnet_conducir, vigencia, habilitado FROM vehiculos WHERE id=%s"
    mycursor.execute(sql, (vehiculo_id,))
    vehiculo = mycursor.fetchone()
    
    if vehiculo:
        # Convertir las fechas a formato de cadena si no son None
        vehiculo = list(vehiculo)        
        poliza=vehiculo[4] 
        tecnica_desde=vehiculo[5] 
        tecnica_hasta=vehiculo[6] 
        pago=vehiculo[7] 
        vigencia=vehiculo[10] 
        # for i in range(4, 11):  # Indices de las fechas en la tabla vehiculos        
        if poliza:
            try:
                fecha_formateada = poliza.strftime('%Y-%m-%d')
                vehiculo[4] = fecha_formateada
                ano=poliza.year
            except ValueError:
                vehiculo[4] = 'Fecha inválida'
        if tecnica_desde:
            try:
                fecha_formateada = tecnica_desde.strftime('%Y-%m-%d')
                vehiculo[5] = fecha_formateada
            except ValueError:
                vehiculo[5] = 'Fecha inválida'
        if tecnica_hasta:
            try:
                fecha_formateada = tecnica_hasta.strftime('%Y-%m-%d')
                vehiculo[6] = fecha_formateada
            except ValueError:
                vehiculo[6] = 'Fecha inválida'
        if pago:
            try:
                fecha_formateada = pago.strftime('%Y-%m-%d')
                vehiculo[7] = fecha_formateada
            except ValueError:
                vehiculo[7] = 'Fecha inválida'
        if vigencia:
            try:
                fecha_formateada = vigencia.strftime('%Y-%m-%d')
                vehiculo[10] = fecha_formateada
            except ValueError:
                vehiculo[10] = 'Fecha inválida'

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
            "habilitado": vehiculo[11]
        }}), 200
    else:
        return jsonify({"error": "Vehículo no encontrado"}), 404

# Ruta de documentos
@app.route('/admin/documentos/<int:contratista_id>')
@login_required
def admin_documentos(contratista_id):
    mycursor.execute("""
        SELECT * FROM cargas_sociales WHERE contratista_id = %s
        ORDER BY fecha_entrega DESC
    """, (contratista_id,))
    documentos = mycursor.fetchall()
    nombre_contratista=obtener_valor("SELECT nombre FROM contratistas WHERE id = %s", (contratista_id,))
    # Organiza por año
    documentos_por_ano = {}    
    for documento in documentos:
        ano = documento[2].year  # fecha_entrega
        if ano not in documentos_por_ano:
            documentos_por_ano[ano] = []
        documentos_por_ano[ano].append(documento)

    return render_template('documentos.html', documentos_por_ano=documentos_por_ano, contratista_id=contratista_id,nombre_contratista=nombre_contratista)

@app.route('/crear_documento/<int:contratista_id>', methods=['POST'])
def crear_documento(contratista_id):
    data = request.form.to_dict()
    data['contratista_id'] = contratista_id
    
    # Convertir el valor del campo 'periodo' a 'yyyy-mm-dd'
    # periodo_str = data.get('periodo')
    # if periodo_str:
    #     periodo_date = datetime.strptime(periodo_str, '%Y-%m')
    #     data['periodo'] = periodo_date.strftime('%Y-%m-%d')
    # else:
    #     data['periodo'] = None
 # Convertir el campo 'periodo' de yyyy-MM a yyyy-MM-dd
    if 'periodo' in data and data['periodo']:
        data['periodo'] = f"{data['periodo']}-01"
    else:
        data['periodo']  = None  

    print(data['periodo'])
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
    
    mycursor.execute(sql, data)
    mydb.commit()
    return jsonify({"message": "Documento creado correctamente."}), 200


@app.route('/editar_documento/<int:documento_id>', methods=['POST'])
def editar_documento(documento_id):
    try:
        data = request.form.to_dict()
        
 # Convertir el campo 'periodo' de yyyy-MM a yyyy-MM-dd
        if 'periodo' in data and data['periodo']:
            data['periodo'] = f"{data['periodo']}-01"
        else:
            data['periodo']  = None  

        print(data['periodo'])

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
        mycursor.execute(sql, data)
        mydb.commit()
        return jsonify({"message": "Documento actualizado correctamente."}), 200
    except Exception as e:
        mydb.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/eliminar_documento/<int:documento_id>', methods=['DELETE'])
def eliminar_documento(documento_id):
    sql = "DELETE FROM cargas_sociales WHERE id = %s"
    val = (documento_id,)
    mycursor.execute(sql, val)
    mydb.commit()
    return jsonify({"message": "Documento eliminado correctamente."}), 200

@app.route('/obtener_documento/<int:documento_id>', methods=['GET'])
def obtener_documento(documento_id):
    sql = "SELECT id, contratista_id, fecha_entrega, periodo, pago_931, uatre, iva, pago_sepelio, f_931_afip, obra_social, personal_afectado, rc_sueldos, altas, bajas, art, s_vida, poliza_vida, tk_pago_vida, remun_bruta, prom_s_931 FROM cargas_sociales WHERE id=%s"
    mycursor.execute(sql, (documento_id,))
    documento = mycursor.fetchone()
    
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
    
    mycursor.execute(consulta,parametro)    
    # Obtener el resultado de la consulta
    resultado = mycursor.fetchone()
    
    if resultado:
        return resultado[0]  # Retorna el valor del primer campo encontrado
    else:
        return None  # Retorna None si no se encontraron resultados



if __name__ == '__main__':
    app.run(debug=True)
