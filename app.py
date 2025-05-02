import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
import bcrypt
import re
from github import Github
import base64
import json
import numpy as np

# Configurar la página al inicio
st.set_page_config(page_title="Arrendamiento MarTech Rent", layout="wide")

# Estilos CSS personalizados para mejorar la interfaz
st.markdown("""
    <style>
    /* Fondo claro y texto oscuro */
    .stApp {
        background-color: #f5f7fa;
        color: #333333;
    }
    /* Estilo para los botones */
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-weight: bold;
        transition: background-color 0.3s;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    /* Botón Editar con color diferente */
    .stButton>button.edit-button {
        background-color: #FFA500;
        color: white;
    }
    .stButton>button.edit-button:hover {
        background-color: #e69500;
    }
    /* Estilo para los mensajes de éxito y error */
    .stAlert {
        border-radius: 5px;
        font-weight: bold;
    }
    /* Estilo para los títulos */
    h1, h2, h3 {
        color: #2c3e50;
    }
    /* Estilo para las tablas */
    .dataframe th {
        background-color: #2c3e50;
        color: white;
    }
    .dataframe td {
        background-color: #ffffff;
        border: 1px solid #ddd;
    }
    </style>
""", unsafe_allow_html=True)

# Configuración de GitHub (usar secretos en Streamlit Cloud)
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", None)
REPO_NAME = "Yorchemtz24/rentapp"
if not GITHUB_TOKEN:
    st.error("GitHub token not configured. Please set GITHUB_TOKEN in Streamlit secrets.")

# Crear carpeta de base de datos si no existe
DB_DIR = "db"
DB_PATH = f"{DB_DIR}/database.db"
if not os.path.exists(DB_DIR):
    try:
        os.makedirs(DB_DIR)
        print(f"Created directory: {DB_DIR}")
    except Exception as e:
        print(f"Error creating directory {DB_DIR}: {e}")

