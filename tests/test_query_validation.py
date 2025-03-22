import os
import sys
import logging
from dotenv import load_dotenv

# Adicionar o diretório raiz do projeto ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.query_validator import QueryValidator, QueryValidationError

# Configuração do logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "DEBUG"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def test_query_validation():
    load_dotenv()
    validator = QueryValidator()

    test_cases = [
        {
            "query": "TTS field for high grade glioma",
            "expected_success": True,
            "description": "Query válida com população e intervenção"
        },
        {
            "query": "glioma",
            "expected_success": True,  # Mesmo que vaga, o validador aceita e refina
            "description": "Query vaga, mas válida"
        },
        {
            "query": "",
            "expected_success": False,
            "description": "Query vazia"
        }
    ]

    logger.info("Iniciando testes de validação de query")
    for i, case in enumerate(test_cases, 1):
        logger.info(f"Teste {i}: {case['description']} - Query: '{case['query']}'")
        try:
            validated_query = validator.validate_query(case["query"])
            logger.debug(f"Query validada: '{validated_query}'")
            if case["expected_success"]:
                logger.info(f"Teste {i} passou - Query válida como esperado")
            else:
                logger.error(f"Teste {i} falhou - Query inválida deveria ter gerado erro")
                raise AssertionError("Esperava falha, mas passou")
        except QueryValidationError as e:
            logger.debug(f"Erro na validação: {e}")
            if not case["expected_success"]:
                logger.info(f"Teste {i} passou - Query inválida detectada como esperado")
            else:
                logger.error(f"Teste {i} falhou - Query válida gerou erro inesperado: {e}")
                raise

if __name__ == "__main__":
    try:
        test_query_validation()
    except Exception as e:
        logger.error(f"Teste de validação falhou: {e}")
        sys.exit(1)
    logger.info("Todos os testes de validação passaram!")
    sys.exit(0)