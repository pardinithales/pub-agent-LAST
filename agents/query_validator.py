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
        
        # Hotfix aplicado ANTES de enviar ao Claude
        if "TTS" in user_query:
            user_query = user_query.replace("TTS", "Tumor Treating Fields (TTFields)")
            logger.debug(f"Query ajustada manualmente antes do LLM: {user_query}")
        
        prompt = f"""
        Recebi a seguinte query do usuário: "{user_query}"
        Sua tarefa é transformá-la em uma query inicial para o PubMed:
        - Identifique os conceitos principais: população (ex.: doenças, condições) e intervenção (ex.: tratamentos, terapias).
        - Adicione sinônimos ou termos relacionados básicos com "OR" e agrupe com parênteses para cada conceito.
        - Combine os conceitos com "AND" para manter a lógica.
        - Use aspas para termos compostos (ex.: "high grade glioma").
        - Não adicione filtros de tipo de estudo, ano, espécie, outcomes ou comparadores, a menos que explicitamente mencionados na query.
        - Se a query não contiver população ou intervenção claras, apenas estruture os termos presentes da melhor forma possível usando operadores OR para sinônimos e AND para conceitos diferentes.
        - Retorne apenas a query formatada para o PubMed, sem explicações adicionais.
        
        IMPORTANTE: Aceite qualquer query do usuário mesmo que não seja específica ou não contenha claramente uma população e intervenção.
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
            
            # Verificar se a resposta tem um formato minimamente válido (contém parênteses)
            if not response or "(" not in response or ")" not in response:
                logger.warning("LLM não gerou uma query estruturada válida, aplicando estruturação básica")
                # Estruturação básica da query original em vez de fallback genérico
                terms = user_query.split()
                structured_query = "(" + " OR ".join([term for term in terms if len(term) > 3]) + ")"
                logger.info(f"Query estruturada manualmente: {structured_query}")
                return structured_query
                
            return response
            
        except APIError as e:
            logger.error(f"Erro na API Anthropic: {e}")
            # Em vez de levantar erro, tenta estruturar a query original
            try:
                terms = user_query.split()
                structured_query = "(" + " OR ".join([term for term in terms if len(term) > 3]) + ")"
                logger.info(f"Falha na API, query estruturada manualmente: {structured_query}")
                return structured_query
            except:
                logger.error("Falha ao estruturar query manualmente")
                raise QueryValidationError("Erro ao processar a query com a API")
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            raise QueryValidationError("Erro desconhecido ao validar a query")

def validate_and_raise(query):
    """
    Valida a query e retorna a query formatada.
    Se a query for inválida, lança QueryValidationError.
    Aceita qualquer consulta que tenha conteúdo, mesmo que genérica.
    """
    logger.info(f"Função validate_and_raise chamada com query: '{query}'")
    
    if not query or query.strip() == "":
        logger.error("Query vazia detectada em validate_and_raise")
        raise QueryValidationError("A query não pode ser vazia")
    
    # É uma consulta minimalista mas válida (só tem um termo)
    if len(query.split()) == 1 and len(query) >= 3:
        logger.info(f"Query minimalista detectada: '{query}', estruturando manualmente")
        return f"({query})"
    
    validator = QueryValidator()
    result = validator.validate_query(query)
    logger.info(f"Query foi validada e retornou: '{result}'")
    return result