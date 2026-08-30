import json
import random
from datetime import datetime, timedelta
import os

# CONFIGURACIÓN DEL SISTEMA (VALORES "NORMALES")

RPM_BASE = 3550              # RPM normal del motor
FRECUENCIAS_BASE = [60.0, 120.0, 180.0]  # Frecuencias normales en Hz

# Umbral de alerta: desviación > 25%
UMBRAL_ALERTA = 25.0

# FUNCIONES PARA GENERAR DATOS

def generar_registro_normal(timestamp):
    rpm = RPM_BASE + random.randint(-30, 30)
    frecuencias = FRECUENCIAS_BASE.copy()
    
    return {
        "timestamp": timestamp.isoformat() + "Z",
        "rpm": round(rpm, 1),
        "frecuencias_medidas_hz": frecuencias
    }


def generar_registro_rpm_alto(timestamp):
    factor = random.uniform(1.25, 1.45)
    rpm = RPM_BASE * factor
    frecuencias = FRECUENCIAS_BASE.copy()
    
    return {
        "timestamp": timestamp.isoformat() + "Z",
        "rpm": round(rpm, 1),
        "frecuencias_medidas_hz": frecuencias
    }


def generar_registro_frecuencia_anomala(timestamp):    
    rpm = RPM_BASE + random.randint(-30, 30)
    
    # Aparecen frecuencias que NO deberían estar (75 Hz y 250 Hz)
    frecuencias = FRECUENCIAS_BASE.copy()
    
    if random.random() < 0.7: 
        frecuencias.append(75.0)
    if random.random() < 0.5:
        frecuencias.append(250.0)
    
    frecuencias.sort()
    
    return {
        "timestamp": timestamp.isoformat() + "Z",
        "rpm": round(rpm, 1),
        "frecuencias_medidas_hz": frecuencias
    }


def generar_registro_desbalanceo(timestamp):
    # El RPM varía más de lo normal (motor inestable)
    rpm = RPM_BASE + random.randint(-100, 100)
    
    frecuencias = FRECUENCIAS_BASE.copy()
    frecuencia_1x = rpm / 60.0
    
    if frecuencia_1x not in frecuencias:
        frecuencias.append(round(frecuencia_1x, 1))
    
    frecuencias.sort()
    
    return {
        "timestamp": timestamp.isoformat() + "Z",
        "rpm": round(rpm, 1),
        "frecuencias_medidas_hz": frecuencias
    }


def generar_semana(semana_numero, escenario, registros_por_semana=2016):
    registros = []
    fecha = datetime(2026, 8, 10) + timedelta(days=(semana_numero - 1) * 7)
    
    generadores = {
        'normal': generar_registro_normal,
        'rpm_alto': generar_registro_rpm_alto,
        'frecuencia_anomala': generar_registro_frecuencia_anomala,
        'desbalanceo': generar_registro_desbalanceo
    }
    
    generador = generadores.get(escenario, generar_registro_normal)
    
    for i in range(registros_por_semana):
        timestamp_actual = fecha + timedelta(minutes=5 * i)
        registro = generador(timestamp_actual)
        registros.append(registro)
    
    semana = {
        "semana": semana_numero,
        "equipo_id": "MOTOR_BOMBA_110V_01",
        "fecha_inicio": fecha.isoformat() + "Z",
        "fecha_fin": (fecha + timedelta(days=6, hours=23, minutes=59)).isoformat() + "Z",
        "escenario": escenario,
        "total_registros": len(registros),
        "registros": registros
    }
    
    return semana


def guardar_json(datos, nombre_archivo, carpeta="datos/raw"):
    os.makedirs(carpeta, exist_ok=True)
    ruta_completa = os.path.join(carpeta, nombre_archivo)
    
    with open(ruta_completa, 'w', encoding='utf-8') as archivo:
        json.dump(datos, archivo, indent=2, ensure_ascii=False)
    
    print(f"Archivo guardado: {ruta_completa}")
    print(f"Registros: {datos['total_registros']}")


def generar_datos_sinteticos_fallas():
    carpeta_sinteticos = "datos/sinteticos"
    os.makedirs(carpeta_sinteticos, exist_ok=True)
    
    escenarios = [
        ("falla_rpm_alto.json", "rpm_alto", 500, "Falla: RPM excedido >25%"),
        ("falla_frecuencia_anomala.json", "frecuencia_anomala", 500, "Falla: Frecuencias anómalas detectadas"),
        ("falla_desbalanceo.json", "desbalanceo", 500, "Falla: Desbalanceo del rotor")
    ]
    
    print("GENERANDO DATOS SINTÉTICOS DE FALLAS")
    
    for nombre_archivo, escenario, cantidad, descripcion in escenarios:
        print(f"\n{descripcion}")
        
        datos = generar_semana(0, escenario, cantidad)
        datos["descripcion"] = descripcion
        
        ruta = os.path.join(carpeta_sinteticos, nombre_archivo)
        with open(ruta, 'w', encoding='utf-8') as archivo:
            json.dump(datos, archivo, indent=2, ensure_ascii=False)
        
        print(f"Guardado: {ruta}")
        print(f"Registros: {datos['total_registros']}")
    


def main():
    print("GENERADOR DE DATOS DE VIBRACIONES")
    
    print("\n¿Cuántos registros por semana quieres generar?")
    print("   - 604800 = 1 registro cada 1 segundo (1 semana real)")
    print("   - 2016 = 1 registro cada 5 minutos (1 semana real)")
    print("   - 10080 = 1 registro cada minuto")
    print("   - 288 = 1 registro cada 30 minutos")
    
    try:
        registros_por_semana = int(input("\nIngresa un número: ") or 2016)
    except ValueError:
        registros_por_semana = 2016
        print("Usando valor predeterminado: 2016")
    
    print("GENERANDO DATOS...")
    
    print("\nSemana 1: Operación NORMAL")
    print("(Estableciendo línea base de operación)")
    semana_1 = generar_semana(1, "normal", registros_por_semana)
    guardar_json(semana_1, "semana_1_normal.json")
    
    print("\nSemana 2: Operación NORMAL")
    print("(Confirmando línea base)")
    semana_2 = generar_semana(2, "normal", registros_por_semana)
    guardar_json(semana_2, "semana_2_normal.json")
    
    print("\nSemana 3: Operación con FALLAS")
    print("(Simulando RPM alto y frecuencias anómalas)")
    
    semana_3 = generar_semana(3, "normal", registros_por_semana)
    registros = semana_3["registros"]
    total = len(registros)
    
    punto_falla = int(total * 0.6)
    
    for i in range(punto_falla, total):
        timestamp = datetime.fromisoformat(registros[i]["timestamp"].replace("Z", "+00:00"))
        
        if i % 3 == 0:
            registro = generar_registro_rpm_alto(timestamp)
        elif i % 3 == 1:
            registro = generar_registro_frecuencia_anomala(timestamp)
        else:
            registro = generar_registro_desbalanceo(timestamp)
        
        registros[i] = registro
    
    semana_3["escenario"] = "fallas_mixtas"
    semana_3["total_registros"] = len(registros)
    guardar_json(semana_3, "semana_3_fallas_mixtas.json")
    
    # GENERAR DATOS SINTÉTICOS DE FALLAS
    generar_datos_sinteticos_fallas()
    
    total_registros = (
        semana_1["total_registros"] +
        semana_2["total_registros"] +
        semana_3["total_registros"]
    )
    print(f"\nTOTAL DE REGISTROS GENERADOS: {total_registros:,}")

if __name__ == "__main__":
    main()