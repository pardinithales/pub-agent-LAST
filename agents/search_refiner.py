# C:\Users\Usuario\Desktop\projetos\PUBMED_CREW\agents\search_refiner.py
from anthropic import Anthropic
import logging
import os
from dotenv import load_dotenv
import json
import re

load_dotenv()

logger = logging.getLogger(__name__)

class SearchRefiner:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-3-7-sonnet-20250219"

    def refine_search(self, current_query, abstracts, original_query, total_results, target_results):
        sampled_abstracts = [abstract["abstract"] for abstract in abstracts[:10]]
        
        system_prompt = """
        You are an expert in refining PubMed queries.

        ## CRITICAL RULES - ABSOLUTELY NON-NEGOTIABLE
        1. Translate the query to English if not already in English.
        2. Return two parenthetical blocks: (POPULATION) AND (INTERVENTION), adding (OUTCOMES) if total_results > target_results.
        3. Use phrases with maximum 3 words in quotes, preferring 2 words when possible (e.g., "high grade glioma" is OK, "tumor treating fields" is OK, but prefer "tumor treating" if sufficient).
        4. Use abbreviations and synonyms from abstracts.
        5. Structure: (POPULATION) AND (INTERVENTION) [AND (OUTCOMES) if total_results > target_results].
        6. Split overly technical terms into 2-3 word components where practical.

        ## INSTRUCTIONS
        - POPULATION: Extract terms/abbreviations for the disease/condition from abstracts, use at least 5 variants (e.g., "high grade glioma", GBM, "brain tumor").
        - INTERVENTION: Extract treatment/procedure terms from abstracts, use at least 5 variants (e.g., "tumor treating fields", TTF, Optune).
        - OUTCOMES (if total_results > target_results): Add outcome terms (e.g., "survival", "efficacy", "prognosis"), max 3 words, to narrow results.
        - If total_results > target_results, prioritize specific terms and add outcomes to reduce result count; if total_results < target_results, expand terms to increase results.
        - RETURN ONLY THE QUERY IN THIS EXACT FORMAT: (term1 OR term2 OR ...) AND (term1 OR term2 OR ...), NO OTHER TEXT.
        """
        
        user_prompt = f"""
        Original query: "{original_query}"
        Current query: "{current_query}"
        Abstracts: {json.dumps(sampled_abstracts)}
        Total results: {total_results}
        Target results: {target_results}
        
        Refine the query:
        - Translate to English.
        - Two blocks: (POPULATION) AND (INTERVENTION), add (OUTCOMES) if total_results > target_results.
        - MAXIMUM 3 WORDS PER QUOTED TERM, prefer 2 words when possible.
        - At least 5 terms per block when possible.
        - RETURN ONLY THE QUERY, NOTHING ELSE.
        """
        
        logger.info(f"Starting query refinement for original query: '{original_query}'")
        logger.debug(f"Current query: '{current_query}'")
        logger.debug(f"Total results: {total_results}, Target results: {target_results}")
        logger.debug(f"Sampled abstracts: {json.dumps(sampled_abstracts)}")
        
        try:
            logger.debug("Sending prompt to Claude")
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=7000,
                temperature=0.2,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            
            refined_query = ""
            for content in message.content:
                if content.type == "text":
                    refined_query = content.text.strip()
            
            logger.debug(f"Raw response from Claude: '{refined_query}'")
            
            # Validação com regex
            if not refined_query or refined_query.count("(") < 2 or refined_query.count(")") < 2:
                logger.warning("Response lacks two parenthetical blocks, applying fallback")
                refined_query = '("high grade glioma" OR GBM OR "brain tumor" OR HGG OR "grade 4") AND ("tumor treating fields" OR TTF OR Optune OR "electric fields" OR Novocure)'
            else:
                quoted_terms = re.findall(r'"([^"]*)"', refined_query)
                for term in quoted_terms:
                    if len(term.split()) > 3:
                        logger.warning(f"Found invalid term with more than 3 words: '{term}', applying fallback")
                        refined_query = '("high grade glioma" OR GBM OR "brain tumor" OR HGG OR "grade 4") AND ("tumor treating fields" OR TTF OR Optune OR "electric fields" OR Novocure)'
                        break
            
            logger.info(f"Refined query generated: '{refined_query}'")
            return refined_query
            
        except Exception as e:
            logger.error(f"Error refining query: {e}")
            return current_query