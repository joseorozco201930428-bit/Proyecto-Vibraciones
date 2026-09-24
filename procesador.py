"""
===========================================================
PROCESADOR DE DATOS DE VIBRACIONES - VERSIÓN 3.3
===========================================================
- Detecta automáticamente la línea base del motor desde el CSV
- Fallback a valores por defecto si el motor está apagado/sensor desconectado
- Análisis y sintéticos adaptados a las características reales del motor
- Firma espectral ADAPTATIVA (se calcula desde el RPM real)
- Genera UN SOLO JSON sintético realista con escenarios mezclados
- Sin metadatos sospechosos (los JSONs parecen datos reales del ESP32)

Autor: [Tu nombre]
Fecha: Septiembre 2026
"""

import pandas as pd
import numpy as np
import json
import os
import random
from datetime import datetime, timedelta


# ============================================================
# CONFIGURACIÓN Y VALORES POR DEFECTO
# ============================================================

# Valores por defecto (usados solo si el CSV no tiene datos válidos)
RPM_BASE_DEFAULT = 3550
TEMP_BASE_DEFAULT = 65.0
ACCEL_X_BASE_DEFAULT = 0.10
ACCEL_Y_BASE_DEFAULT = 0.08

# Umbrales
UMBRAL_ALERTA = 25.0
UMBRAL_FRECUENCIA = 15.0
TEMP_ERROR_DS18B20 = -100.0
RPM_MINIMO_ENCENDIDO = 100  # RPM mínimo para considerar el motor encendido

# Ruido típico del sensor ADXL345 (m/s²)
RUIDO_ADXL345 = 0.02
# Offset de gravedad típico del ADXL345
OFFSET_GRAVEDAD_X = 1.96
OFFSET_GRAVEDAD_Y = 2.04


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def leer_csv(ruta_csv):
    """Lee un archivo CSV con los datos del ESP32."""
    try:
        df = pd.read_csv(ruta_csv)
        df.columns = df.columns.str.strip()
        
        mapeo = {
            'Timestamp': 'timestamp',
            'RPM': 'rpm',
            'Temperatura (°C)': 'temperatura',
            'Temperatura': 'temperatura',
            'Accel X (m/s²)': 'accelX',
            'Accel X': 'accelX',
            'Accel Y (m/s²)': 'accelY',
            'Accel Y': 'accelY',
            'Estado': 'estado'
        }
        df = df.rename(columns=mapeo)
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        for col in ['rpm', 'temperatura', 'accelX', 'accelY']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna(subset=['timestamp'])
        df = df.dropna(subset=['accelX', 'accelY'], how='all')
        
        return df
        
    except Exception as e:
        raise Exception(f"Error al leer CSV: {str(e)}")


def detectar_linea_base(df):
    """
    Detecta la línea base del motor desde los datos del CSV.
    
    Si el motor está encendido (RPM > RPM_MINIMO_ENCENDIDO) y el sensor
    de temperatura está conectado, usa estadísticas reales.
    
    Si no, usa valores por defecto.
    """
    # Filtrar datos válidos
    df_motor_encendido = df[df['rpm'] > RPM_MINIMO_ENCENDIDO].copy()
    df_temp_valida = df_motor_encendido[
        df_motor_encendido['temperatura'] > TEMP_ERROR_DS18B20
    ].copy()
    
    # Detectar RPM base
    if len(df_motor_encendido) > 0:
        rpm_base = float(df_motor_encendido['rpm'].mean())
    else:
        rpm_base = RPM_BASE_DEFAULT
    
    # Detectar temperatura base
    if len(df_temp_valida) > 0:
        temp_base = float(df_temp_valida['temperatura'].mean())
    else:
        temp_base = TEMP_BASE_DEFAULT
    
    # Detectar offsets de aceleración
    if len(df) > 0:
        accel_x_base = float(df['accelX'].mean())
        accel_y_base = float(df['accelY'].mean())
        
        if pd.isna(accel_x_base) or abs(accel_x_base) > 20:
            accel_x_base = OFFSET_GRAVEDAD_X
        if pd.isna(accel_y_base) or abs(accel_y_base) > 20:
            accel_y_base = OFFSET_GRAVEDAD_Y
    else:
        accel_x_base = OFFSET_GRAVEDAD_X
        accel_y_base = OFFSET_GRAVEDAD_Y
    
    return {
        'rpm_base': rpm_base,
        'temp_base': temp_base,
        'accel_x_base': accel_x_base,
        'accel_y_base': accel_y_base
    }


