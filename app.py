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

st.set_page_config(page_title="App de Arrendamiento", layout="wide")
st.title("📦 App de Arrendamiento de Equipos de Cómputo")

# Menú con botones en la barra lateral
view = st.sidebar.radio("Navegación", [
    "📋 Registro de Equipos",
    "👤 Registro de Clientes",
    "📝 Nueva Renta",
    "🔍 Seguimiento de Rentas",
    "📦 Inventario"
])

if view == "📋 Registro de Equipos":
    st.subheader("Registrar Nuevo Equipo")
    with st.form("form_equipo"):
        id_equipo = st.text_input("ID del Equipo")
        marca = st.text_input("Marca")
        modelo = st.text_input("Modelo")
        caracteristicas = st.text_area("Características")
        estado = st.selectbox("Estado", ["disponible", "rentado", "mantenimiento"])
        submitted = st.form_submit_button("Registrar Equipo")

        if submitted:
            df = pd.read_csv("db/equipos.csv")
            nuevo = pd.DataFrame([[id_equipo, marca, modelo, caracteristicas, estado]], columns=df.columns)
            df = pd.concat([df, nuevo], ignore_index=True)
            df.to_csv("db/equipos.csv", index=False)
            st.success("Equipo registrado correctamente")

elif view == "👤 Registro de Clientes":
    st.subheader("Registrar Nuevo Cliente")
    with st.form("form_cliente"):
        id_cliente = st.text_input("ID del Cliente")
        nombre = st.text_input("Nombre Completo")
        contacto = st.text_input("Teléfono")
        correo = st.text_input("Correo Electrónico")
        submitted = st.form_submit_button("Registrar Cliente")

        if submitted:
            df_clientes = pd.read_csv("db/clientes.csv")
            nuevo = pd.DataFrame([[id_cliente, nombre, contacto, correo]], columns=df_clientes.columns)
            df_clientes = pd.concat([df_clientes, nuevo], ignore_index=True)
            df_clientes.to_csv("db/clientes.csv", index=False)
            st.success("Cliente registrado correctamente")

elif view == "📝 Nueva Renta":
    st.subheader("Registrar Nueva Renta")
    equipos = pd.read_csv("db/equipos.csv")
    disponibles = equipos[equipos.estado == "disponible"]
    clientes = pd.read_csv("db/clientes.csv")

    if disponibles.empty:
        st.warning("No hay equipos disponibles para rentar.")
    elif clientes.empty:
        st.warning("No hay clientes registrados.")
    else:
        with st.form("form_renta"):
            id_renta = st.text_input("ID de Renta")
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
                df_rentas = pd.read_csv("db/rentas.csv")
                nuevo = pd.DataFrame([[id_renta, cliente_seleccionado, contacto, equipo, fecha_inicio, fecha_fin, precio]], columns=df_rentas.columns)
                df_rentas = pd.concat([df_rentas, nuevo], ignore_index=True)
                df_rentas.to_csv("db/rentas.csv", index=False)

                # Actualizar estado del equipo
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
