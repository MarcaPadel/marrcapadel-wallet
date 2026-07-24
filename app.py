import streamlit as st
import json
import time
import jwt
import uuid

def generar_enlace_wallet(cliente_uuid, nombre_cliente, object_id):
    # Tus credenciales e IDs de Google Wallet
    ISSUER_ID = "3388000000023162682"
    CLASS_ID = "SellosMPPC"
    
    CLASS_FULL_ID = f"{ISSUER_ID}.{CLASS_ID}"
    clean_uuid = str(cliente_uuid).replace('-', '_')
    
    # Cargar los secretos de Google desde Streamlit
    credentials = json.loads(st.secrets["credenciales_google"])
    private_key = credentials["private_key"]
    if "\\n" in private_key:
        private_key = private_key.replace("\\n", "\n")
        
    # Estructura de la tarjeta
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
        # Tu imagen de 0 sellos alojada en Supabase
        "heroImage": {
            "sourceUri": {
                "uri": "https://cfsrslqamambagahfzzv.supabase.co/storage/v1/object/public/wallet-assets/sellos_0.png"
            },
            "contentDescription": {
                "defaultValue": {
                    "language": "es-MX",
                    "value": "Planilla de sellos del Marca Pádel Premier Club"
                }
            }
        },
        "textModulesData": [
            {
                "header": "Premio al completar 10 sellos",
                "body": "1 Renta de Pista Gratis 🎾",
                "id": "premio"
            }
        ]
    }
    
    # Firmar el pase con JWT
    claims = {
        "iss": credentials["client_email"],
        "aud": "google",
        "typ": "savetowallet",
        "iat": int(time.time()),
        "payload": {
            "loyaltyObjects": [loyalty_object]
        }
    }
    
    token = jwt.encode(claims, private_key, algorithm="RS256")
    if isinstance(token, bytes):
        token = token.decode('utf-8')
        
    return f"https://pay.google.com/gp/v/save/{token}"


# --- INTERFAZ DE USUARIO EN STREAMLIT ---
st.set_page_config(page_title="Emisión de Tarjetas | Marca Pádel", page_icon="🎾")
st.title("🎾 Generador de Tarjetas Premier")
st.markdown("Crea una nueva tarjeta de sellos para Google Wallet.")

nombre_cliente = st.text_input("Nombre completo del Jugador:")

if st.button("Crear Tarjeta"):
    if nombre_cliente:
        with st.spinner("Generando tarjeta encriptada..."):
            # Generar IDs únicos para este nuevo jugador
            nuevo_uuid = str(uuid.uuid4())
            nuevo_object_id = f"3388000000023162682.{nuevo_uuid.replace('-', '_')}"
            
            # Llamar a la función principal
            enlace = generar_enlace_wallet(nuevo_uuid, nombre_cliente, nuevo_object_id)
            
            st.success("¡Tarjeta generada con éxito!")
            st.markdown(f"### [👉 Haz clic aquí para agregar a Google Wallet]({enlace})")
            
            # Mostrar un pequeño resumen
            st.info(f"**ID de Jugador:** {nuevo_uuid}\n\n**Object ID:** {nuevo_object_id}")
    else:
        st.warning("Por favor, ingresa el nombre del jugador antes de continuar.")
