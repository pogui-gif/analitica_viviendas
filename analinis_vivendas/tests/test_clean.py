import pandas as pd
import numpy as np
from modulo_analitics import clean

def test_limpiar_datos():
    # 1. Preparar datos crudos simulando la salida de extract.py
    datos_crudos = [{
        0: '/inmueble/arriendo-apartamento-bogota-M6376734',
        1: 'img.jpg',
        2: ' foto apto ',
        3: ' SUCRE ',
        4: ' ARRIENDO ',
        5: '$1.800.000',
        6: '1800000',
        7: -1.0, # Área sin dato para probar conversión a NaN
        8: 1,
        9: -1.0, # Baño sin dato
        10: 0
    }]
    df = pd.DataFrame(datos_crudos)

    # 2. Ejecutar la función de limpieza
    df_resultado = clean.limpiar_datos(df)

     # 3. Validar que las transformaciones sean correctas
    assert df_resultado['barrio'].iloc[0] == 'Sucre' 
    assert df_resultado['id'].iloc[0] == 'M6376734' 
    assert pd.isna(df_resultado['area'].iloc[0]) 
    assert df_resultado['habitaciones'].iloc[0] == 1 
    assert df_resultado['link'].iloc[0] == 'https://www.metrocuadrado.com/inmueble/arriendo-apartamento-bogota-M6376734'