# Proyecto de Monitoreo Operativo y Análisis de Vibraciones con IA

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

Instalación y Configuración
Sigue estos pasos para levantar el entorno de desarrollo desde cero.

1. Clonar el repositorio
bash
git clone <https://github.com/joseorozco201930428-bit/Proyecto-Vibraciones.git>
cd proyecto_vibraciones
2. Crear y activar entorno virtual
Nota para usuarios de Linux (Ubuntu/Debian):
bash
sudo apt install python3-full
Crear entorno virtual:

bash
python3 -m venv env
Activar entorno:

Sistema	Comando
Linux/macOS	source env/bin/activate
Windows (Git Bash)	source env/Scripts/activate
Windows (CMD)	env\Scripts\activate

Crea el archivo .env en la raíz del proyecto:


Ejecución del Proyecto
Ejecutar el Generador de Datos (Grupo Datos)
bash
python3 generador_datos.py
Ejecutar el Analizador de Datos (Grupo Análisis)
bash
python3 analizador_datos.py
Ejecutar el Comunicador con IA (Grupo IA)
bash
python3 comunicador_gem.py
Ejecutar el Pipeline Completo
bash
python3 pipeline_completo.py
