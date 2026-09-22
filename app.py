import requests
import streamlit as st
import uuid

def generar_enlace_walletwallet(cliente_uuid, nombre_cliente):
    # La API oficial de WalletWallet para crear un pase
    url_api = "https://api.walletwallet.dev/v1/passes"
    
    headers = {
        "Authorization": f"Bearer {st.secrets['WALLETWALLET_API_KEY']}",
        "Content-Type": "application/json"
    }
    
    # -----------------------------------------------------
    # Configuración de tu tarjeta de Marca Pádel Premier Club
    # (No necesitas ir al editor web, todo se arma aquí)
    # -----------------------------------------------------
    payload = {
        # Textos y diseño principal
        "logoText": "Marca Pádel Premier Club",
        "description": "Tarjeta de Lealtad",
        "backgroundColor": "#1E1E1E", # Fondo negro
        "foregroundColor": "#C5A059", # Texto dorado
        
        # El tipo de pase (Store Card es ideal para lealtad)
        "passType": "storeCard",
        
        # Este es el código QR que leerá tu cámara (el cliente_uuid)
        "barcode": {
            "format": "PKBarcodeFormatQR",
            "message": str(cliente_uuid),
            "messageEncoding": "iso-8859-1",
            "altText": "Muestra este código en recepción"
        },
        
        # Los campos que aparecen en la parte delantera de la tarjeta
        "primaryFields": [
            {
                "key": "jugador",
                "label": "JUGADOR",
                "value": nombre_cliente
            }
        ],
        "secondaryFields": [
            {
                "key": "sellos",
                "label": "SELLOS (Renta de Pista)",
                "value": "0 / 10" # Empieza en cero
            }
        ],
        "auxiliaryFields": [
            {
                "key": "premio",
                "label": "PREMIO AL LLENAR",
                "value": "1 Renta Gratis 🎾"
            }
        ]
    }
    
    # Se realiza la petición a WalletWallet
    respuesta = requests.post(url_api, headers=headers, json=payload)
    
    # Evaluamos si fue exitoso (200 o 201)
    if respuesta.status_code in [200, 201]:
        datos = respuesta.json()
        
        # Obtener el link. WalletWallet suele usar 'passUrl' o 'installUrl'.
        # Usamos .get() con una cadena por defecto para evitar errores de llave (KeyError).
        enlace_descarga = datos.get("passUrl", "")
        
        if enlace_descarga:
             return enlace_descarga
        else:
             # Si la estructura del JSON cambia un poco, imprimimos los datos para debuggear.
             raise Exception(f"No se encontró la URL en la respuesta exitosa. Respuesta: {datos}")
            
    else:
        raise Exception(f"Error {respuesta.status_code} de la API de WalletWallet: {respuesta.text}")
