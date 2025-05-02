import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
import bcrypt
import re
import plotly.express as px  # Para gráficos
from github import Github
import base64
import json
import numpy as np

# Configuración de la página
st.set_page_config(page_title="Arrendamiento MarTech Rent", layout="wide")

# Estilos CSS personalizados
st.markdown("""
    <style>
    .stApp {
        background-color: #f5f7fa;
        color: #333333;
    }
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
    .stButton>button.edit-button {
        background-color: #FFA500;
        color: white;
    }
    .stButton>button.edit-button:hover {
        background-color: #e69500;
    }
    .stAlert {
        border-radius: 5px;
        font-weight: bold;
    }
    h1, h2, h3 {
        color: #2c3e50;
    }
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
                equipos TEXT,
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
@st.cache_data
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
else:
    view = st.sidebar.radio("Navegación", [
        "🏠 Inicio",
        "📋 Registro de Equipos",
        "👤 Registro de Clientes",
        "📝 Nueva Renta",
        "🔍 Seguimiento de Rentas",
        "📦 Inventario",
        "📁 Listado de Clientes",
        "📁 Listado de Rentas",
        "✅ Finalizar Renta",
        "📊 Informes"
    ])

    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state.authenticated = False
        st.success("✅ Sesión cerrada")
        st.rerun()

    if view == "🏠 Inicio":
        st.header("🏠 Dashboard Principal")
        col1, col2, col3 = st.columns(3)
        equipos = read_table("equipos")
        clientes = read_table("clientes")
        rentas = read_table("rentas")
        col1.metric("Equipos Totales", len(equipos))
        col2.metric("Clientes Registrados", len(clientes))
        col3.metric("Rentas Activas", len(rentas))

    elif view == "📊 Informes":
        st.header("📈 Informes y Estadísticas")
        tab1, tab2, tab3 = st.tabs(["Equipos", "Clientes", "Rentas"])
        with tab1:
            equipos_df = read_table("equipos")
            fig = px.pie(equipos_df, names="estado", title="Distribución de Equipos por Estado")
            st.plotly_chart(fig)
        with tab2:
            clientes_df = read_table("clientes")
            st.bar_chart(clientes_df.groupby("id_cliente").size())

    elif view == "📦 Inventario":
        st.subheader("📦 Inventario de Equipos")
        equipos = read_table("equipos")
        estado_filtro = st.selectbox("Filtrar por estado", ["Todos"] + equipos['estado'].unique().tolist())
        if estado_filtro != "Todos":
            equipos = equipos[equipos.estado == estado_filtro]
        styled_equipos = equipos.sort_values(by="estado").style.applymap(highlight_status, subset=['estado'])
        st.dataframe(styled_equipos)

        with st.expander("✏️ Editar Equipo"):
            equipo_a_editar = st.selectbox("Seleccionar Equipo a Editar", equipos.id_equipo.tolist(), key="edit_equipo_select")
            if equipo_a_editar:
                equipo_info = equipos[equipos.id_equipo == equipo_a_editar].iloc[0]
                with st.form("form_editar_equipo"):
                    marca_edit = st.text_input("Marca", value=equipo_info.marca)
                    modelo_edit = st.text_input("Modelo", value=equipo_info.modelo)
                    caracteristicas_edit = st.text_area("Características", value=equipo_info.caracteristicas)
                    estado_edit = st.selectbox("Estado", ["disponible", "rentado", "mantenimiento"], index=["disponible", "rentado", "mantenimiento"].index(equipo_info.estado))
                    precio_base_edit = st.number_input("Precio Base de Renta ($)", min_value=0.0, step=0.01, value=float(equipo_info.precio_base))
                    eliminar = st.checkbox("Eliminar este equipo")
                    submitted = st.form_submit_button("Guardar Cambios")
                    if submitted:
                        if eliminar:
                            equipos = equipos[equipos.id_equipo != equipo_a_editar]
                            st.success("🗑️ Equipo eliminado")
                        else:
                            equipos.loc[equipos.id_equipo == equipo_a_editar, ["marca", "modelo", "caracteristicas", "estado", "precio_base"]] = \
                                [marca_edit, modelo_edit, caracteristicas_edit, estado_edit, precio_base_edit]
                        if write_table("equipos", equipos):
                            st.success("✅ Datos actualizados")
                            st.rerun()
                        else:
                            st.error("❌ Error al guardar cambios")