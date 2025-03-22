from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
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

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todas as origens (ajuste para segurança em produção)
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos os métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos os cabeçalhos
)

class SearchRequest(BaseModel):
    picott_text: str
    target_results: int = 100
    max_iterations: int = 5
    max_returned_results: int = 50

def summarize_abstract(abstract, max_words=50):
    if abstract is None:
        return "Abstract não disponível"
    words = abstract.split()
    return " ".join(words[:max_words]) + ("..." if len(words) > max_words else "")

@app.post("/api/search")
async def search_pubmed(request: SearchRequest):
    user_query = request.picott_text
    max_iterations = min(request.max_iterations, 5)
    max_returned_results = min(request.max_returned_results, 100)
    target_results = request.target_results

    logger.info(f"Requisição recebida - Query: '{user_query}', Target: {target_results}, Max iterações: {max_iterations}")

    # Verificação adicional para debug
    if not user_query or user_query.strip() == "":
        logger.error("Query vazia recebida na API")
        raise HTTPException(status_code=400, detail="Query inválida: a query não pode ser vazia")
    
    logger.info(f"Iniciando validação da query: '{user_query}'")
    
    try:
        # Log detalhado antes da validação
        logger.info(f"Chamando validate_and_raise para a query: '{user_query}'")
        validated_query = validate_and_raise(user_query)
        logger.info(f"Query validada com sucesso: '{validated_query}'")

        searcher = PubmedSearcher()
        refiner = SearchRefiner()

        # Busca inicial
        logger.info(f"Iniciando busca inicial com a query validada: '{validated_query}'")
        abstracts, pmids, total_results = searcher.search_initial(validated_query, max_returned_results)
        current_query = validated_query
        logger.info(f"Busca inicial concluída - Query: '{validated_query}', Total: {total_results}")

        if not pmids:
            logger.warning(f"Sem resultados na busca inicial - Query: '{current_query}'")
            return {"query": current_query, "results": [], "total_results": total_results}

        logger.info(f"Busca inicial - Total: {total_results}, PMIDs: {len(pmids)}")

        # Refinamento similar ao test_search_refiner.py
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Iteração {iteration}/{max_iterations} - Total: {total_results}, Target: {target_results}")
            
            # Verifica se já está próximo do alvo
            if 0.5 * target_results <= total_results <= 1.5 * target_results:
                logger.info(f"Total de resultados {total_results} já está próximo do alvo {target_results}, parando refinamento")
                break
            
            # Armazena o valor atual para comparação posterior
            previous_total_results = total_results
                
            logger.info(f"Iniciando refinamento da query: '{current_query}'")
            refined_query = refiner.refine_search(current_query, abstracts, user_query, total_results, target_results)
            logger.info(f"Query refinada: '{refined_query}'")

            if refined_query == current_query:
                logger.info(f"Query estabilizada na iteração {iteration}")
                break

            current_query = refined_query
            
            # Valida se a query refinada tem a estrutura correta com parênteses
            if current_query.count("(") < 2 or current_query.count(")") < 2:
                logger.warning(f"Query refinada com formato inválido: '{current_query}', retornando à query anterior")
                current_query = validated_query
                break
            
            # Executa a busca com a nova query
            logger.info(f"Executando busca com query refinada: '{current_query}'")
            abstracts, pmids, total_results = searcher.search_refined(current_query, abstracts, max_returned_results)
            logger.info(f"Busca refinada - Total: {total_results}, PMIDs: {len(pmids)}")
            
            # Validação adicional de resultados - inspirada no teste
            if (previous_total_results > target_results and total_results > previous_total_results) or \
               (previous_total_results < target_results and total_results < previous_total_results):
                logger.warning(f"Refinamento moveu-se na direção errada: de {previous_total_results} para {total_results} (alvo: {target_results})")
                # O próximo refinamento deve corrigir isso

        # Resultado final com a query refinada
        logger.info(f"Finalizando busca com query final: '{current_query}'")
        final_pmids = searcher.api.fetch_pmids(current_query, retmax=max_returned_results)
        final_abstracts = searcher.api.fetch_abstracts(final_pmids)
        
        # Verificar se os abstracts têm os campos necessários
        results = []
        for abstract in final_abstracts:
            if abstract and "pmid" in abstract:
                pmid = abstract["pmid"]
                abstract_text = abstract.get("abstract")
                results.append({"pmid": pmid, "abstract": summarize_abstract(abstract_text)})
            else:
                logger.warning(f"Abstract sem campos obrigatórios: {abstract}")

        logger.info(f"Busca finalizada - Query: '{current_query}', Total: {total_results}, Retornados: {len(results)}")
        return {"query": current_query, "results": results, "total_results": total_results}

    except QueryValidationError as e:
        logger.error(f"Erro na validação da query: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Query inválida: {str(e)}")
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro durante a busca: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)