from google import genai

API_KEY = "AQ.Ab8RN6I9JPKp1vE7P5AJWy-qMd5QkT_cGBPSo-mG_qZ57weNHg"

def probar_conexion_gem():
    print("Iniciando prueba de conexión con la API del agente GEM...")
    
    try:
        client = genai.Client(api_key=API_KEY)
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents="Responde 'Conexión exitosa' si me escuchas."
        )
        
        print("\nESTADO: API configurada correctamente.")
        print(f"Respuesta del GEM: {response.text}")
        
    except Exception as e:
        print(f"\nERROR de conexión: {e}")

if __name__ == "__main__":
    probar_conexion_gem()