def calcular_rms(accelX, accelY):
    """Calcula el RMS de la vibración (sin gravedad)."""
    try:
        accelX = np.array(accelX, dtype=float)
        accelY = np.array(accelY, dtype=float)
        
        mask = ~(np.isnan(accelX) | np.isnan(accelY))
        accelX = accelX[mask]
        accelY = accelY[mask]
        
        if len(accelX) == 0:
            return None
        
        accelX_ac = accelX - np.mean(accelX)
        accelY_ac = accelY - np.mean(accelY)
        
        magnitud_cuadrada = accelX_ac**2 + accelY_ac**2
        rms = np.sqrt(np.mean(magnitud_cuadrada))
        
        return round(float(rms), 4)
        
    except Exception as e:
        print(f"Error calculando RMS: {e}")
        return None


def calcular_firma_desde_rpm(rpm_promedio):
    """
    Calcula la firma espectral esperada desde el RPM.
    
    FÓRMULA:
    - 1x RPM = rpm / 60
    - 2x RPM = 2 × (rpm / 60)
    - 3x RPM = 3 × (rpm / 60)
    """
    if rpm_promedio <= 0:
        return [0.0, 0.0, 0.0]
    
    f_1x = rpm_promedio / 60
    f_2x = 2 * f_1x
    f_3x = 3 * f_1x
    
    return [round(f_1x, 1), round(f_2x, 1), round(f_3x, 1)]


def comparar_firmas(firma_medida, firma_referencia, tolerancia=UMBRAL_FRECUENCIA):
    """Compara firma medida con la de referencia."""
    diferencias = []
    
    for medida, ref in zip(firma_medida, firma_referencia):
        diff = abs(medida - ref)
        diferencias.append(round(diff, 1))
    
    alerta = any(d > tolerancia for d in diferencias)
    
    return diferencias, alerta


