# C:\Users\Usuario\Desktop\projetos\PUBMED_CREW\api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
from dotenv import load_dotenv
import os
import uvicorn
from agents.pubmed_searcher import PubmedSearcher
from agents.search_refiner import SearchRefiner
from agents.query_validator import validate_and_raise, QueryValidationError

load_dotenv()

required_vars = ["ANTHROPIC_API_KEY", "PUBMED_EMAIL"]
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"Variável de ambiente {var} não definida no .env")

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "DEBUG"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

app = FastAPI()

class SearchRequest(BaseModel):
    picott_text: str
    target_results: int = 100
    max_iterations: int = 5
    max_returned_results: int = 50

def summarize_abstract(abstract, max_words=50):
    words = abstract.split()
    return " ".join(words[:max_words]) + ("..." if len(words) > max_words else "")

@app.post("/api/search")
async def search_pubmed(request: SearchRequest):
    user_query = request.picott_text
    max_iterations = min(request.max_iterations, 5)
    max_returned_results = min(request.max_returned_results, 100)

    logger.info(f"Requisição recebida - Query: '{user_query}', Max iterações: {max_iterations}, Max resultados retornados: {max_returned_results}")

    try:
        logger.debug("Iniciando validação da query")
        validated_query = validate_and_raise(user_query)
        logger.info(f"Query validada: '{validated_query}'")

        searcher = PubmedSearcher()
        refiner = SearchRefiner()

        logger.debug("Iniciando busca inicial no PubMed")
        abstracts, pmids, total_results = searcher.search_initial(validated_query, max_returned_results)
        current_query = validated_query

        if not pmids:
            logger.warning(f"Sem resultados na busca inicial - Query: '{current_query}', Total: {total_results}")
            return {
                "query": current_query,
                "results": [],
                "total_results": total_results
            }

        logger.info(f"Busca inicial concluída - Total: {total_results}, PMIDs: {len(pmids)}")
        for i, abstract in enumerate(abstracts, 1):
            summary = summarize_abstract(abstract["abstract"])
            logger.debug(f"Abstract inicial {i}/{len(abstracts)} (PMID: {abstract['pmid']}): {summary}")

        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Iteração {iteration}/{max_iterations} - Query: '{current_query}', Total: {total_results}")

            logger.debug("Iniciando refinamento da query com ferramenta think")
            previous_query = current_query
            refined_query = refiner.refine_search(
                current_query, 
                abstracts, 
                user_query, 
                total_results, 
                request.target_results
            )
            logger.info(f"Query refinada: '{refined_query}'")

            if refined_query == current_query:
                logger.info(f"Query estabilizada na iteração {iteration} - Total: {total_results}")
                break

            current_query = refined_query
            logger.debug(f"Iniciando busca refinada - Query: '{current_query}'")
            abstracts, pmids, total_results = searcher.search_refined(current_query, abstracts, max_returned_results)
            logger.info(f"Busca refinada concluída - Total: {total_results}, PMIDs: {len(pmids)}")

            for i, abstract in enumerate(abstracts, 1):
                summary = summarize_abstract(abstract["abstract"])
                logger.debug(f"Abstract refinado {i}/{len(abstracts)} (PMID: {abstract['pmid']}): {summary}")

        # Busca final com total correto e mais abstracts
        logger.debug(f"Buscando até {max_returned_results} abstracts para a resposta final")
        total_results = searcher.api.count_results(current_query)  # Garante o total real
        final_pmids = searcher.api.esearch(current_query, retmax=max_returned_results)
        final_abstracts = searcher.api.efetch_abstracts(final_pmids)
        results = [{"pmid": abstract["pmid"], "abstract": abstract["abstract"]} for abstract in final_abstracts]

        logger.info(f"Busca finalizada - Query final: '{current_query}', Total: {total_results}, Resultados retornados: {len(results)}")
        for i, result in enumerate(results, 1):
            summary = summarize_abstract(result["abstract"])
            logger.debug(f"Resultado final {i}/{len(results)} (PMID: {result['pmid']}): {summary}")

        return {
            "query": current_query,
            "results": results,
            "total_results": total_results
        }

    except QueryValidationError as e:
        logger.error(f"Erro na validação da query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro durante a busca: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Iniciando Uvicorn na porta {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)