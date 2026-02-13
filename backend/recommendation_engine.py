
import os
import shutil
import logging
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# --- Configuration ---
SCRIPT_DIR = Path(__file__).parent
PERSIST_DIR = SCRIPT_DIR / "chroma_db"
COLLECTION_NAME = "faculty_embeddings"

# Singleton instance
_recommender_instance = None

class FacultyRecommender:
    def __init__(self):
        logging.info("Initializing FacultyRecommender...")
        try:
            # Initialize Embeddings Model (all-MiniLM-L6-v2 is standard for semantic search)
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            logging.info("Embedding model loaded.")

            # Initialize Chroma Vector Store
            self.vector_store = Chroma(
                persist_directory=str(PERSIST_DIR),
                embedding_function=self.embeddings,
                collection_name=COLLECTION_NAME
            )
            logging.info(f"Vector Store initialized at {PERSIST_DIR}")
            
        except Exception as e:
            logging.error(f"Failed to initialize FacultyRecommender: {e}")
            raise e

    @staticmethod
    def get_instance():
        global _recommender_instance
        if _recommender_instance is None:
            _recommender_instance = FacultyRecommender()
        return _recommender_instance

    def _create_search_text(self, faculty_data: Dict[str, Any]) -> str:
        """
        Combines relevant fields into a single text blob for embedding.
        Context is key for semantic search.
        """
        parts = []
        
        # Name & Department (Basic Context)
        if faculty_data.get("name"):
            parts.append(f"Faculty Name: {faculty_data['name']}")
        if faculty_data.get("department"):
            parts.append(f"Department: {faculty_data['department']}")
        
        # Research Interests (High Importance)
        interests = faculty_data.get("research_interests", [])
        if isinstance(interests, str):
            parts.append(f"Research Interests: {interests}")
        elif isinstance(interests, list) and interests:
            parts.append(f"Research Interests: {', '.join(interests)}")
            
        # Projects / Publications (High Importance for specific matching)
        projects = faculty_data.get("openalex_projects", [])
        if projects:
            proj_titles = [p.get("title", "") for p in projects if p.get("title")]
            if proj_titles:
                parts.append(f"Projects & Publications: {'; '.join(proj_titles)}")
                
        return "\n".join(parts)

    def upsert_faculty(self, faculty_data: Dict[str, Any]):
        """
        Adds or updates a faculty member in the vector store.
        """
        try:
            faculty_id = faculty_data.get("faculty_id")
            if not faculty_id:
                return

            text_content = self._create_search_text(faculty_data)
            
            # Metadata for retrieval (keep it lightweight)
            metadata = {
                "faculty_id": faculty_id,
                "name": faculty_data.get("name", ""),
                "department": faculty_data.get("department", "")
            }

            doc = Document(page_content=text_content, metadata=metadata)
            
            # Chroma upsert (using add_documents with ID handles updates if ID exists? 
            # Actually Chroma 'add' might duplicate if ID not specified. 
            # We should specify IDs explicitly)
            
            self.vector_store.add_documents(documents=[doc], ids=[faculty_id])
            logging.info(f"Upserted vector for faculty: {faculty_id}")
            
        except Exception as e:
            logging.error(f"Error upserting faculty {faculty_data.get('faculty_id')}: {e}")

    def sync_all_faculty(self, all_faculty: List[Dict[str, Any]]):
        """
        Re-indexes all faculty. Useful on startup or full re-sync.
        Warning: This is a heavy operation for large datasets.
        """
        logging.info(f"Syncing {len(all_faculty)} faculty to vector store...")
        try:
            # For a clean sync, we might want to delete existing collection or reset
            # But specific delete is better. For now, we just overwrite.
            # Ideally: valid_ids = [f['faculty_id'] for f in all_faculty]
            # self.vector_store.delete(where={"faculty_id": {"$nin": valid_ids}}) # Cleanup old?
            # For simplicity in this demo, we just upsert all.
            
            docs = []
            ids = []
            for fac in all_faculty:
                if not fac.get("faculty_id"): continue
                
                text = self._create_search_text(fac)
                meta = {
                    "faculty_id": fac["faculty_id"],
                    "name": fac.get("name", ""),
                    "department": fac.get("department", "")
                }
                docs.append(Document(page_content=text, metadata=meta))
                ids.append(fac["faculty_id"])
            
            if docs:
                # Batch add might be faster
                self.vector_store.add_documents(documents=docs, ids=ids)
                logging.info("Sync complete.")
                
        except Exception as e:
            logging.error(f"Error executing full sync: {e}")

    def search_faculty(self, query_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Semantic search for faculty based on a query string (e.g. user interests).
        Returns list of dicts: {"faculty_id": str, "score": float}
        """
        if not query_text.strip():
            return []

        try:
            # similarity_search_with_score returns L2 distance (lower is better)
            # or Cosine distance depending on generic config.
            # Default Chroma is L2. 
            # Distance 0 = Exact Match. Distance > 1 = Poor match.
            
            results = self.vector_store.similarity_search_with_score(query_text, k=top_k)
            
            formatted_results = []
            for doc, score in results:
                # Convert L2 distance to a 0-100 similarity score approximation
                # Heuristic: 0.0 -> 100%, 1.0 -> 50%, >1.5 -> Low
                
                # Continuous decay formula: 1 / (1 + distance)
                # Distance 0 (Exact) -> 100%
                # Distance 0.5 -> 67%
                # Distance 1.0 -> 50%
                similarity = 1 / (1 + score) * 100

                formatted_results.append({
                    "faculty_id": doc.metadata.get("faculty_id"),
                    "name": doc.metadata.get("name"),
                    "score": score, # raw distance
                    "similarity_pct": round(similarity, 1)
                })
                
            return formatted_results

        except Exception as e:
            logging.error(f"Search failed: {e}")
            return []
