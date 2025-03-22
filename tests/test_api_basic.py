import os
import sys
import logging
import requests
from dotenv import load_dotenv

# Adicionar o diretório raiz do projeto ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configuração do logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "DEBUG"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def test_api_basic():
    load_dotenv()
    url = "http://localhost:8000/api/search"
    payload = {
        "picott_text": "TTS field for high grade glioma",
        "target_results": 100,
        "max_iterations": 5
    }
    headers = {"Content-Type": "application/json"}

    logger.info(f"Iniciando teste básico da API - URL: {url}")
    logger.debug(f"Payload da requisição: {payload}")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()

        logger.info(f"Resposta recebida - Status: {response.status_code}, Total resultados: {result['total_results']}")
        logger.debug(f"Query retornada: {result['query']}")
        logger.debug(f"Primeiro resultado (PMID: {result['results'][0]['pmid']}): {result['results'][0]['abstract'][:100]}...")

        assert "query" in result, "Campo 'query' ausente na resposta"
        assert "results" in result, "Campo 'results' ausente na resposta"
        assert "total_results" in result, "Campo 'total_results' ausente na resposta"
        assert len(result["results"]) > 0, "Nenhum resultado retornado"
        logger.info("Teste básico da API concluído com sucesso")

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição à API: {e}")
        raise
    except AssertionError as e:
        logger.error(f"Falha na validação da resposta: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        raise

if __name__ == "__main__":
    try:
        test_api_basic()
    except Exception as e:
        logger.error(f"Teste falhou: {e}")
        sys.exit(1)
    logger.info("Todos os testes passaram!")
    sys.exit(0)