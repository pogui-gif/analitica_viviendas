import pytest
import pandas as pd
import numpy as np
from modulo_analitics.clean import limpiar_datos

def test_limpiar_datos_logica():
    # 1. Crear datos de entrada "sucios"
    data = {
        'col1': ['/inmueble/M123', '/inmueble/M456'],
        'col2': ['img1', 'img2'],
        'col3': [' apto lindo ', 'casa grande'],
        'col4': [' chico norte ', 'CEDRITOS'],
        'col5': [' arriendo ', 'VENTA'],
        'col6': ['$1M', '$2M'],
        'col7': ['1000', '2000'],
        'col8': [50, -1],         # El -1 debe ser NaN en area
        'col9': [3, -1],          # El -1 debe ser NaN en habitaciones
        'col10': [2, 1],
        'col11': [-1, 0]          # El -1 debe ser NaN en parqueaderos
    }
    df_sucio = pd.DataFrame(data)

    # 2. Ejecutar la función
    df_limpio = limpiar_datos(df_sucio)

    # 3. Verificaciones (Asserts)
    
    # Test de Nombres de Columnas
    assert 'id' in df_limpio.columns
    assert 'link' in df_limpio.columns
    assert df_limpio.columns[3] == 'barrio'

    # Test de Normalización de Texto (Punto 2)
    assert df_limpio['barrio'].iloc[0] == 'Chico Norte'
    assert df_limpio['servicio'].iloc[1] == 'Venta'

    # Test de Regex ID (Punto 3)
    assert df_limpio['id'].iloc[0] == 'M123'

    # Test de URL Completa (Punto 4)
    assert df_limpio['link'].iloc[0].startswith('https://www.metrocuadrado.com')

    # Test de Conversión Numérica y reemplazo de -1 (Puntos 5 y 6)
    assert pd.isna(df_limpio['area'].iloc[1])
    assert pd.isna(df_limpio['habitaciones'].iloc[1])
    assert pd.isna(df_limpio['parqueaderos'].iloc[0])
    assert df_limpio['precio'].dtype == np.float64 or df_limpio['precio'].dtype == np.int64