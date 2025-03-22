from anthropic import Anthropic, APIError
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class QueryValidationError(Exception):
    pass

class QueryValidator:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY não definida no .env")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-7-sonnet-20250219"

    def validate_query(self, user_query):
        if not user_query or user_query.strip() == "":
            logger.error("Query vazia ou inválida fornecida")
            raise QueryValidationError("A query não pode ser vazia")
        
        prompt = f"""
        Recebi a seguinte query do usuário: "{user_query}"
        Sua tarefa é transformá-la em uma query inicial genérica para o PubMed:
        - Identifique os conceitos principais: população (ex.: doenças, condições) e intervenção (ex.: tratamentos, terapias).
        - Adicione sinônimos ou termos relacionados básicos com "OR" e agrupe com parênteses para cada conceito.
        - Combine população e intervenção com "AND" para manter a lógica.
        - Use aspas para termos compostos (ex.: "high grade glioma").
        - Não adicione filtros de tipo de estudo, ano, espécie, outcomes ou comparadores, a menos que explicitamente mencionados na query.
        - Retorne apenas a query no formato pronto para o PubMed, sem explicações, com parênteses corretos.
        """
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.8,
                messages=[{"role": "user", "content": prompt}]
            )
            response = message.content[0].text.strip()
            logger.debug(f"Query inicial gerada pelo LLM: {response}")
            if not response:
                raise QueryValidationError("LLM não gerou uma query válida")
            # Hotfix para TTS -> TTFields
            if "TTS" in user_query and "TTFields" not in response:
                response = response.replace('"TTS"', '"TTFields" OR "Tumor Treating Fields"')
                logger.debug(f"Query ajustada manualmente: {response}")
            return response
        except APIError as e:
            logger.error(f"Erro na API Anthropic: {e}")
            raise QueryValidationError("Erro ao processar a query com a API")
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            raise QueryValidationError("Erro desconhecido ao validar a query")

def validate_and_raise(query):
    validator = QueryValidator()
    return validator.validate_query(query)