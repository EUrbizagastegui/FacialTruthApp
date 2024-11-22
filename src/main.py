import flet as ft
import shutil
import os
from pathlib import Path
from reconocimiento_emociones import reconocimiento_emociones
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF

import nbconvert
from nbconvert.preprocessors import ExecutePreprocessor
import nbformat
import requests
import json

url = "https://api.openai.com/v1/chat/completions"

api_key = "API_KEY"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

def download_csv():
    ruta_origen = "../data/resultados/emociones_clase1.csv"
    try:
        ruta_escritorio = str(Path.home() / "Downloads")
        nombre_archivo = os.path.basename(ruta_origen)
        ruta_destino = os.path.join(ruta_escritorio, nombre_archivo)
        shutil.copy(ruta_origen, ruta_destino)
        print("Archivo CSV generado copiado al escritorio del usuario.")

        return True, ruta_destino
    except Exception as e:
        print("Error al copiar el archivo CSV generado al escritorio:", e)
        return False, None
    
def convert_to_html():
    ruta_origen = "notebooks/analisis.ipynb" 
    try:
        print("Leyendo el notebook...")
        with open(ruta_origen, 'r', encoding='utf-8') as f:
            notebook = nbformat.read(f, as_version=4)
        
        print("Ejecutando el notebook...")
        executor = ExecutePreprocessor(timeout=600, kernel_name='python3')
        try:
            processed_notebook, _ = executor.preprocess(notebook, {'metadata': {'path': os.path.dirname(ruta_origen)}})
        except Exception as e:
            print("Error al ejecutar el notebook:", e)
            return False, None
        
        print("El notebook se ha ejecutado correctamente.")

        ruta_escritorio = str(Path.home() / "Downloads")
        html_exporter = nbconvert.HTMLExporter()
        (html_body, resources) = html_exporter.from_notebook_node(processed_notebook)
        nombre_archivo_html = os.path.splitext(os.path.basename(ruta_origen))[0] + ".html"
        ruta_destino = os.path.join(ruta_escritorio, nombre_archivo_html)

        with open(ruta_destino, "w", encoding="utf-8") as f:
            f.write(html_body)
        print("Archivo HTML generado y guardado en el escritorio del usuario.")
        return True, ruta_destino
    except Exception as e:
        print("Error al convertir o guardar el archivo HTML:", e)
        return False, None

def generar_reporte_pdf(csv_path):
    try:
        df = pd.read_csv(csv_path)
        
        emociones = df['Emocion'].value_counts()
        
        plt.figure(figsize=(10, 6))
        emociones.plot(kind='bar', color='skyblue')
        plt.title('Emociones Predominantes')
        plt.xlabel('Emoción')
        plt.ylabel('Frecuencia')
        plt.tight_layout()
        
        ruta_grafico = 'emociones.png'
        plt.savefig(ruta_grafico)
        plt.close()

        emociones_str = ", ".join([f"{emocion}: {count}" for emocion, count in emociones.items()])
        prompt = f"Basado en las siguientes emociones predominantes detectadas en el video: {emociones_str}. Proporciona recomendaciones para que el dueño del producto ajuste su oferta. "
        prompt += "Si las emociones negativas son predominantes (como anger, disgust, sadness, fear, contempt), sugiere mejoras en el producto o en la experiencia de compra para reducir esos sentimientos. "
        prompt += "Si las emociones positivas son más comunes (como happy, surprise), recomienda cómo amplificar esas emociones a través de características adicionales, servicios complementarios o marketing enfocado a reforzar la experiencia positiva del cliente."

        data = {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "Eres un experto en marketing enfocado en focus group."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            response_data = response.json()
            recommendation = response_data["choices"][0]["message"]["content"].strip()
        else:
            recommendation = f"Error {response.status_code}: {response.text}"

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(200, 10, txt="Reporte de Emociones Predominantes", ln=True, align='C')

        pdf.ln(10)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, txt="Este reporte muestra las emociones predominantes en las personas, "
                                 "según los datos obtenidos. El gráfico de barras siguiente muestra la "
                                 "frecuencia de las diferentes emociones registradas.")

        pdf.ln(10)
        pdf.image(ruta_grafico, x=10, y=pdf.get_y(), w=180)

        pdf.add_page()
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(200, 10, txt="Recomendación de la IA", ln=True, align='L')

        pdf.ln(10)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, txt=recommendation)

        ruta_destino = str(Path.home() / "Downloads" / "Reporte_Emociones.pdf")
        pdf.output(ruta_destino)

        print(f"Reporte PDF generado y guardado como {ruta_destino}")
        return True, ruta_destino

    except Exception as e:
        print("Error al generar el reporte PDF:", e)
        return False, None