def analizar_escenario(df_escenario, nombre_escenario, linea_base):
    """
    Analiza un escenario específico.
    
    La firma de referencia se calcula desde el RPM base detectado.
    El JSON resultante NO incluye metadatos de debug.
    """
    n_registros = len(df_escenario)
    rpm_base = linea_base['rpm_base']
    
    # Validaciones
    rpm_max = float(df_escenario['rpm'].max())
    motor_apagado = (rpm_max == 0)
    
    temps_validas = df_escenario['temperatura'][df_escenario['temperatura'] > TEMP_ERROR_DS18B20]
    sensor_temp_ok = len(temps_validas) > 0
    
    # ============================================
    # ANÁLISIS DE RPM
    # ============================================
    rpm_promedio = float(df_escenario['rpm'].mean())
    rpm_desviacion_std = float(df_escenario['rpm'].std()) if len(df_escenario) > 1 else 0.0
    rpm_min_val = float(df_escenario['rpm'].min())
    rpm_max_val = float(df_escenario['rpm'].max())
    
    if motor_apagado:
        desviacion_pct = 0.0
        alerta_rpm = False
    else:
        desviacion_pct = ((rpm_promedio - rpm_base) / rpm_base) * 100
        alerta_rpm = abs(desviacion_pct) > UMBRAL_ALERTA
    
    # ============================================
    # ANÁLISIS DE TEMPERATURA
    # ============================================
    if sensor_temp_ok:
        temp_promedio_val = round(float(temps_validas.mean()), 1)
        temp_desviacion_std = round(float(temps_validas.std()), 2) if len(temps_validas) > 1 else 0.0
        temp_min_val = round(float(temps_validas.min()), 1)
        temp_max_val = round(float(temps_validas.max()), 1)
    else:
        temp_promedio_val = None
        temp_desviacion_std = None
        temp_min_val = None
        temp_max_val = None
    
    # ============================================
    # ANÁLISIS DE VIBRACIÓN (RMS)
    # ============================================
    rms_vibracion = calcular_rms(df_escenario['accelX'].values, df_escenario['accelY'].values)
    
    # ============================================
    # ANÁLISIS DE FRECUENCIA (OPCIÓN B: adaptativa)
    # ============================================
    if motor_apagado:
        firma_medida = []
        firma_referencia = calcular_firma_desde_rpm(rpm_base)
        diferencias = []
        alerta_frecuencia = False
    else:
        firma_medida = calcular_firma_desde_rpm(rpm_promedio)
        firma_referencia = calcular_firma_desde_rpm(rpm_base)
        diferencias, alerta_frecuencia = comparar_firmas(
            firma_medida, firma_referencia
        )
    
    # ============================================
    # ESTADO DEL ESCENARIO
    # ============================================
    if motor_apagado:
        estado_escenario = "Motor Apagado"
    elif alerta_rpm or alerta_frecuencia:
        estado_escenario = "Fuera de Rango"
    else:
        estado_escenario = "En Rango"
    
    # ============================================
    # RESUMEN ANALÍTICO
    # ============================================
    resumen_partes = []
    
    if motor_apagado:
        resumen_partes.append("Motor apagado (RPM = 0)")
    else:
        resumen_partes.append(f"RPM promedio: {rpm_promedio:.1f}")
    
    if sensor_temp_ok:
        resumen_partes.append(f"Temperatura: {temp_promedio_val:.1f}°C")
    
    if rms_vibracion is not None and rms_vibracion > 0:
        resumen_partes.append(f"RMS vibración: {rms_vibracion:.4f} m/s²")
    
    if not motor_apagado and alerta_rpm:
        resumen_partes.append(
            f"ALERTA: RPM desviadas {desviacion_pct:+.2f}% respecto a la línea base ({rpm_base:.1f})"
        )
    
    if not motor_apagado and alerta_frecuencia:
        resumen_partes.append(
            f"ALERTA: firma espectral desviada respecto a la esperada ({firma_referencia} Hz)"
        )
    
    if not motor_apagado and not alerta_rpm and not alerta_frecuencia and sensor_temp_ok:
        resumen_partes.append("Operación normal")
    
    resumen = ". ".join(resumen_partes) + "."
    
    # ============================================
    # RESULTADO - Solo campos esenciales
    # ============================================
    resultado = {
        "estado_operativo": estado_escenario,
        "analisis_rpm": {
            "rpm_medida": round(rpm_promedio, 1),
            "rpm_desviacion_estandar": round(rpm_desviacion_std, 2),
            "rpm_min": round(rpm_min_val, 1),
            "rpm_max": round(rpm_max_val, 1),
            "rpm_linea_base_promedio": round(rpm_base, 1),
            "desviacion_porcentual": round(desviacion_pct, 2),
            "alerta_rpm": alerta_rpm
        },
        "analisis_temperatura": {
            "temperatura_promedio": temp_promedio_val,
            "temperatura_desviacion_estandar": temp_desviacion_std,
            "temperatura_min": temp_min_val,
            "temperatura_max": temp_max_val
        },
        "analisis_vibracion": {
            "rms_vibracion_m_s2": rms_vibracion
        },
        "analisis_frecuencia": {
            "firma_esperada_hz": firma_referencia,
            "frecuencias_medidas_hz": firma_medida,
            "diferencias_hz": diferencias,
            "alerta_frecuencia": alerta_frecuencia
        },
        "resumen_analitico": resumen
    }
    
    return resultado


def calcular_analisis_completo(df):
    """
    Análisis completo agrupando por escenario.
    La línea base se detecta automáticamente desde el CSV.
    """
    linea_base = detectar_linea_base(df)
    
    # Análisis global
    analisis_global = analizar_escenario(df, "Global", linea_base)
    
    # Análisis por escenario
    analisis_por_escenario = {}
    
    if 'estado' in df.columns:
        escenarios_unicos = df['estado'].dropna().unique()
        
        for escenario in escenarios_unicos:
            df_escenario = df[df['estado'] == escenario].copy()
            if len(df_escenario) > 0:
                analisis_por_escenario[escenario] = analizar_escenario(
                    df_escenario, escenario, linea_base
                )
    
    # Estado global
    if len(analisis_por_escenario) > 0:
        estados = [a["estado_operativo"] for a in analisis_por_escenario.values()]
        
        if "Fuera de Rango" in estados:
            estado_global = "Fuera de Rango"
        elif "Motor Apagado" in estados and all(e == "Motor Apagado" for e in estados):
            estado_global = "Motor Apagado"
        else:
            estado_global = "En Rango"
    else:
        estado_global = analisis_global["estado_operativo"]
    
    # ============================================
    # RESULTADO LIMPIO - Sin metadatos de debug
    # ============================================
    resultado = {
        "estado_operativo": estado_global,
        "total_registros": len(df),
        "analisis_rpm": analisis_global["analisis_rpm"],
        "analisis_temperatura": analisis_global["analisis_temperatura"],
        "analisis_vibracion": analisis_global["analisis_vibracion"],
        "analisis_frecuencia": analisis_global["analisis_frecuencia"],
        "resumen_analitico": analisis_global["resumen_analitico"]
    }
    
    # Análisis por escenario (si hay)
    if analisis_por_escenario:
        resultado["analisis_por_escenario"] = analisis_por_escenario
    
    return resultado


