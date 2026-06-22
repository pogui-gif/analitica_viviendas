"""
Agente evaluador de inversion inmobiliaria (soporte de IA del pipeline).

Consume las estadisticas ya limpias y procesadas (resumen_mercado y/o un
inmueble individual) y genera proyecciones y sugerencias estrategicas de
inversion en lenguaje natural.

Arquitectura: capa de proveedor desacoplada (patron Strategy).
    - LMStudioProvider : LLM local via API OpenAI-compatible (default).
    - AnthropicProvider: Claude via SDK oficial.
    - FallbackProvider : reglas deterministas, sin red. Garantiza que el
      pipeline SIEMPRE produzca un reporte aunque no haya LLM disponible.

El proveedor se elige con la variable de entorno LLM_PROVIDER
("lmstudio" | "anthropic" | "none"); ver config.py.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from . import config


# ===========================================================================
# Capa de proveedores LLM
# ===========================================================================
class LLMProvider(ABC):
    """Contrato minimo: dado un system + user prompt, devuelve texto."""

    nombre: str = "base"

    @abstractmethod
    def completar(self, system: str, user: str) -> str: ...

    def chat(self, system: str, mensajes: list) -> str:
        """Conversacion multi-turno. `mensajes` = [{'role','content'}, ...].

        Implementacion por defecto: usa el ultimo mensaje del usuario via
        completar(). Los proveedores que soportan historial la sobreescriben.
        """
        ultimo = next((m["content"] for m in reversed(mensajes) if m["role"] == "user"), "")
        return self.completar(system, ultimo)


class LMStudioProvider(LLMProvider):
    """LLM local servido por LM Studio (endpoint compatible con OpenAI)."""

    nombre = "lmstudio"

    def __init__(self) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Falta el cliente 'openai'. Instala con: pip install openai"
            ) from exc
        self._client = OpenAI(
            base_url=config.LMSTUDIO_BASE_URL,
            api_key=config.LMSTUDIO_API_KEY,
        )

    def completar(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=config.LMSTUDIO_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS,
        )
        return resp.choices[0].message.content or ""

    def chat(self, system: str, mensajes: list) -> str:
        resp = self._client.chat.completions.create(
            model=config.LMSTUDIO_MODEL,
            messages=[{"role": "system", "content": system}, *mensajes],
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS,
        )
        return resp.choices[0].message.content or ""


class AnthropicProvider(LLMProvider):
    """Claude via SDK oficial de Anthropic."""

    nombre = "anthropic"

    def __init__(self) -> None:
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError("Define ANTHROPIC_API_KEY para usar el proveedor 'anthropic'.")
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Falta el SDK 'anthropic'. Instala con: pip install anthropic"
            ) from exc
        self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def completar(self, system: str, user: str) -> str:
        resp = self._client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=config.LLM_MAX_TOKENS,
            temperature=config.LLM_TEMPERATURE,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(bloque.text for bloque in resp.content if bloque.type == "text")

    def chat(self, system: str, mensajes: list) -> str:
        resp = self._client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=config.LLM_MAX_TOKENS,
            temperature=config.LLM_TEMPERATURE,
            system=system,
            messages=mensajes,
        )
        return "".join(bloque.text for bloque in resp.content if bloque.type == "text")


class GeminiProvider(LLMProvider):
    """Google Gemini via SDK oficial google-genai (paquete soportado)."""

    nombre = "gemini"

    def __init__(self) -> None:
        if not config.GEMINI_API_KEY:
            raise RuntimeError("Define GEMINI_API_KEY (o GOOGLE_API_KEY) para usar 'gemini'.")
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Falta el SDK de Gemini. Instala con: pip install google-genai"
            ) from exc
        self._types = types
        self._client = genai.Client(api_key=config.GEMINI_API_KEY)

    def _config(self, system: str):
        return self._types.GenerateContentConfig(
            system_instruction=system,
            temperature=config.LLM_TEMPERATURE,
            max_output_tokens=config.LLM_MAX_TOKENS,
        )

    def completar(self, system: str, user: str) -> str:
        resp = self._client.models.generate_content(
            model=config.GEMINI_MODEL, contents=user, config=self._config(system),
        )
        return (resp.text or "").strip()

    def chat(self, system: str, mensajes: list) -> str:
        # Gemini usa 'user'/'model' como roles y 'parts' para el contenido.
        contents = [
            {"role": "user" if m["role"] == "user" else "model",
             "parts": [{"text": m["content"]}]}
            for m in mensajes
        ]
        resp = self._client.models.generate_content(
            model=config.GEMINI_MODEL, contents=contents, config=self._config(system),
        )
        return (resp.text or "").strip()


class FallbackProvider(LLMProvider):
    """Genera un analisis basado en reglas. No requiere red ni dependencias."""

    nombre = "fallback"

    def completar(self, system: str, user: str) -> str:  # noqa: ARG002
        # Extrae el/los objeto(s) JSON embebidos en el prompt sin asumir que el
        # texto termina en JSON (raw_decode lee solo el primer objeto valido).
        objetos = _extraer_jsons(user)
        if not objetos:
            return "No fue posible generar el analisis automatico (sin LLM disponible)."
        # Si el primer objeto es un inmueble (tiene precio/area pero no es un
        # resumen de mercado), es una evaluacion individual.
        primero = objetos[0]
        if "total_inmuebles" not in primero and {"precio", "area"} <= set(primero):
            mercado = next((o for o in objetos if "total_inmuebles" in o), {})
            return _evaluacion_reglas(primero, mercado)
        return _reporte_reglas(primero)

    def chat(self, system: str, mensajes: list) -> str:
        pregunta = next((m["content"] for m in reversed(mensajes) if m["role"] == "user"), "")
        objetos = _extraer_jsons(system)
        resumen = next((o for o in objetos if "total_inmuebles" in o), {})
        return _responder_reglas(pregunta, resumen)


def obtener_proveedor(forzar: Optional[str] = None) -> LLMProvider:
    """Fabrica de proveedores. Cae a Fallback si el elegido no esta disponible."""
    elegido = (forzar or config.LLM_PROVIDER).lower()
    try:
        if elegido == "anthropic":
            return AnthropicProvider()
        if elegido in ("gemini", "google"):
            return GeminiProvider()
        if elegido in ("lmstudio", "openai", "local"):
            return LMStudioProvider()
        if elegido in ("none", "fallback"):
            return FallbackProvider()
    except Exception as exc:  # noqa: BLE001
        print(f"  [agente] Proveedor '{elegido}' no disponible ({exc}). Uso fallback determinista.")
    return FallbackProvider()


# ===========================================================================
# Prompts y logica del agente
# ===========================================================================
SYSTEM_ANALISTA = (
    "Eres un analista senior de inversion inmobiliaria especializado en el "
    "mercado de arriendo de Bogota. Recibes estadisticas ya procesadas de "
    "ofertas reales de Metrocuadrado. Tu trabajo es interpretar los datos con "
    "rigor, sin inventar cifras que no esten en el insumo, y entregar "
    "recomendaciones accionables. Responde SIEMPRE en espanol y en formato "
    "Markdown."
)

SYSTEM_CHATBOT = (
    "Eres un asesor inmobiliario virtual experto en el mercado de arriendo de "
    "Bogota, que apoya la toma de decisiones de personas que buscan dónde vivir o "
    "invertir. Tu objetivo es ORIENTAR con claridad segun la condicion economica y "
    "las necesidades del usuario.\n\n"
    "Reglas:\n"
    "1. Apoyate en el contexto de mercado (JSON) que recibes abajo. Usa cifras "
    "concretas (canon mediano, valor/m2, correlaciones, barrios) para respaldar "
    "cada afirmacion.\n"
    "2. Si el usuario menciona un presupuesto o ingreso, recomienda un rango de "
    "canon sensato (idealmente <= 30% del ingreso) y sugiere barrios/segmentos "
    "que se ajusten.\n"
    "3. Estructura respuestas elaboradas pero legibles: una conclusion breve al "
    "inicio, luego 2-4 puntos con el porque, y un siguiente paso accionable.\n"
    "4. Explica el razonamiento (por que un barrio conviene, que se gana/sacrifica). "
    "Compara opciones cuando sea util.\n"
    "5. Si algo no esta en los datos, dilo con honestidad; no inventes cifras.\n"
    "Responde SIEMPRE en espanol y en formato Markdown."
)


def _extraer_jsons(texto: str) -> list[Dict[str, Any]]:
    """Devuelve todos los objetos JSON de nivel superior embebidos en `texto`."""
    decoder = json.JSONDecoder()
    objetos: list[Dict[str, Any]] = []
    i = 0
    while i < len(texto):
        if texto[i] == "{":
            try:
                obj, fin = decoder.raw_decode(texto, i)
                if isinstance(obj, dict):
                    objetos.append(obj)
                i = fin
                continue
            except json.JSONDecodeError:
                pass
        i += 1
    return objetos


def _evaluacion_reglas(inmueble: Dict[str, Any], mercado: Dict[str, Any]) -> str:
    """Evaluacion determinista de un inmueble frente al mercado (sin LLM)."""
    precio = inmueble.get("precio") or 0
    area = inmueble.get("area") or 0
    valor_m2 = inmueble.get("valor_m2") or (precio / area if area else 0)
    barrio = inmueble.get("barrio", "N/D")

    # Referencia de mercado: mediana de valor/m2 (de ranking si esta disponible)
    ranking = mercado.get("ranking_valor_m2_top", [])
    valores = [r.get("mediana_valor_m2", 0) for r in ranking if r.get("mediana_valor_m2")]
    ref_m2 = (sorted(valores)[len(valores) // 2] if valores
              else mercado.get("precio", {}).get("mediana", 0) / max(mercado.get("area_mediana", 1), 1))

    if ref_m2 and valor_m2:
        delta = (valor_m2 - ref_m2) / ref_m2 * 100
        if delta < -10:
            veredicto, posicion = "Comprar", f"{abs(delta):.0f}% por DEBAJO"
        elif delta > 10:
            veredicto, posicion = "Negociar", f"{delta:.0f}% por ENCIMA"
        else:
            veredicto, posicion = "Negociar", "en linea con"
    else:
        veredicto, posicion = "Descartar", "sin referencia de"

    return (
        f"### Evaluación — {barrio} (`{inmueble.get('id', 's/id')}`)\n"
        f"- Canon: **${precio:,.0f}** · Área: **{area} m²** · "
        f"Valor/m²: **${valor_m2:,.0f}**\n"
        f"- Está **{posicion}** el valor/m² típico del mercado.\n"
        f"- Habitaciones: {inmueble.get('habitaciones', '?')} · "
        f"Baños: {inmueble.get('banos', '?')} · "
        f"Parqueaderos: {inmueble.get('parqueaderos', '?')}\n"
        f"- **Recomendación: {veredicto}.**"
    )


def _responder_reglas(pregunta: str, resumen: Dict[str, Any]) -> str:
    """Responde una pregunta del chat por reglas (sin LLM), usando el resumen.

    Detecta la intencion por palabras clave y arma una respuesta con cifras del
    contexto. Es un respaldo: con LM Studio o Claude la conversacion es natural.
    """
    if not resumen:
        return ("No tengo datos cargados en este momento. Genera el análisis del "
                "mercado primero para poder responder con cifras.")

    q = pregunta.lower()
    p = resumen.get("precio", {})
    corr = {k: v for k, v in (resumen.get("correlaciones_precio", {}) or {}).items() if k != "precio"}
    ranking = resumen.get("ranking_valor_m2_top", [])
    oferta = resumen.get("top_barrios_oferta", [])

    # NOTA: el orden va de intencion MAS ESPECIFICA a mas general (p.ej. "influye
    # en el precio" o "m2 mas caro" no deben caer en la rama generica de precio).

    # --- Intencion: que influye en el precio / correlacion ---
    if any(w in q for w in ["influye", "determina", "correlac", "factor", "depende", "afecta"]):
        if corr:
            top = max(corr, key=lambda k: abs(corr[k]))
            orden = ", ".join(f"{k} (r={v:.2f})" for k, v in sorted(corr.items(), key=lambda kv: -abs(kv[1])))
            return (f"Lo que más explica el precio es **{top}** (r={corr[top]:.2f}). "
                    f"Orden de influencia: {orden}.")
        return "No tengo la matriz de correlación en el contexto actual."

    # --- Intencion: valor m2 ---
    if "m2" in q or "m²" in q or "metro cuadrado" in q:
        if ranking:
            return (f"Valor del m² (mediana por barrio): más caro **{ranking[0]['barrio']}** "
                    f"(${ranking[0].get('mediana_valor_m2',0):,.0f}/m²), más económico "
                    f"**{ranking[-1]['barrio']}** (${ranking[-1].get('mediana_valor_m2',0):,.0f}/m²).")
        return "No tengo el ranking de valor/m² en el contexto actual."

    # --- Intencion: donde invertir / oportunidad ---
    if any(w in q for w in ["invertir", "invers", "oportunidad", "recomiend", "donde", "dónde", "conviene"]):
        premium = ranking[0]["barrio"] if ranking else "N/D"
        economico = ranking[-1]["barrio"] if ranking else "N/D"
        return (f"Depende de tu objetivo:\n"
                f"- **Flujo de caja / mejor precio por m²**: {economico} (m² más económico).\n"
                f"- **Valorización / zona premium**: {premium} (m² más costoso).\n"
                f"- **Liquidez (más oferta)**: {oferta[0]['barrio'] if oferta else 'N/D'}.")

    # --- Intencion: barrios / zonas ---
    if any(w in q for w in ["barrio", "zona", "sector", "ubicac"]):
        tops = ", ".join(f"{o['barrio']} ({o.get('Cantidad de ofertas', o.get('count','?'))})" for o in oferta[:5])
        return (f"Hay **{resumen.get('total_barrios','?')} barrios** en la muestra. "
                f"Los de mayor oferta: {tops}.")

    # --- Intencion: precio / canon (generica) ---
    if any(w in q for w in ["precio", "canon", "arriendo", "cuesta", "vale", "caro", "barato"]):
        return (f"En la muestra ({resumen.get('total_inmuebles','?')} inmuebles) el "
                f"**canon mediano** es **${p.get('mediana',0):,.0f}** "
                f"(promedio ${p.get('media',0):,.0f}), con un rango de "
                f"${p.get('min',0):,.0f} a ${p.get('max',0):,.0f}. "
                "La mediana es la referencia más confiable porque no se infla con casos extremos.")

    # --- Respuesta por defecto ---
    return ("Puedo ayudarte con: precios/canon, qué factores influyen en el precio, "
            "dónde invertir, barrios con más oferta y valor del m². "
            "¿Sobre cuál quieres profundizar? "
            "(Para conversación abierta, activa LM Studio o Claude.)")


def _reporte_reglas(resumen: Dict[str, Any]) -> str:
    """Reporte determinista de respaldo a partir del resumen de mercado."""
    p = resumen.get("precio", {})
    corr = resumen.get("correlaciones_precio", {}) or {}
    # Variable mas correlacionada con precio (excluyendo el propio precio)
    drivers = {k: v for k, v in corr.items() if k != "precio"}
    driver_top = max(drivers, key=lambda k: abs(drivers[k])) if drivers else "area"

    top_oferta = resumen.get("top_barrios_oferta", [])
    barrio_lider = top_oferta[0].get("barrio") if top_oferta else "N/D"

    ranking_m2 = resumen.get("ranking_valor_m2_top", [])
    premium = ranking_m2[0].get("barrio") if ranking_m2 else "N/D"
    economico = ranking_m2[-1].get("barrio") if ranking_m2 else "N/D"

    lineas = [
        "# Reporte de Inversion Inmobiliaria (analisis determinista)",
        "",
        "> Generado sin LLM (proveedor de respaldo). Para narrativa enriquecida, "
        "configura LM Studio o Claude.",
        "",
        "## 1. Panorama del mercado",
        f"- Inmuebles analizados: **{resumen.get('total_inmuebles', 'N/D')}** "
        f"en **{resumen.get('total_barrios', 'N/D')}** barrios.",
        f"- Canon mediano: **${p.get('mediana', 0):,.0f}** "
        f"(media ${p.get('media', 0):,.0f}, rango ${p.get('min', 0):,.0f}–${p.get('max', 0):,.0f}).",
        f"- Area mediana: **{resumen.get('area_mediana', 'N/D')} m2**.",
        "",
        "## 2. Factor que mas influye en el precio",
        f"- La variable mas correlacionada con el canon es **{driver_top}** "
        f"(r={drivers.get(driver_top, 0):.2f}).",
        "",
        "## 3. Oportunidades por valorizacion (valor/m2)",
        f"- Zona mas premium (m2 mas caro): **{premium}**.",
        f"- Mejor relacion espacio/precio (m2 mas economico): **{economico}**.",
        f"- Barrio con mayor volumen de oferta: **{barrio_lider}** "
        "(mayor liquidez para arrendar/revender).",
        "",
        "## 4. Sugerencia estrategica",
        f"- Para **flujo de caja**: priorizar barrios de m2 economico ({economico}) "
        "con buena demanda.",
        f"- Para **valorizacion de capital**: exposicion a zonas premium ({premium}).",
        f"- Negociar al alza el atributo **{driver_top}**, que es el que mejor "
        "explica el precio en esta muestra.",
    ]
    return "\n".join(lineas)


# ===========================================================================
# API publica del agente
# ===========================================================================
class AgenteInmobiliario:
    """Agente evaluador que consume el resumen de mercado del pipeline."""

    def __init__(self, proveedor: Optional[LLMProvider] = None) -> None:
        self.proveedor = proveedor or obtener_proveedor()

    # --- Reporte de mercado ------------------------------------------------
    def generar_reporte_mercado(self, resumen_mercado: Dict[str, Any]) -> str:
        """Genera proyecciones y sugerencias de inversion a nivel mercado."""
        user = (
            "Analiza el siguiente resumen estadistico del mercado de arriendo en "
            "Bogota y entrega: (1) panorama general, (2) que caracteristica "
            "fisica influye mas en el precio y por que, (3) 3 barrios con mejor "
            "oportunidad de inversion justificados con las cifras, (4) riesgos a "
            "vigilar y (5) una proyeccion cualitativa.\n\n"
            "Datos (JSON):\n" + json.dumps(resumen_mercado, ensure_ascii=False, indent=2)
        )
        return self.proveedor.completar(SYSTEM_ANALISTA, user)

    # --- Evaluacion de un inmueble individual ------------------------------
    def evaluar_inmueble(self, inmueble: Dict[str, Any], resumen_mercado: Dict[str, Any]) -> str:
        """Evalua una propiedad concreta contra el contexto de mercado."""
        user = (
            "Evalua si el siguiente inmueble es una buena oportunidad de "
            "inversion comparado con su mercado. Indica si esta por encima o por "
            "debajo del precio/m2 tipico de la muestra, fortalezas, debilidades y "
            "una recomendacion (Comprar / Negociar / Descartar).\n\n"
            f"Inmueble (JSON):\n{json.dumps(inmueble, ensure_ascii=False, default=str, indent=2)}\n\n"
            f"Contexto de mercado (JSON):\n{json.dumps(resumen_mercado, ensure_ascii=False, indent=2)}"
        )
        return self.proveedor.completar(SYSTEM_ANALISTA, user)

    # --- Chatbot conversacional --------------------------------------------
    def responder_chat(self, historial: list, resumen_mercado: Dict[str, Any]) -> str:
        """Responde en modo chat usando el contexto de mercado y el historial.

        `historial` es una lista de turnos [{'role': 'user'|'assistant',
        'content': str}, ...]. El contexto de mercado se inyecta en el system
        prompt para que las respuestas esten ancladas a los datos vigentes.
        """
        system = (
            SYSTEM_CHATBOT
            + "\n\nContexto de mercado (JSON):\n"
            + json.dumps(resumen_mercado, ensure_ascii=False, indent=2)
        )
        return self.proveedor.chat(system, historial)


# ===========================================================================
# Helpers de alto nivel (usados por main.py)
# ===========================================================================
def generar_y_guardar_reporte(resumen_mercado: Dict[str, Any],
                              proveedor: Optional[str] = None,
                              fecha: Optional[str] = None) -> Path:
    """Genera el reporte de mercado y lo persiste en data/processed/reports/."""
    config.asegurar_directorios()
    agente = AgenteInmobiliario(obtener_proveedor(proveedor))
    print(f"  [agente] Proveedor activo: {agente.proveedor.nombre}")
    reporte = agente.generar_reporte_mercado(resumen_mercado)

    fecha = fecha or datetime.now().strftime("%Y-%m-%d")
    destino = config.REPORTS_DIR / f"reporte_inversion_{fecha}.md"
    destino.write_text(reporte, encoding="utf-8")
    print(f"  [agente] Reporte guardado en: {destino}")
    return destino


def evaluar_top_inmuebles(df: pd.DataFrame, resumen_mercado: Dict[str, Any],
                          n: int = 3, proveedor: Optional[str] = None) -> str:
    """Evalua los N inmuebles mas economicos por valor/m2 como ejemplo accionable."""
    agente = AgenteInmobiliario(obtener_proveedor(proveedor))
    trabajo = df.copy()
    if "valor_m2" not in trabajo.columns:
        trabajo["valor_m2"] = pd.to_numeric(trabajo["precio"], errors="coerce") / \
            pd.to_numeric(trabajo["area"], errors="coerce")
    candidatos = trabajo.dropna(subset=["valor_m2"]).nsmallest(n, "valor_m2")

    partes = []
    for _, fila in candidatos.iterrows():
        inmueble = fila[[c for c in config.COLUMNAS_LIMPIAS if c in fila.index] + ["valor_m2"]].to_dict()
        partes.append(agente.evaluar_inmueble(inmueble, resumen_mercado))
    return "\n\n---\n\n".join(partes)
