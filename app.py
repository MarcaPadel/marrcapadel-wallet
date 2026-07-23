import streamlit as st
import json
import time
import jwt
import datetime #
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
        "state": "COMPLETED",
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
st.markdown("Regístrate para obtener tu tarjeta digital, acumular sellos en cada visita y ganar descuentos exclusivos en tus rentas. Si tienes algún problema con tu registro, Ale o Jenny en recepción con gusto te apoyarán.")

# Creamos el formulario de registro
with st.form("registro_form"):
    st.subheader("Tus Datos Generales")
    nombre = st.text_input("Nombre completo*")
    telefono = st.text_input("Teléfono (WhatsApp)*")
    email = st.text_input("Correo electrónico*")
    fecha_nacimiento = st.date_input(
        "Fecha de nacimiento", 
        min_value=datetime.date(1930, 1, 1), 
        max_value=datetime.date.today(),
        value=None
    )
    genero = st.selectbox("Género", ["Selecciona una opción", "Masculino", "Femenino", "Prefiero no decirlo"])
    
    st.markdown("---")
    st.subheader("Perfil de Jugador")
    st.caption("Conocer tu nivel y posición nos ayudará a armar mejores cuadros para torneos y clínicas con nuestros coaches (Isaac, Manu, Dana y Edu).")
    
    categoria = st.selectbox("Categoría de Juego", ["No sé mi nivel", "Principiante", "6ta", "5ta", "4ta", "3ra", "2da", "1ra"])
    posicion = st.selectbox("Posición favorita", ["Aún no lo sé", "Drive (Derecha)", "Revés (Izquierda)", "Ambas"])
    
    # Botón de envío
    submit_button = st.form_submit_button("Generar mi Tarjeta Digital", use_container_width=True)

# Lógica cuando el jugador presiona el botón
if submit_button:
    if nombre and email and telefono:
        try:
            # 1. Conectarnos a Supabase usando los Secrets
            supabase_url = st.secrets["SUPABASE_URL"]
            supabase_key = st.secrets["SUPABASE_KEY"]
            supabase: Client = create_client(supabase_url, supabase_key)
            
            # Formatear datos opcionales
            genero_final = genero if genero != "Selecciona una opción" else None
            categoria_final = categoria if categoria != "No sé mi nivel" else None
            posicion_final = posicion if posicion != "Aún no lo sé" else None
            
            # 2. Guardar al jugador en tu tabla
            respuesta = supabase.table("clientes_wallet").insert({
                "nombre_completo": nombre,
                "telefono": telefono,
                "email": email,
                "saldo": 0,
                "genero": genero_final,
                "fecha_nacimiento": str(fecha_nacimiento),
                "categoria": categoria_final,
                "posicion": posicion_final
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
                <div style="text-align: center; margin-top: 20px;">
                    <a href="{wallet_link}" target="_blank">
                        <img src="https://developers.google.com/wallet/images/es-419_add_to_google_wallet_add-wallet-badge.png" alt="Añadir a Google Wallet" width="250">
                    </a>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
        except Exception as e:
            st.error(f"Error técnico detallado para revisión: {e}")
    else:
        st.warning("⚠️ El nombre, teléfono y correo son obligatorios.")
