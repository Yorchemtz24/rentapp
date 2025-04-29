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

st.set_page_config(page_title="App de Arrendamiento", layout="wide")
st.title("📦 App de Arrendamiento de Equipos de Cómputo")

# Menú con botones
col1, col2, col3 = st.columns(3)
view = None

with col1:
    if st.button("📋 Registro de Equipos"):
        view = "Registro de Equipos"

with col2:
    if st.button("📝 Registro de Renta"):
        view = "Registro de Renta"

with col3:
    if st.button("🔍 Seguimiento de Rentas"):
        view = "Seguimiento de Rentas"

if view == "Registro de Equipos":
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

elif view == "Registro de Renta":
    st.subheader("Registrar Nueva Renta")
    equipos = pd.read_csv("db/equipos.csv")
    disponibles = equipos[equipos.estado == "disponible"]

    if disponibles.empty:
        st.warning("No hay equipos disponibles para rentar.")
    else:
        with st.form("form_renta"):
            id_renta = st.text_input("ID de Renta")
            cliente = st.text_input("Nombre del Cliente")
            contacto = st.text_input("Contacto")
            equipo = st.selectbox("Equipo", disponibles.id_equipo.tolist())
            fecha_inicio = st.date_input("Fecha de Inicio", value=datetime.now())
            fecha_fin = st.date_input("Fecha de Fin", value=datetime.now() + timedelta(days=7))
            precio = st.number_input("Precio de Renta", min_value=0.0)
            submitted = st.form_submit_button("Registrar Renta")

        if submitted:
            df_rentas = pd.read_csv("db/rentas.csv")
            nuevo = pd.DataFrame([[id_renta, cliente, contacto, equipo, fecha_inicio, fecha_fin, precio]], columns=df_rentas.columns)
            df_rentas = pd.concat([df_rentas, nuevo], ignore_index=True)
            df_rentas.to_csv("db/rentas.csv", index=False)
            
            # Actualizar estado del equipo
            equipos.loc[equipos.id_equipo == equipo, "estado"] = "rentado"
            equipos.to_csv("db/equipos.csv", index=False)
            st.success("Renta registrada correctamente")

elif view == "Seguimiento de Rentas":
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

# Instrucciones para archivos adicionales
if st.sidebar.button("📄 Mostrar instrucciones de descarga"):
    st.markdown("""
    ### Archivos adicionales para tu repositorio:

    **1. `requirements.txt`**
    ```
    streamlit
    pandas
    ```

    **2. `README.md`**
    ```markdown
    # Rental App Streamlit

    Aplicación web con Streamlit para registrar y hacer seguimiento de rentas de equipo de cómputo.

    ## Funcionalidades
    - Registro de equipos
    - Registro de rentas
    - Seguimiento de rentas próximas a vencer

    ## Requisitos
    ```bash
    pip install -r requirements.txt
    ```

    ## Ejecución
    ```bash
    streamlit run app.py
    ```
    ```
    """)
