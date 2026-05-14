import pytest
import pandas as pd
# Importamos la función principal y la de apoyo lógica
from src.modulo_analitics.extract import extraer_datos, filtrar_atributos

# --- 1. PRUEBA DE UNIDAD: filtrar_atributos ---
# Probamos la lógica matemática sin necesidad de HTML complejo
def test_filtrar_atributos_logica():
    # Arrange (Organizar): Lista de strings como los que devuelve BeautifulSoup
    entrada = ["45 m2", "2 hab", "1 bañ", "1 par"]
    
    # Act (Actuar): Ejecutamos la función
    resultado = filtrar_atributos(entrada)
    
    # Assert (Afirmar): Verificamos que los valores sean correctos
    assert resultado["area"] == 45.0
    assert resultado["habitaciones"] == 2
    assert resultado["banos"] == 1.0
    assert resultado["parqueaderos"] == 1

# --- 2. PRUEBA DE INTEGRACIÓN: extraer_datos ---
# Simulamos el flujo completo desde el HTML hasta el DataFrame
def test_extraer_datos_flujo_completo():
    # Arrange: HTML simulado con una tarjeta (card)
    html_simulado = """
    <div class="property-card__container">
        <a href="/inmueble/prueba-123">Link</a>
        <img src="imagen.jpg" alt="Foto Inmueble"/>
        <div class="property-card__detail-top__left">
            <div>Chapinero | Bogotá</div>
        </div>
        <div class="property-card__detail-title">
            <h2>Apartamento Prueba</h2>
        </div>
        <div class="property-card__detail-price">$ 1.500.000</div>
        <div class="pt-main-specs--feature">50 m2</div>
        <div class="pt-main-specs--feature">3 hab</div>
    </div>
    """
    
    # Act: Ejecutamos la extracción principal
    df = extraer_datos(html_simulado)
    
    # Assert: Validaciones manuales sobre el DataFrame resultante
    # A. Verificamos que se creó el DataFrame y no está vacío
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    
    # B. Verificamos columnas por NOMBRE (esto evita errores de índice)
    assert df['url'].iloc[0] == "/inmueble/prueba-123"
    assert df['barrio'].iloc[0] == "Chapinero"
    assert df['precio'].iloc[0] == 1500000
    assert df['area'].iloc[0] == 50.0
    assert df['habitaciones'].iloc[0] == 3
    
    # C. Verificamos que los nombres de las columnas existan
    columnas_esperadas = ['url', 'barrio', 'precio', 'area', 'habitaciones']
    for col in columnas_esperadas:
        assert col in df.columns