"""
Módulo de traducción de subtítulos y textos para Voizy.
"""

import time
from deep_translator import GoogleTranslator
from utils.logger import log_exception


class SubtitleTranslator:
    def __init__(self, target_lang, source_lang="auto", retries=3):
        self.target_lang = target_lang
        self.source_lang = source_lang
        self.retries = retries
        self.translator = GoogleTranslator(source=source_lang, target=target_lang)

    def traducir_texto(self, texto):
        """Traduce un fragmento de texto con reintentos automáticos y fallback al texto original."""
        texto_limpio = (texto or "").strip()
        if not texto_limpio:
            return texto, True

        for intento in range(self.retries):
            try:
                resultado = self.translator.translate(texto_limpio)
                if resultado:
                    return resultado.strip(), True
            except Exception as e:
                if intento < self.retries - 1:
                    time.sleep(0.5 * (intento + 1))
                else:
                    log_exception(f"Fallo de traducción para '{texto_limpio[:30]}...'", e)

        return texto_limpio, False

