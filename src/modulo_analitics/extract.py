import pandas as pd
from bs4 import BeautifulSoup

# --- 1. FUNCIONES DE EXTRACCIÓN (Obtienen texto crudo del HTML) ---

def get_href(card):
    try:
        return card.find_all("a")[0]["href"]
    except (IndexError, KeyError, AttributeError):
        return ""

def get_url_img(card):
    try:
        return card.find_all("img")[0]["src"]
    except (IndexError, AttributeError):
        return ""

def get_alt_img(card):
    try:
        return card.find_all("img")[0]["alt"]
    except (IndexError, AttributeError):
        return ""

def get_barrio(card):
    try:
        # Busca el contenedor de ubicación y extrae la parte antes del separador '|'
        container = card.find("div", class_="property-card__detail-top__left")
        texto = container.find("div").get_text(strip=True)
        return texto.split("|")[0].strip()
    except (AttributeError, IndexError):
        return "N/A"

def get_titulo(card):
    try:
        return card.find("div", class_="property-card__detail-title").find("h2").get_text(strip=True)
    except AttributeError:
        return "Sin título"

def get_precio_str(card):
    try:
        return card.find("div", class_="property-card__detail-price").get_text(strip=True)
    except AttributeError:
        return "$ 0"

def get_atributos(card):
    """Extrae la lista de textos de las etiquetas de características."""
    tags = card.find_all("div", class_="pt-main-specs--feature")
    return [t.get_text(strip=True) for t in tags]

# --- 2. FUNCIONES DE PROCESAMIENTO (Limpieza y conversión) ---

def get_precio(precio_str):
    """Convierte un string como '$1.500.000' en un entero 1500000."""
    if not precio_str:
        return 0
    # Quitamos todo lo que no sea número
    solo_numeros = "".join(filter(str.isdigit, precio_str))
    return int(solo_numeros) if solo_numeros else 0

def filtrar_atributos(lista_atributos):
    """Procesa la lista de textos ['45 m2', '2 hab'] y devuelve un diccionario."""
    esquema_salida = {
        "area": -1.0,
        "habitaciones": -1,
        "banos": -1.0,
        "parqueaderos": 0
    }
    
    for item in lista_atributos:
        item_lower = item.lower()
        partes = item_lower.split()
        if not partes:
            continue
            
        # El primer elemento suele ser el valor numérico
        valor_raw = partes[0].replace(",", ".")
        
        try:
            # El portal usa 'm²' (superindice) en el HTML real y 'm2' en otros
            # contextos; aceptamos ambos para no perder el area.
            if 'm2' in item_lower or 'm²' in item_lower:
                esquema_salida['area'] = float(valor_raw)
            elif 'hab' in item_lower:
                esquema_salida['habitaciones'] = int(float(valor_raw))
            elif 'bañ' in item_lower or 'ban' in item_lower:
                esquema_salida['banos'] = float(valor_raw)
            elif 'par' in item_lower:
                esquema_salida['parqueaderos'] = int(float(valor_raw))
        except ValueError:
            continue
            
    return esquema_salida

# --- 3. FUNCIONES INTEGRADORAS (Unen todo) ---

def get_esquema(card):
    """Compila toda la información de una tarjeta en un diccionario con nombres."""
    p_str = get_precio_str(card)
    lista_attr = get_atributos(card)
    res_attr = filtrar_atributos(lista_attr)
    
    return {
        "url": get_href(card),
        "url_img": get_url_img(card),
        "alt_img": get_alt_img(card),
        "barrio": get_barrio(card),
        "titulo": get_titulo(card),
        "precio_str": p_str,
        "precio": get_precio(p_str),
        "area": res_attr["area"],
        "habitaciones": res_attr["habitaciones"],
        "banos": res_attr["banos"],
        "parqueaderos": res_attr["parqueaderos"]
    }

def extraer_datos(html_content):
    """Función principal: Recibe HTML, devuelve DataFrame con nombres de columnas."""
    soup = BeautifulSoup(html_content, "html.parser")
    cards = soup.find_all("div", class_="property-card__container")
    
    lista_final = []
    for card in cards:
        info_dict = get_esquema(card)
        lista_final.append(info_dict)
    
    # Al ser una lista de diccionarios, Pandas usa las llaves como nombres de columnas
    return pd.DataFrame(lista_final)