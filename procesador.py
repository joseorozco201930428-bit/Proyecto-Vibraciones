import pandas as pd
import numpy as np
import json
import os
import random
from datetime import datetime, timedelta
from scipy.signal import find_peaks


# CONFIGURACIÓN BASE

RPM_BASE_DEFAULT = 3450
TEMP_BASE_DEFAULT = 58.0
ACCEL_X_BASE_DEFAULT = 10.0
ACCEL_Y_BASE_DEFAULT = 1.5

RPM_ALERTA_TEMPRANA = 3277
RPM_ALERTA_CRITICA = 3105
TEMP_NORMAL_MIN = 55.0
TEMP_NORMAL_MAX = 62.0
TEMP_ALERTA_TEMPRANA_MIN = 70.0
TEMP_ALERTA_TEMPRANA_MAX = 72.0
TEMP_ALERTA_CRITICA = 80.0
ACCEL_X_ALERTA_TEMPRANA = 11.5
ACCEL_X_ALERTA_CRITICA = 13.0
ACCEL_Y_ALERTA_TEMPRANA = 3.0
ACCEL_Y_ALERTA_CRITICA = 4.5

TEMP_ERROR_DS18B20 = -100.0
RPM_MINIMO_ENCENDIDO = 100
RUIDO_ADXL345 = 0.02

ACCEL_Y_LIMITE_CORRECCION = 10.0
ACCEL_Y_FACTOR_CORRECCION = 1000.0

MAX_PUNTOS_GRAFICA = 500

# CORRECCIÓN DE ACCEL Y

def corregir_accel_y(valor):
    try:
        valor = float(valor)
    except:
        return valor
    
    if abs(valor) > ACCEL_Y_LIMITE_CORRECCION:
        return valor / ACCEL_Y_FACTOR_CORRECCION
    
    return valor

# FIRMA ESPECTRAL

def calcular_firma_desde_rpm(rpm):
    if rpm <= 0:
        return [0.0, 0.0, 0.0]
    
    f_1x = rpm / 60
    f_2x = 2 * f_1x
    f_3x = 3 * f_1x
    
    return [round(f_1x, 1), round(f_2x, 1), round(f_3x, 1)]

# DETECCIÓN DE ESTADOS

def detectar_estado_registro(rpm, temp, accelX, accelY):
    alertas = []
    
    if rpm == 0:
        return "Motor_Apagado", ["Motor apagado"]
    
    if rpm < RPM_ALERTA_CRITICA:
        alertas.append("RPM_Critica")
    elif rpm < RPM_ALERTA_TEMPRANA:
        alertas.append("RPM_Temprana")
    
    if temp > TEMP_ERROR_DS18B20:
        if temp > TEMP_ALERTA_CRITICA:
            alertas.append("Temp_Critica")
        elif temp >= TEMP_ALERTA_TEMPRANA_MIN:
            alertas.append("Temp_Temprana")
    
    if accelX > ACCEL_X_ALERTA_CRITICA:
        alertas.append("AccelX_Critica")
    elif accelX > ACCEL_X_ALERTA_TEMPRANA:
        alertas.append("AccelX_Temprana")
    
    if accelY > ACCEL_Y_ALERTA_CRITICA:
        alertas.append("AccelY_Critica")
    elif accelY > ACCEL_Y_ALERTA_TEMPRANA:
        alertas.append("AccelY_Temprana")
    
    if not alertas:
        return "Normal", []
    
    criticas = [a for a in alertas if "Critica" in a]
    tempranas = [a for a in alertas if "Temprana" in a]
    
    if len(alertas) >= 2 or len(criticas) >= 1:
        return "Alerta_Critica", alertas
    
    if len(tempranas) == 1:
        tipo = tempranas[0].replace("_Temprana", "")
        return f"Alerta_{tipo}", alertas
    
    return "Normal", []

# APARTADO 1: CSV A JSON BÁSICO

def leer_csv(ruta_csv):
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
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', dayfirst=True)
        
        for col in ['rpm', 'temperatura', 'accelX', 'accelY']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if 'accelY' in df.columns:
            df['accelY'] = df['accelY'].apply(corregir_accel_y)
        
        df = df.dropna(subset=['timestamp'])
        df = df.dropna(subset=['accelX', 'accelY'], how='all')
        
        return df
        
    except Exception as e:
        raise Exception(f"Error al leer CSV: {str(e)}")


