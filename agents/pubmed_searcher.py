# C:\Users\Usuario\Desktop\projetos\PUBMED_CREW\agents\pubmed_searcher.py
from utils.pubmed_api import PubmedAPI
import logging

logger = logging.getLogger(__name__)

class PubmedSearcher:
    def __init__(self):
        self.api = PubmedAPI()
        self.retmax = 500  # Limite para recuperar PMIDs

    def search_initial(self, query, max_returned_results):
        total_results = self.api.count_results(query)
        if total_results == 0:
            logger.warning(f"Nenhum resultado encontrado para a query: {query}")
            return [], [], 0
        
        pmids = self.api.esearch(query, retmax=min(self.retmax, total_results))
        if not pmids:
            logger.warning(f"Nenhum PMID retornado para a query: {query}")
            return [], [], total_results
        
        selected_pmids = pmids[:max_returned_results]  # Usa o limite do request
        abstracts = self.api.efetch_abstracts(selected_pmids)
        logger.info(f"Inicial: {len(abstracts)} abstracts recuperados de {total_results} resultados.")
        return abstracts, selected_pmids, total_results

    def search_refined(self, query, previous_abstracts, max_returned_results):
        total_results = self.api.count_results(query)
        if total_results == 0:
            logger.warning(f"Nenhum resultado encontrado para a query refinada: {query}")
            return previous_abstracts, [], total_results
        
        pmids = self.api.esearch(query, retmax=min(self.retmax, total_results))
        if not pmids:
            logger.warning(f"Nenhum PMID retornado para a query refinada: {query}")
            return previous_abstracts, [], total_results
        
        selected_pmids = pmids[:max_returned_results]  # Usa o limite do request
        abstracts = self.api.efetch_abstracts(selected_pmids)
        logger.info(f"Refinado: {len(abstracts)} abstracts recuperados de {total_results} resultados.")
        return abstracts, selected_pmids, total_results