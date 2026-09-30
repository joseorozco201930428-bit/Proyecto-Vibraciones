#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL345_U.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <WiFi.h>
#include <HTTPClient.h>

// =====================================================
// CONFIGURACIÓN WIFI
// =====================================================
const char* ssid = "RED_SENSOR_VIBRACIONES";
const char* password = "contra@vibra123";

// URL de Google Apps Script
const char* googleScriptUrl = "https://script.google.com/macros/s/AKfycbww2XoGkx0ISwQA_z6vOIpczv1jV-AIrUDM9RmfW5sml8ZYF7KhQmHDb_zq3joSk6s3/exec";

// =====================================================
// PINES
// =====================================================
#define PIN_HALL 13
#define PIN_DS18B20 2
#define I2C_SDA 15
#define I2C_SCL 14

// =====================================================
// LCD & SENSORES
// =====================================================
LiquidCrystal_I2C lcd(0x27, 20, 4);
Adafruit_ADXL345_Unified accel = Adafruit_ADXL345_Unified(12345);
OneWire oneWire(PIN_DS18B20);
DallasTemperature sensors(&oneWire);

// =====================================================
// VARIABLES RPM (FILTRO Y PROMEDIO)
// =====================================================
volatile unsigned long ultimoPulso = 0;
volatile unsigned long intervaloPulso = 0;

// Filtro anti-rebote: 5000 microsegundos (5 ms)
const unsigned long TIEMPO_REBOTE = 5000;

// Variables para el Promedio Móvil
#define NUM_MUESTRAS 5
float lecturasRPM[NUM_MUESTRAS] = {0};
int indiceRPM = 0;
float totalRPM = 0;
float rpmPromedio = 0;

// =====================================================
// VARIABLES TEMPERATURA Y ACELEROMETRO
// =====================================================
float temperatura = 0;
float ax = 0, ay = 0, az = 0;
float magnitud = 0;
float anguloX = 0, anguloY = 0;

// =====================================================
// CONTROL DE TIEMPO
// =====================================================
unsigned long tiempoRPM = 0;
unsigned long tiempoTemp = 0;
unsigned long tiempoAccel = 0;
unsigned long tiempoLCD = 0;
unsigned long tiempoSerial = 0;
unsigned long tiempoEnvio = 0;  // ← NUEVO: para envío a Google Sheets
int pantalla = 0;

// =====================================================
// UMBRALES DE ALERTA
// =====================================================
const float RPM_BASE = 3550;              // RPM de línea base
const float RPM_UMBRAL_ALTO = 1.25;       // +25% = 4437.5 RPM
const float TEMP_UMBRAL_ALTA = 85.0;      // °C
const float TEMP_ERROR_DS18B20 = -100.0;  // Valor de error del sensor
const float VIB_UMBRAL = 0.5;             // m/s² (vibración elevada)
const int INTERVALO_ENVIO_MS = 3000;      // Enviar cada 3 segundos

// =====================================================
// INTERRUPCION SENSOR HALL (CON FILTRO ANTI-REBOTE)
// =====================================================
void IRAM_ATTR detectarPulso() {
  unsigned long ahora = micros();
  
  if (ahora - ultimoPulso > TIEMPO_REBOTE) {
    if (ultimoPulso > 0) {
      intervaloPulso = ahora - ultimoPulso;
    }
    ultimoPulso = ahora;
  }
}

// =====================================================
// FUNCIÓN PARA DETERMINAR EL ESTADO
// =====================================================
String determinarEstado(float rpm, float temp, float accelX, float accelY) {
  
  bool alerta_rpm = false;
  bool alerta_vib = false;
  bool alerta_temp = false;
  bool sensor_temp_ok = (temp > TEMP_ERROR_DS18B20);
  
  // --- Evaluar RPM ---
  if (rpm == 0) {
    return "Motor_Apagado";
  }
  if (rpm > RPM_BASE * RPM_UMBRAL_ALTO) {
    alerta_rpm = true;
  }
  
  // --- Evaluar vibración ---
  // Restar la gravedad (~1.0 m/s² en reposo)
  float vibX = abs(accelX - 1.0);
  float vibY = abs(accelY - 1.0);
  if (vibX > VIB_UMBRAL || vibY > VIB_UMBRAL) {
    alerta_vib = true;
  }
  
  // --- Evaluar temperatura ---
  if (sensor_temp_ok && temp > TEMP_UMBRAL_ALTA) {
    alerta_temp = true;
  }
  
  // --- Determinar estado final ---
  int num_alertas = alerta_rpm + alerta_vib + alerta_temp;
  
  if (num_alertas >= 2) {
    return "Alerta_Critica";
  } else if (alerta_rpm) {
    return "Alerta_RPM";
  } else if (alerta_vib) {
    return "Alerta_Vibracion";
  } else if (alerta_temp) {
    return "Alerta_Temperatura";
  }
  
  return "Normal";
}