def upload_video(result):
    if result is not None and result.files is not None:
        if len(result.files) == 1:
            f = result.files[0]
            filename, file_extension = os.path.splitext(f.name)
            if file_extension.lower() in ('.mp4', '.avi', '.mov', '.mkv', '.wmv'):
                destination_path = "../data/pruebas/" + f.name 
                try:
                    shutil.copy(f.path, destination_path)
                    print("Video guardado exitosamente en:", destination_path)
                    
                    duracion_analisis = 60
                    reconocimiento_emociones(destination_path, duracion_analisis)

                except FileNotFoundError:
                    print("Error: No se encontró el archivo o la ruta de destino no es válida.")
                except Exception as ex:
                    print("Error al guardar el video:", str(ex))
            else:
                print("Error: El archivo seleccionado no es un video.")
        else:
            print("Error: Selecciona solo un archivo de video.")
    else:
        print("Error: No se seleccionó ningún archivo.")

def choose_video():
    global file_picker
    print("Abriendo ventana de selección de archivos...")
    file_picker.pick_files(allow_multiple=False)

def main(page: ft.Page):
    page.window_width = 1300
    page.window_height = 700

    global file_picker
    file_picker = ft.FilePicker(on_result=upload_video)

    page.title = "FACIALTRUTH"
    page.bgcolor = "white"

    def on_button_click(e):
        # Ruta al archivo CSV
        csv_path = "../data/resultados/emociones_clase1.csv"  # Asegúrate de tener este archivo con las emociones
        exito, ruta_pdf = generar_reporte_pdf(csv_path)
        if exito:
            print(f"Reporte PDF generado en: {ruta_pdf}")
        else:
            print("Hubo un error al generar el reporte.")


    page.add(
        ft.Row([
            ft.Container(
                content=ft.Image(src="https://i.ibb.co/Z2PwKTJ/facialtruth.png", width=200, height=200),
                height=100,
                width=300,
            ),

            ft.Container(
                content=ft.Text("Aplicación de Reconocimiento de emociones", size=50, font_family="BankGothic Md Bt",
                color="black",
                weight=ft.FontWeight.W_100,
                text_align = "center"),
                width = 900,
                alignment = ft.alignment.center
            )
        ]),

        ft.Row([
            ft.Container(
                content=ft.Image(src="https://i.ibb.co/nbGGKJB/logo-para-la-empresa-Facial-Truth-con-letra-removebg-preview.png", width=400, height=400),
                margin = 40),
            ft.Column([
                ft.Container(
                    content=ft.ElevatedButton("Subir video", on_click=lambda _: choose_video()),
                    width=500,
                    height=100,
                    padding=30,
                    margin=10),
                ft.Container(
                    content=ft.ElevatedButton("Generar CSV", on_click=lambda _: download_csv()),
                    width=500,
                    height=100,
                    padding=30,
                   margin=10),
                ft.Container(
                    ft.ElevatedButton("Descargar informe", on_click=on_button_click),
                    width=500,
                    height=100,
                    padding=30,
                    margin=10),
            ]),
            
        ]),

        
        ),
        

    page.overlay.append(file_picker)
    page.update()

ft.app(main)





















