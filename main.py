import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import os
import threading

from procesador import (
    csv_a_json_basico,
    json_basico_a_analisis,
    json_basico_a_sinteticos
)


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


COLOR_PRIMARIO = "#1f6aa5"
COLOR_PRIMARIO_HOVER = "#144870"
COLOR_EXITO = "#2d7a3e"
COLOR_EXITO_HOVER = "#1e5429"
COLOR_ANALISIS = "#7c3aed"
COLOR_ANALISIS_HOVER = "#5b21b6"
COLOR_FONDO = "#2b2b2b"
COLOR_SECCION = "#3a3a3a"
COLOR_INFO = "#4a9eff"
COLOR_OK = "#4ade80"
COLOR_ERROR = "#f87171"
COLOR_WARN = "#fbbf24"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Procesador de Vibraciones - ESP32")
        
        try:
            self.state('zoomed')
        except:
            try:
                self.attributes('-zoomed', True)
            except:
                self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        
        self.resizable(True, True)
        self.minsize(1100, 700)
        
        self.csv_seleccionado = None
        self.json_basico_analisis = None
        self.json_basico_sinteticos = None
        self.carpeta_salida_1 = None
        self.carpeta_salida_2 = None
        self.carpeta_salida_3 = None
        
        self.crear_widgets()
        self.bind('<F11>', lambda e: self.attributes('-fullscreen',
                  not self.attributes('-fullscreen')))
        self.bind('<Escape>', lambda e: self.attributes('-fullscreen', False))
    
    
    def crear_widgets(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=7)
        self.grid_columnconfigure(1, weight=3)
        
        self.frame_izq = ctk.CTkFrame(self, fg_color=COLOR_FONDO)
        self.frame_izq.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.frame_izq.grid_rowconfigure(1, weight=1)
        self.frame_izq.grid_columnconfigure(0, weight=1)
        
        t = ctk.CTkFrame(self.frame_izq, fg_color=COLOR_PRIMARIO, corner_radius=8)
        t.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        ctk.CTkLabel(t, text="PANEL DE CONTROL",
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="white").pack(pady=12)
        
        self.scroll = ctk.CTkScrollableFrame(self.frame_izq, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        
        self.crear_apartado_1()
        self.crear_apartado_2()
        self.crear_apartado_3()
        
        self.frame_der = ctk.CTkFrame(self, fg_color=COLOR_FONDO)
        self.frame_der.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.frame_der.grid_rowconfigure(1, weight=1)
        self.frame_der.grid_columnconfigure(0, weight=1)
        
        self.crear_consola()
    
    
    def crear_apartado_1(self):
        frame = ctk.CTkFrame(self.scroll, fg_color=COLOR_SECCION, corner_radius=10)
        frame.pack(fill="x", pady=6, padx=4)
        
        head = ctk.CTkFrame(frame, fg_color=COLOR_PRIMARIO, corner_radius=8)
        head.pack(fill="x", padx=8, pady=(8, 6))
        ctk.CTkLabel(head, text="1. GENERADOR DE JSON BÁSICO",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="white").pack(pady=8, padx=12, anchor="w")
        
        f1 = ctk.CTkFrame(frame, fg_color="transparent")
        f1.pack(fill="x", padx=12, pady=3)
        ctk.CTkButton(f1, text="Seleccionar CSV",
                     command=self.sel_csv,
                     width=200, height=34,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     fg_color=COLOR_PRIMARIO, hover_color=COLOR_PRIMARIO_HOVER
                     ).pack(side="left")
        self.lbl_csv = ctk.CTkLabel(f1, text="Sin archivo",
                                    text_color="gray", font=ctk.CTkFont(size=10),
                                    anchor="w", wraplength=350)
        self.lbl_csv.pack(side="left", padx=8, fill="x", expand=True)
        
        f2 = ctk.CTkFrame(frame, fg_color="transparent")
        f2.pack(fill="x", padx=12, pady=3)
        ctk.CTkButton(f2, text="Carpeta salida",
                     command=lambda: self.sel_carpeta(1),
                     width=200, height=34,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     fg_color=COLOR_PRIMARIO, hover_color=COLOR_PRIMARIO_HOVER
                     ).pack(side="left")
        self.lbl_carpeta_1 = ctk.CTkLabel(f2, text="Sin carpeta",
                                          text_color="gray", font=ctk.CTkFont(size=10),
                                          anchor="w", wraplength=350)
        self.lbl_carpeta_1.pack(side="left", padx=8, fill="x", expand=True)
        
        self.btn_1 = ctk.CTkButton(frame, text="Generar JSON Básico",
                                   command=self.accion_1,
                                   width=380, height=40,
                                   font=ctk.CTkFont(size=13, weight="bold"),
                                   fg_color=COLOR_PRIMARIO,
                                   hover_color=COLOR_PRIMARIO_HOVER)
        self.btn_1.pack(padx=12, pady=(6, 12))
    
    
    def crear_apartado_2(self):
        frame = ctk.CTkFrame(self.scroll, fg_color=COLOR_SECCION, corner_radius=10)
        frame.pack(fill="x", pady=6, padx=4)
        
        head = ctk.CTkFrame(frame, fg_color=COLOR_ANALISIS, corner_radius=8)
        head.pack(fill="x", padx=8, pady=(8, 6))
        ctk.CTkLabel(head, text="2. GENERADOR DE JSON DE ANÁLISIS",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="white").pack(pady=8, padx=12, anchor="w")
        
        f1 = ctk.CTkFrame(frame, fg_color="transparent")
        f1.pack(fill="x", padx=12, pady=3)
        ctk.CTkButton(f1, text="Seleccionar JSON básico",
                     command=self.sel_json_analisis,
                     width=200, height=34,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     fg_color=COLOR_ANALISIS, hover_color=COLOR_ANALISIS_HOVER
                     ).pack(side="left")
        self.lbl_json_analisis = ctk.CTkLabel(f1, text="Sin archivo",
                                              text_color="gray", font=ctk.CTkFont(size=10),
                                              anchor="w", wraplength=350)
        self.lbl_json_analisis.pack(side="left", padx=8, fill="x", expand=True)
        
        f2 = ctk.CTkFrame(frame, fg_color="transparent")
        f2.pack(fill="x", padx=12, pady=3)
        ctk.CTkButton(f2, text="Carpeta salida",
                     command=lambda: self.sel_carpeta(2),
                     width=200, height=34,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     fg_color=COLOR_ANALISIS, hover_color=COLOR_ANALISIS_HOVER
                     ).pack(side="left")
        self.lbl_carpeta_2 = ctk.CTkLabel(f2, text="Sin carpeta",
                                          text_color="gray", font=ctk.CTkFont(size=10),
                                          anchor="w", wraplength=350)
        self.lbl_carpeta_2.pack(side="left", padx=8, fill="x", expand=True)
        
        self.btn_2 = ctk.CTkButton(frame, text="Generar Análisis",
                                   command=self.accion_2,
                                   width=380, height=40,
                                   font=ctk.CTkFont(size=13, weight="bold"),
                                   fg_color=COLOR_ANALISIS,
                                   hover_color=COLOR_ANALISIS_HOVER)
        self.btn_2.pack(padx=12, pady=(6, 12))
    
    
    def crear_apartado_3(self):
        frame = ctk.CTkFrame(self.scroll, fg_color=COLOR_SECCION, corner_radius=10)
        frame.pack(fill="x", pady=6, padx=4)
        
        head = ctk.CTkFrame(frame, fg_color=COLOR_EXITO, corner_radius=8)
        head.pack(fill="x", padx=8, pady=(8, 6))
        ctk.CTkLabel(head, text="3. GENERADOR DE SINTÉTICOS",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="white").pack(pady=8, padx=12, anchor="w")
        
        f1 = ctk.CTkFrame(frame, fg_color="transparent")
        f1.pack(fill="x", padx=12, pady=3)
        ctk.CTkButton(f1, text="Seleccionar JSON básico",
                     command=self.sel_json_sinteticos,
                     width=200, height=34,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     fg_color=COLOR_EXITO, hover_color=COLOR_EXITO_HOVER
                     ).pack(side="left")
        self.lbl_json_sint = ctk.CTkLabel(f1, text="Sin archivo",
                                          text_color="gray", font=ctk.CTkFont(size=10),
                                          anchor="w", wraplength=350)
        self.lbl_json_sint.pack(side="left", padx=8, fill="x", expand=True)
        
        f2 = ctk.CTkFrame(frame, fg_color="transparent")
        f2.pack(fill="x", padx=12, pady=3)
        ctk.CTkButton(f2, text="Carpeta salida",
                     command=lambda: self.sel_carpeta(3),
                     width=200, height=34,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     fg_color=COLOR_EXITO, hover_color=COLOR_EXITO_HOVER
                     ).pack(side="left")
        self.lbl_carpeta_3 = ctk.CTkLabel(f2, text="Sin carpeta",
                                          text_color="gray", font=ctk.CTkFont(size=10),
                                          anchor="w", wraplength=350)
        self.lbl_carpeta_3.pack(side="left", padx=8, fill="x", expand=True)
        
        self.crear_campo_fecha(frame, "Fecha inicio:", "date_inicio")
        self.crear_campo_texto(frame, "Hora inicio:", "entry_hora_ini", "08:00:00")
        self.crear_campo_texto(frame, "Hora fin:", "entry_hora_fin", "18:00:00")
        self.crear_campo_texto(frame, "Días:", "entry_dias", "7")
        self.crear_campo_texto(frame, "Intervalo (s):", "entry_intervalo", "3")
        
        self.btn_3 = ctk.CTkButton(frame, text="Generar Sintéticos",
                                   command=self.accion_3,
                                   width=380, height=40,
                                   font=ctk.CTkFont(size=13, weight="bold"),
                                   fg_color=COLOR_EXITO,
                                   hover_color=COLOR_EXITO_HOVER)
        self.btn_3.pack(padx=12, pady=(6, 12))
    
    
    def crear_campo_fecha(self, parent, label, attr):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10),
                    width=120, anchor="w").pack(side="left")
        w = DateEntry(f, width=11, background='darkblue', foreground='white',
                     borderwidth=2, date_pattern='yyyy-mm-dd', font=('Arial', 10))
        w.pack(side="left", padx=4)
        w.set_date(datetime.now())
        setattr(self, attr, w)
    
    
    def crear_campo_texto(self, parent, label, attr, default):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10),
                    width=120, anchor="w").pack(side="left")
        w = ctk.CTkEntry(f, width=90, height=26, font=ctk.CTkFont(size=10))
        w.insert(0, default)
        w.pack(side="left", padx=4)
        setattr(self, attr, w)
    
    
    def crear_consola(self):
        head = ctk.CTkFrame(self.frame_der, fg_color=COLOR_EXITO, corner_radius=8)
        head.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        ctk.CTkLabel(head, text="CONSOLA",
                    font=ctk.CTkFont(size=15, weight="bold"),
                    text_color="white").pack(pady=10)
        
        box = ctk.CTkFrame(self.frame_der, fg_color="transparent")
        box.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        box.grid_rowconfigure(0, weight=1)
        box.grid_columnconfigure(0, weight=1)
        
        self.log_box = ctk.CTkTextbox(box, font=ctk.CTkFont(size=10, family="Consolas"),
                                       wrap="word", fg_color="#1a1a1a",
                                       text_color="#e0e0e0", corner_radius=8)
        self.log_box.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        
        prog = ctk.CTkFrame(box, fg_color=COLOR_SECCION, corner_radius=8)
        prog.grid(row=1, column=0, sticky="ew")
        
        self.progress = ctk.CTkProgressBar(prog, height=12, corner_radius=6,
                                           progress_color=COLOR_PRIMARIO)
        self.progress.pack(fill="x", padx=10, pady=(8, 4))
        self.progress.set(0)
        
        self.lbl_estado = ctk.CTkLabel(prog, text="En espera...",
                                       font=ctk.CTkFont(size=10, weight="bold"),
                                       text_color="gray", anchor="w")
        self.lbl_estado.pack(fill="x", padx=10, pady=(0, 8))
    
    
    def log(self, msg):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.update()
    
    
    def estado(self, msg, color="gray"):
        self.lbl_estado.configure(text=msg, text_color=color)
        self.update()
    
    
    def sel_csv(self):
        r = filedialog.askopenfilename(title="Seleccionar CSV",
                                       filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
        if r:
            self.csv_seleccionado = r
            self.lbl_csv.configure(text=f"{os.path.basename(r)}", text_color=COLOR_OK)
            self.log(f"CSV: {os.path.basename(r)}")
    
    
    def sel_json_analisis(self):
        r = filedialog.askopenfilename(title="Seleccionar JSON básico",
                                       filetypes=[("JSON", "*.json"), ("Todos", "*.*")])
        if r:
            self.json_basico_analisis = r
            self.lbl_json_analisis.configure(text=f"{os.path.basename(r)}", text_color=COLOR_OK)
            self.log(f"JSON análisis: {os.path.basename(r)}")
    
    
    def sel_json_sinteticos(self):
        r = filedialog.askopenfilename(title="Seleccionar JSON básico",
                                       filetypes=[("JSON", "*.json"), ("Todos", "*.*")])
        if r:
            self.json_basico_sinteticos = r
            self.lbl_json_sint.configure(text=f"{os.path.basename(r)}", text_color=COLOR_OK)
            self.log(f"JSON sintéticos: {os.path.basename(r)}")
    
    
    def sel_carpeta(self, n):
        r = filedialog.askdirectory(title="Carpeta de salida")
        if r:
            if n == 1:
                self.carpeta_salida_1 = r
                self.lbl_carpeta_1.configure(text=f"{r}", text_color=COLOR_OK)
            elif n == 2:
                self.carpeta_salida_2 = r
                self.lbl_carpeta_2.configure(text=f"{r}", text_color=COLOR_OK)
            elif n == 3:
                self.carpeta_salida_3 = r
                self.lbl_carpeta_3.configure(text=f"{r}", text_color=COLOR_OK)
            self.log(f"Salida: {r}")
    
    
    def bloquear(self, b=True):
        e = "disabled" if b else "normal"
        self.btn_1.configure(state=e)
        self.btn_2.configure(state=e)
        self.btn_3.configure(state=e)
        self.update()
    
    
    def accion_1(self):
        if not self.csv_seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un CSV")
            return
        if not self.carpeta_salida_1:
            messagebox.showwarning("Advertencia", "Selecciona carpeta de salida")
            return
        threading.Thread(target=self._run_1, daemon=True).start()
    
    
    def _run_1(self):
        try:
            self.bloquear(True)
            self.estado("Procesando CSV...", COLOR_WARN)
            self.log("\n" + "="*50)
            self.log("CSV A JSON BÁSICO")
            self.log("="*50)
            
            self.progress.set(0.3)
            ruta, total = csv_a_json_basico(self.csv_seleccionado, self.carpeta_salida_1)
            
            self.progress.set(1.0)
            self.log(f"\nCompletado")
            self.log(f"   Registros: {total:,}")
            self.log(f"   {os.path.basename(ruta)}")
            self.estado("JSON básico OK", COLOR_OK)
            
            messagebox.showinfo("Éxito",
                f"JSON básico generado\n\n{total:,} registros\n\n{os.path.basename(ruta)}")
            self.progress.set(0)
        except Exception as e:
            self.log(f"\nError: {e}")
            self.estado("Error", COLOR_ERROR)
            messagebox.showerror("Error", str(e))
            self.progress.set(0)
        finally:
            self.bloquear(False)
    
    
    def accion_2(self):
        if not self.json_basico_analisis:
            messagebox.showwarning("Advertencia", "Selecciona JSON básico")
            return
        if not self.carpeta_salida_2:
            messagebox.showwarning("Advertencia", "Selecciona carpeta de salida")
            return
        threading.Thread(target=self._run_2, daemon=True).start()
    
    
    def _run_2(self):
        try:
            self.bloquear(True)
            self.estado("Generando análisis...", COLOR_WARN)
            self.log("\n" + "="*50)
            self.log("JSON BÁSICO A ANÁLISIS")
            self.log("="*50)
            
            self.progress.set(0.3)
            ruta, carpeta_per, total = json_basico_a_analisis(
                self.json_basico_analisis, self.carpeta_salida_2
            )
            
            self.progress.set(1.0)
            self.log(f"\nCompletado")
            self.log(f"   Registros: {total:,}")
            self.log(f"   Análisis: {os.path.basename(ruta)}")
            self.log(f"   Períodos: {carpeta_per}")
            self.estado("Análisis OK", COLOR_OK)
            
            messagebox.showinfo("Éxito",
                f"Análisis generado\n\n{total:,} registros\n\n"
                f"{os.path.basename(ruta)}\n"
                f"Carpeta: analisis_por_periodos/")
            self.progress.set(0)
        except Exception as e:
            self.log(f"\nError: {e}")
            self.estado("Error", COLOR_ERROR)
            messagebox.showerror("Error", str(e))
            self.progress.set(0)
        finally:
            self.bloquear(False)
    
    
    def accion_3(self):
        if not self.json_basico_sinteticos:
            messagebox.showwarning("Advertencia", "Selecciona JSON básico")
            return
        if not self.carpeta_salida_3:
            messagebox.showwarning("Advertencia", "Selecciona carpeta de salida")
            return
        
        try:
            fecha_base = self.date_inicio.get_date()
            h_ini = datetime.strptime(self.entry_hora_ini.get(), "%H:%M:%S").time()
            h_fin = datetime.strptime(self.entry_hora_fin.get(), "%H:%M:%S").time()
            dias = int(self.entry_dias.get())
            intervalo = int(self.entry_intervalo.get())
            
            if dias <= 0 or intervalo <= 0:
                raise ValueError("Días e intervalo deben ser > 0")
            
            f_ini = datetime.combine(fecha_base, h_ini)
            f_fin = datetime.combine(fecha_base, h_fin)
            if dias > 1:
                f_fin += timedelta(days=dias - 1)
            
            if f_fin <= f_ini:
                raise ValueError("Fecha fin debe ser posterior")
        except Exception as e:
            messagebox.showwarning("Advertencia", f"Datos inválidos:\n{e}")
            return
        
        threading.Thread(target=self._run_3, args=(f_ini, f_fin, intervalo),
                        daemon=True).start()
    
    
    def _run_3(self, f_ini, f_fin, intervalo):
        try:
            self.bloquear(True)
            self.estado("Generando sintéticos...", COLOR_WARN)
            self.log("\n" + "="*50)
            self.log("JSON BÁSICO A SINTÉTICOS")
            self.log("="*50)
            self.log(f"{f_ini} -> {f_fin}")
            self.log(f"Intervalo: {intervalo}s")
            
            self.progress.set(0.4)
            ruta, total = json_basico_a_sinteticos(
                self.json_basico_sinteticos,
                f_ini, f_fin, intervalo,
                {},
                self.carpeta_salida_3
            )
            
            self.progress.set(1.0)
            self.log(f"\nCompletado")
            self.log(f"   Total: {total:,} registros")
            self.log(f"   {os.path.basename(ruta)}")
            self.estado("Sintéticos OK", COLOR_OK)
            
            messagebox.showinfo("Éxito",
                f"Sintéticos generados\n\n"
                f"Registros: {total:,}\n\n"
                f"{os.path.basename(ruta)}")
            self.progress.set(0)
        except Exception as e:
            self.log(f"\nError: {e}")
            self.estado("Error", COLOR_ERROR)
            messagebox.showerror("Error", str(e))
            self.progress.set(0)
        finally:
            self.bloquear(False)


if __name__ == "__main__":
    app = App()
    app.mainloop()