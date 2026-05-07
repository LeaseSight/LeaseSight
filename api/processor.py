import os
import json
import sqlite3
from typing import List, Dict, Any
from pathlib import Path
from openai import OpenAI
from scripts.processor import process_new_pdf
from scripts.query_engine import ask_document
from scripts.visual_anchor import find_coordinates
from api.schemas import EntityStatus, MigrationEntity, ResearchScorecard, Finding, Coordinate

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "leasesight.db"

class UniversalProcessor:
    def __init__(self, openai_client: OpenAI, pinecone_index: Any, azure_client: Any = None):
        self.openai = openai_client
        self.pinecone = pinecone_index
        self.azure = azure_client

    async def process_batch(self, task_id: str, files: List[str]):
        """
        Processes a batch of files: OCR, Index, and Universal Entity Extraction.
        """
        RAW_PDF_DIR = BASE_DIR / "data" / "raw_pdfs"
        
        for file_name in files:
            try:
                pdf_path = RAW_PDF_DIR / file_name
                
                # 1. OCR & Indexing
                process_new_pdf(str(pdf_path), file_name, 
                                openai_client=self.openai, 
                                pinecone_index=self.pinecone, 
                                azure_client=self.azure)
                
                # 2. Universal Extraction (High Temperature for discovery)
                schema_query = """
                Extract ALL significant entities from this document. 
                Focus on: Names, Organizations, Dates, Statistical Findings, and Citations.
                
                Return a JSON list of objects:
                [{"category": "...", "value": "...", "confidence": 0.0-1.0}, ...]
                """
                
                # Using a high temperature for 'Discovery' mode
                response = self.openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a surgical data extraction agent. Return ONLY raw JSON."},
                        {"role": "user", "content": f"Analyze this document content and extract entities: {file_name}\n\nContext: {ask_document('Give me a full summary of this document', file_name, openai_client=self.openai, pinecone_index=self.pinecone)['answer']}"}
                    ],
                    temperature=0.8,
                    response_format={"type": "json_object"}
                )
                
                entities_raw = json.loads(response.choices[0].message.content).get('entities', [])
                
                # 3. Store in Staging Table
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                for ent in entities_raw:
                    c.execute("""INSERT INTO migration_results 
                                (batch_id, file_name, category, value, confidence, status)
                                VALUES (?,?,?,?,?,?)""",
                             (task_id, file_name, 
                              ent.get('category', 'Unknown'),
                              str(ent.get('value', 'Unknown')),
                              ent.get('confidence', 0.5),
                              EntityStatus.PENDING.value))
                
                # Update progress
                c.execute("UPDATE migration_batches SET processed_files = processed_files + 1 WHERE id = ?", (task_id,))
                conn.commit()
                conn.close()
                
            except Exception as e:
                print(f"Error processing {file_name}: {e}")

class ResearchAuditor:
    def __init__(self, openai_client: OpenAI, pinecone_index: Any):
        self.openai = openai_client
        self.pinecone = pinecone_index

    async def _retrieve_benchmarks(self, query: str) -> str:
        """
        Retrieves 'Gold Standard' paper structures and conference guidelines from Pinecone.
        """
        try:
            # Create embedding for the query
            res = self.openai.embeddings.create(input=[query], model="text-embedding-3-small")
            vec = res.data[0].embedding
            
            # Query Pinecone for benchmarks (assuming they are indexed with metadata type='benchmark')
            # If no benchmarks found, it returns a high-quality synthetic guideline.
            results = self.pinecone.query(
                vector=vec, 
                top_k=3, 
                filter={"type": {"$eq": "benchmark"}}, 
                include_metadata=True
            )
            
            contexts = [match['metadata']['text'] for match in results.get('matches', []) if 'metadata' in match and 'text' in match['metadata']]
            
            if not contexts:
                return """
                Standard Conference Guidelines (NeurIPS/EMNLP):
                - Novelty: Significant contribution beyond state-of-the-art.
                - Rigor: Sound methodology, proofs, and exhaustive empirical evaluation.
                - Clarity: Precise language, logical flow, and clear visualization.
                - Citations: Discussion of all relevant related work, including recent SOTA.
                """
            return "\n---\n".join(contexts)
        except Exception as e:
            print(f"Benchmark retrieval error: {e}")
            return "General Academic Excellence Guidelines: Soundness, Novelty, Clarity."

    async def audit_paper(self, file_name: str) -> Dict[str, Any]:
        """
        Deep-dive Pre-Submission Audit.
        Identifies contradictions, missing citations, and narrative gaps.
        """
        # 1. Retrieve specific benchmarks
        benchmark_context = await self._retrieve_benchmarks(f"Guidelines and high-scoring papers for {file_name}")
        
        # 2. Get document context (summary and key claims)
        doc_summary = ask_document("Identify the core claims, methodology, and related work mentioned in this paper.", file_name, openai_client=self.openai, pinecone_index=self.pinecone)
        
        # 3. Perform Deep Audit
        prompt = f"""
        Act as a Senior Area Chair for top-tier AI conferences (NeurIPS, EMNLP, NAACL). 
        Audit the draft paper: {file_name}
        
        PAPER SUMMARY & CLAIMS:
        {doc_summary['answer']}
        
        CONFERENCE BENCHMARKS & GOLD STANDARDS:
        {benchmark_context}
        
        TASK:
        Perform a technical deep-dive. Identify:
        1. Originality: Compared to SOTA, is there a clear novelty?
        2. Technical Rigor: Are there contradictions between claims and results? Any logical gaps in proofs?
        3. Citation Validity: Are key works from the retrieved benchmarks missing?
        4. Narrative Clarity: Is the abstract grounded in the results? Is the narrative flow consistent?
        
        For each category, provide:
        - value: (Short summary of the audit)
        - explanation: (Detailed reasoning, e.g., 'Compared to high-scoring papers in NAACL 2025, your section X lacks Y')
        - evidence_snippet: (EXACT snippet from the paper that illustrates the issue or needs improvement)
        
        Identify specific "Missing Citations" as a list of author/year/topic.
        Flag any "Technical Contradictions" or "Factual Errors".
        Provide an overall_score (1-10).
        
        Return JSON.
        """
        
        # Using a higher temperature for creative/critical auditing
        response = self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a critical Area Chair. Return ONLY raw JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            response_format={"type": "json_object"}
        )
        
        try:
            raw_data = json.loads(response.choices[0].message.content)
            
            # 4. Coordinate Mapping for Visual Grounding
            categories = ['originality', 'technical_rigor', 'citation_validity', 'narrative_clarity']
            # Also handle potentially nested or differently named keys from LLM output
            for key in categories:
                cat_data = raw_data.get(key)
                if not cat_data: continue
                
                snippet = cat_data.get('evidence_snippet', '')
                if snippet and len(snippet) > 10:
                    coords = find_coordinates(file_name, snippet[:100]) # Use prefix for better matching
                    if coords:
                        cat_data['coordinates'] = {
                            "page": int(coords['page']),
                            "x": coords['bounding_box'][0]['x'],
                            "y": coords['bounding_box'][0]['y'],
                            "width": coords['bounding_box'][2]['x'] - coords['bounding_box'][0]['x'],
                            "height": coords['bounding_box'][2]['y'] - coords['bounding_box'][0]['y']
                        }
            
            return raw_data
        except Exception as e:
            print(f"Deep Audit parsing error: {e}")
            return {"error": f"Failed to parse audit results: {str(e)}"}
