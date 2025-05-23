import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
import bcrypt
import re
from github import Github
import json

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

# Configuración de GitHub
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
    except Exception as e:
        st.error(f"Error creating directory {DB_DIR}: {e}")

# Inicializar base de datos SQLite
def initialize_db():
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
    conn.commit()
    conn.close()

initialize_db()

# Función para sincronizar database.db con GitHub
def update_db_in_github():
    if not GITHUB_TOKEN:
        st.error("Cannot update GitHub: GITHUB_TOKEN is not set.")
        return
    try:
        from github import Github
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
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

def write_table(table_name, df):
    conn = sqlite3.connect(DB_PATH)
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    conn.close()
    update_db_in_github()
    return True

def validate_email(email):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None

def validate_phone(phone):
    pattern = r"^\+?\d{10,15}$"
    return re.match(pattern, phone) is not None

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
                total = subtotal + (subtotal * 0.16 if incluir_iva else 0.0)
                if incluir_iva:
                    st.markdown(f"**IVA (16%):** ${(subtotal * 0.16):.2f}")
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

    elif st.session_state.view == "Seguimiento de Rentas":
        st.subheader("🔍 Seguimiento de Rentas")
        df = read_table("rentas")
        if df.empty:
            st.info("ℹ️ No hay rentas registradas.")
        else:
            try:
                df["equipos"] = df["equipos"].apply(lambda x: json.loads(x) if isinstance(x, str) and x else [])
                df["fecha_fin"] = pd.to_datetime(df["fecha_fin"])
                hoy = datetime.now()
                df["dias_restantes"] = (df["fecha_fin"] - hoy).dt.days
                st.dataframe(df)
                proximas = df[df.dias_restantes <= 3]
                if not proximas.empty:
                    st.warning("⚠️ Rentas próximas a vencer:")
                    st.dataframe(proximas[["id_renta", "cliente", "equipos", "fecha_fin", "dias_restantes"]])
            except Exception as e:
                st.error(f"❌ Error al procesar fechas o equipos: {e}")
        if st.button("⬅️ Regresar al inicio"):
            st.session_state.view = "Inicio"
            st.rerun()

    elif st.session_state.view == "Inventario":
        st.subheader("📦 Inventario de Equipos")
        equipos = read_table("equipos")
        if not equipos.empty:
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
        else:
            st.info("ℹ️ No hay equipos registrados.")
        if st.button("⬅️ Regresar al inicio"):
            st.session_state.view = "Inicio"
            st.rerun()

    elif st.session_state.view == "Listado de Clientes":
        st.subheader("📁 Listado de Clientes")
        df_clientes = read_table("clientes")
        if not df_clientes.empty:
            st.dataframe(df_clientes)
            with st.expander("✏️ Editar Cliente"):
                cliente_a_editar = st.selectbox("Seleccionar Cliente a Editar", df_clientes.id_cliente.tolist(), key="edit_cliente_select")
                if cliente_a_editar:
                    cliente_info = df_clientes[df_clientes.id_cliente == cliente_a_editar].iloc[0]
                    with st.form("form_editar_cliente"):
                        nombre_edit = st.text_input("Nombre Completo", value=cliente_info.nombre)
                        contacto_edit = st.text_input("Teléfono", value=cliente_info.contacto)
                        correo_edit = st.text_input("Correo Electrónico", value=cliente_info.correo)
                        eliminar = st.checkbox("Eliminar este cliente")
                        submitted = st.form_submit_button("Guardar Cambios")
                        if submitted:
                            if eliminar:
                                df_clientes = df_clientes[df_clientes.id_cliente != cliente_a_editar]
                                st.success("🗑️ Cliente eliminado")
                            else:
                                df_clientes.loc[df_clientes.id_cliente == cliente_a_editar, ["nombre", "contacto", "correo"]] = \
                                    [nombre_edit, contacto_edit, correo_edit]
                            if write_table("clientes", df_clientes):
                                st.success("✅ Datos actualizados")
                                st.rerun()
                            else:
                                st.error("❌ Error al guardar cambios")
        else:
            st.info("ℹ️ No hay clientes registrados.")
        if st.button("⬅️ Regresar al inicio"):
            st.session_state.view = "Inicio"
            st.rerun()

    elif st.session_state.view == "Listado de Rentas":
        st.subheader("📁 Listado de Rentas")
        df_rentas = read_table("rentas")
        if not df_rentas.empty:
            df_rentas["equipos"] = df_rentas["equipos"].apply(lambda x: json.loads(x) if isinstance(x, str) and x else [])
            st.dataframe(df_rentas)
        else:
            st.info("ℹ️ No hay rentas registradas.")
        if st.button("⬅️ Regresar al inicio"):
            st.session_state.view = "Inicio"
            st.rerun()

       elif st.session_state.view == "Finalizar Renta":
        st.subheader("✅ Finalizar Renta")
        df_rentas = read_table("rentas")
        equipos = read_table("equipos")
        if df_rentas.empty:
            st.info("ℹ️ No hay rentas activas.")
        else:
            df_rentas["equipos"] = df_rentas["equipos"].apply(lambda x: json.loads(x) if isinstance(x, str) and x else [])
            rentas_activas = df_rentas[df_rentas.equipos.apply(
                lambda eqs: any(
                    equipos[equipos.id_equipo == eq].estado.iloc[0] == "rentado" 
                    for eq in eqs 
                    if not equipos[equipos.id_equipo == eq].empty
                )
            )]
            if rentas_activas.empty:
                st.info("ℹ️ No hay rentas activas para finalizar.")
            else:
                with st.form("form_finalizar_renta"):
                    renta_seleccionada = st.selectbox("Renta", rentas_activas.id_renta.tolist())
                    submitted = st.form_submit_button("Finalizar Renta")
                    if submitted:
                        equipos_renta = rentas_activas[rentas_activas.id_renta == renta_seleccionada].equipos.iloc[0]
                        for equipo in equipos_renta:
                            equipos.loc[equipos.id_equipo == equipo, "estado"] = "disponible"
                        df_rentas = df_rentas[df_rentas.id_renta != renta_seleccionada]
                        df_rentas["equipos"] = df_rentas["equipos"].apply(json.dumps)
                        if write_table("equipos", equipos) and write_table("rentas", df_rentas):
                            st.success(f"✅ Renta {renta_seleccionada} finalizada")
                        else:
                            st.error("❌ Error al finalizar la renta")
        if st.button("⬅️ Regresar al inicio"):
            st.session_state.view = "Inicio"
            st.rerun()
