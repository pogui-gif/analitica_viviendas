import pandas as pd

def obtener_extremos_precio(df):
    """Retorna los inmuebles con el precio mínimo y máximo [1]."""
    df_extremos = pd.concat([
        df.loc[df['precio'] == df['precio'].min(), ['id', 'barrio', 'precio', 'link']],
        df.loc[df['precio'] == df['precio'].max(), ['id', 'barrio', 'precio', 'link']]
    ])
    return df_extremos

def distribucion_geografica(df):
    """Calcula el número de barrios únicos y la frecuencia de ofertas [2]."""
    total_barrios = df['barrio'].nunique()
    frec_absoluta = df['barrio'].value_counts()
    frec_relativa = df['barrio'].value_counts(normalize=True) * 100
    
    tabla_frecuencias = pd.DataFrame({
        'Cantidad de ofertas': frec_absoluta,
        'Porcentaje de ofertas': frec_relativa
    })
    return total_barrios, tabla_frecuencias

def tendencia_central_precios(df):
    """Calcula métricas estadísticas por barrio y los clasifica en segmentos [2]."""
    resumen_barrios = df.groupby('barrio')['precio'].agg(['mean', 'median', 'min', 'max'])
    resumen_barrios.columns = ['Media', 'Mediana', 'Minimo', 'Maximo']
    resumen_barrios = resumen_barrios.sort_values(by='Mediana', ascending=False)
    resumen_barrios['Segmento'] = pd.qcut(resumen_barrios['Mediana'], q=3, labels=['Segmento bajo', 'Segmento medio', 'Segmento alto'])
    return resumen_barrios

def valorizacion_metro_cuadrado(df):
    """Calcula el valor del metro cuadrado por barrio [3]."""
    df_calc = df.copy()
    df_calc['valor_m2'] = df_calc['precio'] / df_calc['area']
    ranking_m2 = df_calc.groupby('barrio')['valor_m2'].agg('median').reset_index()
    ranking_m2.columns = ['barrio', 'mediana_valor_m2']
    ranking_m2 = ranking_m2.sort_values(by='mediana_valor_m2', ascending=False)
    return df_calc, ranking_m2

def determinantes_precio(df):
    """Calcula la matriz de correlación de Pearson [3]."""
    columnas_num = ['precio', 'area', 'habitaciones', 'banos', 'parqueaderos']
    matriz_corr = df[columnas_num].corr()
    return matriz_corr

def analisis_adicional(df):
    """Compara precios promedio y realiza análisis controlado por barrio [4]."""
    precio_por_banos = df.groupby('banos')['precio'].mean().reset_index()
    precio_por_habitacion = df.groupby('habitaciones')['precio'].mean().reset_index()
    
    inmuebles_similares = df[(df['habitaciones'] == 1) & (df['banos'] == 1) & (df['parqueaderos'] == 1)]
    control_barrio = inmuebles_similares.groupby('barrio')['precio'].median().sort_values(ascending=False).head(5).reset_index()
    
    return precio_por_banos, precio_por_habitacion, control_barrio

def impacto_caracteristicas(df):
    """Calcula la variación del precio según características y rangos de área [4, 5]."""
    # Baños
    impacto_banos = df.groupby('banos')['precio'].agg(['mean', 'count']).reset_index()
    impacto_banos.columns = ['cant_banos', 'precio_promedio', 'total_inmuebles']
    impacto_banos['variacion_vs_anterior'] = impacto_banos['precio_promedio'].diff()
    
    # Habitaciones
    impacto_habit = df.groupby('habitaciones')['precio'].agg(['mean', 'count']).reset_index()
    impacto_habit.columns = ['cant_habit', 'precio_promedio', 'total_inmuebles']
    impacto_habit['variacion_vs_anterior'] = impacto_habit['precio_promedio'].diff()
    
    # Parqueaderos
    impacto_parq = df.groupby('parqueaderos')['precio'].agg(['mean', 'count']).reset_index()
    impacto_parq.columns = ['cant_parq', 'precio_promedio', 'total_inmuebles']
    impacto_parq['variacion_vs_anterior'] = impacto_parq['precio_promedio'].diff()
    
    # Área
    df_temp = df.copy()
    df_temp['rango_area'] = pd.qcut(df_temp['area'], q=5)
    impacto_area = df_temp.groupby('rango_area', observed=False)['precio'].agg(['mean', 'count']).reset_index()
    impacto_area.columns = ['rango_area', 'precio_promedio', 'total_inmuebles']
    impacto_area['variacion_vs_anterior'] = impacto_area['precio_promedio'].diff()
    
    return impacto_banos, impacto_habit, impacto_parq, impacto_area