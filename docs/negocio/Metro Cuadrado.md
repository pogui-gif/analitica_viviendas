## Proyecto ETL Inmobiliario: Arriendos en Bogotá

### Objetivos del Proyecto
- **Objetivo Principal:** Extraer datos de páginas web sobre venta y arrendamiento de bienes inmuebles en la ciudad de Bogotá, estructurarlos y analizarlos.
- **Objetivo Educativo:** Aprender de forma práctica sobre la implementación de pipelines de datos (ETL) paso a paso, utilizando Inteligencia Artificial como soporte analítico y guía, pero escribiendo y comprendiendo el código de forma autónoma.

### Arquitectura y Flujo de Trabajo (Macro)
Basado en el mapa mental del proyecto, el flujo se divide en cuatro grandes fases secuenciales [1]:
1. **Obtención de los datos:** Extracción automatizada desde páginas web y almacenamiento local inicial en formato CSV [1].
2. **Análisis de los datos:** Exploración de la información utilizando Python y Pandas [1].
3. **Procesamiento de los datos:** Limpieza, normalización y transformación de los DataFrames, perfilando su carga hacia bases de datos (SQL / CSV) [1].
4. **Modelos:** Etapa final proyectada para el entrenamiento de modelos predictivos o estadísticos sobre la data ya depurada [1].

### Composición del Script (Fase de Extracción)
El entorno de desarrollo es Google Colab, orquestado en Python con las siguientes herramientas clave [2]:

#### 1. Navegación Dinámica (Playwright)
- **`scroll_page(page)`:** Función asíncrona que simula el comportamiento humano haciendo scroll en la página de Metrocuadrado para forzar la carga de todas las tarjetas de propiedades (enfrentando el scroll infinito) [2].
- **`get_rendered_html(page)`:** Extrae el HTML renderizado. Ejecuta un script en JavaScript diseñado para expandir el "Shadow DOM", un obstáculo técnico común en scraping moderno [3].

#### 2. Análisis HTML (BeautifulSoup)
- Lee el archivo HTML guardado localmente e identifica todos los contenedores de los inmuebles utilizando la clase principal `.property-card__container` [4].

#### 3. Parsing y Lógica de Atributos
- **`filtrar_atributos`:** Lógica condicional inteligente que busca palabras clave (`m2`, `hab`, `bañ`, `par`) en las etiquetas de texto para clasificar correctamente el área, habitaciones, baños y parqueaderos, independientemente de su orden de aparición [5, 6].
- **`get_precio`:** Limpieza temprana de texto que remueve los símbolos de peso (`$`) y puntos, convirtiendo el valor a un número continuo (float) [6, 9].

#### 4. Estructuración (Pandas)
- La función **`get_esquema`** consolida las extracciones individuales y las almacena en una lista de listas, la cual es finalmente transformada en un `DataFrame` de Pandas y exportada a `salida.csv` [6, 7].

---

### Lista de Tareas (TODO) y Análisis Descriptivo
Pasos a seguir sobre el DataFrame (`df`) para completar el pipeline de transformación y análisis [8].

#### Fase 1: Limpieza y Normalización (ETL)
- [x] **Nombrar columnas:** Reasignar el atributo `df.columns` para nombrar las 12 variables extraídas (ej. `href`, `barrio`, `precio`, `area`, `id`, etc.) [8].
- [x] **Creación y limpieza de ID:** Extraer el identificador único desde la URL (`href`) aislando el código alfanumérico que inicia por "M" (ej. `M6017977`) mediante Expresiones Regulares (`.str.extract(r'(M[A-Z0-9]+)')`) [4, 8].
- [x] **Validación de duplicados:** Utilizar `.groupby('id').size()` o `.duplicated()` para encontrar y tratar publicaciones repetidas.
- [x] **Normalización de Texto:** Estandarizar la columna `barrio` (y futuras columnas categóricas como `servicio`) aplicándole mayúsculas (`.str.upper()`) y eliminando espacios en blanco (`.str.strip()`) [8].
- [x] **Validación de Tipos (Casting):** Asegurar que `precio`, `area` y `banos` sean numéricos continuos (`float`), y que `habitaciones` y `parqueaderos` sean enteros (`int`) [8].  [completion:: 2026-04-06]

#### Fase 2: Análisis Descriptivo
[[Análisis Descriptivo]]

Consideraciones adicionales, permiso de publicación y extracción de los datos por parte de los publicantes de las ofertas
	Políticas de datos
	Alcance del proyecto
	Asemejar pautas para el comportamiento humano
	Restricciones de las páginas
	Valor de las iniciativas (Alternativas de publicación encriptada)
		Tiempo y recurso destinado.
		Valor de los datos, encriptarlos.