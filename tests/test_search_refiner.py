# Código completo ajustado
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import logging
from agents.search_refiner import SearchRefiner
from agents.pubmed_searcher import PubmedSearcher
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def test_refine_search_with_real_time_abstracts():
    print("Iniciando teste com abstracts reais obtidos em tempo real da API PubMed...")
    
    original_query = "TTS field for high grade glioma"
    current_query = '("high grade glioma" OR HGG OR "high-grade glioma" OR GBM) AND (TTS OR "tumor treating fields" OR "tumour treating fields" OR "alternating electric fields" OR Optune OR TTF)'
    target_results = 100
    max_returned_results = 10
    
    logger.info("Starting test of SearchRefiner with real-time PubMed abstracts")
    logger.debug(f"Original query: '{original_query}'")
    logger.debug(f"Current query: '{current_query}'")
    logger.debug(f"Target results: {target_results}, Max returned results: {max_returned_results}")
    
    searcher = PubmedSearcher()
    refiner = SearchRefiner()
    
    logger.info("Fetching real-time abstracts from PubMed API")
    abstracts, pmids, total_results = searcher.search_initial(current_query, max_returned_results)
    
    if not abstracts:
        logger.error("No abstracts retrieved from PubMed API")
        raise AssertionError("Failed to retrieve abstracts from PubMed API")
    
    logger.info(f"Retrieved {len(abstracts)} abstracts from {total_results} total results")
    logger.debug(f"PMIDs retrieved: {pmids}")
    for i, abstract in enumerate(abstracts, 1):
        summary = abstract["abstract"][:100] + "..." if len(abstract["abstract"]) > 100 else abstract["abstract"]
        logger.debug(f"Abstract {i} (PMID: {abstract['pmid']}): {summary}")
    
    logger.info("Sending real-time abstracts to SearchRefiner for processing")
    refined_query = refiner.refine_search(current_query, abstracts, original_query, total_results, target_results)
    
    logger.info("Refinement completed")
    logger.debug(f"Final refined query: '{refined_query}'")
    
    population_terms = refined_query.split(" AND ")[0].strip("()").split(" OR ")
    intervention_terms = refined_query.split(" AND ")[1].strip("()").split(" OR ")
    outcome_terms = refined_query.split(" AND ")[2].strip("()").split(" OR ") if len(refined_query.split(" AND ")) > 2 else []
    logger.debug(f"Population terms extracted: {population_terms}")
    logger.debug(f"Intervention terms extracted: {intervention_terms}")
    logger.debug(f"Outcome terms extracted: {outcome_terms if outcome_terms else 'None (not expected since total_results < 300)' if total_results <= 300 else 'None (unexpected since total_results > 300)'}")
    
    assert len(population_terms) >= 5, f"Expected at least 5 population terms, got {len(population_terms)}"
    assert len(intervention_terms) >= 5, f"Expected at least 5 intervention terms, got {len(intervention_terms)}"
    for term in population_terms + intervention_terms + outcome_terms:
        if term.startswith('"') and term.endswith('"'):
            word_count = len(term.strip('"').split())
            assert word_count <= 3, f"Term '{term}' exceeds 3 words (found {word_count})"  # Ajustado para <= 3
    
    logger.info("Validating refined query with a follow-up search")
    refined_abstracts, refined_pmids, refined_total = searcher.search_refined(refined_query, abstracts, max_returned_results)
    assert len(refined_pmids) > 0, "Refined query returned no results"
    logger.info(f"Refined query validation - Retrieved {len(refined_abstracts)} abstracts from {refined_total} total results")
    
    if total_results > target_results:
        logger.info(f"Initial results {total_results} > target {target_results}, expecting reduction")
        assert refined_total < total_results, f"Expected refined total ({refined_total}) to be less than initial ({total_results}) to approach target ({target_results})"
    elif total_results < target_results:
        logger.info(f"Initial results {total_results} < target {target_results}, expecting increase")
        assert refined_total > total_results, f"Expected refined total ({refined_total}) to be greater than initial ({total_results}) to approach target ({target_results})"
    else:
        logger.info(f"Initial results {total_results} = target {target_results}, expecting no significant change")
    
    if total_results > 300:
        assert len(outcome_terms) > 0, f"Expected outcome terms since total_results ({total_results}) > 300, but none found"
        logger.info("Outcome terms added as expected for total_results > 300")
    else:
        assert len(outcome_terms) == 0, f"Unexpected outcome terms found when total_results ({total_results}) <= 300"
        logger.info("No outcome terms added, as expected for total_results <= 300")
    
    logger.info(f"Refined query adjusted results from {total_results} to {refined_total} (target: {target_results})")
    logger.info("Test with real-time abstracts fully completed successfully")

if __name__ == "__main__":
    try:
        test_refine_search_with_real_time_abstracts()
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)
    logger.info("All tests passed successfully!")
    sys.exit(0)