// =====================================================
// FUNCIÓN PARA ENVIAR DATOS A GOOGLE SHEETS
// =====================================================
void enviarDatos(float rpm, float temp, float accelX, float accelY) {
  
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️ WiFi no conectado, no se envían datos");
    return;
  }
  
  // Determinar estado
  String estado = determinarEstado(rpm, temp, accelX, accelY);
  
  // Construir URL con parámetros
  String url = String(googleScriptUrl) + 
               "?rpm=" + String(rpm, 0) +
               "&temp=" + String(temp, 1) +
               "&accelX=" + String(accelX, 3) +
               "&accelY=" + String(accelY, 3) +
               "&estado=" + estado;
  
  Serial.print("📤 Enviando: RPM=");
  Serial.print(rpm, 0);
  Serial.print(" | Temp=");
  Serial.print(temp, 1);
  Serial.print(" | Estado=");
  Serial.println(estado);
  
  HTTPClient http;
  http.begin(url);
  http.setFollowRedirects(HTTPC_FORCE_FOLLOW_REDIRECTS);
  http.setTimeout(5000);
  
  int httpCode = http.GET();
  
  if (httpCode > 0) {
    String respuesta = http.getString();
    if (httpCode == 200) {
      Serial.println("✅ Datos guardados en Google Sheets");
    } else {
      Serial.print("⚠️ HTTP ");
      Serial.print(httpCode);
      Serial.print(": ");
      Serial.println(respuesta);
    }
  } else {
    Serial.print("❌ Error HTTP: ");
    Serial.println(httpCode);
  }
  
  http.end();
}

// =====================================================
// SETUP
// =====================================================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n================================");
  Serial.println(" SISTEMA DE MONITOREO");
  Serial.println(" RPM + TEMPERATURA + VIBRACION");
  Serial.println("================================");

  // --- CONEXIÓN WIFI ---
  Serial.print("📡 Conectando a WiFi");
  WiFi.begin(ssid, password);
  
  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < 30) {
    delay(500);
    Serial.print(".");
    intentos++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi conectado");
    Serial.print("   IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ No se pudo conectar a WiFi");
    Serial.println("   El sistema funcionará sin enviar datos");
  }
  
  // --- INICIAR I2C ---
  Wire.begin(I2C_SDA, I2C_SCL);

  // --- INICIAR LCD ---
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("MONITOREO MOTOR");
  lcd.setCursor(0, 1);
  lcd.print("Iniciando...");
  
  if (WiFi.status() == WL_CONNECTED) {
    lcd.setCursor(0, 2);
    lcd.print("WiFi: OK");
  } else {
    lcd.setCursor(0, 2);
    lcd.print("WiFi: OFF");
  }
  delay(1500);

  // --- SENSOR HALL ---
  pinMode(PIN_HALL, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_HALL), detectarPulso, FALLING);

  // --- SENSOR TEMPERATURA ---
  sensors.begin();

  // --- ACELERÓMETRO ---
  if (!accel.begin()) {
    Serial.println("ERROR: ADXL345 no detectado");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("ERROR ADXL345");
    while (1) { delay(100); }
  }
  
  Serial.println("ADXL345 detectado");
  accel.setRange(ADXL345_RANGE_4_G);

  Serial.println("\nTiempo(ms),RPM,Temp_C,Ax,Ay,Az,Mag,AngX,AngY");
  lcd.clear();
}

