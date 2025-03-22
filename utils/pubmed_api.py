import requests
import time
from xml.etree import ElementTree as ET
from typing import List, Dict

class PubmedAPI:
    def __init__(self, email: str, api_key: str = None):
        self.base_esearch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        self.base_efetch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        self.email = email
        self.api_key = api_key
        self.retmax = 500  # Limite prático por requisição

    def _make_request(self, url: str, retries: int = 3, backoff: float = 1.0) -> str:
        for attempt in range(retries):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                return response.text
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    time.sleep(backoff * (2 ** attempt))  # Backoff exponencial
                    continue
                raise e
        raise Exception("Max retries exceeded")

    def count_results(self, query: str) -> int:
        params = {
            "db": "pubmed",
            "term": query,
            "email": self.email,
            "retmax": 0,  # Só contar, sem retornar PMIDs
            "api_key": self.api_key
        }
        url = f"{self.base_esearch}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        xml_data = self._make_request(url)
        root = ET.fromstring(xml_data)
        count = int(root.find(".//Count").text)
        return count

    def fetch_pmids(self, query: str, retmax: int) -> List[str]:
        params = {
            "db": "pubmed",
            "term": query,
            "email": self.email,
            "retmax": retmax,
            "api_key": self.api_key
        }
        url = f"{self.base_esearch}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        xml_data = self._make_request(url)
        root = ET.fromstring(xml_data)
        return [id_elem.text for id_elem in root.findall(".//Id")]

    def fetch_abstracts(self, pmids: List[str]) -> List[Dict[str, str]]:
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "email": self.email,
            "api_key": self.api_key
        }
        url = f"{self.base_efetch}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        xml_data = self._make_request(url)
        root = ET.fromstring(xml_data)
        abstracts = []
        for article in root.findall(".//PubmedArticle"):
            pmid = article.find(".//PMID").text
            abstract_elem = article.find(".//AbstractText")
            abstract = abstract_elem.text if abstract_elem is not None else ""
            abstracts.append({"pmid": pmid, "abstract": abstract})
        return abstracts

# Exemplo de uso no api.py
from fastapi import FastAPI
app = FastAPI()
pubmed_api = PubmedAPI(email="seu_email@example.com", api_key="sua_chave")

@app.post("/api/search")
async def search(data: dict):
    query = data["picott_text"]
    max_results = data["max_returned_results"]
    total = pubmed_api.count_results(query)
    pmids = pubmed_api.fetch_pmids(query, max_results)
    abstracts = pubmed_api.fetch_abstracts(pmids)
    return {"query": query, "results": abstracts, "total_results": total}