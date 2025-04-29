import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from filelock import FileLock
import bcrypt
import re

# Crear carpeta de base de datos si no existe
DB_DIR = "db"
if not os.path.exists(DB_DIR):
    try:
        os.makedirs(DB_DIR)
        st.write(f"Created directory: {DB_DIR}")
    except Exception as e:
        st.error(f"Error creating directory {DB_DIR}: {e}")

# Archivos CSV
EQUIPOS_CSV = f"{DB_DIR}/equipos.csv"
RENTAS_CSV = f"{DB_DIR}/rentas.csv"
CLIENTES_CSV = f"{DB_DIR}/clientes.csv"
USUARIOS_CSV = f"{DB_DIR}/usuarios.csv"

# Inicializar archivos CSV si no existen
def initialize_csv():
    if not os.path.exists(EQUIPOS_CSV):
        pd.DataFrame(columns=["id_equipo", "marca", "modelo", "caracteristicas", "estado"]).to_csv(EQUIPOS_CSV, index=False)
        st.write(f"Created {EQUIPOS_CSV}")
    if not os.path.exists(RENTAS_CSV):
        pd.DataFrame(columns=["id_renta", "cliente", "contacto", "id_equipo", "fecha_inicio", "fecha_fin", "precio"]).to_csv(RENTAS_CSV, index=False)
        st.write(f"Created {RENTAS_CSV}")
    if not os.path.exists(CLIENTES_CSV):
        pd.DataFrame(columns=["id_cliente", "nombre", "contacto", "correo"]).to_csv(CLIENTES_CSV, index=False)
        st.write(f"Created {CLIENTES_CSV}")
    if not os.path.exists(USUARIOS_CSV):
        try:
            hashed_password = bcrypt.hashpw("12345".encode('utf-8'), bcrypt.gensalt())
            pd.DataFrame([{"usuario": "admin", "password": hashed_password.decode('utf-8')}], dtype=str).to_csv(USUARIOS_CSV, index=False)
            st.write(f"Created {USUARIOS_CSV} with admin user")
            df_usuarios = pd.read_csv(USUARIOS_CSV, dtype=str)
            if not df_usuarios.empty and df_usuarios.iloc[0]["password"].startswith('$2b$'):
                st.write("Password hash in usuarios.csv is valid")
            else:
                st.error("Failed to create valid password hash in usuarios.csv")
        except Exception as e:
            st.error(f"Error creating {USUARIOS_CSV}: {e}")

initialize_csv()

# Funciones auxiliares
def read_csv_safe(file_path):
    try:
        with FileLock(f"{file_path}.lock"):
            if file_path == USUARIOS_CSV:
                return pd.read_csv(file_path, dtype={"usuario": str, "password": str})
            return pd.read_csv(file_path)
    except Exception as e:
        st.error(f"Error al leer {file_path}: {e}")
        return pd.DataFrame()

def write_csv_safe(file_path, df):
    try:
        with FileLock(f"{file_path}.lock"):
            df.to_csv(file_path, index=False)
            st.write(f"Successfully wrote to {file_path}")
        return True
    except Exception as e:
        st.error(f"Error al escribir en {file_path}: {e}")
        return False

def validate_email(email):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None

def validate_phone(phone):
    pattern = r"^\+?\d{10,15}$"
    return re.match(pattern, phone) is not None

# Configuración de la página
st.set_page_config(page_title="Arrendamiento MarTech Rent", layout="wide")

