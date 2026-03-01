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
        
        logging.info(f"Initializing FacultyRecommender...")
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
            logging.info("System Ready.")
            
        except Exception as e:
            logging.error(f"Failed to initialize FacultyRecommender: {e}")
            raise e

    @staticmethod
    def get_instance():
        return FacultyRecommender()

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
                
            logging.info("Vector sync complete.")
            return True
        except Exception as e:
            logging.error(f"Error executing full sync: {e}")
            return False

    def _calculate_keyword_score(self, content: str, keyword: str) -> (float, List[str]):
        reasons = []
        interest_score = 0.0
        project_score = 0.0
        
        kw_lower = keyword.lower()
        interest_match = re.search(r"Research Interests: (.*?)(?:\n|$)", content)
        if interest_match:
            interests_str = interest_match.group(1)
            interests_list = [i.strip() for i in interests_str.split(',') if i.strip()]
            total_interests = len(interests_list)
            
            if total_interests > 0:
                matched = [i for i in interests_list if kw_lower in i.lower()]
                if matched:
                    ratio = len(matched) / total_interests
                    interest_score = ratio * 60.0
                    reasons.append(f"Matched {len(matched)} of {total_interests} research interests")

        project_match = re.search(r"Projects & Publications: (.*?)(?:\n|$)", content)
        if project_match:
            projs_str = project_match.group(1)
            projs_list = [p.strip() for p in projs_str.split(';') if p.strip()]
            total_projs = len(projs_list)
            
            if total_projs > 0:
                matched = [p for p in projs_list if kw_lower in p.lower()]
                if matched:
                    ratio = len(matched) / total_projs
                    project_score = ratio * 40.0
                    reasons.append(f"Matched {len(matched)} of {total_projs} projects")

        if not reasons and kw_lower in content.lower():
            return 50.0, ["Keyword mentioned in profile"]

        total_score = interest_score + project_score
        return total_score, reasons

    def search_faculty(self, query_text: str, top_k: int = 100) -> List[Dict[str, Any]]:
        if not query_text.strip():
            return []

        try:
            try:
                keyword_docs = self.vector_store.similarity_search(
                    query_text, k=500, filter={"$contains": query_text}
                )
            except Exception:
                broad_docs = self.vector_store.similarity_search(query_text, k=500)
                keyword_docs = [d for d in broad_docs if query_text.lower() in d.page_content.lower()]

            keyword_results = {}
            
            for doc in keyword_docs:
                fac_id = doc.metadata.get("faculty_id")
                if not fac_id: continue
                score, reasons = self._calculate_keyword_score(doc.page_content, query_text)
                if score == 0 and query_text.lower() in doc.page_content.lower():
                    score = 25.0 
                    reasons = ["Keyword found in text"]
                if fac_id not in keyword_results or keyword_results[fac_id]['score'] < score:
                    keyword_results[fac_id] = {
                        "metadata": doc.metadata,
                        "score": score,
                        "reasons": reasons,
                        "content": doc.page_content
                    }

            vector_candidates = self.vector_store.similarity_search_with_score(query_text, k=top_k * 3)            
            semantic_results = {}            
            rerank_inputs = []
            candidate_map = []

            for doc, dist_score in vector_candidates:
                fac_id = doc.metadata.get("faculty_id")
                if not fac_id: continue
                candidate_map.append((fac_id, doc, dist_score))
                rerank_inputs.append((query_text, doc.page_content))

            if rerank_inputs:
                rerank_scores = self.reranker.predict(rerank_inputs)
                
                for i, (fac_id, doc, dist_score) in enumerate(candidate_map):
                    rerank_val = rerank_scores[i]
                    
                    if rerank_val < -0.5: 
                        continue
                    
                    normalized_score = 1 / (1 + math.exp(-rerank_val / 3)) * 100
                    
                    if normalized_score > 30.0:
                        if fac_id not in semantic_results or semantic_results[fac_id]['score'] < normalized_score:
                            semantic_results[fac_id] = {
                                "metadata": doc.metadata,
                                "score": normalized_score,
                                "reasons": [f"Semantic Match ({normalized_score:.1f}%)"],
                                "content": doc.page_content
                            }
            final_results = {}            
            for fac_id, data in keyword_results.items():
                kw_score = data['score']
                reasons = data['reasons']
                
                if fac_id in semantic_results:
                    sem_score = semantic_results[fac_id]['score']
                    reasons.append(f"Semantic Match ({sem_score:.1f}%)")
                    
                    final_score = (kw_score + sem_score) / 2 + 10.0 
                else:
                    final_score = kw_score
                
                final_results[fac_id] = {
                    "faculty_id": fac_id,
                    "name": data["metadata"].get("name"),
                    "department": data["metadata"].get("department"),
                    "similarity_pct": round(min(final_score, 100), 2),
                    "match_reasons": reasons
                }

            for fac_id, data in semantic_results.items():
                if fac_id not in final_results:
                    final_results[fac_id] = {
                        "faculty_id": fac_id,
                        "name": data["metadata"].get("name"),
                        "department": data["metadata"].get("department"),
                        "similarity_pct": round(data['score'], 2),
                        "match_reasons": data['reasons']
                    }

            sorted_results = sorted(final_results.values(), key=lambda x: x['similarity_pct'], reverse=True)            
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