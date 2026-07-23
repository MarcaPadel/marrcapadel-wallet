import streamlit as st
from supabase import create_client, Client
import jwt
import json
import time
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
    st.error("Error de configuración de secretos de Supabase.")

# --- 3. FUNCIÓN DE GOOGLE WALLET ---
def generar_enlace_wallet(cliente_uuid, nombre_cliente, object_id):
    ISSUER_ID = "3388000000023162682"
    CLASS_ID = "SellosMPPC"
    
    CLASS_FULL_ID = f"{ISSUER_ID}.{CLASS_ID}"
    
    # Limpiamos el UUID para el accountId (max 12 caracteres sin guiones)
    clean_uuid = str(cliente_uuid).replace('-', '_')
    
    # Cargamos credenciales y forzamos la lectura correcta de saltos de línea
    credentials = json.loads(st.secrets["credenciales_google"])
    private_key = credentials["private_key"]
    if "\\n" in private_key:
        private_key = private_key.replace("\\n", "\n")
        
    # Estructura oficial y completa requerida por Google para pases activos
    loyalty_object = {
        "id": object_id,
        "classId": CLASS_FULL_ID,
        "state": "ACTIVE",
        "accountId": clean_uuid[:12],
        "accountName": nombre_cliente,
        "barcode": {
            "type": "QR_CODE",
            "value": str(cliente_uuid),
            "alternateText": nombre_cliente
        },
        "loyaltyPoints": {
            "label": "Sellos",
            "balance": {
                "string": "0 / 10"
            }
        }
    }
    
    # Reclamaciones (Claims) del JWT
    claims = {
        "iss": credentials["client_email"],
        "aud": "google",
        "typ": "savetowallet",
        "iat": int(time.time()),
        "payload": {
            "loyaltyObjects": [loyalty_object]
        }
    }
    
    # Generación y firma del Token
    token = jwt.encode(claims, private_key, algorithm="RS256")
    
    # Compatibilidad para versiones anteriores de PyJWT
    if isinstance(token, bytes):
        token = token.decode('utf-8')
        
    return f"https://pay.google.com/gp/v/save/{token}"

# --- 4. INTERFAZ DE USUARIO (STREAMLIT) ---
st.title("🎾 Marca Pádel Premier Club")
st.subheader("Regístrate para obtener tu tarjeta de sellos digital")
st.write("Acumula 10 sellos en tus rentas de pista y obtén un descuento especial.")

with st.form("registro_form"):
    nombre = st.text_input("Nombre completo *")
    correo = st.text_input("Correo electrónico *")
    telefono = st.text_input("Teléfono (Opcional)")
    
    # Agrupamos los campos adicionales en columnas para mejor diseño
    col1, col2 = st.columns(2)
    with col1:
        genero = st.selectbox("Género", ["Masculino", "Femenino", "Otro", "Prefiero no decirlo"])
        # Fecha por defecto hace 25 años para facilitar la navegación en el calendario
        fecha_nacimiento = st.date_input("Fecha de nacimiento", 
                                         value=datetime.date(1999, 1, 1),
                                         min_value=datetime.date(1940, 1, 1),
                                         max_value=datetime.date.today())
    with col2:
        categoria = st.selectbox("Categoría", ["1ra", "2da", "3ra", "4ta", "5ta", "6ta", "Iniciación"])
        posicion = st.selectbox("Posición de juego", ["Drive", "Revés", "Ambos"])
    
    submit_btn = st.form_submit_button("Generar mi tarjeta", use_container_width=True)

    if submit_btn:
        if nombre and correo:
            # Generamos un ID único para el cliente
            cliente_uuid = str(uuid.uuid4())
            # Creamos el ID del objeto de Wallet para guardarlo en la base de datos
            wallet_object_id = f"3388000000023162682.{cliente_uuid.replace('-', '_')}"
            
            try:
                # 4.1 Guardar en Supabase con TODOS los campos
                datos_insertar = {
                    "id": cliente_uuid,
                    "nombre_completo": nombre,
                    "email": correo,
                    "telefono": telefono,
                    "genero": genero,
                    "fecha_nacimiento": fecha_nacimiento.strftime("%Y-%m-%d"), # Convertimos a texto para SQL
                    "categoria": categoria,
                    "posicion": posicion,
                    "wallet_object_id": wallet_object_id
                }
                
                respuesta = supabase.table("clientes_wallet").insert(datos_insertar).execute()
                
                # 4.2 Generar enlace de Wallet
                wallet_link = generar_enlace_wallet(cliente_uuid, nombre, wallet_object_id)
                
                # 4.3 Mostrar mensaje de éxito y botón
                st.success(f"¡Registro exitoso para {nombre}! Descarga tu tarjeta aquí abajo:")
                
                # Botón oficial de Google
                st.markdown(
                    f"""
                    <div style="text-align: center; margin-top: 20px; margin-bottom: 20px;">
                        <a href="{wallet_link}" target="_blank">
                            <img src="https://developers.google.com/wallet/images/es-419_add_to_google_wallet_add-wallet-badge.png" alt="Añadir a Google Wallet" width="250">
                        </a>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                # Enlace alternativo en texto
                st.markdown(f"<div style='text-align: center;'><a href='{wallet_link}' target='_blank'>Si la imagen no carga, haz clic aquí para abrir Wallet</a></div>", unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Hubo un error de conexión con la base de datos: {e}")
        else:
            st.warning("Por favor, llena los campos obligatorios (Nombre y Correo).")
