[[Metro Cuadrado]]

# Preguntas de negocio traducidas a métricas estadísticas [8].

1. **Concentración Geográfica (Distribución):**
	- *Métrica:* Frecuencias absolutas (`value_counts`) y porcentuales.
	- *Objetivo:* Identificar el volumen total de barrios únicos y el Top 5 de zonas con mayor cantidad de ofertas [8].
2. **Tendencia Central de Precios:**
	  - Métrica:* Mediana, Media, Mínimo y Máximo.
	  - *Objetivo:* Calcular la centralidad de la columna `precio` agrupada por `barrio` para clasificar las zonas en segmentos (alto, medio y bajo) [8].
3. **Valorización del Espacio ($/m2):**
	  - *Métrica:* Creación de variable (`precio` / `area`) y Mediana agrupada.
	  - *Objetivo:* Descubrir qué barrios tienen el metro cuadrado más costoso y cuáles ofrecen más área por menor costo [8].
4. **Determinantes del Canon de Arriendo:**
	  - *Métrica:* Coeficiente de correlación.
	  - *Objetivo:* Evaluar matemáticamente qué variable física (`area`, `habitaciones`, `banos

# 1. Requerimiento: Análisis de la distribución geográfica de la oferta

_"Cuales son los barrios de las ofertas y cual es el que mas se repite"_

- [ ] **Conteo de diversidad:** Calcular el total de barrios únicos presentes en el DataFrame para entender la amplitud de la cobertura del scraping.
- [ ] **Frecuencia absoluta:** Realizar un conteo de la cantidad exacta de inmuebles disponibles agrupados por la variable **barrio**.
- [ ] **Frecuencia relativa (Participación):** Calcular qué porcentaje del total de la base de datos representa cada barrio, para identificar monopolios de oferta.
- [ ] **Identificación del Top:** Extraer el top 5 de los barrios con mayor volumen de publicaciones y el top 5 de los barrios con menor volumen.

# 2. Requerimiento: Análisis de tendencia central del canon de arrendamiento

_"Cual es el barrio con un promedio de arriendo alto, bajo y el medio"_

- [ ] **Promedio por zona:** Calcular la media matemática de la variable **precio** agrupada por **barrio**.
- [ ] **Mediana por zona (Métrica clave):** Calcular la mediana del **precio** agrupada por **barrio** para obtener un valor más realista, ya que el promedio puede verse afectado si hay un solo apartamento excesivamente caro en la zona.
- [ ] **Dispersión interna:** Determinar el **precio** mínimo y máximo dentro de cada barrio para entender qué tanta variación hay en una misma ubicación.
- [ ] **Estratificación del mercado:** Ordenar los resultados consolidados para clasificar formalmente qué barrios componen el segmento alto (los más caros), segmento medio y segmento bajo (los más económicos).

# 3. Requerimiento: Análisis de valorización del espacio físico

_"En terminos de area cuadrada cual es el barrio mas caro, bajo y medio"_

- [ ] **Creación de nueva métrica:** Generar una nueva columna en el DataFrame calculando el **"Valor por metro cuadrado"** (dividiendo la columna **precio** entre la columna **area** para cada fila).
- [ ] **Promedio de valorización por zona:** Agrupar por **barrio** y calcular el promedio de esta nueva métrica ($/m2).
- [ ] **Ranking de costo de espacio:** Ordenar los barrios según su costo por metro cuadrado para identificar dónde el espacio físico es más premium (segmento alto) y dónde se obtiene más espacio por menos dinero (segmento bajo).

# 4. Requerimiento: Análisis de factores determinantes del precio

_"Que influye mas en el costo, el area, el barrio o la cantidad de habitaciones, baños o paqueaderos."_

- [ ] **Matriz de correlación numérica:** Calcular el coeficiente de correlación para determinar la fuerza de la relación lineal entre el **precio** y las características físicas continuas/discretas **(area, hab, bano, parq_cant)**. _(Nota: Esta es una técnica estadística estándar para responder matemáticamente qué variable influye más en otra)._
- [ ] **Impacto de las comodidades:** Analizar cómo cambia el **precio** promedio al aumentar cada característica específica (ej. calcular la diferencia promedio de precio entre un apartamento de 1 baño vs. uno de 2 baños).
- [ ] **Comparación de variables (Ubicación vs. Tamaño):** Aislar grupos de apartamentos con características idénticas (ej. todos los de 2 habitaciones y 1 baño) y comparar la variabilidad de su precio únicamente en función del **barrio**.

# 5. Requerimiento transversal: Validación de tipos y métricas descriptivas

_"Validar los tipos de variables y que métricas se debe usar para su descriptiva"_

- [ ] **Variables Numéricas Continuas (_precio, area, baño_):** Validar que estén en formato _float_. Las métricas descriptivas obligatorias a aplicarles son: Media, Mediana, Mínimo, Máximo y Desviación Estándar.
- [ ] **Variables Numéricas Discretas (_hab, parq_cant_):** Validar que estén en formato _integer_ (entero). Las métricas descriptivas obligatorias son: Moda (valor más frecuente) y Frecuencias absolutas.
- [ ] **Variables Categóricas (_barrio_):** Validar que sea texto (_string_), sin espacios sobrantes ni diferencias entre mayúsculas y minúsculas. Las métricas descriptivas a usar son: Conteo de categorías únicas y Modas.

# Consultas adicionales

- [ ] Identificar si el numero antes del - tiene alguna coorelación con cant parq, habitaciones, barrio, publicante