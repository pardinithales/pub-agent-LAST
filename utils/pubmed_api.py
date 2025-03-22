import requests
import xml.etree.ElementTree as ET
import os
import logging

logger = logging.getLogger(__name__)

class PubmedAPI:
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.db = "pubmed"
        self.email = os.getenv("PUBMED_EMAIL")
        if not self.email:
            raise ValueError("PUBMED_EMAIL não definida no .env")
        self.headers = {"User-Agent": "PUBMED_CREW/1.0"}

    def count_results(self, query):
        url = f"{self.base_url}esearch.fcgi?db={self.db}&term={query}&retmax=0&retmode=xml&email={self.email}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            count = int(root.find(".//Count").text)
            logger.info(f"Total de resultados para query '{query}': {count}")
            return count
        except (requests.RequestException, AttributeError) as e:
            logger.error(f"Erro ao contar resultados: {e}")
            return 0

    def esearch(self, query, retmax=100):
        url = f"{self.base_url}esearch.fcgi?db={self.db}&term={query}&retmax={retmax}&retmode=xml&email={self.email}"
        logger.info(f"Enviando esearch URL: {url}")
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            id_list = [id_elem.text for id_elem in root.findall(".//Id")]
            logger.info(f"PMIDs encontrados: {id_list}")
            return id_list
        except requests.RequestException as e:
            logger.error(f"Erro na busca esearch: {e}")
            return []

    def efetch_abstracts(self, pmids):
        url = f"{self.base_url}efetch.fcgi?db={self.db}&id={','.join(pmids)}&retmode=xml&email={self.email}"
        logger.info(f"Enviando efetch URL: {url}")
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            abstracts = []
            for article in root.findall(".//PubmedArticle"):
                pmid = article.find(".//PMID").text
                abstract_text = article.find(".//AbstractText")
                abstract = abstract_text.text.strip() if abstract_text is not None and abstract_text.text else "Abstract não disponível"
                abstracts.append({"pmid": pmid, "abstract": abstract})
            return abstracts
        except requests.RequestException as e:
            logger.error(f"Erro na busca efetch: {e}")
            return []