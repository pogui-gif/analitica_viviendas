import pandas as pd
import numpy as np

def limpiar_datos(df):
    """
    Función principal del módulo: Asigna nombres de columnas, normaliza textos, 
    extrae IDs, crea URLs completas y maneja los valores nulos.
    """
    # 1. Asignación de nombres a las columnas
    df.columns = ['href', 'url_img', 'alt_img', 'barrio', 'servicio', 'precio_str', 'precio', 'area', 'habitaciones', 'banos', 'parqueaderos']
    
    # 2. Normalización de datos de texto (Capitalización y limpieza de espacios)
    df['barrio'] = df['barrio'].str.title().str.strip()
    df['servicio'] = df['servicio'].str.title().str.strip()
    df['alt_img'] = df['alt_img'].str.title().str.strip()
    
    # 3. Creación de ID mediante regex
    df['id'] = df['href'].str.extract(r'(M[A-Z0-9]+)')
    
    # 4. Creación de nueva columna con el link del servicio
    direccion = 'https://www.metrocuadrado.com'
    df['link'] = direccion + df['href']
    
    # 5. Convertir a numéricas las columnas que requieran este tipo de dato
    num_colums = ['precio', 'area', 'habitaciones', 'banos', 'parqueaderos']
    for col in num_colums:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    # 6. Reemplazamos los -1 por nulos reales (NaN) en las columnas correspondientes
    df[['area', 'habitaciones', 'banos', 'parqueaderos']] = df[['area', 'habitaciones', 'banos', 'parqueaderos']].replace(-1, np.nan)
    
    return df