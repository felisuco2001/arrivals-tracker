from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)  # Permitir CORS para GitHub Pages

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'arrivals-arrivals.b.aivencloud.com',
    'port': 18199,
    'user': 'avnadmin',
    'password': 'AVNS_iuKV6RnRMlRVcQe62j2',
    'database': 'defaultdb',
    'ssl_ca': 'ca.pem'
}

def get_db_connection():
    """Crear conexión a la base de datos"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error de conexión: {err}")
        return None

def init_database():
    """Inicializar la tabla si no existe"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Crear tabla si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS arrivals (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    fecha DATE NOT NULL,
                    tiempo_ida INT DEFAULT NULL,
                    tiempo_vuelta INT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_fecha (fecha)
                )
            """)
            conn.commit()
            print("✅ Tabla 'arrivals' verificada/creada correctamente")
        except mysql.connector.Error as err:
            print(f"❌ Error al crear tabla: {err}")
        finally:
            cursor.close()
            conn.close()

@app.route('/')
def home():
    """Endpoint de prueba"""
    return jsonify({
        'message': 'Arrivals Tracker API funcionando correctamente',
        'version': '1.0',
        'endpoints': [
            'GET / - Información de la API',
            'POST /api/arrivals - Registrar tiempo de viaje',
            'GET /api/arrivals - Obtener todos los registros',
            'GET /api/arrivals/stats - Obtener estadísticas'
        ]
    })

@app.route('/api/arrivals', methods=['POST'])
def create_arrival():
    """Registrar tiempo de ida o vuelta"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not data or 'fecha' not in data or 'tipo' not in data or 'tiempo' not in data:
            return jsonify({
                'success': False,
                'message': 'Faltan datos requeridos: fecha, tipo, tiempo'
            }), 400
        
        fecha = data['fecha']
        tipo = data['tipo']  # 'ida' o 'vuelta'
        tiempo = int(data['tiempo'])
        
        # Validar tipo
        if tipo not in ['ida', 'vuelta']:
            return jsonify({
                'success': False,
                'message': 'Tipo debe ser "ida" o "vuelta"'
            }), 400
        
        # Validar fecha
        try:
            datetime.strptime(fecha, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Formato de fecha inválido. Use YYYY-MM-DD'
            }), 400
        
        # Validar tiempo
        if tiempo <= 0 or tiempo > 999:
            return jsonify({
                'success': False,
                'message': 'El tiempo debe estar entre 1 y 999 minutos'
            }), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
        
        cursor = conn.cursor()
        
        try:
            # Verificar si ya existe un registro para esa fecha
            cursor.execute("SELECT id, tiempo_ida, tiempo_vuelta FROM arrivals WHERE fecha = %s", (fecha,))
            existing = cursor.fetchone()
            
            if existing:
                # Actualizar registro existente
                id_registro, tiempo_ida_actual, tiempo_vuelta_actual = existing
                
                if tipo == 'ida':
                    if tiempo_ida_actual is not None:
                        return jsonify({
                            'success': False,
                            'message': f'Ya existe un tiempo de ida registrado para {fecha}'
                        }), 409
                    
                    cursor.execute(
                        "UPDATE arrivals SET tiempo_ida = %s WHERE id = %s",
                        (tiempo, id_registro)
                    )
                else:  # vuelta
                    if tiempo_vuelta_actual is not None:
                        return jsonify({
                            'success': False,
                            'message': f'Ya existe un tiempo de vuelta registrado para {fecha}'
                        }), 409
                    
                    cursor.execute(
                        "UPDATE arrivals SET tiempo_vuelta = %s WHERE id = %s",
                        (tiempo, id_registro)
                    )
            else:
                # Crear nuevo registro
                if tipo == 'ida':
                    cursor.execute(
                        "INSERT INTO arrivals (fecha, tiempo_ida) VALUES (%s, %s)",
                        (fecha, tiempo)
                    )
                else:  # vuelta
                    cursor.execute(
                        "INSERT INTO arrivals (fecha, tiempo_vuelta) VALUES (%s, %s)",
                        (fecha, tiempo)
                    )
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': f'Tiempo de {tipo} registrado correctamente para {fecha}',
                'data': {
                    'fecha': fecha,
                    'tipo': tipo,
                    'tiempo': tiempo
                }
            })
            
        except mysql.connector.Error as err:
            conn.rollback()
            return jsonify({
                'success': False,
                'message': f'Error de base de datos: {str(err)}'
            }), 500
        
        finally:
            cursor.close()
            conn.close()
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error interno del servidor: {str(e)}'
        }), 500

@app.route('/api/arrivals', methods=['GET'])
def get_arrivals():
    """Obtener todos los registros"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT fecha, tiempo_ida, tiempo_vuelta, created_at, updated_at
                FROM arrivals
                ORDER BY fecha DESC
            """)
            
            registros = cursor.fetchall()
            
            # Convertir a formato compatible con el frontend
            data = []
            for registro in registros:
                fecha_str = registro['fecha'].strftime('%Y-%m-%d')
                
                if registro['tiempo_ida'] is not None:
                    data.append({
                        'fecha': fecha_str,
                        'tipo': 'ida',
                        'tiempo': registro['tiempo_ida']
                    })
                
                if registro['tiempo_vuelta'] is not None:
                    data.append({
                        'fecha': fecha_str,
                        'tipo': 'vuelta',
                        'tiempo': registro['tiempo_
