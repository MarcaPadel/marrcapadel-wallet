import streamlit as st
from supabase import create_client, Client
import cv2
import numpy as np
from PIL import Image
import requests
import zxingcpp

st.set_page_config(page_title="Recepción | Marca Pádel", page_icon="📲", layout="centered")

# --- 1. CONEXIÓN A SUPABASE ---
try:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(supabase_url, supabase_key)
except Exception as e:
    st.error("Error de configuración de Supabase.")

# --- 2. FUNCIÓN PARA ACTUALIZAR TARJETA (SELLOS Y FOTOS) ---
def actualizar_tarjeta_saas(serial_number, nuevos_sellos):
    try:
        url_api = f"https://api.walletwallet.dev/api/passes/{serial_number}" 
        
        headers = {
            "Authorization": f"Bearer {st.secrets['WALLETWALLET_API_KEY']}",
            "Content-Type": "application/json"
        }
        
        # Enlace real de la imagen según el número de sellos
        url_nueva_imagen = f"https://github.com/MarcaPadel/marrcapadel-wallet/blob/main/imagenes/sellos_{nuevos_sellos}.png?raw=true"
        
        payload = {
            "heroImage": url_nueva_imagen,
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

# --- 3. LÓGICA COMPARTIDA DE PERFIL Y BOTONES ---
def mostrar_perfil_y_controles(jugador):
    cliente_id = jugador['id']
    nombre_jugador = jugador['nombre_completo']
    saldo_actual = int(jugador.get('saldo') or 0)
    serial_del_pase = jugador.get('wallet_object_id')
    categoria = jugador.get('categoria', 'No especificada')
    
    st.markdown("---")
    st.subheader(f"🎾 {nombre_jugador}")
    
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.write(f"**Categoría:** {categoria}")
    with col_info2:
        st.write(f"**Sellos:** {saldo_actual} / 10")
        
    st.write("") # Espacio
    
    # --- CONTROLES DE SELLOS ---
    col1, col2 = st.columns(2)
    
    # BOTÓN: RESTAR SELLO
    with col1:
        if st.button("➖ Restar 1 (Corregir)", key=f"restar_{cliente_id}", use_container_width=True):
            if saldo_actual > 0:
                nuevo_saldo = saldo_actual - 1
                procesar_actualizacion(cliente_id, serial_del_pase, nuevo_saldo, nombre_jugador, "restado")
            else:
                st.warning("El jugador tiene 0 sellos, no se puede restar más.")
                
    # BOTÓN: SUMAR / CANJEAR
    with col2:
        if saldo_actual < 10:
            if st.button("➕ Sumar 1 Sello", key=f"sumar_{cliente_id}", type="primary", use_container_width=True):
                nuevo_saldo = saldo_actual + 1
                procesar_actualizacion(cliente_id, serial_del_pase, nuevo_saldo, nombre_jugador, "sumado")
        else:
            if st.button("🎁 Canjear Premio y Reiniciar", key=f"canjear_{cliente_id}", type="primary", use_container_width=True):
                procesar_actualizacion(cliente_id, serial_del_pase, 0, nombre_jugador, "canjeado")

# --- 4. FUNCIÓN AUXILIAR PARA PROCESAR EL CAMBIO ---
def procesar_actualizacion(cliente_id, serial_del_pase, nuevo_saldo, nombre_jugador, accion):
    # 1. Actualizar DB
    supabase.table("clientes_wallet").update({"saldo": nuevo_saldo}).eq("id", cliente_id).execute()
    
    # 2. Actualizar Tarjeta Móvil
    if serial_del_pase:
        with st.spinner("Actualizando celular..."):
            exito_saas, msj = actualizar_tarjeta_saas(serial_del_pase, nuevo_saldo)
        if exito_saas:
            if accion == "canjeado":
                st.success(f"¡Premio entregado! La tarjeta de {nombre_jugador} se reinició a 0 sellos.")
            else:
                st.success(f"Sello {accion} correctamente. {nombre_jugador} ahora tiene {nuevo_saldo} sellos.")
        else:
            st.warning(f"Se guardó en base de datos, pero falló la actualización del celular: {msj}")
    else:
        st.info(f"Sello {accion} guardado. Cliente sin tarjeta digital vinculada.")


# ==========================================
# INTERFAZ PRINCIPAL
# ==========================================
st.title("Centro de Recepción")

tab_escaner, tab_manual = st.tabs(["📷 Escanear Tarjeta", "🔍 Búsqueda Manual"])

# --- PESTAÑA 1: ESCÁNER ---
with tab_escaner:
    st.write("Usa la cámara para leer el código Aztec o QR de la tarjeta del jugador.")
    foto = st.camera_input("Cámara de Recepción", key="camara_principal")

    if foto is not None:
        image = Image.open(foto)
        img_array = np.array(image)
        cv_img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        resultados = zxingcpp.read_barcodes(cv_img)
        
        if len(resultados) > 0:
            data = resultados[0].text 
            st.success("✅ ¡Código leído exitosamente!")
            
            try:
                respuesta = supabase.table("clientes_wallet").select("*").eq("id", data).execute()
                cliente = respuesta.data
                
                if len(cliente) > 0:
                    mostrar_perfil_y_controles(cliente[0])
                else:
                    st.error("El código escaneado no corresponde a ningún jugador registrado.")
            except Exception as e:
                st.error(f"Error de base de datos: {e}")
        else:
            st.warning("No se detectó ningún código. Intenta acercar la pantalla.")

# --- PESTAÑA 2: BÚSQUEDA MANUAL (PLAN B) ---
with tab_manual:
    st.write("¿El cliente olvidó su celular? Búscalo por nombre o correo.")
    
    termino_busqueda = st.text_input("Ingresa el nombre o correo del jugador", placeholder="Ej. Juan Pérez o juan@email.com")
    
    if st.button("Buscar Jugador", use_container_width=True):
        if termino_busqueda:
            try:
                # Buscamos coincidencias que contengan el texto en el nombre o en el correo
                respuesta = supabase.table("clientes_wallet").select("*").or_(f"nombre_completo.ilike.%{termino_busqueda}%,email.ilike.%{termino_busqueda}%").execute()
                resultados_busqueda = respuesta.data
                
                if len(resultados_busqueda) > 0:
                    st.success(f"Se encontraron {len(resultados_busqueda)} coincidencias:")
                    for jugador_encontrado in resultados_busqueda:
                        mostrar_perfil_y_controles(jugador_encontrado)
                else:
                    st.warning("No se encontró ningún jugador con ese nombre o correo.")
            except Exception as e:
                st.error(f"Error en la búsqueda: {e}")
        else:
            st.warning("Por favor ingresa un nombre o correo para buscar.")
