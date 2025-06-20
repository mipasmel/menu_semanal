from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
import os
import json

app = Flask(__name__)
CORS(app) # Habilitar CORS para permitir solicitudes desde el frontend

# Configuración de la base de datos PostgreSQL
# Render proveerá esta URL en las variables de entorno
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost:5432/mydatabase')

def get_db_connection():
    """Establece y devuelve una conexión a la base de datos."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    """Inicializa la base de datos creando la tabla diet_plans si no existe."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS diet_plans (
                id SERIAL PRIMARY KEY,
                plan_data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cur.close()
        print("Tabla 'diet_plans' verificada/creada exitosamente.")
    except Exception as e:
        print(f"Error al inicializar la base de datos: {e}")
    finally:
        if conn:
            conn.close()

# Inicializar la base de datos al iniciar la aplicación
with app.app_context():
    init_db()

# Ruta para servir el frontend (index.html)
# Render por defecto busca el home, así que esto servirá la app.
@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'index.html')

# Ruta para servir cualquier otro archivo estático (CSS, JS, etc.)
# Para este caso simple, con index.html y sin otras dependencias de archivos en carpetas,
# la ruta '/' debería ser suficiente, pero es buena práctica tener esto si crece la app.
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)


@app.route('/api/diet_plan', methods=['POST'])
def create_diet_plan():
    """Crea un nuevo plan de dieta en la base de datos."""
    data = request.get_json()
    if not data or 'plan' not in data:
        return jsonify({"error": "Plan de dieta no proporcionado"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Convertir el objeto Python (plan) a una cadena JSON para almacenar en JSONB
        plan_json = json.dumps(data['plan'])
        cur.execute("INSERT INTO diet_plans (plan_data) VALUES (%s) RETURNING id;", (plan_json,))
        plan_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return jsonify({"message": "Plan de dieta guardado exitosamente", "id": plan_id}), 201
    except Exception as e:
        print(f"Error al guardar el plan de dieta: {e}")
        return jsonify({"error": "Error al guardar el plan de dieta", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/diet_plan/<int:plan_id>', methods=['GET'])
def get_diet_plan(plan_id):
    """Obtiene un plan de dieta por su ID."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT plan_data FROM diet_plans WHERE id = %s;", (plan_id,))
        plan_row = cur.fetchone()
        cur.close()
        if plan_row:
            # Los datos JSONB se recuperan como objeto Python/diccionario directamente por psycopg2
            return jsonify({"id": plan_id, "plan": plan_row[0]}), 200
        else:
            return jsonify({"message": "Plan de dieta no encontrado"}), 404
    except Exception as e:
        print(f"Error al obtener el plan de dieta: {e}")
        return jsonify({"error": "Error al obtener el plan de dieta", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/diet_plan/<int:plan_id>', methods=['PUT'])
def update_diet_plan(plan_id):
    """Actualiza un plan de dieta existente en la base de datos."""
    data = request.get_json()
    if not data or 'plan' not in data:
        return jsonify({"error": "Plan de dieta actualizado no proporcionado"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Convertir el objeto Python (plan) a una cadena JSON para almacenar en JSONB
        updated_plan_json = json.dumps(data['plan'])
        cur.execute("UPDATE diet_plans SET plan_data = %s WHERE id = %s;", (updated_plan_json, plan_id))
        
        if cur.rowcount == 0:
            conn.rollback() # No se encontró el ID, revertir cambios si los hubiera
            return jsonify({"message": "Plan de dieta no encontrado para actualizar"}), 404
        
        conn.commit()
        cur.close()
        return jsonify({"message": f"Plan de dieta ID {plan_id} actualizado exitosamente"}), 200
    except Exception as e:
        print(f"Error al actualizar el plan de dieta: {e}")
        return jsonify({"error": "Error al actualizar el plan de dieta", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
