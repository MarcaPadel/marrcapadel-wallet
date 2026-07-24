import streamlit as st
from supabase import create_client, Client
import cv2
import numpy as np
from PIL import Image

st.set_page_config(page_title="Recepción | Marca Pádel", page_icon="📲", layout="centered")

try:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(supabase_url, supabase_key)
except Exception as e:
    st.error("Error de configuración de Supabase.")

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
                
                st.markdown("---")
                st.subheader(f"🎾 {nombre_jugador}")
                st.write(f"**Sellos actuales:** {saldo_actual} / 10")
                
                if saldo_actual < 10:
                    if st.button("➕ Sumar 1 Sello", type="primary", use_container_width=True):
                        nuevo_saldo = saldo_actual + 1
                        supabase.table("clientes_wallet").update({"saldo": nuevo_saldo}).eq("id", data).execute()
                        st.success(f"¡Sello sumado! {nombre_jugador} ahora tiene {nuevo_saldo} sellos.")
                        # TODO: Aquí irá el código para actualizar la imagen en Google Wallet
                else:
                    st.info("🎉 ¡Tarjeta completada! Premio listo para ser canjeado.")
            else:
                st.error("El código no corresponde a ningún jugador registrado.")
                
        except Exception as e:
            st.error(f"Error en la base de datos: {e}")
            
    else:
        st.warning("No se detectó ningún QR claro. Intenta de nuevo.")
