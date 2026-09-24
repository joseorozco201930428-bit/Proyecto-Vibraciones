"""
===========================================================
INTERFAZ GRÁFICA - PROCESADOR DE VIBRACIONES v3.2
===========================================================
Layout mejorado de 2 columnas para pantalla completa.
- Columna izquierda: Controles
- Columna derecha: Consola (más grande y visible)
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import os
import threading

from procesador import (
    leer_csv,
    convertir_csv_a_json,
    generar_json_sintetico
)


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ============================================================
# COLORES PERSONALIZADOS
# ============================================================

COLOR_PRIMARIO = "#1f6aa5"      # Azul para convertir
COLOR_PRIMARIO_HOVER = "#144870"
COLOR_EXITO = "#2d7a3e"          # Verde para sintéticos
COLOR_EXITO_HOVER = "#1e5429"
COLOR_FONDO_FRAME = "#2b2b2b"    # Fondo de frames
COLOR_FONDO_SECCION = "#3a3a3a"  # Fondo de secciones internas
COLOR_TEXTO_INFO = "#4a9eff"     # Azul claro para info
COLOR_TEXTO_EXITO = "#4ade80"    # Verde claro para éxito
COLOR_TEXTO_ERROR = "#f87171"    # Rojo claro para errores
COLOR_TEXTO_WARN = "#fbbf24"     # Amarillo para advertencias


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Procesador de Vibraciones - ESP32")
        
        # Pantalla completa
        try:
            self.state('zoomed')
        except:
            try:
                self.attributes('-zoomed', True)
            except:
                ancho = self.winfo_screenwidth()
                alto = self.winfo_screenheight()
                self.geometry(f"{ancho}x{alto}+0+0")
        
        self.resizable(True, True)
        self.minsize(1200, 700)
        
        self.archivo_csv_seleccionado = None
        self.carpeta_salida = None
        
        self.crear_widgets()
        
        # Atajos de teclado
        self.bind('<F11>', self.toggle_fullscreen)
        self.bind('<Escape>', self.salir_fullscreen)
        self.es_fullscreen = False
    
    
    def toggle_fullscreen(self, event=None):
        self.es_fullscreen = not self.es_fullscreen
        self.attributes('-fullscreen', self.es_fullscreen)
    
    
    def salir_fullscreen(self, event=None):
        if self.es_fullscreen:
            self.attributes('-fullscreen', False)
            self.es_fullscreen = False
    
    
    # ============================================================
    # CREAR WIDGETS PRINCIPALES
    # ============================================================
    
    def crear_widgets(self):
        # ============================================
        # GRID PRINCIPAL - 2 COLUMNAS
        # ============================================
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=550)  # Columna controles (ancho fijo)
        self.grid_columnconfigure(1, weight=1)               # Columna consola (expandible)
        
        # ============================================
        # COLUMNA IZQUIERDA - CONTROLES
        # ============================================
        self.frame_izq = ctk.CTkFrame(self, fg_color=COLOR_FONDO_FRAME)
        self.frame_izq.grid(row=0, column=0, sticky="nsew", padx=(15, 8), pady=15)
        
        self.frame_izq.grid_rowconfigure(0, weight=0)  # Título
        self.frame_izq.grid_rowconfigure(1, weight=1)  # Scroll
        self.frame_izq.grid_columnconfigure(0, weight=1)
        
        # Título izquierdo
        self.crear_titulo_izquierdo()
        
        # Frame con scroll para controles
        self.frame_scroll = ctk.CTkScrollableFrame(
            self.frame_izq,
            fg_color="transparent"
        )
        self.frame_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Secciones de control
        self.crear_seccion_archivo()
        self.crear_seccion_carpeta()
        self.crear_seccion_acciones()
        self.crear_seccion_config_sinteticos()
        
        # ============================================
        # COLUMNA DERECHA - CONSOLA
        # ============================================
        self.frame_der = ctk.CTkFrame(self, fg_color=COLOR_FONDO_FRAME)
        self.frame_der.grid(row=0, column=1, sticky="nsew", padx=(8, 15), pady=15)
        
        self.frame_der.grid_rowconfigure(1, weight=1)  # Consola expandible
        self.frame_der.grid_columnconfigure(0, weight=1)
        
        self.crear_consola()
    
    
    # ============================================================
    # TÍTULO IZQUIERDO
    # ============================================================
    
    def crear_titulo_izquierdo(self):
        frame_titulo = ctk.CTkFrame(self.frame_izq, fg_color=COLOR_PRIMARIO, corner_radius=8)
        frame_titulo.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            frame_titulo,
            text="⚙️  PANEL DE CONTROL",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="white"
        ).pack(pady=15, padx=20)
    
    
    # ============================================================
    # SECCIONES DE LA COLUMNA IZQUIERDA
    # ============================================================
    
    def crear_seccion_archivo(self):
        """Sección 1: Seleccionar archivo CSV."""
        frame = ctk.CTkFrame(self.frame_scroll, fg_color=COLOR_FONDO_SECCION, corner_radius=10)
        frame.pack(fill="x", pady=(5, 10), padx=5)
        
        # Título sección
        ctk.CTkLabel(
            frame,
            text="📁  Archivo CSV",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="white"
        ).pack(anchor="w", padx=15, pady=(12, 8))
        
        # Botón
        ctk.CTkButton(
            frame,
            text="📂  Seleccionar archivo",
            command=self.seleccionar_archivo,
            width=250,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_PRIMARIO,
            hover_color=COLOR_PRIMARIO_HOVER
        ).pack(padx=15, pady=(0, 8))
        
        # Label de archivo seleccionado
        self.lbl_archivo = ctk.CTkLabel(
            frame,
            text="⚠️ Ningún archivo seleccionado",
            text_color="gray",
            font=ctk.CTkFont(size=11),
            wraplength=450,
            justify="left",
            anchor="w"
        )
        self.lbl_archivo.pack(fill="x", padx=15, pady=(0, 12))
    
    
    def crear_seccion_carpeta(self):
        """Sección 2: Carpeta de salida."""
        frame = ctk.CTkFrame(self.frame_scroll, fg_color=COLOR_FONDO_SECCION, corner_radius=10)
        frame.pack(fill="x", pady=(5, 10), padx=5)
        
        ctk.CTkLabel(
            frame,
            text="📁  Carpeta de salida",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="white"
        ).pack(anchor="w", padx=15, pady=(12, 8))
        
        ctk.CTkButton(
            frame,
            text="📂  Seleccionar carpeta",
            command=self.seleccionar_carpeta,
            width=250,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_PRIMARIO,
            hover_color=COLOR_PRIMARIO_HOVER
        ).pack(padx=15, pady=(0, 8))
        
        self.lbl_carpeta = ctk.CTkLabel(
            frame,
            text="⚠️ Ninguna carpeta seleccionada",
            text_color="gray",
            font=ctk.CTkFont(size=11),
            wraplength=450,
            justify="left",
            anchor="w"
        )
        self.lbl_carpeta.pack(fill="x", padx=15, pady=(0, 12))
    
    
    def crear_seccion_acciones(self):
        """Sección 3: Botones de acción principales."""
        frame = ctk.CTkFrame(self.frame_scroll, fg_color=COLOR_FONDO_SECCION, corner_radius=10)
        frame.pack(fill="x", pady=(5, 10), padx=5)
        
        ctk.CTkLabel(
            frame,
            text="⚙️  Operación",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="white"
        ).pack(anchor="w", padx=15, pady=(12, 8))
        
        # Botón: Convertir
        self.btn_convertir = ctk.CTkButton(
            frame,
            text="Convertir CSV → JSON",
            command=self.convertir_a_json,
            width=350,
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLOR_PRIMARIO,
            hover_color=COLOR_PRIMARIO_HOVER,
            corner_radius=8
        )
        self.btn_convertir.pack(padx=15, pady=(0, 8))
        
        # Botón: Sintéticos
        self.btn_sinteticos = ctk.CTkButton(
            frame,
            text="Generar Datos Sintéticos",
            command=self.generar_sinteticos,
            width=350,
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLOR_EXITO,
            hover_color=COLOR_EXITO_HOVER,
            corner_radius=8
        )
        self.btn_sinteticos.pack(padx=15, pady=(0, 12))
    
    
    def crear_seccion_config_sinteticos(self):
        """Sección 4: Configuración de datos sintéticos."""
        frame = ctk.CTkFrame(self.frame_scroll, fg_color=COLOR_FONDO_SECCION, corner_radius=10)
        frame.pack(fill="x", pady=(5, 10), padx=5)
        
        ctk.CTkLabel(
            frame,
            text="Configuración de sintéticos",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="white"
        ).pack(anchor="w", padx=15, pady=(12, 8))
        
        # --- Fecha inicio ---
        self.crear_campo_fecha(frame, "📅  Fecha de inicio:", "date_inicio")
        
        # --- Hora inicio ---
        self.crear_campo_texto(frame, "🕐  Hora inicio:", "entry_hora_ini", "08:00:00")
        
        # --- Hora fin ---
        self.crear_campo_texto(frame, "🕐  Hora fin:", "entry_hora_fin", "18:00:00")
        
        # --- Días ---
        self.crear_campo_texto(frame, "📆  Días consecutivos:", "entry_dias", "7")
        
        # --- Intervalo ---
        self.crear_campo_texto(frame, "⏱️  Intervalo (seg):", "entry_intervalo", "3")
        
        # --- Preview ---
        frame_preview = ctk.CTkFrame(frame, fg_color="#1a1a1a", corner_radius=6)
        frame_preview.pack(fill="x", padx=15, pady=(5, 12))
        
        self.lbl_preview = ctk.CTkLabel(
            frame_preview,
            text="Vista previa: calculando...",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXTO_INFO,
            wraplength=400,
            justify="left",
            anchor="w"
        )
        self.lbl_preview.pack(fill="x", padx=12, pady=10)
        
        # Actualizar preview
        self.entry_dias.bind('<KeyRelease>', self.actualizar_preview)
        self.entry_intervalo.bind('<KeyRelease>', self.actualizar_preview)
        self.entry_hora_ini.bind('<KeyRelease>', self.actualizar_preview)
        self.entry_hora_fin.bind('<KeyRelease>', self.actualizar_preview)
        
        self.actualizar_preview()
    
    
    def crear_campo_fecha(self, parent, label_text, attr_name):
        """Crea un campo de fecha con calendario."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=4)
        
        ctk.CTkLabel(
            frame,
            text=label_text,
            font=ctk.CTkFont(size=12),
            width=180,
            anchor="w"
        ).pack(side="left")
        
        widget = DateEntry(
            frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd',
            font=('Arial', 11)
        )
        widget.pack(side="left", padx=(10, 5))
        widget.set_date(datetime.now())
        
        setattr(self, attr_name, widget)
    
    
    def crear_campo_texto(self, parent, label_text, attr_name, default_value):
        """Crea un campo de texto simple."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=4)
        
        ctk.CTkLabel(
            frame,
            text=label_text,
            font=ctk.CTkFont(size=12),
            width=180,
            anchor="w"
        ).pack(side="left")
        
        widget = ctk.CTkEntry(
            frame,
            width=120,
            height=30,
            font=ctk.CTkFont(size=12)
        )
        widget.insert(0, default_value)
        widget.pack(side="left", padx=(10, 5))
        
        setattr(self, attr_name, widget)
    
    
    def actualizar_preview(self, event=None):
        """Calcula y muestra cuántos registros se van a generar."""
        try:
            dias = int(self.entry_dias.get())
            intervalo = int(self.entry_intervalo.get())
            
            hora_ini = datetime.strptime(self.entry_hora_ini.get(), "%H:%M:%S")
            hora_fin = datetime.strptime(self.entry_hora_fin.get(), "%H:%M:%S")
            
            segundos_por_dia = (hora_fin - hora_ini).total_seconds()
            if segundos_por_dia <= 0:
                self.lbl_preview.configure(
                    text="⚠️  La hora de fin debe ser mayor que la hora de inicio",
                    text_color=COLOR_TEXTO_WARN
                )
                return
            
            registros_por_dia = int(segundos_por_dia / intervalo)
            total_registros = registros_por_dia * dias
            
            self.lbl_preview.configure(
                text=f"📊  Vista previa:\n"
                     f"     • {registros_por_dia:,} registros/día\n"
                     f"     • {total_registros:,} registros totales",
                text_color=COLOR_TEXTO_INFO
            )
        except Exception as e:
            self.lbl_preview.configure(
                text=f"⚠️  Verifica los valores",
                text_color=COLOR_TEXTO_WARN
            )
    
    
    # ============================================================
    # CONSOLA (COLUMNA DERECHA)
    # ============================================================
    
    def crear_consola(self):
        """Crea la consola de registro y progreso."""
        
        # Título de la consola
        frame_titulo = ctk.CTkFrame(self.frame_der, fg_color=COLOR_EXITO, corner_radius=8)
        frame_titulo.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            frame_titulo,
            text="CONSOLA",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="white"
        ).pack(pady=15, padx=20)
        
        # Frame de consola + estado
        frame_consola = ctk.CTkFrame(self.frame_der, fg_color="transparent")
        frame_consola.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        frame_consola.grid_rowconfigure(0, weight=1)
        frame_consola.grid_columnconfigure(0, weight=1)
        
        # Área de texto (log)
        self.text_log = ctk.CTkTextbox(
            frame_consola,
            font=ctk.CTkFont(size=12, family="Consolas"),
            wrap="word",
            fg_color="#1a1a1a",
            text_color="#e0e0e0",
            corner_radius=8
        )
        self.text_log.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        
        # Frame de progreso + estado
        frame_progreso = ctk.CTkFrame(frame_consola, fg_color=COLOR_FONDO_SECCION, corner_radius=8)
        frame_progreso.grid(row=1, column=0, sticky="ew")
        
        # Barra de progreso
        self.progress = ctk.CTkProgressBar(
            frame_progreso,
            height=15,
            corner_radius=8,
            progress_color=COLOR_PRIMARIO
        )
        self.progress.pack(fill="x", padx=15, pady=(12, 8))
        self.progress.set(0)
        
        # Estado actual
        self.lbl_estado = ctk.CTkLabel(
            frame_progreso,
            text="⏸️  En espera...",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="gray",
            anchor="w"
        )
        self.lbl_estado.pack(fill="x", padx=15, pady=(0, 12))
    
    
    # ============================================================
    # MÉTODOS DE LA INTERFAZ
    # ============================================================
    
    def log(self, mensaje):
        self.text_log.insert("end", mensaje + "\n")
        self.text_log.see("end")
        self.update()
    
    
    def set_estado(self, texto, color="gray"):
        self.lbl_estado.configure(text=texto, text_color=color)
        self.update()
    
    
    def seleccionar_archivo(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar CSV",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")]
        )
        if ruta:
            self.archivo_csv_seleccionado = ruta
            self.lbl_archivo.configure(
                text=f"✅ {os.path.basename(ruta)}",
                text_color=COLOR_TEXTO_EXITO
            )
            self.log(f"📂 Archivo seleccionado: {os.path.basename(ruta)}")
            self.set_estado("✅ Archivo listo", COLOR_TEXTO_EXITO)
    
    
    def seleccionar_carpeta(self):
        ruta = filedialog.askdirectory(title="Carpeta de salida")
        if ruta:
            self.carpeta_salida = ruta
            self.lbl_carpeta.configure(
                text=f"✅ {ruta}",
                text_color=COLOR_TEXTO_EXITO
            )
            self.log(f"📁 Carpeta de salida: {ruta}")
    
    
    def validar(self):
        if not self.archivo_csv_seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un archivo CSV")
            return False
        if not self.carpeta_salida:
            messagebox.showwarning("Advertencia", "Selecciona una carpeta de salida")
            return False
        return True
    
    
    def bloquear_botones(self, bloquear=True):
        estado = "disabled" if bloquear else "normal"
        self.btn_convertir.configure(state=estado)
        self.btn_sinteticos.configure(state=estado)
        self.update()
    
    
    # ============================================================
    # CONVERSIÓN CSV → JSON
    # ============================================================
    
    def convertir_a_json(self):
        if not self.validar():
            return
        threading.Thread(target=self._convertir_thread, daemon=True).start()
    
    
    def _convertir_thread(self):
        try:
            self.bloquear_botones(True)
            self.set_estado("⏳ Procesando conversión...", COLOR_TEXTO_WARN)
            
            self.log("\n" + "="*70)
            self.log("🚀 INICIANDO CONVERSIÓN CSV → JSON")
            self.log("="*70)
            
            self.progress.set(0.3)
            self.log("📖 Leyendo CSV...")
            
            ruta_orig, ruta_anal, total = convertir_csv_a_json(
                self.archivo_csv_seleccionado,
                self.carpeta_salida
            )
            
            self.progress.set(1.0)
            self.log(f"\n✅ Conversión completada exitosamente")
            self.log(f"   📊 Total de registros: {total:,}")
            self.log(f"   📄 JSON original: {os.path.basename(ruta_orig)}")
            self.log(f"   📊 JSON análisis: {os.path.basename(ruta_anal)}")
            
            self.set_estado("✅ Conversión completada", COLOR_TEXTO_EXITO)
            
            messagebox.showinfo(
                "✅ Éxito",
                f"Conversión completada\n\n"
                f"Registros procesados: {total:,}\n\n"
                f"Archivos generados:\n"
                f"• {os.path.basename(ruta_orig)}\n"
                f"• {os.path.basename(ruta_anal)}"
            )
            self.progress.set(0)
            
        except Exception as e:
            self.log(f"\n❌ ERROR: {str(e)}")
            self.set_estado("❌ Error en conversión", COLOR_TEXTO_ERROR)
            messagebox.showerror("Error", str(e))
            self.progress.set(0)
        finally:
            self.bloquear_botones(False)
    
    
    # ============================================================
    # GENERACIÓN DE DATOS SINTÉTICOS
    # ============================================================
    
    def generar_sinteticos(self):
        if not self.validar():
            return
        
        try:
            fecha_base = self.date_inicio.get_date()
            hora_ini = datetime.strptime(self.entry_hora_ini.get(), "%H:%M:%S").time()
            hora_fin = datetime.strptime(self.entry_hora_fin.get(), "%H:%M:%S").time()
            dias = int(self.entry_dias.get())
            intervalo = int(self.entry_intervalo.get())
            
            if dias <= 0:
                raise ValueError("Los días deben ser mayor a 0")
            if intervalo <= 0:
                raise ValueError("El intervalo debe ser mayor a 0")
            
            fecha_inicio = datetime.combine(fecha_base, hora_ini)
            fecha_fin = datetime.combine(fecha_base, hora_fin)
            
            if dias > 1:
                fecha_fin = fecha_fin + timedelta(days=dias - 1)
            
            if fecha_fin <= fecha_inicio:
                raise ValueError("La fecha de fin debe ser posterior a la de inicio")
            
        except Exception as e:
            messagebox.showwarning("Advertencia", f"Datos inválidos:\n{str(e)}")
            return
        
        threading.Thread(
            target=self._sinteticos_thread,
            args=(fecha_inicio, fecha_fin, intervalo),
            daemon=True
        ).start()
    
    
    def _sinteticos_thread(self, fecha_inicio, fecha_fin, intervalo):
        try:
            self.bloquear_botones(True)
            self.set_estado("⏳ Generando sintéticos...", COLOR_TEXTO_WARN)
            
            self.log("\n" + "="*70)
            self.log("🧬 INICIANDO GENERACIÓN DE DATOS SINTÉTICOS")
            self.log("="*70)
            self.log(f"📅 Fecha inicio:  {fecha_inicio.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log(f"📅 Fecha fin:     {fecha_fin.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log(f"⏱️  Intervalo:     {intervalo} segundos")
            
            self.progress.set(0.2)
            self.log("\n📖 Leyendo datos reales para calibración...")
            df_real = leer_csv(self.archivo_csv_seleccionado)
            self.log(f"   ✅ {len(df_real):,} registros reales cargados")
            
            self.progress.set(0.4)
            self.log("\n🧬 Generando datos sintéticos...")
            self.log(f"   Mezclando escenarios realistas...")
            
            ruta_json, total = generar_json_sintetico(
                df_real,
                fecha_inicio,
                fecha_fin,
                intervalo,
                self.carpeta_salida
            )
            
            self.progress.set(1.0)
            self.log(f"\n✅ Generación completada exitosamente")
            self.log(f"   📊 Total registros: {total:,}")
            self.log(f"   📄 Archivo: {os.path.basename(ruta_json)}")
            
            self.set_estado("✅ Sintéticos generados", COLOR_TEXTO_EXITO)
            
            messagebox.showinfo(
                "✅ Éxito",
                f"Datos sintéticos generados\n\n"
                f"Total registros: {total:,}\n\n"
                f"Archivo:\n{os.path.basename(ruta_json)}"
            )
            self.progress.set(0)
            
        except Exception as e:
            self.log(f"\n❌ ERROR: {str(e)}")
            self.set_estado("❌ Error en generación", COLOR_TEXTO_ERROR)
            messagebox.showerror("Error", str(e))
            self.progress.set(0)
        finally:
            self.bloquear_botones(False)


if __name__ == "__main__":
    app = App()
    app.mainloop()