def convertir_csv_a_json(ruta_csv, carpeta_salida):
    """Convierte un CSV en dos JSONs (original + análisis)."""
    df = leer_csv(ruta_csv)
    
    if len(df) == 0:
        raise Exception("El CSV está vacío")
    
    fecha_inicio = df['timestamp'].min()
    fecha_fin = df['timestamp'].max()
    fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
    fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')
    
    # JSON original
    registros = []
    for _, row in df.iterrows():
        registro = {
            "timestamp": row['timestamp'].isoformat() + "Z" if pd.notna(row['timestamp']) else None,
            "rpm": float(row['rpm']) if pd.notna(row['rpm']) else None,
            "temperatura": float(row['temperatura']) if pd.notna(row['temperatura']) else None,
            "accelX": float(row['accelX']) if pd.notna(row['accelX']) else None,
            "accelY": float(row['accelY']) if pd.notna(row['accelY']) else None,
            "estado": str(row['estado']) if pd.notna(row['estado']) else "Desconocido"
        }
        registros.append(registro)
    
    json_original = {
        "equipo_id": "MOTOR_BOMBA_110V_01",
        "fecha_inicio": fecha_inicio.isoformat() + "Z",
        "fecha_fin": fecha_fin.isoformat() + "Z",
        "total_registros": len(registros),
        "registros": registros
    }
    
    analisis = calcular_analisis_completo(df)
    
    os.makedirs(carpeta_salida, exist_ok=True)
    nombre_base = f"datos_de_{fecha_inicio_str}_a_{fecha_fin_str}"
    
    ruta_original = os.path.join(carpeta_salida, f"{nombre_base}_original.json")
    ruta_analisis = os.path.join(carpeta_salida, f"{nombre_base}_analisis.json")
    
    with open(ruta_original, 'w', encoding='utf-8') as f:
        json.dump(json_original, f, indent=2, ensure_ascii=False)
    
    with open(ruta_analisis, 'w', encoding='utf-8') as f:
        json.dump(analisis, f, indent=2, ensure_ascii=False)
    
    return ruta_original, ruta_analisis, len(registros)


# ============================================================
# GENERADOR DE DATOS SINTÉTICOS REALISTAS
# ============================================================

def simular_ruido_sensor(escala=1.0):
    """Simula el ruido característico del sensor ADXL345."""
    return np.random.normal(0, RUIDO_ADXL345 * escala)


def simular_deriva_temporal(valor_anterior, valor_objetivo, factor_suavizado=0.3):
    """Simula la inercia del sensor: los valores cambian gradualmente."""
    return valor_anterior + factor_suavizado * (valor_objetivo - valor_anterior)


def generar_plan_escenarios(cantidad_total):
    """
    Crea un plan de escenarios en 'rachas' que simulan cómo un motor
    real pasa por períodos de falla.
    """
    proporciones = {
        'normal': 0.80,
        'rpm_alto': 0.08,
        'frecuencia_anomala': 0.06,
        'temperatura_alta': 0.04,
        'alerta_critica': 0.02
    }
    
    objetivos = {k: int(cantidad_total * v) for k, v in proporciones.items()}
    total_objetivos = sum(objetivos.values())
    objetivos['normal'] += cantidad_total - total_objetivos
    
    plan = []
    contadores = {k: 0 for k in proporciones.keys()}
    
    while sum(contadores.values()) < cantidad_total:
        restantes = {k: objetivos[k] - contadores[k] for k in objetivos}
        escenarios_disponibles = [k for k, v in restantes.items() if v > 0]
        
        if not escenarios_disponibles:
            break
        
        pesos = [restantes[k] for k in escenarios_disponibles]
        escenario = random.choices(escenarios_disponibles, weights=pesos)[0]
        
        tamaño_racha = min(
            random.randint(30, 150),
            restantes[escenario],
            cantidad_total - sum(contadores.values())
        )
        
        if tamaño_racha <= 0:
            break
        
        plan.extend([escenario] * tamaño_racha)
        contadores[escenario] += tamaño_racha
    
    while len(plan) < cantidad_total:
        plan.append('normal')
    
    return plan


