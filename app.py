from flask import Flask, request, render_template, redirect, url_for
import pandas as pd
from fuzzywuzzy import process
import logging
import time
import unicodedata
import openpyxl 


app = Flask(__name__)

# Configuración de logging
logging.basicConfig(filename='flask_app.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Normalizar la cadena para manejar caracteres especiales
def normalize_string(s):
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('utf-8', 'ignore')

def find_matches(name, choices, threshold=87):
    results = process.extractOne(name, choices)
    if results and results[1] >= threshold:
        return results[0]
    return None

@app.route('/')
def upload_files():
    return render_template('upload.html')

@app.route('/compare', methods=['POST'])
def compare_files():
    start_time = time.time()

    if 'file1' not in request.files or 'file2' not in request.files:
        return redirect(url_for('upload_files'))

    file1 = request.files['file1']
    file2 = request.files['file2']

    if not file1.filename or not file2.filename:
        return redirect(url_for('upload_files'))

    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)

    # Normalizar las columnas necesarias
    df1['partner_name_normalized'] = df1.iloc[:, 2].apply(lambda x: normalize_string(x.strip().lower()))
    df2['Descripción_normalized'] = df2.iloc[:, 3].apply(lambda x: normalize_string(x.strip().lower()))

    choices = df2['Descripción_normalized'].tolist()
    matches = []
    coincidencias_con_descripcion = 0

    for _, row in df1.iterrows():
        match = find_matches(row['partner_name_normalized'], choices)
        if match:
            matched_row = df2[df2['Descripción_normalized'] == match].iloc[0]
            descripcion = matched_row.iloc[2]
            coincidencias_con_descripcion += bool(descripcion)
            matches.append({
                'ID': row.iloc[1],
                'partner_name': row.iloc[2],
                'Descripción': descripcion
            })
        else:
            matches.append({
                'ID': row.iloc[1],
                'partner_name': row.iloc[2],
                'Descripción': ''
            })

    if matches:
        coincidencias_df = pd.DataFrame(matches)
        coincidencias_df.to_csv('coincidencias.csv', index=False, encoding='utf-8')
        coincidencias_df.to_excel('coincidencias.xlsx', index=False, engine='xlsxwriter')

    # Calcular y registrar tiempo de procesamiento
    processing_time = time.time() - start_time
    logging.info(f'Tiempo de procesamiento: {processing_time:.2f} segundos')

    total_coincidencias = len(matches)

    return render_template('results.html', tables=[coincidencias_df.to_html(classes='data')],
        titles=coincidencias_df.columns.values, total_coincidencias=total_coincidencias, 
        coincidencias_con_descripcion=coincidencias_con_descripcion,
        processing_time=processing_time)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