# Inicializar base de datos SQLite
def initialize_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Crear tablas si no existen
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equipos (
                id_equipo TEXT PRIMARY KEY,
                marca TEXT,
                modelo TEXT,
                caracteristicas TEXT,
                estado TEXT,
                precio_base REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id_cliente TEXT PRIMARY KEY,
                nombre TEXT,
                contacto TEXT,
                correo TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rentas (
                id_renta TEXT PRIMARY KEY,
                cliente TEXT,
                contacto TEXT,
                equipos TEXT,  -- Lista de equipos en formato JSON
                fecha_inicio TEXT,
                fecha_fin TEXT,
                subtotal REAL,
                precio REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                usuario TEXT PRIMARY KEY,
                password TEXT
            )
        """)
        # Insertar usuario admin si no existe
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE usuario = 'admin'")
        if cursor.fetchone()[0] == 0:
            hashed_password = bcrypt.hashpw("12345".encode('utf-8'), bcrypt.gensalt())
            cursor.execute("INSERT INTO usuarios (usuario, password) VALUES (?, ?)", 
                          ("admin", hashed_password.decode('utf-8')))
            print("Created admin user in usuarios table")
        conn.commit()
        conn.close()
        print(f"Initialized database: {DB_PATH}")
    except Exception as e:
        print(f"Error initializing database: {e}")

initialize_db()

# Función para sincronizar database.db con GitHub
def update_db_in_github():
    if not GITHUB_TOKEN:
        st.error("Cannot update GitHub: GITHUB_TOKEN is not set.")
        return
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        with open(DB_PATH, "rb") as file:
            content = file.read()
        try:
            contents = repo.get_contents("db/database.db")
            repo.update_file(contents.path, "Update database.db", content, contents.sha)
        except:
            repo.create_file("db/database.db", "Create database.db", content)
        st.write("✅ Updated database.db in GitHub")
    except Exception as e:
        st.error(f"❌ Error updating database in GitHub: {e}")

# Funciones auxiliares
def read_table(table_name):
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Error al leer {table_name}: {e}")
        return pd.DataFrame()

def write_table(table_name, df):
    try:
        conn = sqlite3.connect(DB_PATH)
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        conn.close()
        st.write(f"✅ Successfully wrote to {table_name}")
        update_db_in_github()  # Sincronizar con GitHub
        return True
    except Exception as e:
        st.error(f"❌ Error al escribir en {table_name}: {e}")
        return False

def validate_email(email):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None

def validate_phone(phone):
    pattern = r"^\+?\d{10,15}$"
    return re.match(pattern, phone) is not None

# Función para colorear el estado de los equipos
def highlight_status(val):
    color = 'green' if val == 'disponible' else 'orange' if val == 'rentado' else 'red'
    return f'background-color: {color}; color: white;'

# Autenticación
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.subheader("🔐 Iniciar Sesión")
    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Iniciar Sesión")
        if submitted:
            if not username or not password:
                st.error("Por favor, ingrese usuario y contraseña")
            else:
                df_usuarios = read_table("usuarios")
                user = df_usuarios[df_usuarios["usuario"] == username]
                if user.empty:
                    st.error("Usuario no encontrado")
                else:
                    stored_password = user.iloc[0]["password"]
                    try:
                        if not isinstance(stored_password, str):
                            st.error(f"Tipo de contraseña almacenada inválido: {type(stored_password)}")
                            st.write(f"Contenido de stored_password: {stored_password}")
                            raise ValueError("La contraseña almacenada no es un string")
                        stored_password = stored_password.encode('utf-8')
                        if bcrypt.checkpw(password.encode('utf-8'), stored_password):
                            st.session_state.authenticated = True
                            st.success("✅ Inicio de sesión exitoso")
                            st.rerun()
                        else:
                            st.error("❌ Contraseña incorrecta")
                    except Exception as e:
                        st.error(f"❌ Error al verificar contraseña: {e}")
                        st.write(f"Contenido de stored_password: {stored_password.decode('utf-8') if isinstance(stored_password, bytes) else stored_password}")
else:
    # Menú con botones en la barra lateral
    view = st.sidebar.radio("Navegación", [
        "📋 Registro de Equipos",
        "👤 Registro de Clientes",
        "📝 Nueva Renta",
        "🔍 Seguimiento de Rentas",
        "📦 Inventario",
        "📁 Listado de Clientes",
        "📁 Listado de Rentas",
        "✅ Finalizar Renta"
    ])
    # Botón de Cerrar Sesión en la barra lateral
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state.authenticated = False
        st.success("✅ Sesión cerrada")
        st.rerun()

    # --- Secciones de la aplicación ---
    if view == "📋 Registro de Equipos":
        st.subheader("📋 Registrar Nuevo Equipo")
        with st.form("form_equipo"):
            df_equipos = read_table("equipos")
            nuevo_id = f"ME{len(df_equipos) + 1:04d}"
            st.text_input("ID del Equipo", value=nuevo_id, disabled=True)
            marca = st.text_input("Marca")
            modelo = st.text_input("Modelo")
            caracteristicas = st.text_area("Características")
            estado = st.selectbox("Estado", ["disponible", "rentado", "mantenimiento"])
            precio_base = st.number_input("Precio Base de Renta ($)", min_value=0.0, step=0.01)
            submitted = st.form_submit_button("Registrar Equipo")
            if submitted:
                if not marca or not modelo:
                    st.error("❌ Marca y modelo son obligatorios")
                elif precio_base <= 0:
                    st.error("❌ El precio base debe ser mayor a 0")
                else:
                    nuevo = pd.DataFrame([[nuevo_id, marca, modelo, caracteristicas, estado, precio_base]], 
                                        columns=["id_equipo", "marca", "modelo", "caracteristicas", "estado", "precio_base"])
                    st.write(f"Attempting to register equipo: {nuevo.to_dict()}")
                    df_equipos = pd.concat([df_equipos, nuevo], ignore_index=True)
                    if write_table("equipos", df_equipos):
                        st.success("✅ Equipo registrado correctamente")
                    else:
                        st.error("❌ Fallo al registrar el equipo")

    # Aquí continúa el resto del código...
    # (Se omite por límite de caracteres, pero puedes pegar el resto del código original aquí)
