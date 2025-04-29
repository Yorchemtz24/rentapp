import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# Crear carpeta de base de datos si no existe
if not os.path.exists("db"):
    os.makedirs("db")

# Inicializar archivos CSV si no existen
if not os.path.exists("db/equipos.csv"):
    pd.DataFrame(columns=["id_equipo", "marca", "modelo", "caracteristicas", "estado"]).to_csv("db/equipos.csv", index=False)

if not os.path.exists("db/rentas.csv"):
    pd.DataFrame(columns=["id_renta", "cliente", "contacto", "id_equipo", "fecha_inicio", "fecha_fin", "precio"]).to_csv("db/rentas.csv", index=False)

if not os.path.exists("db/clientes.csv"):
    pd.DataFrame(columns=["id_cliente", "nombre", "contacto", "correo"]).to_csv("db/clientes.csv", index=False)

if not os.path.exists("db/usuarios.csv"):
    pd.DataFrame([{"usuario": "admin", "password": "12345"}]).to_csv("db/usuarios.csv", index=False)

st.set_page_config(page_title="Arrendamiento MarTech Rent", layout="wide")

# Autenticación básica
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Iniciar Sesión")
    usuario_input = st.text_input("Usuario")
    password_input = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        usuarios_df = pd.read_csv("db/usuarios.csv")
        user_match = usuarios_df[(usuarios_df.usuario == usuario_input) & (usuarios_df.password == password_input)]
        if not user_match.empty:
            st.session_state.authenticated = True
            st.session_state.usuario = usuario_input
            st.success("Inicio de sesión exitoso")
            st.experimental_rerun()
        else:
            st.error("Credenciales inválidas")
else:
    st.title("💻 Arrendamiento MarTech Rent")

    # Gestión de usuarios (solo admin)
    if st.session_state.usuario == "admin":
        st.sidebar.markdown("## 👥 Gestión de Usuarios")
        with st.sidebar.expander("➕ Crear nuevo usuario"):
            nuevo_usuario = st.text_input("Nuevo Usuario")
            nueva_contraseña = st.text_input("Nueva Contraseña", type="password")
            if st.button("Crear Usuario"):
                usuarios_df = pd.read_csv("db/usuarios.csv")
                if nuevo_usuario in usuarios_df['usuario'].values:
                    st.warning("⚠️ El usuario ya existe.")
                else:
                    nuevo = pd.DataFrame([[nuevo_usuario, nueva_contraseña]], columns=["usuario", "password"])
                    usuarios_df = pd.concat([usuarios_df, nuevo], ignore_index=True)
                    usuarios_df.to_csv("db/usuarios.csv", index=False)
                    st.success("✅ Usuario creado correctamente.")

    # Menú con botones en la barra lateral
    view = st.sidebar.radio("Navegación", [
        "📋 Registro de Equipos",
        "👤 Registro de Clientes",
        "📝 Nueva Renta",
        "🔍 Seguimiento de Rentas",
        "📦 Inventario",
        "📁 Registro de Clientes",
        "📁 Registro de Rentas"
    ])

    if view == "📋 Registro de Equipos":
        st.subheader("Registrar Nuevo Equipo")
        with st.form("form_equipo"):
            df_equipos = pd.read_csv("db/equipos.csv")
            nuevo_id = f"ME{len(df_equipos) + 1:04d}"
            st.text_input("ID del Equipo", value=nuevo_id, disabled=True)
            marca = st.text_input("Marca")
            modelo = st.text_input("Modelo")
            caracteristicas = st.text_area("Características")
            estado = st.selectbox("Estado", ["disponible", "rentado", "mantenimiento"])
            submitted = st.form_submit_button("Registrar Equipo")

            if submitted:
                nuevo = pd.DataFrame([[nuevo_id, marca, modelo, caracteristicas, estado]], columns=df_equipos.columns)
                df_equipos = pd.concat([df_equipos, nuevo], ignore_index=True)
                df_equipos.to_csv("db/equipos.csv", index=False)
                st.success("Equipo registrado correctamente")

    elif view == "👤 Registro de Clientes":
        st.subheader("Registrar Nuevo Cliente")
        with st.form("form_cliente"):
            df_clientes = pd.read_csv("db/clientes.csv")
            nuevo_id = f"MC{len(df_clientes) + 1:04d}"
            st.text_input("ID del Cliente", value=nuevo_id, disabled=True)
            nombre = st.text_input("Nombre Completo")
            contacto = st.text_input("Teléfono")
            correo = st.text_input("Correo Electrónico")
            submitted = st.form_submit_button("Registrar Cliente")

            if submitted:
                nuevo = pd.DataFrame([[nuevo_id, nombre, contacto, correo]], columns=df_clientes.columns)
                df_clientes = pd.concat([df_clientes, nuevo], ignore_index=True)
                df_clientes.to_csv("db/clientes.csv", index=False)
                st.success("Cliente registrado correctamente")

    elif view == "📝 Nueva Renta":
        st.subheader("Registrar Nueva Renta")
        equipos = pd.read_csv("db/equipos.csv")
        disponibles = equipos[equipos.estado == "disponible"]
        clientes = pd.read_csv("db/clientes.csv")
        df_rentas = pd.read_csv("db/rentas.csv")

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
                precio = st.number_input("Precio de Renta", min_value=0.0)
                submitted = st.form_submit_button("Registrar Renta")

                if submitted:
                    nuevo = pd.DataFrame([[nuevo_id_renta, cliente_seleccionado, contacto, equipo, fecha_inicio, fecha_fin, precio]], columns=df_rentas.columns)
                    df_rentas = pd.concat([df_rentas, nuevo], ignore_index=True)
                    df_rentas.to_csv("db/rentas.csv", index=False)

                    equipos.loc[equipos.id_equipo == equipo, "estado"] = "rentado"
                    equipos.to_csv("db/equipos.csv", index=False)
                    st.success("Renta registrada correctamente")

    elif view == "🔍 Seguimiento de Rentas":
        st.subheader("Seguimiento de Rentas")
        df = pd.read_csv("db/rentas.csv")

        if df.empty:
            st.info("No hay rentas registradas.")
        else:
            df["fecha_fin"] = pd.to_datetime(df["fecha_fin"])
            hoy = datetime.now()
            df["dias_restantes"] = (df["fecha_fin"] - hoy).dt.days

            st.dataframe(df)

            proximas = df[df.dias_restantes <= 3]
            if not proximas.empty:
                st.warning("⚠️ Rentas próximas a vencer:")
                st.dataframe(proximas[["id_renta", "cliente", "id_equipo", "fecha_fin", "dias_restantes"]])

    elif view == "📦 Inventario":
        st.subheader("Inventario de Equipos")
        equipos = pd.read_csv("db/equipos.csv")
        st.dataframe(equipos.sort_values(by="estado"))

    elif view == "📁 Registro de Clientes":
        st.subheader("Listado de Clientes Registrados")
        df_clientes = pd.read_csv("db/clientes.csv")
        st.dataframe(df_clientes)

    elif view == "📁 Registro de Rentas":
        st.subheader("Listado de Rentas Realizadas")
        df_rentas = pd.read_csv("db/rentas.csv")
        st.dataframe(df_rentas)
