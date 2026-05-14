import pandas as pd
import numpy as np
from modulo_analitics import stats # Cambia "stats" por el nombre exacto de tu archivo

def test_funciones_estadisticas():
    # 1. Crear un DataFrame simulado con 5 filas (requerido para el qcut de q=5)
    # y con inmuebles idénticos en distintos barrios para la función analisis_adicional.
    datos_prueba = [
        {'id': '1', 'barrio': 'Centro', 'precio': 1000000, 'link': 'url1', 'area': 40, 'habitaciones': 1, 'banos': 1, 'parqueaderos': 1},
        {'id': '2', 'barrio': 'Norte', 'precio': 2000000, 'link': 'url2', 'area': 50, 'habitaciones': 2, 'banos': 1, 'parqueaderos': 0},
        {'id': '3', 'barrio': 'Sur', 'precio': 1500000, 'link': 'url3', 'area': 60, 'habitaciones': 1, 'banos': 1, 'parqueaderos': 1},
        {'id': '4', 'barrio': 'Centro', 'precio': 3000000, 'link': 'url4', 'area': 80, 'habitaciones': 3, 'banos': 2, 'parqueaderos': 2},
        {'id': '5', 'barrio': 'Norte', 'precio': 2500000, 'link': 'url5', 'area': 70, 'habitaciones': 2, 'banos': 2, 'parqueaderos': 1}
    ]
    df = pd.DataFrame(datos_prueba)

    # 2. Probar: obtener_extremos_precio
    df_extremos = stats.obtener_extremos_precio(df)
    assert len(df_extremos) == 2 # Debe traer 1 mínimo y 1 máximo
    assert df_extremos['precio'].min() == 1000000
    assert df_extremos['precio'].max() == 3000000

    # 3. Probar: distribucion_geografica
    total_barrios, tabla_frec = stats.distribucion_geografica(df)
    assert total_barrios == 3 # Centro, Norte, Sur
    assert len(tabla_frec) == 3 # La tabla debe tener 3 filas

    # 4. Probar: tendencia_central_precios
    resumen_barrios = stats.tendencia_central_precios(df)
    assert 'Segmento' in resumen_barrios.columns # Validar que se creó la columna de cuantiles
    assert len(resumen_barrios) == 3