def csv_a_json_basico(ruta_csv, carpeta_salida):
    df = leer_csv(ruta_csv)
    
    if len(df) == 0:
        raise Exception("El CSV está vacío")
    
    fecha_inicio = df['timestamp'].min()
    fecha_fin = df['timestamp'].max()
    fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
    fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')
    
    registros = []
    for _, row in df.iterrows():
        rpm_val = float(row['rpm']) if pd.notna(row['rpm']) else 0
        temp_val = float(row['temperatura']) if pd.notna(row['temperatura']) else TEMP_ERROR_DS18B20
        accelX_val = float(row['accelX']) if pd.notna(row['accelX']) else 0
        accelY_val = float(row['accelY']) if pd.notna(row['accelY']) else 0
        
        firma = calcular_firma_desde_rpm(rpm_val)
        estado, _ = detectar_estado_registro(rpm_val, temp_val, accelX_val, accelY_val)
        
        registros.append({
            "timestamp": row['timestamp'].isoformat() + "Z" if pd.notna(row['timestamp']) else None,
            "rpm": rpm_val,
            "temperatura": temp_val,
            "accelX": round(accelX_val, 3),
            "accelY": round(accelY_val, 3),
            "firma_hz": firma,
            "estado": estado
        })
    
    json_basico = {
        "equipo_id": "MOTOR_BOMBA_110V_01",
        "fecha_inicio": fecha_inicio.isoformat() + "Z",
        "fecha_fin": fecha_fin.isoformat() + "Z",
        "total_registros": len(registros),
        "registros": registros
    }
    
    os.makedirs(carpeta_salida, exist_ok=True)
    nombre_base = f"datos_basicos_{fecha_inicio_str}_a_{fecha_fin_str}.json"
    ruta_json = os.path.join(carpeta_salida, nombre_base)
    
    with open(ruta_json, 'w', encoding='utf-8') as f:
        json.dump(json_basico, f, indent=2, ensure_ascii=False)
    
    return ruta_json, len(registros)

# APARTADO 2: JSON BÁSICO A JSON DE ANÁLISIS

def leer_json_basico(ruta_json):
    with open(ruta_json, 'r', encoding='utf-8') as f:
        datos = json.load(f)
    
    registros = datos.get('registros', [])
    if not registros:
        raise Exception("El JSON no tiene registros")
    
    df = pd.DataFrame(registros)
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    for col in ['rpm', 'temperatura', 'accelX', 'accelY']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def calcular_rms(accelX, accelY):
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
    except:
        return None


