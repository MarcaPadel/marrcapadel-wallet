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

# --- 2. NUEVA FUNCIÓN PARA AVISAR A WALLETWALLET (ACTUALIZAR SELLOS) ---
def actualizar_tarjeta_saas(cliente_uuid, nuevos_sellos):
    try:
        # En la API de WalletWallet, envías un PUT al endpoint pasándole el barcode o ID del pase
        # Asegúrate de revisar su documentación exacta, generalmente es así:
        url_api = f"https://api.walletwallet.dev/v1/passes/{cliente_uuid}" 
        
        headers = {
            "Authorization": f"Bearer {st.secrets['WALLETWALLET_API_KEY']}",
            "Content-Type": "application/json"
        }
        
        # Solo necesitas enviar la sección que cambia. 
        # En este caso, queremos actualizar el secondaryField de 'sellos'
        payload = {
            "secondaryFields": [
                {
                    "key": "sellos",
                    "label": "SELLOS (Renta de Pista)",
                    "value": f"{nuevos_sellos} / 10" 
                }
            ]
        }
        
        # OJO: Es requests.put para actualizar (Push notification)
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
            # Tu código QR contiene el UUID (que es el ID en tu tabla)
            respuesta = supabase.table("clientes_wallet").select("*").eq("id", data).execute()
            cliente = respuesta.data
            
            if len(cliente) > 0:
                jugador = cliente[0]
                nombre_jugador = jugador['nombre_completo']
                saldo_actual = int(jugador.get('saldo') or 0)
                
                st.markdown("---")
                st.subheader(f"🎾 {nombre_jugador}")
                st.write(f"**Sellos actuales:** {saldo_actual} / 10")
                
                # ── LÓGICA DE CICLO INFINITO (RESETEO) ──
                if saldo_actual < 10:
                    texto_boton = "➕ Sumar 1 Sello"
                    nuevo_saldo = saldo_actual + 1
                    mensaje_exito = f"¡Listo! {nombre_jugador} ahora tiene {nuevo_saldo} sellos. Su tarjeta se actualizó en el teléfono."
                else:
                    st.info("🎉 Esta tarjeta ya estaba llena. Al escanear ahora, se canjeará el premio y se reiniciará el conteo.")
                    texto_boton = "🎁 Canjear Premio y Reiniciar"
                    nuevo_saldo = 1
                    mensaje_exito = f"¡Premio canjeado! {nombre_jugador} inició una nueva tarjeta con {nuevo_saldo} sello."

                if st.button(texto_boton, type="primary", use_container_width=True):
                    
                    # 1. Actualizar tu base de datos (Sigue igual)
                    supabase.table("clientes_wallet").update({"saldo": nuevo_saldo}).eq("id", data).execute()
                    
                    # 2. AVISAR AL SAAS (Manda la señal a Apple y Google)
                    with st.spinner("Mandando notificación push al teléfono del jugador..."):
                        # 'data' es el cliente_uuid extraído del código QR
                        exito_saas, mensaje_error = actualizar_tarjeta_saas(data, nuevo_saldo)
                    
                    if exito_saas:
                        st.success(mensaje_exito)
                    else:
                        st.warning(f"Se guardó el sello en tu base de datos ({nuevo_saldo}/10), pero falló la actualización al teléfono.")
                        st.error(f"Detalle técnico de WalletWallet: {mensaje_error}")
                        
            else:
                st.error("El código no corresponde a ningún jugador registrado.")
                
        except Exception as e:
            st.error(f"Error en la base de datos: {e}")
            
    else:
        st.warning("No se detectó ningún QR claro. Intenta de nuevo.")
