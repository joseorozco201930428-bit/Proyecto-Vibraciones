# Proyecto de Monitoreo Operativo y Análisis de Vibraciones con IA
[![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)](https://python.org)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-API-orange?logo=google)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-Repositorio-black?logo=github)](https://github.com)

**Monitoreo de Motor Eléctrico 110V - Detección de Anomalías mediante IA**

## Descripción General del Proyecto

Este proyecto consiste en un **sistema completo de monitoreo operativo** para un motor eléctrico de 110V acoplado a una bomba. El sistema utiliza **tres sensores** para capturar datos en tiempo real y procesarlos mediante un pipeline de datos que incluye:

1. **Captura de datos** (hardware y sensores)
2. **Generación de datos sintéticos** (para simular fallas)
3. **Análisis y detección de anomalías** (Python)
4. **Generación de informes automáticos** (IA - Google Gemini)

El proyecto sigue la metodología **CRISP-DM** y mantiene una **separación estricta de responsabilidades**:

- **Python** realiza todos los cálculos numéricos (determinista)
- **IA (GEM)** actúa exclusivamente como redactor de informes técnicos
- **Prohibido** que la IA realice cálculos matemáticos o invente variables

## Ejecutar Localmente

### Requisitos Previos

- Python 3.12 o superior
- pip (gestor de paquetes de Python)

### Instalación
```bash
# 1. Clonar el repositorio
git clone https://github.com/joseorozco201930428-bit/Proyecto-Vibraciones.git
cd proyecto_vibraciones

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```
### Ejecución de scripts
```bash
# 1. Generar datos sintéticos
python3 /generador_datos.py

# 2. Analizar datos y detectar anomalías (pendiente)
python3 /analizador_datos.py

# 3. Generar informes con IA (fase inicial, solo comunicación)
python3 comunicador_gem.py

# 4. Ejecutar completa
python3 pipeline_completo.py
