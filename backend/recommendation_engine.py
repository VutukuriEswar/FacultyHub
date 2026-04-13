import logging
import threading
import math
import re
from pathlib import Path
from typing import List, Dict, Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import CrossEncoder
from rank_bm25 import BM25Okapi
import nltk

try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
except (LookupError, Exception):
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt_tab', quiet=True)


from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

SCRIPT_DIR = Path(__file__).parent
PERSIST_DIR = SCRIPT_DIR / "chroma_db"
COLLECTION_NAME = "faculty_embeddings"

_recommender_instance = None
_instance_lock = threading.Lock()

class FacultyRecommender:
    def __new__(cls, *args, **kwargs):
        global _recommender_instance
        if _recommender_instance is None:
            with _instance_lock:
                if _recommender_instance is None:
                    _recommender_instance = super(FacultyRecommender, cls).__new__(cls)
        return _recommender_instance

    def __init__(self, persist_dir: str = None, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        if hasattr(self, 'vector_store') and self.vector_store is not None:
            return

        self.persist_dir = persist_dir or str(PERSIST_DIR)
        self.model_name = model_name
        
        logging.info(f"Initializing FacultyRecommender with Hybrid Search (BM25 + Vector)...")
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.model_name,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            
            self.vector_store = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings,
                collection_name=COLLECTION_NAME
            )
            
            self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512)
            
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=800,
                chunk_overlap=100,
                length_function=len
            )
            
            self.bm25 = None
            self.bm25_docs = []
            self.stop_words = set(stopwords.words('english'))
            
            logging.info("System Ready.")
            
        except Exception as e:
            logging.error(f"Failed to initialize FacultyRecommender: {e}")
            raise e

    @staticmethod
    def get_instance():
        return FacultyRecommender()

    def _preprocess_text(self, text: str) -> List[str]:
        text = text.lower()
        tokens = word_tokenize(text)
        tokens = [t for t in tokens if t.isalnum() and t not in self.stop_words]
        return tokens

    def _create_search_text(self, faculty_data: Dict[str, Any]) -> str:
        parts = []
        if faculty_data.get("name"):
            parts.append(f"Faculty Name: {faculty_data['name']}")
        if faculty_data.get("department"):
            parts.append(f"Department: {faculty_data['department']}")
        
        interests = faculty_data.get("research_interests", [])
        if isinstance(interests, str):
            parts.append(f"Research Interests: {interests}")
        elif isinstance(interests, list) and interests:
            parts.append(f"Research Interests: {', '.join(interests)}")
            
        projects = faculty_data.get("openalex_projects", [])
        if projects:
            proj_titles = [p.get("title", "") for p in projects if p.get("title")]
            if proj_titles:
                parts.append(f"Projects & Publications: {'; '.join(proj_titles)}")
                
        description = faculty_data.get("description")
        if description:
            parts.append(f"Bio: {description}")

        return "\n".join(parts)

    def _prepare_documents(self, faculty_data: Dict[str, Any]) -> List[Document]:
        faculty_id = faculty_data.get("faculty_id")
        if not faculty_id:
            return []

        text_content = self._create_search_text(faculty_data)
        base_metadata = {
            "faculty_id": faculty_id,
            "name": faculty_data.get("name", ""),
            "department": faculty_data.get("department", "")
        }

        chunks = self.text_splitter.split_text(text_content)
        docs = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{faculty_id}_chunk_{i}"
            meta = base_metadata.copy()
            meta["chunk_index"] = i
            docs.append(Document(page_content=chunk, metadata=meta, id=chunk_id))
            
        return docs

    def upsert_faculty(self, faculty_data: Dict[str, Any]) -> bool:
        faculty_id = faculty_data.get("faculty_id")
        try:
            if not faculty_id:
                return False
            docs = self._prepare_documents(faculty_data)
            if not docs:
                return False
            ids = [doc.id for doc in docs]
            self.vector_store.add_documents(documents=docs, ids=ids)
            return True
        except Exception as e:
            logging.error(f"Error upserting faculty {faculty_id}: {e}")
            return False

    def sync_all_faculty(self, all_faculty: List[Dict[str, Any]], batch_size: int = 32) -> bool:
        logging.info(f"Syncing {len(all_faculty)} faculty...")
        try:
            all_docs = []
            all_ids = []
            for fac in all_faculty:
                if not fac.get("faculty_id"): continue
                docs = self._prepare_documents(fac)
                all_docs.extend(docs)
                all_ids.extend([d.id for d in docs])
            
            for i in range(0, len(all_docs), batch_size):
                batch_docs = all_docs[i:i + batch_size]
                batch_ids = all_ids[i:i + batch_size]
                self.vector_store.add_documents(documents=batch_docs, ids=batch_ids)
            
            logging.info("Initializing BM25 Index for Hybrid Search...")
            tokenized_corpus = [self._preprocess_text(doc.page_content) for doc in all_docs]
            self.bm25 = BM25Okapi(tokenized_corpus)
            self.bm25_docs = all_docs
            
            logging.info("Vector and BM25 sync complete.")
            return True
        except Exception as e:
            logging.error(f"Error executing full sync: {e}")
            return False

    def _reciprocal_rank_fusion(self, results: Dict[str, Dict], k: int = 60) -> Dict[str, float]:
        fused_scores = {}
        for system, doc_list in results.items():
            for rank, entry in enumerate(doc_list):
                doc_id = entry['doc_id']
                if doc_id not in fused_scores:
                    fused_scores[doc_id] = 0
                fused_scores[doc_id] += 1 / (k + rank + 1)
        
        sorted_fused = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_fused

    def search_faculty(self, query_text: str, top_k: int = 100) -> List[Dict[str, Any]]:
        if not query_text.strip():
            return []

        try:
            hybrid_results = {"vector": [], "bm25": []}
            
            vector_candidates = self.vector_store.similarity_search_with_score(query_text, k=top_k * 3)
            
            doc_map = {}
            for doc, dist_score in vector_candidates:
                fac_id = doc.metadata.get("faculty_id")
                if not fac_id: continue
                
                rerank_val = 1 / (1 + dist_score) 
                
                if fac_id not in doc_map or doc_map[fac_id]['score'] < rerank_val:
                    doc_map[fac_id] = {
                        "doc_id": fac_id,
                        "score": rerank_val, 
                        "metadata": doc.metadata,
                        "content": doc.page_content
                    }

            hybrid_results["vector"] = list(doc_map.values())
            
            if self.bm25:
                tokenized_query = self._preprocess_text(query_text)
                bm25_scores = self.bm25.get_scores(tokenized_query)
                top_n_indices = bm25_scores.argsort()[-(top_k * 3):][::-1]
                
                bm25_doc_map = {}
                for idx in top_n_indices:
                    doc = self.bm25_docs[idx]
                    fac_id = doc.metadata.get("faculty_id")
                    if not fac_id: continue
                    
                    if fac_id not in bm25_doc_map:
                         bm25_doc_map[fac_id] = {
                            "doc_id": fac_id,
                            "score": bm25_scores[idx],
                            "metadata": doc.metadata,
                            "content": doc.page_content
                        }
                hybrid_results["bm25"] = list(bm25_doc_map.values())

            fused_ranking = self._reciprocal_rank_fusion(hybrid_results)
            
            candidate_contents = []
            candidate_map = []
            
            seen_ids = set()
            
            for doc_id, score in fused_ranking:
                if doc_id in seen_ids: continue
                seen_ids.add(doc_id)
                
                data = None
                if doc_id in doc_map:
                    data = doc_map[doc_id]
                elif self.bm25:
                     for entry in hybrid_results["bm25"]:
                         if entry['doc_id'] == doc_id:
                             data = entry
                             break
                
                if data:
                    candidate_contents.append((query_text, data['content']))
                    candidate_map.append((doc_id, data))

            if not candidate_contents:
                return []

            rerank_scores = self.reranker.predict(candidate_contents)
            
            final_results = []
            for i, (doc_id, data) in enumerate(candidate_map):
                rerank_val = rerank_scores[i]
                
                normalized_score = 1 / (1 + math.exp(-rerank_val / 3)) * 100
                
                if normalized_score > 20.0:
                    final_results.append({
                        "faculty_id": doc_id,
                        "name": data["metadata"].get("name"),
                        "department": data["metadata"].get("department"),
                        "similarity_pct": round(min(normalized_score, 100), 2),
                        "match_reasons": [f"Hybrid Match ({normalized_score:.1f}%)"],
                        "content": data['content']
                    })

            sorted_results = sorted(final_results, key=lambda x: x['similarity_pct'], reverse=True)            
            return sorted_results[:top_k]

        except Exception as e:
            logging.error(f"Search failed: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return []
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        try:
            return self.embeddings.embed_documents(texts)
        except Exception as e:
            logging.error(f"Embedding failed: {e}")
            return []