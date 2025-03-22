from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
from dotenv import load_dotenv
import os
from agents.pubmed_searcher import PubmedSearcher
from agents.search_refiner import SearchRefiner
from agents.query_validator import validate_and_raise, QueryValidationError

load_dotenv()

required_vars = ["ANTHROPIC_API_KEY", "PUBMED_EMAIL"]
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"Variável de ambiente {var} não definida no .env")

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

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
    target_results = request.target_results

    logger.info(f"Requisição recebida - Query: '{user_query}', Target: {target_results}, Max iterações: {max_iterations}")

    try:
        validated_query = validate_and_raise(user_query)
        logger.info(f"Query validada: '{validated_query}'")

        searcher = PubmedSearcher()
        refiner = SearchRefiner()

        # Busca inicial
        abstracts, pmids, total_results = searcher.search_initial(validated_query, max_returned_results)
        current_query = validated_query

        if not pmids:
            logger.warning(f"Sem resultados na busca inicial - Query: '{current_query}'")
            return {"query": current_query, "results": [], "total_results": total_results}

        logger.info(f"Busca inicial - Total: {total_results}, PMIDs: {len(pmids)}")

        # Refinamento baseado em test_search_refiner.py
        iteration = 0
        while iteration < max_iterations and (total_results < target_results / 2 or total_results > target_results * 2):
            iteration += 1
            logger.info(f"Iteração {iteration}/{max_iterations} - Total: {total_results}")
            refined_query = refiner.refine_search(current_query, abstracts, user_query, total_results, target_results)

            if refined_query == current_query:
                logger.info(f"Query estabilizada na iteração {iteration}")
                break

            current_query = refined_query
            abstracts, pmids, total_results = searcher.search_refined(current_query, abstracts, max_returned_results)
            logger.info(f"Busca refinada - Total: {total_results}, PMIDs: {len(pmids)}")

        # Resultado final
        total_results = searcher.api.count_results(current_query)
        final_pmids = searcher.api.esearch(current_query, retmax=max_returned_results)
        final_abstracts = searcher.api.efetch_abstracts(final_pmids)
        results = [{"pmid": abstract["pmid"], "abstract": summarize_abstract(abstract["abstract"])} for abstract in final_abstracts]

        logger.info(f"Busca finalizada - Query: '{current_query}', Total: {total_results}, Retornados: {len(results)}")
        return {"query": current_query, "results": results, "total_results": total_results}

    except QueryValidationError as e:
        logger.error(f"Erro na validação da query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro durante a busca: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)