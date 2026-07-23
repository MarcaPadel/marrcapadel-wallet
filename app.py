import streamlit as st
import json
import time
import jwt
from supabase import create_client, Client

# --- Configuración visual para celulares ---
st.set_page_config(page_title="Lealtad Marca Pádel", page_icon="🎾", layout="centered")

# --- Función que genera la llave de Google ---
def generar_enlace_wallet(cliente_uuid, nombre_cliente):
    # Tus identificadores oficiales
    ISSUER_ID = "BCR2DN6D7KSY5MZ2"
    CLASS_ID = "SellosMPPC"
    OBJECT_ID = f"{ISSUER_ID}.{cliente_uuid}"
    
    # Leemos la credencial de forma segura desde los Secrets de Streamlit
    credentials = json.loads(st.secrets["credenciales_google"])
    
    loyalty_object = {
        "id": OBJECT_ID,
        "classId": f"{ISSUER_ID}.{CLASS_ID}",
        "state": "ACTIVE",
        "accountId": cliente_uuid[:8].upper(),
        "accountName": nombre_cliente,
        "textModulesData": [
            {
                "header": "Sellos Acumulados",
                "body": "0 / 10" 
            }
        ]
    }
    
    claims = {
        "iss": credentials["client_email"],
        "aud": "google",
        "typ": "savetowallet",
        "iat": int(time.time()),
        "payload": {
            "loyaltyObjects": [loyalty_object]
        }
    }
    
    token = jwt.encode(claims, credentials["private_key"], algorithm="RS256")
    return f"https://pay.google.com/gp/v/save/{token}"

# --- Interfaz de Usuario (El Portal) ---
st.title("¡Únete al Premier Club! 🎾")
st.markdown("Regístrate para obtener tu tarjeta digital, acumular sellos en cada visita y ganar descuentos exclusivos en tus rentas de pistas.")

# Creamos el formulario de registro
with st.form("registro_form"):
    nombre = st.text_input("Nombre completo")
    telefono = st.text_input("Teléfono (WhatsApp)")
    email = st.text_input("Correo electrónico")
    
    submit_button = st.form_submit_button("Generar mi Tarjeta Digital", use_container_width=True)

# Lógica cuando el jugador presiona el botón
if submit_button:
    if nombre and email:
        try:
            # 1. Conectarnos a Supabase usando los Secrets
            supabase_url = st.secrets["SUPABASE_URL"]
            supabase_key = st.secrets["SUPABASE_KEY"]
            supabase: Client = create_client(supabase_url, supabase_key)
            
            # 2. Guardar al jugador en tu tabla
            respuesta = supabase.table("clientes_wallet").insert({
                "nombre_completo": nombre,
                "telefono": telefono,
                "email": email,
                "saldo": 0
            }).execute()
            
            # Extraer el ID único que Supabase le asignó
            nuevo_uuid = respuesta.data[0]['id']
            
            # 3. Fabricar su enlace de Google Wallet
            wallet_link = generar_enlace_wallet(nuevo_uuid, nombre)
            
            # 4. Actualizar el registro en Supabase para vincular su tarjeta de Google
            object_id = f"BCR2DN6D7KSY5MZ2.{nuevo_uuid}"
            supabase.table("clientes_wallet").update({"wallet_object_id": object_id}).eq("id", nuevo_uuid).execute()

            # 5. Mostrar el botón final de descarga
            st.success("¡Registro exitoso! Descarga tu tarjeta aquí abajo:")
            st.markdown(
                f"""
                <a href="{wallet_link}" target="_blank">
                    <img src="https://developers.google.com/wallet/images/es-419_add_to_google_wallet_add-wallet-badge.png" alt="Añadir a Google Wallet" width="250">
                </a>
                """, 
                unsafe_allow_html=True
            )
            
        except Exception as e:
            st.error("Ocurrió un error o este correo ya tiene una tarjeta registrada. Por favor, verifica tus datos.")
    else:
        st.warning("⚠️ El nombre y el correo son obligatorios.")
