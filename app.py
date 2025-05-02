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
    if "view" not in st.session_state:
        st.session_state.view = "Inicio"

    if st.session_state.view == "Inicio":
        st.title("🏠 Panel Principal - Arrendamiento MarTech Rent")
        st.markdown("Selecciona una opción para continuar:")

        col1, col2, col3 = st.columns(3)

        if col1.button("📋 Registro de Equipos", use_container_width=True):
            st.session_state.view = "Registro de Equipos"
            st.rerun()
        if col2.button("👤 Registro de Clientes", use_container_width=True):
            st.session_state.view = "Registro de Clientes"
            st.rerun()
        if col3.button("📝 Nueva Renta", use_container_width=True):
            st.session_state.view = "Nueva Renta"
            st.rerun()

        col4, col5, col6 = st.columns(3)

        if col4.button("🔍 Seguimiento de Rentas", use_container_width=True):
            st.session_state.view = "Seguimiento de Rentas"
            st.rerun()
        if col5.button("📦 Inventario", use_container_width=True):
            st.session_state.view = "Inventario"
            st.rerun()
        if col6.button("📁 Listado de Clientes", use_container_width=True):
            st.session_state.view = "Listado de Clientes"
            st.rerun()

        col7, col8, col9 = st.columns(3)

        if col7.button("📁 Listado de Rentas", use_container_width=True):
            st.session_state.view = "Listado de Rentas"
            st.rerun()
        if col8.button("✅ Finalizar Renta", use_container_width=True):
            st.session_state.view = "Finalizar Renta"
            st.rerun()
        if col9.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.authenticated = False
            st.success("✅ Sesión cerrada")
            st.rerun()

    elif st.session_state.view == "Registro de Equipos":
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
                    df_equipos = pd.concat([df_equipos, nuevo], ignore_index=True)
                    if write_table("equipos", df_equipos):
                        st.success("✅ Equipo registrado correctamente")
                    else:
                        st.error("❌ Fallo al registrar el equipo")
        if st.button("⬅️ Regresar al inicio"):
            st.session_state.view = "Inicio"
            st.rerun()

    elif st.session_state.view == "Registro de Clientes":
        st.subheader("👤 Registrar Nuevo Cliente")
        with st.form("form_cliente"):
            df_clientes = read_table("clientes")
            nuevo_id = f"MC{len(df_clientes) + 1:04d}"
            st.text_input("ID del Cliente", value=nuevo_id, disabled=True)
            nombre = st.text_input("Nombre Completo")
            contacto = st.text_input("Teléfono")
            correo = st.text_input("Correo Electrónico")
            submitted = st.form_submit_button("Registrar Cliente")
            if submitted:
                if not nombre or not contacto or not correo:
                    st.error("❌ Todos los campos son obligatorios")
                elif not validate_email(correo):
                    st.error("❌ Correo electrónico inválido")
                elif not validate_phone(contacto):
                    st.error("❌ Teléfono inválido (debe tener 10-15 dígitos)")
                else:
                    nuevo = pd.DataFrame([[nuevo_id, nombre, contacto, correo]], 
                                        columns=["id_cliente", "nombre", "contacto", "correo"])
                    df_clientes = pd.concat([df_clientes, nuevo], ignore_index=True)
                    if write_table("clientes", df_clientes):
                        st.success("✅ Cliente registrado correctamente")
                    else:
                        st.error("❌ Fallo al registrar el cliente")
        if st.button("⬅️ Regresar al inicio"):
            st.session_state.view = "Inicio"
            st.rerun()

    elif st.session_state.view == "Nueva Renta":
        st.subheader("📝 Registrar Nueva Renta")
        equipos = read_table("equipos")
        disponibles = equipos[equipos.estado == "disponible"]
        clientes = read_table("clientes")
        df_rentas = read_table("rentas")
        if disponibles.empty:
            st.warning("⚠️ No hay equipos disponibles para rentar.")
        elif clientes.empty:
            st.warning("⚠️ No hay clientes registrados.")
        else:
            with st.form("form_renta"):
                nuevo_id_renta = f"RE-{len(df_rentas) + 1:04d}"
                st.text_input("ID de Renta", value=nuevo_id_renta, disabled=True)
                cliente_seleccionado = st.selectbox("Cliente", clientes.nombre.tolist())
                cliente_info = clientes[clientes.nombre == cliente_seleccionado].iloc[0]
                contacto = cliente_info.contacto
                correo = cliente_info.correo
                st.markdown(f"**📞 Contacto:** {contacto}")
                st.markdown(f"**✉️ Correo:** {correo}")
                equipos_seleccionados = st.multiselect("Seleccionar Equipos", disponibles.id_equipo.tolist())
                precios_equipos = {}
                if equipos_seleccionados:
                    for equipo in equipos_seleccionados:
                        precio_base = disponibles[disponibles.id_equipo == equipo].precio_base.iloc[0]
                        precio_base = float(precio_base) if pd.notnull(precio_base) else 0.0
                        precio = st.number_input(
                            f"Precio de Renta para {equipo} (Precio base: ${precio_base:.2f})", 
                            min_value=0.0, step=0.01, value=precio_base,
                            key=f"precio_{equipo}"
                        )
                        precios_equipos[equipo] = precio
                subtotal = sum(precios_equipos.values()) if precios_equipos else 0.0
                st.markdown(f"**Subtotal (sin IVA):** ${subtotal:.2f}")
                incluir_iva = st.checkbox("Incluir IVA del 16% (México)")
                iva = subtotal * 0.16 if incluir_iva else 0.0
                total = subtotal + iva
                if incluir_iva:
                    st.markdown(f"**IVA (16%):** ${iva:.2f}")
                st.markdown(f"**Total:** ${total:.2f}")
                fecha_inicio = st.date_input("Fecha de Inicio", value=datetime.now())
                fecha_fin = st.date_input("Fecha de Fin", value=datetime.now() + timedelta(days=7))
                submitted = st.form_submit_button("Registrar Renta")
                if submitted:
                    if not equipos_seleccionados:
                        st.error("❌ Debe seleccionar al menos un equipo")
                    elif fecha_fin <= fecha_inicio:
                        st.error("❌ La fecha de fin debe ser posterior a la fecha de inicio")
                    elif subtotal <= 0:
                        st.error("❌ El subtotal debe ser mayor a 0")
                    else:
                        equipos_json = json.dumps(equipos_seleccionados)
                        nuevo = pd.DataFrame([[nuevo_id_renta, cliente_seleccionado, contacto, equipos_json, fecha_inicio, fecha_fin, subtotal, total]],
                                            columns=["id_renta", "cliente", "contacto", "equipos", "fecha_inicio", "fecha_fin", "subtotal", "precio"])
                        df_rentas = pd.concat([df_rentas, nuevo], ignore_index=True)
                        if write_table("rentas", df_rentas):
                            for equipo in equipos_seleccionados:
                                equipos.loc[equipos.id_equipo == equipo, "estado"] = "rentado"
                            if write_table("equipos", equipos):
                                st.success("✅ Renta registrada correctamente")
                            else:
                                st.error("❌ Fallo al actualizar el estado de los equipos")
                        else:
                            st.error("❌ Fallo al registrar la renta")
        if st.button("⬅️ Regresar al inicio"):
            st.session_state.view = "Inicio"
            st.rerun()

    # Repite esta estructura para las demás vistas: "Seguimiento de Rentas", "Inventario", etc.
    # Y agrega siempre el botón de regreso al final de cada sección