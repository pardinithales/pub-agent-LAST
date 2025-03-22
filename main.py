# C:\Users\Usuario\Desktop\projetos\PUBMED_CREW\main.py
import os
import logging
from dotenv import load_dotenv
from agents.query_validator import QueryValidator, QueryValidationError
from agents.pubmed_searcher import PubmedSearcher
from agents.search_refiner import SearchRefiner

load_dotenv()

required_vars = ["ANTHROPIC_API_KEY", "PUBMED_EMAIL"]
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"Variável de ambiente {var} não definida no .env")

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

def main():
    user_query = input("Digite sua query: ")
    logger.info(f"Query recebida: {user_query}")
    
    validator = QueryValidator()
    searcher = PubmedSearcher()
    refiner = SearchRefiner()

    try:
        validated_query = validator.validate_query(user_query)
        logger.info(f"Query validada e traduzida: {validated_query}")
    except QueryValidationError as e:
        logger.error(f"Erro na validação da query: {e}")
        print(f"Erro: {e}")
        return

    # Busca inicial
    abstracts, pmids, total_results = searcher.search_initial(validated_query, 10)
    
    if not pmids:
        logger.warning("Nenhum resultado na busca inicial.")
        print("Nenhum resultado encontrado para a query inicial.")
        return

    logger.info(f"Busca inicial - {len(abstracts)} abstracts de {total_results} resultados.")
    print(f"Encontrados {total_results} resultados no total, analisando {len(abstracts)} abstracts.")

    current_query = validated_query
    iteration = 0
    max_iterations = 3
    target_results = 100

    while iteration < max_iterations:
        iteration += 1
        logger.info(f"Iteração {iteration}/{max_iterations} - Total: {total_results}, Target: {target_results}")
        
        # Verifica se já está próximo do alvo
        if 0.5 * target_results <= total_results <= 1.5 * target_results:
            logger.info(f"Total de resultados {total_results} já está próximo do alvo {target_results}, parando refinamento")
            break
            
        refined_query = refiner.refine_search(current_query, abstracts, user_query, total_results, target_results)

        if refined_query == current_query:
            logger.info(f"Query estabilizada na iteração {iteration}")
            break

        logger.info(f"Query refinada: {refined_query}")
        current_query = refined_query
        
        # Executa a busca com a nova query
        abstracts, pmids, total_results = searcher.search_refined(current_query, abstracts, 10)
        logger.info(f"Busca refinada - Total: {total_results}, PMIDs: {len(pmids)}")

    # Apresentação dos resultados
    print(f"\nQuery final para o PubMed:\n{current_query}")
    print(f"\nTotal de resultados: {total_results}")
    
    if pmids:
        print("\nAmostras de resultados:")
        for i, abstract in enumerate(abstracts[:5], 1):
            print(f"\n{i}. PMID: {abstract['pmid']}")
            preview = abstract["abstract"][:200] + "..." if len(abstract["abstract"]) > 200 else abstract["abstract"]
            print(f"Abstract: {preview}")

if __name__ == "__main__":
    main()