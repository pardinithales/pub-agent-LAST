import os
import sys
import logging
from dotenv import load_dotenv

# Adicionar o diretório raiz do projeto ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.pubmed_api import PubmedAPI

# Configuração do logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

def count_pubmed_articles(query):
    """
    Retorna o número total de artigos no PubMed para uma dada query.
    
    Args:
        query (str): A query de busca no formato PubMed.
    
    Returns:
        int: Número total de artigos encontrados.
    """
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Verificar se PUBMED_EMAIL está definido
    if not os.getenv("PUBMED_EMAIL"):
        logger.error("PUBMED_EMAIL não definida no .env")
        raise ValueError("PUBMED_EMAIL não definida no .env")
    
    # Instanciar a API do PubMed
    pubmed_api = PubmedAPI()
    
    # Contar os resultados
    try:
        total_results = pubmed_api.count_results(query)
        logger.info(f"Query: '{query}' retornou {total_results} artigos.")
        return total_results
    except Exception as e:
        logger.error(f"Erro ao contar artigos: {e}")
        return 0

if __name__ == "__main__":
    # Exemplo de query
    sample_query = "(\"high grade glioma\"[tiab] OR HGG[tiab] OR \"high-grade glioma\"[tiab] OR GBM[tiab]) AND (TTS[tiab] OR \"tumor treating fields\"[tiab] OR \"tumour treating fields\"[tiab] OR \"alternating electric fields\"[tiab] OR Optune[tiab] OR TTF[tiab])"
    
    # Executar a função e exibir o resultado
    result = count_pubmed_articles(sample_query)
    print(f"Número de artigos encontrados: {result}")