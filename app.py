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

# --- 3. FUNCIÓN DE WALLETWALLET ---
def generar_enlace_walletwallet(cliente_uuid, nombre_cliente):
    url_api = "https://api.walletwallet.dev/v1/passes"
    headers = {
        "Authorization": f"Bearer {st.secrets['WALLETWALLET_API_KEY']}",
        "Content-Type": "application/json"
    }
    payload = {
        "logoText": "Marca Pádel Premier Club",
        "description": "Tarjeta de Lealtad",
        "backgroundColor": "#1E1E1E", 
        "foregroundColor": "#C5A059", 
        "passType": "storeCard",
        "barcode": {
            "format": "PKBarcodeFormatQR",
            "message": str(cliente_uuid),
            "messageEncoding": "iso-8859-1",
            "altText": "Muestra este código en recepción"
        },
        "primaryFields": [{"key": "jugador", "label": "JUGADOR", "value": nombre_cliente}],
        "secondaryFields": [{"key": "sellos", "label": "SELLOS (Renta de Pista)", "value": "0 / 10"}],
        "auxiliaryFields": [{"key": "premio", "label": "PREMIO AL LLENAR", "value": "1 Renta Gratis 🎾"}]
    }
    respuesta = requests.post(url_api, headers=headers, json=payload)
    if respuesta.status_code in [200, 201]:
        datos = respuesta.json()
        enlace_descarga = datos.get("passUrl", "")
        if enlace_descarga:
             return enlace_descarga
        else:
             raise Exception(f"No se encontró URL en WalletWallet. Datos: {datos}")
    else:
        raise Exception(f"Error {respuesta.status_code} API: {respuesta.text}")

# --- 4. FUNCIÓN PARA DIBUJAR EL BOTÓN ---
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

# --- 5. INTERFAZ DE USUARIO CON PESTAÑAS ---
st.title("🎾 Marca Pádel Premier Club")
st.write("Gestiona tu tarjeta digital de lealtad.")

# Creamos dos pestañas
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
                    # VERIFICAR DUPLICADOS
                    verificacion = supabase.table("clientes_wallet").select("id").eq("email", correo).execute()
                    if len(verificacion.data) > 0:
                        st.warning(f"⚠️ El correo {correo} ya está registrado. Ve a la pestaña 'Recuperar mi Tarjeta' si la perdiste.")
                    else:
                        cliente_uuid = str(uuid.uuid4())
                        datos_insertar = {
                            "id": cliente_uuid, "nombre_completo": nombre, "email": correo,
                            "telefono": telefono, "genero": genero, "fecha_nacimiento": fecha_nacimiento.strftime("%Y-%m-%d"),
                            "categoria": categoria, "posicion": posicion, "saldo": 0
                        }
                        supabase.table("clientes_wallet").insert(datos_insertar).execute()
                        
                        with st.spinner("Creando tu tarjeta digital..."):
                            wallet_link = generar_enlace_walletwallet(cliente_uuid, nombre)
                        
                        st.success(f"¡Bienvenido al club, {nombre}! Descarga tu tarjeta aquí:")
                        mostrar_boton_descarga(wallet_link)
                except Exception as e:
                    st.error("Hubo un problema procesando tu solicitud. Por favor intenta de nuevo.")
            else:
                st.warning("Por favor, llena los campos obligatorios (Nombre y Correo).")

# ==========================================
# PESTAÑA 2: RECUPERAR TARJETA
# ==========================================
with tab_recuperar:
    st.subheader("¿Ya eres parte del club?")
    st.write("Si cambiaste de celular o borraste tu tarjeta, ingresa tu correo para volver a descargarla. ¡Tus sellos están a salvo!")
    
    with st.form("recuperar_form"):
        correo_recuperar = st.text_input("Ingresa tu correo electrónico registrado *")
        submit_recuperar = st.form_submit_button("Buscar mi tarjeta", use_container_width=True)
        
        if submit_recuperar:
            if correo_recuperar:
                try:
                    # Buscar el correo en Supabase
                    respuesta = supabase.table("clientes_wallet").select("id, nombre_completo").eq("email", correo_recuperar).execute()
                    
                    if len(respuesta.data) > 0:
                        usuario = respuesta.data[0]
                        cliente_uuid = usuario["id"]
                        nombre_guardado = usuario["nombre_completo"]
                        
                        with st.spinner("Generando tu enlace de recuperación..."):
                            # Volvemos a pedirle a WalletWallet el enlace usando el mismo UUID
                            wallet_link = generar_enlace_walletwallet(cliente_uuid, nombre_guardado)
                            
                        st.success(f"¡Hola de nuevo, {nombre_guardado}! Aquí tienes el enlace de tu tarjeta:")
                        mostrar_boton_descarga(wallet_link)
                    else:
                        st.error("❌ No encontramos ninguna tarjeta registrada con ese correo. Por favor verifica que esté bien escrito o ve a la pestaña de Nuevo Registro.")
                except Exception as e:
                    st.error("Hubo un problema buscando tu información. Intenta de nuevo.")
            else:
                st.warning("Por favor ingresa tu correo electrónico para buscar tu tarjeta.")
