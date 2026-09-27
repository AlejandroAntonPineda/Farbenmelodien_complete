#!/usr/bin/env python3

import cv2
import numpy as np
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD

def color_to_note_id(hsv_color):
    h, s, v = hsv_color
    if s < 50 or v < 150: return "null"
    
    if h < 10 or h > 170: return "C"      
    elif 10 <= h < 25: return "D"         
    elif 25 <= h < 35: return "E"         
    elif 35 <= h < 55: return "F"         
    elif 55 <= h < 90: return "G"         
    elif 90 <= h < 130: return "A"        
    elif 130 <= h < 165: return "H"       
    return "null"

def get_dominant_color_area(roi_hsv):
    if roi_hsv.size == 0: return "null"
    pixels = roi_hsv.reshape(-1, 3)
    valid_pixels = [p for p in pixels if p[1] >= 50 and p[2] >= 150]
    
    if not valid_pixels:
        return "null"
        
    median_color = np.median(valid_pixels, axis=0)
    return color_to_note_id(median_color)

def procesar_imagen(ruta_imagen=None):
    if not ruta_imagen:
        ruta_imagen = filedialog.askopenfilename(
            title="Selecciona la partitura en JPG",
            filetypes=[("Archivos de imagen", "*.jpg *.jpeg *.png")]
        )
        
    if not ruta_imagen: 
        return

    try:
        ruta_guardado = filedialog.asksaveasfilename(
            title="Guardar archivo JSON",
            defaultextension=".json",
            filetypes=[("Archivos JSON", "*.json")]
        )
        if not ruta_guardado: return

        img = cv2.imread(ruta_imagen)
        if img is None:
            raise ValueError(f"No se pudo cargar la imagen desde la ruta: {ruta_imagen}")

        img_h, img_w = img.shape[:2]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        contours = sorted(contours, key=lambda c: (cv2.boundingRect(c)[1] // (img_h // 10), cv2.boundingRect(c)[0]))
        pattern = []
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = cv2.contourArea(cnt)
            
            # Filtro 1 Dinámico
            if w < (img_w * 0.01) or h < (img_h * 0.01) or h > (img_h * 0.4): 
                continue 
            
            # Filtro 2: Solidez
            if area / (w * h) < 0.5: 
                continue
            
            ratio = w / h
            
            if ratio > 1.3:
                roi = hsv[y + int(h*0.2) : y + int(h*0.8), x + int(w*0.4) : x + int(w*0.6)]
                id_note = get_dominant_color_area(roi)
                
                duration = "2" if ratio < 2.5 else "4"
                spaces = 2 if ratio < 2.5 else 4
                
                pattern.append({"id": id_note, "id2": "null", "dur": duration})
                for _ in range(spaces - 1):
                    pattern.append({"id": "tie", "id2": "null", "dur": "1"})
                    
            else:
                roi_left = hsv[y + int(h*0.15) : y + int(h*0.85), x + int(w*0.1) : x + int(w*0.45)]
                roi_right = hsv[y + int(h*0.15) : y + int(h*0.85), x + int(w*0.55) : x + int(w*0.9)]
                
                id_left = get_dominant_color_area(roi_left)
                id_right = get_dominant_color_area(roi_right)
                
                if id_left != id_right and id_left != "null" and id_right != "null":
                    pattern.append({"id": id_left, "id2": id_right, "dur": "0.5"})
                else:
                    note_id = id_left if id_left != "null" else id_right
                    
                    # Detección robusta de C2 usando contraste (desviación estándar)
                    if note_id == "C":
                        # Recortar el centro exacto donde va la flecha
                        arrow_roi = gray[y + int(h*0.35) : y + int(h*0.65), x + int(w*0.4) : x + int(w*0.6)]
                        
                        # Si la desviación estándar es alta, hay una figura contrastante (la flecha)
                        if np.std(arrow_roi) > 15: 
                            note_id = "C2"
                            
                    pattern.append({"id": note_id, "id2": "null", "dur": "1"})

        melody_data = {
            "pattern": pattern,
            "beats": 4
        }
        
        with open(ruta_guardado, 'w', encoding='utf-8') as f:
            json.dump(melody_data, f, indent=2)
            
        messagebox.showinfo("¡Éxito!", f"La imagen se ha convertido a JSON correctamente.\nGuardado en:\n{ruta_guardado}")
        
    except Exception as e:
        messagebox.showerror("Error", f"Hubo un problema al procesar la imagen:\n{str(e)}")

def on_drop(event):
    archivos = root.tk.splitlist(event.data)
    if archivos:
        ruta_archivo = archivos[0]
        procesar_imagen(ruta_archivo)

root = TkinterDnD.Tk()
root.title("Conversor de Partituras")
root.geometry("450x250")
root.config(bg="#f3f4f6")

frame_drop = tk.Frame(root, bg="#f3f4f6", bd=2, relief="solid")
frame_drop.pack(expand=True, fill="both", padx=20, pady=20)

frame_drop.drop_target_register(DND_FILES)
frame_drop.dnd_bind('<<Drop>>', on_drop)

lbl_titulo = tk.Label(frame_drop, text="Convierte tu Partitura JPG a JSON", font=("Arial", 14, "bold"), bg="#f3f4f6", fg="#334155")
lbl_titulo.pack(pady=(20, 5))

lbl_instrucciones = tk.Label(frame_drop, text="Arrastra y suelta aquí tu archivo de imagen\no utiliza el botón de abajo.", font=("Arial", 11), bg="#f3f4f6", fg="#64748b")
lbl_instrucciones.pack(pady=5)

btn_subir = tk.Button(
    frame_drop, 
    text="📂 Buscar JPG Manualmente", 
    command=lambda: procesar_imagen(), 
    font=("Arial", 11, "bold"), 
    bg="#3b82f6", 
    fg="white",
    activebackground="#2563eb",
    activeforeground="white",
    cursor="hand2",
    padx=15,
    pady=8,
    border=0
)
btn_subir.pack(pady=15)

root.mainloop()