// =====================================================
// LOOP
// =====================================================
void loop() {

  // ===================================================
  // CALCULAR RPM Y PROMEDIO (Cada 200ms)
  // ===================================================
  if (millis() - tiempoRPM >= 200) {
    tiempoRPM = millis();

    noInterrupts();
    unsigned long intervalo = intervaloPulso;
    unsigned long ultimo = ultimoPulso;
    interrupts();

    float rpmInstantaneo = 0;

    // Si el motor se detiene (sin pulsos por 2 segundos)
    if (ultimo == 0 || micros() - ultimo > 2000000) {
      rpmInstantaneo = 0;
    } 
    else if (intervalo > 0) {
      rpmInstantaneo = 60000000.0 / intervalo;
    }

    // Calcular Promedio Móvil
    totalRPM = totalRPM - lecturasRPM[indiceRPM];
    lecturasRPM[indiceRPM] = rpmInstantaneo;
    totalRPM = totalRPM + lecturasRPM[indiceRPM];
    indiceRPM = (indiceRPM + 1) % NUM_MUESTRAS;
    
    rpmPromedio = totalRPM / NUM_MUESTRAS;
  }

  // ===================================================
  // TEMPERATURA
  // ===================================================
  if (millis() - tiempoTemp >= 1000) {
    tiempoTemp = millis();
    sensors.requestTemperatures();
    temperatura = sensors.getTempCByIndex(0);
  }

  // ===================================================
  // ACELEROMETRO
  // ===================================================
  if (millis() - tiempoAccel >= 20) {
    tiempoAccel = millis();
    sensors_event_t event;
    accel.getEvent(&event);

    ax = event.acceleration.x;
    ay = event.acceleration.y;
    az = event.acceleration.z;
    magnitud = sqrt(ax * ax + ay * ay + az * az);

    anguloX = atan2(ay, sqrt(ax * ax + az * az)) * 180.0 / PI;
    anguloY = atan2(-ax, sqrt(ay * ay + az * az)) * 180.0 / PI;
  }

  // ===================================================
  // ENVIAR DATOS A GOOGLE SHEETS (Cada 3 segundos)
  // ===================================================
  if (millis() - tiempoEnvio >= INTERVALO_ENVIO_MS) {
    tiempoEnvio = millis();
    
    if (WiFi.status() == WL_CONNECTED) {
      enviarDatos(rpmPromedio, temperatura, ax, ay);
    }
  }

  // ===================================================
  // CAMBIAR PANTALLA LCD
  // ===================================================
  if (millis() - tiempoLCD >= 2000) {
    tiempoLCD = millis();
    pantalla++;
    if (pantalla > 2) pantalla = 0;
    lcd.clear();

    if (pantalla == 0) {
      lcd.setCursor(0, 0); lcd.print("VELOCIDAD");
      lcd.setCursor(0, 1); lcd.print("RPM: ");
      lcd.print(rpmPromedio, 0);
      lcd.setCursor(0, 2); lcd.print("TEMP: ");
      lcd.print(temperatura, 1);
      lcd.print(" C");
      // Indicador WiFi
      lcd.setCursor(0, 3);
      if (WiFi.status() == WL_CONNECTED) {
        lcd.print("WiFi: OK");
      } else {
        lcd.print("WiFi: --");
      }
    }
    else if (pantalla == 1) {
      lcd.setCursor(0, 0); lcd.print("ACELERACION");
      lcd.setCursor(0, 1); lcd.print("X:"); lcd.print(ax, 2);
      lcd.setCursor(10, 1); lcd.print("Y:"); lcd.print(ay, 2);
      lcd.setCursor(0, 2); lcd.print("Z:"); lcd.print(az, 2);
      lcd.setCursor(0, 3); lcd.print("MAG:"); lcd.print(magnitud, 2); lcd.print(" m/s2");
    }
    else if (pantalla == 2) {
      lcd.setCursor(0, 0); lcd.print("ORIENTACION");
      lcd.setCursor(0, 1); lcd.print("ANG X:"); lcd.print(anguloX, 1); lcd.print((char)223);
      lcd.setCursor(0, 2); lcd.print("ANG Y:"); lcd.print(anguloY, 1); lcd.print((char)223);
      lcd.setCursor(0, 3); lcd.print("RPM:"); lcd.print(rpmPromedio, 0);
    }
  }

  // ===================================================
  // ENVIAR DATOS AL MONITOR SERIAL
  // ===================================================
  if (millis() - tiempoSerial >= 100) {
    tiempoSerial = millis();
    Serial.print(millis()); Serial.print(",");
    Serial.print(rpmPromedio, 2); Serial.print(",");
    Serial.print(temperatura, 2); Serial.print(",");
    Serial.print(ax, 4); Serial.print(",");
    Serial.print(ay, 4); Serial.print(",");
    Serial.print(az, 4); Serial.print(",");
    Serial.print(magnitud, 4); Serial.print(",");
    Serial.print(anguloX, 2); Serial.print(",");
    Serial.println(anguloY, 2);
  }
}