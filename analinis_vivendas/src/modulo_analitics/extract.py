import pandas as pd
from bs4 import BeautifulSoup

def get_href(card):
    href = card.find_all("a")["href"]
    return href

def get_url_img(card):
    url_img = card.find_all("img")["src"]
    return url_img

def get_alt_img(card):
    alt_img = card.find_all("img")["alt"]
    return alt_img

def get_barrio(card):
    barrio = card.find_all("div", class_="property-card__detail-top__left").find_all("div").get_text(strip=True).split("|")
    return barrio

def get_titulo(card):
    titulo = card.find_all("div", class_="property-card__detail-title").find_all("h2").get_text(strip=True)
    return titulo

def get_precio_str(card):
    precio_str = card.find_all("div", class_="property-card__detail-price").get_text(strip=True)
    return precio_str

def get_precio(precio_str):
    precio = int(precio_str.replace("$", "").replace(".", ""))
    return precio

def get_atributos(card):
    atributos = card.find_all("div", class_="pt-main-specs--feature")
    list_atributos = [a.get_text(strip=True) for a in atributos]
    return list_atributos

def filtrar_atributos(lista_atributos):
    esquema_salida = {
        "area": -1,
        "habitaciones": -1,
        "banos": -1,
        "parqueaderos": 0
    }
    
    for item in lista_atributos:
        if 'm2' in item:
            esquema_salida['area'] = float(item.split().replace(",", "."))
        elif 'hab' in item:
            esquema_salida['habitaciones'] = int(item.split())
        elif 'bañ' in item:
            esquema_salida['banos'] = float(item.split())
        elif 'par' in item:
            esquema_salida['parqueaderos'] = int(item.split())
            
    return esquema_salida

def get_area(resultado_filtro):
    return resultado_filtro["area"]

def get_habitaciones(resultado_filtro):
    return resultado_filtro["habitaciones"]

def get_bano(resultado_filtro):
    return resultado_filtro["banos"]

def get_parq_cant(resultado_filtro):
    return resultado_filtro["parqueaderos"]

def get_esquema(card):
    href = get_href(card)
    url_img = get_url_img(card)
    alt_img = get_alt_img(card)
    barrio = get_barrio(card)
    titulo = get_titulo(card)
    precio_str = get_precio_str(card)
    lista_atributos = get_atributos(card)
    resultado_filtro = filtrar_atributos(lista_atributos)
    area = get_area(resultado_filtro)
    hab = get_habitaciones(resultado_filtro)
    bano = get_bano(resultado_filtro)
    parq_cant = get_parq_cant(resultado_filtro)
    precio = get_precio(precio_str)
    
    return [href, url_img, alt_img, barrio, titulo, precio_str, precio, area, hab, bano, parq_cant]

def extraer_datos(html_content):
    """
    Función principal del módulo: Lee el HTML, extrae las tarjetas
    y retorna el DataFrame inicial.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    cards = soup.find_all("div", class_="property-card__container")
    
    datos = []
    for card in cards:
        formato = get_esquema(card)
        datos.append(formato)
        
    df = pd.DataFrame(datos)
    return df