import os
import sys
import logging
import random
from dotenv import load_dotenv

# Adicionar o diretório raiz do projeto ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.pubmed_api import PubmedAPI

# Configuração do logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

def get_random_abstracts(query, num_abstracts=10, retmax=500):
    """
    Retorna um número especificado de abstracts aleatórios para uma query no PubMed.
    
    Args:
        query (str): A query de busca no formato PubMed.
        num_abstracts (int): Número de abstracts a retornar (padrão: 10).
        retmax (int): Número máximo de PMIDs a recuperar por chamada (padrão: 500).
    
    Returns:
        list: Lista de dicionários com PMID e abstract.
    """
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Verificar se PUBMED_EMAIL está definido
    if not os.getenv("PUBMED_EMAIL"):
        logger.error("PUBMED_EMAIL não definida no .env")
        raise ValueError("PUBMED_EMAIL não definida no .env")
    
    # Instanciar a API do PubMed
    pubmed_api = PubmedAPI()
    
    # Obter o total de resultados
    total_results = pubmed_api.count_results(query)
    logger.info(f"Total de resultados encontrados: {total_results}")
    
    if total_results == 0:
        logger.warning("Nenhum artigo encontrado para a query.")
        return []

    # Buscar PMIDs (limitado por retmax)
    pmids = pubmed_api.esearch(query, retmax=min(retmax, total_results))
    logger.info(f"Recuperados {len(pmids)} PMIDs (limite: {retmax}) de um total de {total_results}.")

    if not pmids:
        logger.warning("Nenhum PMID retornado na busca.")
        return []

    # Selecionar 10 PMIDs aleatoriamente
    selected_pmids = random.sample(pmids, min(num_abstracts, len(pmids)))
    logger.info(f"Selecionados {len(selected_pmids)} PMIDs aleatoriamente: {selected_pmids}")

    # Buscar abstracts para os PMIDs selecionados
    abstract_list = pubmed_api.efetch_abstracts(selected_pmids)
    logger.info(f"Recuperados {len(abstract_list)} abstracts.")

    return abstract_list

if __name__ == "__main__":
    # Query fixa baseada no resultado anterior
    sample_query = "(\"high grade glioma\"[tiab] OR HGG[tiab] OR \"high-grade glioma\"[tiab] OR GBM[tiab]) AND (TTS[tiab] OR \"tumor treating fields\"[tiab] OR \"tumour treating fields\"[tiab] OR \"alternating electric fields\"[tiab] OR Optune[tiab] OR TTF[tiab])"
    
    # Obter 10 abstracts aleatórios
    random_abstracts = get_random_abstracts(sample_query, num_abstracts=10)
    
    # Exibir os resultados
    print(f"\nEncontrados {len(random_abstracts)} abstracts aleatórios de um total de 243:\n")
    for i, result in enumerate(random_abstracts, 1):
        print(f"{i}. PMID: {result['pmid']}")
        print(f"Abstract: {result['abstract']}\n")