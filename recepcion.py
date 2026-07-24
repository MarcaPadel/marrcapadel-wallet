import streamlit as st
from supabase import create_client, Client
import cv2
import numpy as np
from PIL import Image
import json
import requests
from google.oauth2 import service_account
import google.auth.transport.requests

st.set_page_config(page_title="Recepción | Marca Pádel", page_icon="📲", layout="centered")

try:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(supabase_url, supabase_key)
except Exception as e:
    st.error("Error de configuración de Supabase.")

# --- NUEVA FUNCIÓN PARA AVISAR A GOOGLE (CON DETECTOR DE ERRORES) ---
def actualizar_tarjeta_google(object_id, nuevos_sellos):
    try:
        cred_dict = json.loads(st.secrets["credenciales_google"])
        if "\\n" in cred_dict["private_key"]:
            cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
            
        credentials = service_account.Credentials.from_service_account_info(
            cred_dict,
            scopes=['https://www.googleapis.com/auth/wallet_object.issuer']
        )
        
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        token = credentials.token
        
        url = f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyObject/{object_id}"
        nueva_imagen = f"https://cfsrslqamambagahfzzv.supabase.co/storage/v1/object/public/wallet-assets/sellos_{nuevos_sellos}.png"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "heroImage": {
                "sourceUri": {
                    "uri": nueva_imagen
                },
                "contentDescription": {
                    "defaultValue": {
                        "language": "es-MX",
                        "value": f"Planilla con {nuevos_sellos} sellos"
                    }
                }
            },
            "loyaltyPoints": {
                "label": "Sellos",
                "balance": {
                    "string": f"{nuevos_sellos} / 10"
                }
            }
        }
        
        respuesta = requests.patch(url, headers=headers, json=payload)
        
        if respuesta.status_code == 200:
            return True, "OK"
        else:
            return False, f"Error {respuesta.status_code}: {respuesta.text}"
            
    except Exception as e:
        return False, str(e)

# --- INTERFAZ DE ESCÁNER ---
st.title("📲 Escáner de Visitas")
st.write("Toma una foto del código QR del jugador para sumar un sello.")

foto = st.camera_input("Escanear Tarjeta")

if foto is not None:
    image = Image.open(foto)
    img_array = np.array(image)
    cv_img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    detector = cv2.QRCodeDetector()
    data, bbox, _ = detector.detectAndDecode(cv_img)
    
    if data:
        st.success("✅ ¡Código QR leído!")
        try:
            respuesta = supabase.table("clientes_wallet").select("*").eq("id", data).execute()
            cliente = respuesta.data
            
            if len(cliente) > 0:
                jugador = cliente[0]
                nombre_jugador = jugador['nombre_completo']
                saldo_actual = int(jugador.get('saldo') or 0)
                wallet_object_id = jugador['wallet_object_id']
                
                st.markdown("---")
                st.subheader(f"🎾 {nombre_jugador}")
                st.write(f"**Sellos actuales:** {saldo_actual} / 10")
                
                if saldo_actual < 10:
                    if st.button("➕ Sumar 1 Sello", type="primary", use_container_width=True):
                        nuevo_saldo = saldo_actual + 1
                        
                        # 1. Actualizar Supabase
                        supabase.table("clientes_wallet").update({"saldo": nuevo_saldo}).eq("id", data).execute()
                        
                        # 2. AVISAR A GOOGLE WALLET
                        with st.spinner("Actualizando pase en el celular del jugador..."):
                            exito_google, mensaje_error = actualizar_tarjeta_google(wallet_object_id, nuevo_saldo)
                        
                        if exito_google:
                            st.success(f"¡Listo! {nombre_jugador} ahora tiene {nuevo_saldo} sellos y su Google Wallet ha sido actualizado.")
                        else:
                            st.warning(f"Sello guardado en base de datos ({nuevo_saldo}/10), pero hubo un error actualizando Google Wallet.")
                            # AQUÍ ESTÁ LA MAGIA: Nos mostrará el error exacto
                            st.error(f"Detalle técnico para Google: {mensaje_error}")
                            
                else:
                    st.info("🎉 ¡Tarjeta completada! Premio listo para ser canjeado.")
            else:
                st.error("El código no corresponde a ningún jugador registrado.")
                
        except Exception as e:
            st.error(f"Error en la base de datos: {e}")
            
    else:
        st.warning("No se detectó ningún QR claro. Intenta de nuevo.")
