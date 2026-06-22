# Guía de integración con Power BI

Power BI no se "programa" desde Python: es una herramienta de escritorio que
**consume** los datos que produce el pipeline. Esta guía explica cómo conectar
Power BI Desktop a la capa BI generada en `data/processed/`.

## 1. Insumos que genera el pipeline

Tras correr `python main.py --fuente datalake` (o `sample`), tienes:

| Archivo | Rol en el modelo Power BI |
|---|---|
| `data/processed/inmuebles_procesados.parquet` (o `.csv`) | **Tabla de hechos** (1 fila por inmueble) |
| `data/processed/bi/distribucion_geografica.csv` | Frecuencia de oferta por barrio |
| `data/processed/bi/tendencia_central.csv` | Media/mediana/segmento por barrio |
| `data/processed/bi/ranking_valor_m2.csv` | Ranking de valor/m² por barrio |
| `data/processed/bi/matriz_correlacion.csv` | Determinantes del precio |
| `data/processed/bi/impacto_*.csv` | Variación de precio por característica |

> Instala `pyarrow` (`pip install pyarrow`) para obtener el `.parquet`: Power BI
> lo carga más rápido y conserva tipos. Si no, usa los `.csv`.

## 2. Conexión (paso a paso)

1. **Inicio → Obtener datos → Carpeta** y selecciona `data/processed/`
   (o `Texto/CSV` archivo por archivo / `Parquet` para la tabla de hechos).
2. En *Power Query*, para cada CSV: **Usar la primera fila como encabezado** y
   confirmar tipos (`precio`, `area`, `valor_m2` = Decimal; `habitaciones`,
   `parqueaderos` = Entero; `barrio` = Texto).
3. **Cerrar y aplicar**.
4. En la **vista de Modelo**, relaciona las tablas dimensión con la de hechos por
   `barrio` (cardinalidad muchos-a-uno desde hechos hacia cada tabla por-barrio).

## 3. Automatizar la actualización

- Programa el pipeline (cron en la VM Vagrant / GitHub Actions) para regenerar
  `data/processed/` y, si la carpeta está sincronizada con Google Drive / OneDrive,
  Power BI Service la refresca con un *gateway*.
- Alternativa simple: botón **Actualizar** en Power BI Desktop tras correr el pipeline.

## 4. Medidas DAX sugeridas

Crea una tabla de medidas y pega:

```DAX
Total Inmuebles   = COUNTROWS('inmuebles_procesados')
Canon Mediano     = MEDIAN('inmuebles_procesados'[precio])
Canon Promedio    = AVERAGE('inmuebles_procesados'[precio])
Valor m2 Mediano  = MEDIAN('inmuebles_procesados'[valor_m2])
Area Mediana      = MEDIAN('inmuebles_procesados'[area])

-- Participación de oferta del barrio en el filtro actual
% Participacion Oferta =
DIVIDE(
    [Total Inmuebles],
    CALCULATE([Total Inmuebles], ALL('inmuebles_procesados'[barrio]))
)

-- Premium relativo del barrio vs. la mediana global de valor/m2
Indice Premium m2 =
DIVIDE(
    [Valor m2 Mediano],
    CALCULATE([Valor m2 Mediano], ALL('inmuebles_procesados'[barrio]))
)
```

## 5. Páginas recomendadas del informe

1. **Resumen ejecutivo** — KPIs (medidas anteriores) + mapa/treemap de oferta por barrio.
2. **Precios** — barras de `Canon Mediano` por barrio coloreadas por `Segmento`
   (de `tendencia_central.csv`).
3. **Valorización** — ranking de `Valor m2 Mediano` + dispersión `precio` vs `area`.
4. **Determinantes** — matriz de correlación (matriz/heatmap) + gráficos de `impacto_*`.

## 6. ¿Power BI o Streamlit?

- **Power BI**: reporting ejecutivo, distribución corporativa, refresco programado.
- **Streamlit** (`dashboard/app.py`): vista web ligera, embebe el agente de IA,
  ideal para correr dentro de la VM. Ambas leen los mismos artefactos del pipeline.
