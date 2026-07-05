"""
Moderacion y filtrado de contenido.

Cubre el requisito etico del enunciado: evitar la generacion de imagenes o
texto inapropiados o daninos. Se implementa un filtro basado en listas de
terminos prohibidos y patrones de riesgo. En un entorno de produccion, este
filtro se complementaria con los guardrails nativos de Amazon Bedrock o con un
servicio de moderacion dedicado; aqui se deja una base propia y transparente.
"""

import re

# Categorias de contenido que no se permite generar. La lista es ilustrativa y
# ampliable; el objetivo es demostrar el mecanismo de filtrado.
TERMINOS_PROHIBIDOS = [
    # violencia explicita
    "gore", "decapitacion", "masacre", "tortura",
    # contenido sexual explicito / abuso
    "pornografia", "explicito sexual", "abuso infantil", "menores desnudos",
    # odio / discriminacion
    "apologia nazi", "limpieza etnica",
    # actividades ilegales / peligrosas
    "fabricar explosivos", "fabricar armas", "instrucciones para bomba",
]

# Patrones adicionales (expresiones regulares) para casos que evaden palabras sueltas.
PATRONES_RIESGO = [
    # cualquier mencion de fabricar/hacer/construir + bomba/explosivo/arma
    r"\b(fabricar|hacer|construir|crear|elaborar)\s+.*\b(bomba|explosiv|arma)",
    r"\binstrucciones\s+para\s+.*\b(bomba|explosiv|matar|arma)",
    r"\bc[o0]mo\s+fabricar\s+(un[a]?\s+)?(bomba|explosiv)",
    r"\bda[nñ]ar\s+a\s+(alguien|una\s+persona)",
]


class ModeracionError(Exception):
    """Se lanza cuando el contenido no supera la moderacion."""

    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


def revisar_texto(texto: str) -> None:
    """
    Revisa un texto (prompt o contenido). Si detecta material prohibido, lanza
    ModeracionError. Si el texto es aceptable, no hace nada.
    """
    if not texto or not texto.strip():
        return

    minus = texto.lower()

    for termino in TERMINOS_PROHIBIDOS:
        if termino in minus:
            raise ModeracionError(
                f"El contenido fue bloqueado por la politica de uso responsable "
                f"(categoria detectada: '{termino}')."
            )

    for patron in PATRONES_RIESGO:
        if re.search(patron, minus):
            raise ModeracionError(
                "El contenido fue bloqueado por describir una actividad peligrosa o ilegal."
            )


def es_seguro(texto: str) -> bool:
    """Version booleana de revisar_texto (True si el texto es aceptable)."""
    try:
        revisar_texto(texto)
        return True
    except ModeracionError:
        return False
