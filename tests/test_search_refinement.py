import os
import sys
import logging
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.pubmed_searcher import PubmedSearcher
from agents.search_refiner import SearchRefiner

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "DEBUG"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def test_search_refinement():
    load_dotenv()
    searcher = PubmedSearcher()
    refiner = SearchRefiner()

    initial_query = '("TTFields" OR "Tumor Treating Fields") AND ("high grade glioma" OR glioblastoma)'
    target_results = 100
    user_query = "TTS field for high grade glioma"

    logger.info(f"Iniciando teste de refinamento - Query inicial: '{initial_query}'")

    abstracts, pmids, total_results = searcher.search_initial(initial_query)
    logger.info(f"Busca inicial - Total: {total_results}, PMIDs: {len(pmids)}")
    if not pmids:
        logger.error("Nenhum resultado na busca inicial")
        raise AssertionError("Busca inicial retornou zero resultados")

    logger.debug("Iniciando refinamento da query")
    refined_query = refiner.refine_search(initial_query, abstracts, user_query, total_results, target_results)
    logger.info(f"Query refinada: '{refined_query}'")

    abstracts_refined, pmids_refined, total_results_refined = searcher.search_refined(refined_query, abstracts)
    logger.info(f"Busca refinada - Total: {total_results_refined}, PMIDs: {len(pmids_refined)}")

    assert refined_query != initial_query, "Query não foi refinada"
    if total_results > target_results:
        assert total_results_refined < total_results, "Total de resultados deveria diminuir para se aproximar do alvo"
    else:
        assert total_results_refined > total_results, "Total de resultados deveria aumentar para se aproximar do alvo"
    logger.info("Teste de refinamento concluído com sucesso")

if __name__ == "__main__":
    try:
        test_search_refinement()
    except Exception as e:
        logger.error(f"Teste de refinamento falhou: {e}")
        sys.exit(1)
    logger.info("Todos os testes de refinamento passaram!")
    sys.exit(0)