def generar_registros_sinteticos_realistas(df_real, fecha_inicio, fecha_fin, intervalo_segundos):
    """
    Genera registros sintéticos que simulan ser datos reales del ESP32.
    La línea base se detecta automáticamente del CSV.
    """
    duracion_total = (fecha_fin - fecha_inicio).total_seconds()
    cantidad_total = int(duracion_total / intervalo_segundos)
    
    if cantidad_total <= 0:
        raise Exception("El rango de fechas es demasiado corto para el intervalo seleccionado")
    
    # Detectar línea base del CSV
    linea_base = detectar_linea_base(df_real)
    
    rpm_mean = linea_base['rpm_base']
    temp_mean = linea_base['temp_base']
    accelX_base = linea_base['accel_x_base']
    accelY_base = linea_base['accel_y_base']
    
    # Calcular desviaciones estándar
    df_motor_encendido = df_real[df_real['rpm'] > RPM_MINIMO_ENCENDIDO]
    if len(df_motor_encendido) > 1:
        rpm_std = float(df_motor_encendido['rpm'].std())
        if pd.isna(rpm_std) or rpm_std == 0:
            rpm_std = rpm_mean * 0.008
    else:
        rpm_std = rpm_mean * 0.008
    
    df_temp_valida = df_real[df_real['temperatura'] > TEMP_ERROR_DS18B20]
    if len(df_temp_valida) > 1:
        temp_std = float(df_temp_valida['temperatura'].std())
        if pd.isna(temp_std) or temp_std == 0:
            temp_std = 1.5
    else:
        temp_std = 1.5
    
    plan_escenarios = generar_plan_escenarios(cantidad_total)
    
    registros = []
    intervalo = timedelta(seconds=intervalo_segundos)
    
    # Valores iniciales
    rpm_actual = rpm_mean
    temp_actual = temp_mean
    accelX_actual = accelX_base + ACCEL_X_BASE_DEFAULT
    accelY_actual = accelY_base + ACCEL_Y_BASE_DEFAULT
    
    for i in range(cantidad_total):
        ts = fecha_inicio + intervalo * i
        escenario = plan_escenarios[i]
        
        if escenario == "normal":
            rpm_objetivo = rpm_mean + np.random.normal(0, rpm_std * 0.3)
            temp_objetivo = temp_mean + np.random.normal(0, temp_std * 0.3)
            vib_x = 0.10 + np.random.normal(0, 0.03)
            vib_y = 0.08 + np.random.normal(0, 0.03)
            accelX_objetivo = accelX_base + vib_x
            accelY_objetivo = accelY_base + vib_y
            estado = "Normal"
            
        elif escenario == "rpm_alto":
            factor = random.uniform(1.25, 1.45)
            rpm_objetivo = rpm_mean * factor + np.random.normal(0, rpm_std * 0.5)
            temp_objetivo = temp_mean + random.uniform(5, 15) + np.random.normal(0, 1.5)
            vib_x = 0.25 + np.random.normal(0, 0.05)
            vib_y = 0.20 + np.random.normal(0, 0.05)
            accelX_objetivo = accelX_base + vib_x
            accelY_objetivo = accelY_base + vib_y
            estado = "Alerta_RPM"
            
        elif escenario == "frecuencia_anomala":
            rpm_objetivo = rpm_mean + np.random.normal(0, rpm_std * 0.3)
            temp_objetivo = temp_mean + random.uniform(0, 8) + np.random.normal(0, 1.0)
            t = i * 0.05
            amplitud_oscilante = 0.5 + 0.5 * np.sin(2 * np.pi * 0.1 * t)
            vib_x = 0.20 * amplitud_oscilante + np.random.normal(0, 0.03)
            vib_y = 0.15 * amplitud_oscilante + np.random.normal(0, 0.03)
            accelX_objetivo = accelX_base + vib_x
            accelY_objetivo = accelY_base + vib_y
            estado = "Alerta_Vibracion"
            
        elif escenario == "temperatura_alta":
            rpm_objetivo = rpm_mean + np.random.normal(0, rpm_std * 0.3)
            temp_objetivo = temp_mean + random.uniform(20, 35) + np.random.normal(0, 2.0)
            vib_x = 0.10 + np.random.normal(0, 0.04)
            vib_y = 0.08 + np.random.normal(0, 0.04)
            accelX_objetivo = accelX_base + vib_x
            accelY_objetivo = accelY_base + vib_y
            estado = "Alerta_Temperatura"
            
        elif escenario == "alerta_critica":
            factor = random.uniform(1.25, 1.45)
            rpm_objetivo = rpm_mean * factor + np.random.normal(0, rpm_std * 0.5)
            temp_objetivo = temp_mean + random.uniform(25, 40) + np.random.normal(0, 2.0)
            vib_x = 0.40 + np.random.normal(0, 0.08)
            vib_y = 0.35 + np.random.normal(0, 0.08)
            accelX_objetivo = accelX_base + vib_x
            accelY_objetivo = accelY_base + vib_y
            estado = "Alerta_Critica"
            
        else:
            rpm_objetivo = rpm_mean
            temp_objetivo = temp_mean
            accelX_objetivo = accelX_base + ACCEL_X_BASE_DEFAULT
            accelY_objetivo = accelY_base + ACCEL_Y_BASE_DEFAULT
            estado = "Normal"
        
        # Deriva temporal
        rpm_actual = simular_deriva_temporal(rpm_actual, rpm_objetivo, 0.4)
        temp_actual = simular_deriva_temporal(temp_actual, temp_objetivo, 0.3)
        accelX_actual = simular_deriva_temporal(accelX_actual, accelX_objetivo, 0.5)
        accelY_actual = simular_deriva_temporal(accelY_actual, accelY_objetivo, 0.5)
        
        # Ruido del sensor
        rpm_final = int(round(rpm_actual + np.random.normal(0, 3)))
        temp_final = temp_actual + np.random.normal(0, 0.2)
        accelX_final = accelX_actual + simular_ruido_sensor(1.0)
        accelY_final = accelY_actual + simular_ruido_sensor(1.0)
        
        # Timestamp en formato IDÉNTICO al del ESP32
        timestamp_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        
        registros.append({
            'timestamp': timestamp_str,
            'rpm': float(max(0, rpm_final)),
            'temperatura': round(float(temp_final), 1),
            'accelX': round(float(accelX_final), 3),
            'accelY': round(float(accelY_final), 3),
            'estado': estado
        })
    
    return registros