# Autenticación
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.subheader("Iniciar Sesión")
    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Iniciar Sesión")

        if submitted:
            if not username or not password:
                st.error("Por favor, ingrese usuario y contraseña")
            else:
                df_usuarios = read_csv_safe(USUARIOS_CSV)
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
                            st.success("Inicio de sesión exitoso")
                            st.rerun()
                        else:
                            st.error("Contraseña incorrecta")
                    except Exception as e:
                        st.error(f"Error al verificar contraseña: {e}")
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

    if view == "📋 Registro de Equipos":
        st.subheader("Registrar Nuevo Equipo")
        with st.form("form_equipo"):
            df_equipos = read_csv_safe(EQUIPOS_CSV)
            nuevo_id = f"ME{len(df_equipos) + 1:04d}"
            st.text_input("ID del Equipo", value=nuevo_id, disabled=True)
            marca = st.text_input("Marca")
            modelo = st.text_input("Modelo")
            caracteristicas = st.text_area("Características")
            estado = st.selectbox("Estado", ["disponible", "rentado", "mantenimiento"])
            submitted = st.form_submit_button("Registrar Equipo")

            if submitted:
                if not marca or not modelo:
                    st.error("Marca y modelo son obligatorios")
                else:
                    nuevo = pd.DataFrame([[nuevo_id, marca, modelo, caracteristicas, estado]], columns=df_equipos.columns)
                    st.write(f"Attempting to register equipo: {nuevo.to_dict()}")
                    df_equipos = pd.concat([df_equipos, nuevo], ignore_index=True)
                    if write_csv_safe(EQUIPOS_CSV, df_equipos):
                        st.success("Equipo registrado correctamente")
                    else:
                        st.error("Fallo al registrar el equipo")

    elif view == "👤 Registro de Clientes":
        st.subheader("Registrar Nuevo Cliente")
        with st.form("form_cliente"):
            df_clientes = read_csv_safe(CLIENTES_CSV)
            nuevo_id = f"MC{len(df_clientes) + 1:04d}"
            st.text_input("ID del Cliente", value=nuevo_id, disabled=True)
            nombre = st.text_input("Nombre Completo")
            contacto = st.text_input("Teléfono")
            correo = st.text_input("Correo Electrónico")
            submitted = st.form_submit_button("Registrar Cliente")

            if submitted:
                if not nombre or not contacto or not correo:
                    st.error("Todos los campos son obligatorios")
                elif not validate_email(correo):
                    st.error("Correo electrónico inválido")
                elif not validate_phone(contacto):
                    st.error("Teléfono inválido (debe tener 10-15 dígitos)")
                else:
                    nuevo = pd.DataFrame([[nuevo_id, nombre, contacto, correo]], columns=df_clientes.columns)
                    st.write(f"Attempting to register cliente: {nuevo.to_dict()}")
                    df_clientes = pd.concat([df_clientes, nuevo], ignore_index=True)
                    if write_csv_safe(CLIENTES_CSV, df_clientes):
                        st.success("Cliente registrado correctamente")
                    else:
                        st.error("Fallo al registrar el cliente")

    elif view == "📝 Nueva Renta":
        st.subheader("Registrar Nueva Renta")
        equipos = read_csv_safe(EQUIPOS_CSV)
        disponibles = equipos[equipos.estado == "disponible"]
        clientes = read_csv_safe(CLIENTES_CSV)
        df_rentas = read_csv_safe(RENTAS_CSV)

        if disponibles.empty:
            st.warning("No hay equipos disponibles para rentar.")
        elif clientes.empty:
            st.warning("No hay clientes registrados.")
        else:
            with st.form("form_renta"):
                nuevo_id_renta = f"RE-{len(df_rentas) + 1:04d}"
                st.text_input("ID de Renta", value=nuevo_id_renta, disabled=True)
                cliente_seleccionado = st.selectbox("Cliente", clientes.nombre.tolist())

                cliente_info = clientes[clientes.nombre == cliente_seleccionado].iloc[0]
                contacto = cliente_info.contacto
                correo = cliente_info.correo
                st.markdown(f"**Contacto:** {contacto}")
                st.markdown(f"**Correo:** {correo}")

                equipo = st.selectbox("Equipo", disponibles.id_equipo.tolist())
                fecha_inicio = st.date_input("Fecha de Inicio", value=datetime.now())
                fecha_fin = st.date_input("Fecha de Fin", value=datetime.now() + timedelta(days=7))
                precio = st.number_input("Precio de Renta", min_value=0.0, step=0.01)
                submitted = st.form_submit_button("Registrar Renta")

                if submitted:
                    if fecha_fin <= fecha_inicio:
                        st.error("La fecha de fin debe ser posterior a la fecha de inicio")
                    elif precio <= 0:
                        st.error("El precio debe ser mayor a 0")
                    else:
                        nuevo = pd.DataFrame([[nuevo_id_renta, cliente_seleccionado, contacto, equipo, fecha_inicio, fecha_fin, precio]], columns=df_rentas.columns)
                        st.write(f"Attempting to register renta: {nuevo.to_dict()}")
                        df_rentas = pd.concat([df_rentas, nuevo], ignore_index=True)
                        if write_csv_safe(RENTAS_CSV, df_rentas):
                            equipos.loc[equipos.id_equipo == equipo, "estado"] = "rentado"
                            if write_csv_safe(EQUIPOS_CSV, equipos):
                                st.success("Renta registrada correctamente")
                            else:
                                st.error("Fallo al actualizar el estado del equipo")
                        else:
                            st.error("Fallo al registrar la renta")

    elif view == "🔍 Seguimiento de Rentas":
        st.subheader("Seguimiento de Rentas")
        df = read_csv_safe(RENTAS_CSV)

        if df.empty:
            st.info("No hay rentas registradas.")
        else:
            try:
                df["fecha_fin"] = pd.to_datetime(df["fecha_fin"])
                hoy = datetime.now()
                df["dias_restantes"] = (df["fecha_fin"] - hoy).dt.days
                st.dataframe(df)

                proximas = df[df.dias_restantes <= 3]
                if not proximas.empty:
                    st.warning("⚠️ Rentas próximas a vencer:")
                    st.dataframe(proximas[["id_renta", "cliente", "id_equipo", "fecha_fin", "dias_restantes"]])
            except Exception as e:
                st.error(f"Error al procesar fechas: {e}")

    elif view == "📦 Inventario":
        st.subheader("Inventario de Equipos")
        equipos = read_csv_safe(EQUIPOS_CSV)
        if not equipos.empty:
            st.dataframe(equipos.sort_values(by="estado"))
        else:
            st.info("No hay equipos registrados.")

    elif view == "📁 Listado de Clientes":
        st.subheader("Listado de Clientes Registrados")
        df_clientes = read_csv_safe(CLIENTES_CSV)
        if not df_clientes.empty:
            st.dataframe(df_clientes)
        else:
            st.info("No hay clientes registrados.")

    elif view == "📁 Listado de Rentas":
        st.subheader("Listado de Rentas Realizadas")
        df_rentas = read_csv_safe(RENTAS_CSV)
        if not df_rentas.empty:
            st.dataframe(df_rentas)
        else:
            st.info("No hay rentas registradas.")

    elif view == "✅ Finalizar Renta":
        st.subheader("Finalizar Renta")
        df_rentas = read_csv_safe(RENTAS_CSV)
        equipos = read_csv_safe(EQUIPOS_CSV)
        rentas_activas = df_rentas[df_rentas.id_equipo.isin(equipos[equipos.estado == "rentado"].id_equipo)]

        if rentas_activas.empty:
            st.info("No hay rentas activas para finalizar.")
        else:
            with st.form("form_finalizar_renta"):
                renta_seleccionada = st.selectbox("Renta", rentas_activas.id_renta.tolist())
                submitted = st.form_submit_button("Finalizar Renta")

                if submitted:
                    id_equipo = rentas_activas[rentas_activas.id_renta == renta_seleccionada].id_equipo.iloc[0]
                    equipos.loc[equipos.id_equipo == id_equipo, "estado"] = "disponible"
                    df_rentas = df_rentas[df_rentas.id_renta != renta_seleccionada]
                    st.write(f"Attempting to finalize renta {renta_seleccionada}")
                    if write_csv_safe(EQUIPOS_CSV, equipos) and write_csv_safe(RENTAS_CSV, df_rentas):
                        st.success(f"Renta {renta_seleccionada} finalizada. Equipo disponible nuevamente.")
                    else:
                        st.error("Fallo al finalizar la renta")
