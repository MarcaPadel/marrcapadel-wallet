import streamlit as st
from supabase import create_client, Client
import requests
import uuid
import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Marca Pádel Premier Club", page_icon="🎾")

# --- 2. CONEXIÓN A SUPABASE ---
try:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(supabase_url, supabase_key)
except Exception as e:
    st.error(f"Error conectando a la base de datos: {e}")

# --- 3. FUNCIÓN DE WALLETWALLET (CORREGIDA AL 100%) ---
def generar_tarjeta_walletwallet(cliente_uuid, nombre_cliente):
    # Endpoint oficial verificado de WalletWallet
    url_api = "https://api.walletwallet.dev/api/passes"
    
    headers = {
        "Authorization": f"Bearer {st.secrets['WALLETWALLET_API_KEY']}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "barcodeValue": str(cliente_uuid),
        "barcodeFormat": "QR",
        "barcodeAltText": "Muestra este código en recepción",
        "logoText": "Marca Pádel Premier",
        "organizationName": "Marca Pádel Premier Club",
        "colorPreset": "dark",
        "primaryFields": [
            {
                "label": "JUGADOR",
                "value": nombre_cliente
            }
        ],
        "secondaryFields": [
            {
                "label": "SELLOS",
                "value": "0 / 10"
            }
        ]
    }
    
    respuesta = requests.post(url_api, headers=headers, json=payload)
    
    if respuesta.status_code in [200, 201]:
        datos = respuesta.json()
        enlace_descarga = datos.get("shareUrl")
        serial_number = datos.get("serialNumber")
        
        if enlace_descarga:
            return enlace_descarga, serial_number
        else:
            raise Exception(f"WalletWallet no devolvió shareUrl. Respuesta: {datos}")
    else:
        raise Exception(f"Error {respuesta.status_code} de WalletWallet: {respuesta.text}")

# --- 4. FUNCIÓN PARA EL BOTÓN VISUAL ---
def mostrar_boton_descarga(enlace):
    st.markdown(
        f"""
        <style>
        .btn-premium {{
            display: inline-flex; align-items: center; justify-content: center;
            background-color: #1E1E1E; color: #FFFFFF !important; text-decoration: none;
            padding: 14px 28px; border-radius: 30px; font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 16px; font-weight: 600; border: 2px solid #C5A059;
            transition: all 0.3s ease; margin: 20px auto;
        }}
        .btn-premium:hover {{ background-color: #C5A059; color: #000000 !important; }}
        </style>
        <div style="text-align: center;">
            <a href="{enlace}" target="_blank" class="btn-premium">
                📲 Añadir a mi Teléfono (Apple / Google)
            </a>
        </div>
        """, 
        unsafe_allow_html=True
    )

# --- 5. INTERFAZ DE USUARIO ---
st.title("🎾 Marca Pádel Premier Club")
st.write("Gestiona tu tarjeta digital de lealtad.")

tab_nuevo, tab_recuperar = st.tabs(["📝 Nuevo Registro", "🔄 Recuperar mi Tarjeta"])

# ==========================================
# PESTAÑA 1: NUEVO REGISTRO
# ==========================================
with tab_nuevo:
    st.subheader("¿Eres nuevo? Regístrate aquí")
    with st.form("registro_form"):
        nombre = st.text_input("Nombre completo *")
        correo = st.text_input("Correo electrónico *")
        telefono = st.text_input("Teléfono (Opcional)")
        
        col1, col2 = st.columns(2)
        with col1:
            genero = st.selectbox("Género", ["Masculino", "Femenino", "Otro", "Prefiero no decirlo"])
            fecha_nacimiento = st.date_input("Fecha de nacimiento", 
                                             value=datetime.date(1999, 1, 1),
                                             min_value=datetime.date(1940, 1, 1),
                                             max_value=datetime.date.today())
        with col2:
            categoria = st.selectbox("Categoría", ["1ra", "2da", "3ra", "4ta", "5ta", "6ta", "Iniciación"])
            posicion = st.selectbox("Posición de juego", ["Drive", "Revés", "Ambos"])
        
        submit_registro = st.form_submit_button("Generar mi tarjeta", use_container_width=True)

        if submit_registro:
            if nombre and correo:
                try:
                    verificacion = supabase.table("clientes_wallet").select("id").eq("email", correo).execute()
                    if len(verificacion.data) > 0:
                        st.warning(f"⚠️ El correo {correo} ya está registrado. Usa la pestaña 'Recuperar mi Tarjeta'.")
                    else:
                        cliente_uuid = str(uuid.uuid4())
                        
                        # 1. Crear el pase en WalletWallet primero
                        with st.spinner("Creando tu tarjeta digital con Apple y Google..."):
                            wallet_link, serial_number = generar_tarjeta_walletwallet(cliente_uuid, nombre)
                        
                        # 2. Guardar en Supabase (incluyendo el serial_number en wallet_object_id)
                        datos_insertar = {
                            "id": cliente_uuid,
                            "nombre_completo": nombre,
                            "email": correo,
                            "telefono": telefono,
                            "genero": genero,
                            "fecha_nacimiento": fecha_nacimiento.strftime("%Y-%m-%d"),
                            "categoria": categoria,
                            "posicion": posicion,
                            "wallet_object_id": serial_number,
                            "saldo": 0
                        }
                        supabase.table("clientes_wallet").insert(datos_insertar).execute()
                        
                        st.success(f"¡Bienvenido al club, {nombre}! Descarga tu tarjeta aquí:")
                        mostrar_boton_descarga(wallet_link)
                        
                except Exception as e:
                    st.error(f"Error al generar la tarjeta: {e}")
            else:
                st.warning("Por favor, llena los campos obligatorios (Nombre y Correo).")

# ==========================================
# PESTAÑA 2: RECUPERAR TARJETA
# ==========================================
with tab_recuperar:
    st.subheader("¿Ya eres parte del club?")
    st.write("Ingresa tu correo registrado para volver a descargar tu tarjeta.")
    
    with st.form("recuperar_form"):
        correo_recuperar = st.text_input("Ingresa tu correo electrónico registrado *")
        submit_recuperar = st.form_submit_button("Buscar mi tarjeta", use_container_width=True)
        
        if submit_recuperar:
            if correo_recuperar:
                try:
                    respuesta = supabase.table("clientes_wallet").select("*").eq("email", correo_recuperar).execute()
                    
                    if len(respuesta.data) > 0:
                        usuario = respuesta.data[0]
                        nombre_guardado = usuario["nombre_completo"]
                        serial = usuario.get("wallet_object_id")
                        
                        # Si tenemos el serial de WalletWallet, consultamos su link
                        if serial:
                            url_recuperar = f"https://api.walletwallet.dev/api/passes/{serial}"
                            headers = {"Authorization": f"Bearer {st.secrets['WALLETWALLET_API_KEY']}"}
                            res = requests.get(url_recuperar, headers=headers)
                            
                            if res.status_code == 200:
                                link = res.json().get("shareUrl")
                                st.success(f"¡Hola de nuevo, {nombre_guardado}! Aquí está tu tarjeta:")
                                mostrar_boton_descarga(link)
                            else:
                                st.error("No se pudo obtener el enlace del servidor. Intenta de nuevo.")
                        else:
                            st.info("Este registro es anterior. Por favor contacta a recepción para actualizar tu tarjeta.")
                    else:
                        st.error("❌ No encontramos ninguna tarjeta registrada con ese correo.")
                except Exception as e:
                    st.error(f"Error buscando la información: {e}")
            else:
                st.warning("Por favor ingresa tu correo electrónico.")