def generar_json_sintetico(df_real, fecha_inicio, fecha_fin, intervalo_segundos, carpeta_salida):
    """
    Genera un JSON con datos sintéticos realistas.
    La línea base se detecta del CSV (motor encendido) o usa defaults.
    """
    registros = generar_registros_sinteticos_realistas(
        df_real, fecha_inicio, fecha_fin, intervalo_segundos
    )
    
    fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%dT%H:%M:%SZ")
    fecha_fin_str = fecha_fin.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    json_sintetico = {
        "equipo_id": "MOTOR_BOMBA_110V_01",
        "fecha_inicio": fecha_inicio_str,
        "fecha_fin": fecha_fin_str,
        "total_registros": len(registros),
        "registros": registros
    }
    
    os.makedirs(carpeta_salida, exist_ok=True)
    
    fecha_ini_nombre = fecha_inicio.strftime('%Y-%m-%d')
    fecha_fin_nombre = fecha_fin.strftime('%Y-%m-%d')
    nombre_archivo = f"datos_de_{fecha_ini_nombre}_a_{fecha_fin_nombre}.json"
    
    ruta_json = os.path.join(carpeta_salida, nombre_archivo)
    
    with open(ruta_json, 'w', encoding='utf-8') as f:
        json.dump(json_sintetico, f, indent=2, ensure_ascii=False)
    
    return ruta_json, len(registros)