def muestreo_inteligente(df, max_puntos=MAX_PUNTOS_GRAFICA):
    n = len(df)
    
    if n <= max_puntos:
        return df
    
    indices_importantes = set()
    
    indices_importantes.add(0)
    indices_importantes.add(n - 1)
    
    variables_picos = ['rpm', 'temperatura', 'accelX', 'accelY']
    
    for var in variables_picos:
        if var not in df.columns:
            continue
        
        serie = df[var].values.astype(float)
        
        if np.all(np.isnan(serie)):
            continue
        
        media = np.nanmean(serie)
        serie_limpia = np.nan_to_num(serie, nan=media)
        
        distancia = max(int(n * 0.02), 5)
        
        try:
            picos_max, _ = find_peaks(serie_limpia, distance=distancia)
            for idx in picos_max:
                indices_importantes.add(int(idx))
            
            picos_min, _ = find_peaks(-serie_limpia, distance=distancia)
            for idx in picos_min:
                indices_importantes.add(int(idx))
        except Exception:
            pass
    
    if 'estado' in df.columns:
        estados = df['estado'].values
        for i in range(1, len(estados)):
            if estados[i] != estados[i-1]:
                indices_importantes.add(i)
                indices_importantes.add(i - 1)
    
    indices_importantes = sorted(indices_importantes)
    puntos_disponibles = max_puntos - len(indices_importantes)
    
    if puntos_disponibles > 0:
        paso = max(1, n // puntos_disponibles)
        for i in range(0, n, paso):
            indices_importantes.append(i)
    
    indices_importantes = sorted(set(indices_importantes))
    
    if len(indices_importantes) > max_puntos:
        paso = len(indices_importantes) // max_puntos
        indices_importantes = indices_importantes[::paso]
    
    return df.iloc[indices_importantes]


def calcular_analisis_dashboard(df):
    n_registros = len(df)
    
    rpm_promedio = float(df['rpm'].mean())
    rpm_std = float(df['rpm'].std()) if len(df) > 1 else 0.0
    rpm_min = float(df['rpm'].min())
    rpm_max = float(df['rpm'].max())
    
    firmas_registros = [calcular_firma_desde_rpm(r) for r in df['rpm'].values]
    firma_promedio = np.mean(firmas_registros, axis=0).tolist() if firmas_registros else [0, 0, 0]
    firma_max = np.max(firmas_registros, axis=0).tolist() if firmas_registros else [0, 0, 0]
    firma_esperada = calcular_firma_desde_rpm(RPM_BASE_DEFAULT)
    
    temps_validas = df['temperatura'][df['temperatura'] > TEMP_ERROR_DS18B20]
    temp_promedio = float(temps_validas.mean()) if len(temps_validas) > 0 else None
    temp_std = float(temps_validas.std()) if len(temps_validas) > 1 else 0.0
    temp_min = float(temps_validas.min()) if len(temps_validas) > 0 else None
    temp_max = float(temps_validas.max()) if len(temps_validas) > 0 else None
    
    accelX_promedio = float(df['accelX'].mean())
    accelY_promedio = float(df['accelY'].mean())
    accelX_max = float(df['accelX'].max())
    accelY_max = float(df['accelY'].max())
    
    rms = calcular_rms(df['accelX'].values, df['accelY'].values)
    
    tiempos_criticos = {
        "primera_alerta_temperatura_min": None,
        "primera_alerta_rpm_min": None,
        "primera_alerta_vibracion_x_min": None,
        "primera_alerta_vibracion_y_min": None
    }
    
    if n_registros > 0:
        ts_inicio = df['timestamp'].min()
        
        temp_alertas = df[df['temperatura'] >= TEMP_ALERTA_TEMPRANA_MIN]
        if len(temp_alertas) > 0:
            ts = temp_alertas['timestamp'].min()
            tiempos_criticos["primera_alerta_temperatura_min"] = round((ts - ts_inicio).total_seconds() / 60, 1)
        
        rpm_alertas = df[(df['rpm'] > 0) & (df['rpm'] < RPM_ALERTA_TEMPRANA)]
        if len(rpm_alertas) > 0:
            ts = rpm_alertas['timestamp'].min()
            tiempos_criticos["primera_alerta_rpm_min"] = round((ts - ts_inicio).total_seconds() / 60, 1)
        
        accelX_alertas = df[df['accelX'] >= ACCEL_X_ALERTA_TEMPRANA]
        if len(accelX_alertas) > 0:
            ts = accelX_alertas['timestamp'].min()
            tiempos_criticos["primera_alerta_vibracion_x_min"] = round((ts - ts_inicio).total_seconds() / 60, 1)
        
        accelY_alertas = df[df['accelY'] >= ACCEL_Y_ALERTA_TEMPRANA]
        if len(accelY_alertas) > 0:
            ts = accelY_alertas['timestamp'].min()
            tiempos_criticos["primera_alerta_vibracion_y_min"] = round((ts - ts_inicio).total_seconds() / 60, 1)
    
    picos = {}
    if n_registros > 0:
        idx_max = df['rpm'].idxmax()
        picos["rpm_max"] = {
            "valor": round(float(df.loc[idx_max, 'rpm']), 1),
            "timestamp": df.loc[idx_max, 'timestamp'].isoformat() + "Z"
        }
        
        rpm_validos = df[df['rpm'] > 0]
        if len(rpm_validos) > 0:
            idx_min = rpm_validos['rpm'].idxmin()
            picos["rpm_min"] = {
                "valor": round(float(rpm_validos.loc[idx_min, 'rpm']), 1),
                "timestamp": rpm_validos.loc[idx_min, 'timestamp'].isoformat() + "Z"
            }
        
        if len(temps_validas) > 0:
            idx_t = temps_validas.idxmax()
            picos["temperatura_max"] = {
                "valor": round(float(temps_validas.loc[idx_t]), 1),
                "timestamp": df.loc[idx_t, 'timestamp'].isoformat() + "Z"
            }
        
        idx_x = df['accelX'].idxmax()
        picos["accelX_max"] = {
            "valor": round(float(df.loc[idx_x, 'accelX']), 3),
            "timestamp": df.loc[idx_x, 'timestamp'].isoformat() + "Z"
        }
        
        idx_y = df['accelY'].idxmax()
        picos["accelY_max"] = {
            "valor": round(float(df.loc[idx_y, 'accelY']), 3),
            "timestamp": df.loc[idx_y, 'timestamp'].isoformat() + "Z"
        }
    
    estados = {}
    for _, row in df.iterrows():
        rpm_v = float(row['rpm']) if pd.notna(row['rpm']) else 0
        temp_v = float(row['temperatura']) if pd.notna(row['temperatura']) else TEMP_ERROR_DS18B20
        ax_v = float(row['accelX']) if pd.notna(row['accelX']) else 0
        ay_v = float(row['accelY']) if pd.notna(row['accelY']) else 0
        
        estado, _ = detectar_estado_registro(rpm_v, temp_v, ax_v, ay_v)
        estados[estado] = estados.get(estado, 0) + 1
    
    df_m = muestreo_inteligente(df, max_puntos=MAX_PUNTOS_GRAFICA)
    
    datos_grafica = []
    for _, row in df_m.iterrows():
        rpm_v = float(row['rpm']) if pd.notna(row['rpm']) else 0
        temp_v = float(row['temperatura']) if pd.notna(row['temperatura']) else None
        ax_v = float(row['accelX']) if pd.notna(row['accelX']) else 0
        ay_v = float(row['accelY']) if pd.notna(row['accelY']) else 0
        
        if temp_v is not None and temp_v <= TEMP_ERROR_DS18B20:
            temp_v = None
        
        estado_v = str(row['estado']) if 'estado' in row and pd.notna(row['estado']) else None
        
        datos_grafica.append({
            "timestamp": row['timestamp'].isoformat() + "Z",
            "rpm": round(rpm_v, 1),
            "temperatura": round(temp_v, 1) if temp_v is not None else None,
            "accelX": round(ax_v, 3),
            "accelY": round(ay_v, 3),
            "estado": estado_v
        })
    
    resultado = {
        "resumen_general": {
            "total_registros": n_registros,
            "duracion_horas": round((df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600, 2),
            "estado_predominante": max(estados, key=estados.get) if estados else "Desconocido"
        },
        "distribucion_estados": estados,
        "analisis_rpm": {
            "rpm_promedio": round(rpm_promedio, 1),
            "rpm_desviacion_estandar": round(rpm_std, 2),
            "rpm_min": round(rpm_min, 1),
            "rpm_max": round(rpm_max, 1),
            "rpm_linea_base": RPM_BASE_DEFAULT,
            "desviacion_porcentual": round(((rpm_promedio - RPM_BASE_DEFAULT) / RPM_BASE_DEFAULT) * 100, 2)
        },
        "analisis_temperatura": {
            "temperatura_promedio": round(temp_promedio, 1) if temp_promedio else None,
            "temperatura_desviacion_estandar": round(temp_std, 2),
            "temperatura_min": round(temp_min, 1) if temp_min else None,
            "temperatura_max": round(temp_max, 1) if temp_max else None
        },
        "analisis_vibracion": {
            "accelX_promedio": round(accelX_promedio, 3),
            "accelY_promedio": round(accelY_promedio, 3),
            "accelX_max": round(accelX_max, 3),
            "accelY_max": round(accelY_max, 3),
            "rms_vibracion_m_s2": rms
        },
        "analisis_frecuencia": {
            "firma_esperada_hz": firma_esperada,
            "firma_promedio_hz": [round(f, 1) for f in firma_promedio],
            "firma_maxima_hz": [round(f, 1) for f in firma_max]
        },
        "tiempos_criticos": tiempos_criticos,
        "picos": picos,
        "datos_grafica": datos_grafica
    }
    
    if "Alerta_Critica" in estados:
        resultado["estado_operativo"] = "Fuera de Rango"
    elif len([e for e in estados if e.startswith("Alerta")]) > 0:
        resultado["estado_operativo"] = "Alerta"
    else:
        resultado["estado_operativo"] = "En Rango"
    
    return resultado


def json_basico_a_analisis(ruta_json_basico, carpeta_salida):
    df = leer_json_basico(ruta_json_basico)
    
    if len(df) == 0:
        raise Exception("El JSON básico está vacío")
    
    fecha_inicio = df['timestamp'].min()
    fecha_fin = df['timestamp'].max()
    fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
    fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')
    
    analisis = calcular_analisis_dashboard(df)
    
    os.makedirs(carpeta_salida, exist_ok=True)
    
    nombre_analisis = f"analisis_{fecha_inicio_str}_a_{fecha_fin_str}.json"
    ruta_analisis = os.path.join(carpeta_salida, nombre_analisis)
    
    with open(ruta_analisis, 'w', encoding='utf-8') as f:
        json.dump(analisis, f, indent=2, ensure_ascii=False)
    
    carpeta_periodos = os.path.join(carpeta_salida, "analisis_por_periodos")
    generar_analisis_por_periodos(df, carpeta_periodos)
    
    return ruta_analisis, carpeta_periodos, len(df)


def generar_analisis_por_periodos(df, carpeta_salida):
    if len(df) == 0:
        return
    
    df = df.copy()
    df['año_mes'] = df['timestamp'].dt.strftime('%Y-%m')
    df['año_semana'] = df['timestamp'].dt.strftime('%Y-W%U')
    df['fecha_dia'] = df['timestamp'].dt.strftime('%Y-%m-%d')
    
    for año_mes in df['año_mes'].unique():
        df_mes = df[df['año_mes'] == año_mes]
        carpeta = os.path.join(carpeta_salida, año_mes)
        os.makedirs(carpeta, exist_ok=True)
        
        analisis = calcular_analisis_dashboard(df_mes)
        with open(os.path.join(carpeta, f"analisis_mes_{año_mes}.json"), 'w', encoding='utf-8') as f:
            json.dump(analisis, f, indent=2, ensure_ascii=False)
    
    for año_semana in df['año_semana'].unique():
        df_sem = df[df['año_semana'] == año_semana]
        año_mes = df_sem['año_mes'].iloc[0]
        
        carpeta = os.path.join(carpeta_salida, año_mes, f"semana_{año_semana}")
        os.makedirs(carpeta, exist_ok=True)
        
        analisis = calcular_analisis_dashboard(df_sem)
        with open(os.path.join(carpeta, f"analisis_semana_{año_semana}.json"), 'w', encoding='utf-8') as f:
            json.dump(analisis, f, indent=2, ensure_ascii=False)
    
    for fecha_dia in df['fecha_dia'].unique():
        df_dia = df[df['fecha_dia'] == fecha_dia]
        año_mes = df_dia['año_mes'].iloc[0]
        año_semana = df_dia['año_semana'].iloc[0]
        
        carpeta = os.path.join(
            carpeta_salida, año_mes, f"semana_{año_semana}", f"dia_{fecha_dia}"
        )
        os.makedirs(carpeta, exist_ok=True)
        
        analisis = calcular_analisis_dashboard(df_dia)
        with open(os.path.join(carpeta, f"analisis_dia_{fecha_dia}.json"), 'w', encoding='utf-8') as f:
            json.dump(analisis, f, indent=2, ensure_ascii=False)

# APARTADO 3: JSON BÁSICO A JSON SINTÉTICOS

def simular_ruido_sensor(escala=1.0):
    return np.random.normal(0, RUIDO_ADXL345 * escala)


def simular_deriva(valor_ant, valor_obj, factor=0.3):
    return valor_ant + factor * (valor_obj - valor_ant)


def detectar_linea_base_sintetica(df_real):
    df_motor = df_real[df_real['rpm'] > RPM_MINIMO_ENCENDIDO].copy()
    
    if len(df_motor) > 0:
        rpm_base = float(df_motor['rpm'].mean())
        rpm_std = float(df_motor['rpm'].std()) if len(df_motor) > 1 else 20.0
    else:
        rpm_base = RPM_BASE_DEFAULT
        rpm_std = 20.0
    
    df_temp = df_real[df_real['temperatura'] > TEMP_ERROR_DS18B20].copy()
    
    if len(df_temp) > 0:
        temp_min = max(15.0, float(df_temp['temperatura'].min()))
        temp_max = float(df_temp['temperatura'].max())
        temp_std = float(df_temp['temperatura'].std()) if len(df_temp) > 1 else 2.0
        
        temp_apagado_min = min(74.0, temp_max - 2.0)
        temp_apagado_max = min(77.0, temp_max)
    else:
        temp_min = 18.0
        temp_max = 75.0
        temp_std = 2.0
        temp_apagado_min = 74.0
        temp_apagado_max = 77.0
    
    accelX_base = float(df_real['accelX'].mean())
    accelY_base = float(df_real['accelY'].mean())
    
    duracion_ciclo_min = 30.0
    
    if len(df_real) > 1:
        temp_diffs = df_real['temperatura'].diff()
        caidas = df_real[temp_diffs < -20]
        
        if len(caidas) >= 2:
            timestamps = caidas['timestamp'].sort_values()
            diffs = timestamps.diff().dropna()
            
            if len(diffs) > 0:
                duracion_ciclo_min = diffs.dt.total_seconds().mean() / 60
                duracion_ciclo_min = max(20.0, min(60.0, duracion_ciclo_min))
    
    return {
        'rpm_base': rpm_base,
        'rpm_std': rpm_std,
        'temp_min': temp_min,
        'temp_max': temp_max,
        'temp_std': temp_std,
        'temp_apagado_min': temp_apagado_min,
        'temp_apagado_max': temp_apagado_max,
        'accelX_base': accelX_base,
        'accelY_base': accelY_base,
        'duracion_ciclo_min': duracion_ciclo_min
    }


def calcular_temperatura_progreso(progreso, temp_inicial, temp_final):
    lineal = progreso
    exponencial = 1 - np.exp(-3 * progreso)
    factor = 0.5 * lineal + 0.5 * exponencial
    return temp_inicial + (temp_final - temp_inicial) * factor


def generar_ciclo(df_base, timestamp_inicio, duracion_min, intervalo_segundos, linea_base):
    registros = []
    
    temp_inicial = random.uniform(15.0, 25.0)
    temp_final = random.uniform(
        linea_base['temp_apagado_min'],
        linea_base['temp_apagado_max']
    )
    
    rpm_base = linea_base['rpm_base']
    rpm_std = linea_base['rpm_std']
    accelX_base = linea_base['accelX_base']
    accelY_base = linea_base['accelY_base']
    
    duracion_seg = duracion_min * 60
    n_registros = int(duracion_seg / intervalo_segundos)
    
    if n_registros < 1:
        n_registros = 1
    
    temp_actual = temp_inicial
    rpm_actual = rpm_base
    ax_actual = accelX_base
    ay_actual = accelY_base
    
    for i in range(n_registros):
        ts = timestamp_inicio + timedelta(seconds=intervalo_segundos * i)
        progreso = i / max(1, n_registros - 1)
        
        temp_objetivo = calcular_temperatura_progreso(
            progreso, temp_inicial, temp_final
        )
        
        temp_anterior = temp_actual
        temp_actual = simular_deriva(temp_actual, temp_objetivo, 0.3)
        temp_con_ruido = temp_actual + np.random.normal(0, 0.2)
        temp_final_reg = max(temp_anterior, temp_con_ruido)
        temp_actual = temp_final_reg
        
        rpm_objetivo = rpm_base + np.random.normal(0, rpm_std * 0.5)
        
        if progreso > 0.7 and random.random() < 0.15:
            rpm_objetivo = rpm_base - random.uniform(100, 250)
        
        if random.random() < 0.05:
            rpm_objetivo = rpm_base + random.uniform(30, 80)
        
        rpm_actual = simular_deriva(rpm_actual, rpm_objetivo, 0.4)
        rpm_final = int(round(rpm_actual + np.random.normal(0, 5)))
        rpm_final = max(0, rpm_final)
        
        accelX_objetivo = accelX_base + np.random.normal(0, 0.3)
        
        prob_alerta_x = 0.10 + 0.15 * progreso
        
        if random.random() < prob_alerta_x:
            if random.random() < 0.7:
                accelX_objetivo = random.uniform(11.5, 12.5)
            else:
                accelX_objetivo = random.uniform(13.0, 14.5)
        
        ax_actual = simular_deriva(ax_actual, accelX_objetivo, 0.6)
        ax_final = ax_actual + simular_ruido_sensor(1.5)
        ax_final = max(0, ax_final)
        
        accelY_objetivo = accelY_base + np.random.normal(0, 0.15)
        
        if progreso > 0.7:
            accelY_objetivo += random.uniform(0, 0.5)
        
        ay_actual = simular_deriva(ay_actual, accelY_objetivo, 0.5)
        ay_final = ay_actual + simular_ruido_sensor(1.0)
        ay_final = max(0, ay_final)
        
        estado, _ = detectar_estado_registro(
            rpm_final, temp_final_reg, ax_final, ay_final
        )
        firma = calcular_firma_desde_rpm(rpm_final)
        
        registros.append({
            'timestamp': ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            'rpm': float(rpm_final),
            'temperatura': round(float(temp_final_reg), 1),
            'accelX': round(float(ax_final), 3),
            'accelY': round(float(ay_final), 3),
            'firma_hz': firma,
            'estado': estado
        })
    
    ts_final = timestamp_inicio + timedelta(seconds=intervalo_segundos * n_registros)
    
    return registros, ts_final


def generar_registros_sinteticos_con_ciclos(df_real, fecha_inicio, fecha_fin,
                                              intervalo_segundos, linea_base):
    registros = []
    timestamp_actual = fecha_inicio
    num_ciclos = 0
    
    while timestamp_actual < fecha_fin:
        duracion_base = linea_base['duracion_ciclo_min']
        duracion_ciclo = duracion_base * random.uniform(0.8, 1.2)
        
        registros_ciclo, ts_final = generar_ciclo(
            df_real, timestamp_actual, duracion_ciclo,
            intervalo_segundos, linea_base
        )
        
        if ts_final > fecha_fin:
            registros_validos = []
            for r in registros_ciclo:
                ts_r = datetime.strptime(r['timestamp'], "%Y-%m-%dT%H:%M:%SZ")
                if ts_r <= fecha_fin:
                    registros_validos.append(r)
            registros.extend(registros_validos)
            break
        
        registros.extend(registros_ciclo)
        num_ciclos += 1
        
        salto_min = random.uniform(20, 30)
        timestamp_actual = ts_final + timedelta(minutes=salto_min)
    
    return registros, num_ciclos


def json_basico_a_sinteticos(ruta_json_basico, fecha_inicio, fecha_fin,
                              intervalo_segundos, porcentajes, carpeta_salida):
    df_real = leer_json_basico(ruta_json_basico)
    
    linea_base = detectar_linea_base_sintetica(df_real)
    
    registros, num_ciclos = generar_registros_sinteticos_con_ciclos(
        df_real, fecha_inicio, fecha_fin, intervalo_segundos, linea_base
    )
    
    json_sintetico = {
        "equipo_id": "MOTOR_BOMBA_110V_01",
        "fecha_inicio": fecha_inicio.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fecha_fin": fecha_fin.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_registros": len(registros),
        "registros": registros
    }
    
    os.makedirs(carpeta_salida, exist_ok=True)
    nombre = f"sinteticos_{fecha_inicio.strftime('%Y-%m-%d')}_a_{fecha_fin.strftime('%Y-%m-%d')}.json"
    ruta_json = os.path.join(carpeta_salida, nombre)
    
    with open(ruta_json, 'w', encoding='utf-8') as f:
        json.dump(json_sintetico, f, indent=2, ensure_ascii=False)
    
    return ruta_json, len(registros)