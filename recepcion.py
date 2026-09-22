import streamlit as st
from supabase import create_client, Client
import cv2
import numpy as np
from PIL import Image
import requests

st.set_page_config(page_title="Recepción | Marca Pádel", page_icon="📲", layout="centered")

# --- 1. CONEXIÓN A SUPABASE ---
try:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(supabase_url, supabase_key)
except Exception as e:
    st.error("Error de configuración de Supabase.")

# --- 2. FUNCIÓN PARA ACTUALIZAR TARJETA VÍA PUSH NOTIFICATION ---
def actualizar_tarjeta_saas(serial_number, nuevos_sellos):
    try:
        url_api = f"https://api.walletwallet.dev/api/passes/{serial_number}" 
        
        headers = {
            "Authorization": f"Bearer {st.secrets['WALLETWALLET_API_KEY']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "dynamicData": {
                "sellos": f"{nuevos_sellos} / 10" 
            }
        }
        
        respuesta = requests.put(url_api, headers=headers, json=payload)
        
        if respuesta.status_code in [200, 201]:
            return True, "OK"
        else:
            return False, f"Error {respuesta.status_code}: {respuesta.text}"
            
    except Exception as e:
        return False, str(e)

# --- 3. INTERFAZ DE ESCÁNER ---
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
                serial_del_pase = jugador.get('wallet_object_id')
                
                st.markdown("---")
                st.subheader(f"🎾 {nombre_jugador}")
                st.write(f"**Sellos actuales:** {saldo_actual} / 10")
                
                if saldo_actual < 10:
                    texto_boton = "➕ Sumar 1 Sello"
                    nuevo_saldo = saldo_actual + 1
                    mensaje_exito = f"¡Listo! {nombre_jugador} ahora tiene {nuevo_saldo} sellos."
                else:
                    st.info("🎉 Esta tarjeta ya estaba llena. Al escanear ahora, se canjeará el premio y se reiniciará el conteo.")
                    texto_boton = "🎁 Canjear Premio y Reiniciar"
                    nuevo_saldo = 1
                    mensaje_exito = f"¡Premio canjeado! Se inició una nueva tarjeta con {nuevo_saldo} sello."

                if st.button(texto_boton, type="primary", use_container_width=True):
                    # Guardar en base de datos
                    supabase.table("clientes_wallet").update({"saldo": nuevo_saldo}).eq("id", data).execute()
                    
                    # Notificar a los teléfonos
                    if serial_del_pase:
                        with st.spinner("Mandando actualización al celular del jugador..."):
                            exito_saas, mensaje_error = actualizar_tarjeta_saas(serial_del_pase, nuevo_saldo)
                        
                        if exito_saas:
                            st.success(mensaje_exito + " La pantalla de su teléfono se actualizará en unos segundos.")
                        else:
                            st.warning(f"Sello guardado ({nuevo_saldo}/10), pero falló la notificación Push.")
                    else:
                        st.warning(f"Sello guardado ({nuevo_saldo}/10). Este cliente tiene un pase viejo.")
                        
            else:
                st.error("El código no corresponde a ningún jugador registrado.")
                
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            
    else:
        st.warning("No se detectó ningún QR claro. Intenta de nuevo.")
