from abc import ABC, abstractmethod
from typing import List, Dict, Union, Optional
from openai import AsyncOpenAI
import torch
import os
from dotenv import load_dotenv


class BaseSemanticSearcher(ABC):
    """
    Abstract base class for semantic search implementations.
    """

    @abstractmethod
    def _get_embeddings(self, texts: List[str]) -> torch.Tensor:
        pass

    async def calculate_scores(
        self,
        queries: List[str],
        documents: List[str],
    ) -> torch.Tensor:
        query_embeddings = await self._get_embeddings(queries)
        doc_embeddings = await self._get_embeddings(documents)
        scores = query_embeddings @ doc_embeddings.T
        scores = torch.softmax(scores, dim=-1)
        return scores

    async def rerank(
        self,
        query: Union[str, List[str]],
        documents: List[str],
        top_k: int = 5,
    ) -> List[Dict[str, Union[str, float]]]:
        queries = [query] if isinstance(query, str) else query
        scores = await self.calculate_scores(queries, documents)

        results = []
        for query_scores in scores:
            top_indices = torch.topk(query_scores, min(top_k, len(documents)), dim=0)
            query_results = [
                {
                    "document": documents[idx.item()],
                    "score": score.item()
                }
                for score, idx in zip(top_indices.values, top_indices.indices)
            ]
            results.append(query_results)

        return results[0] if isinstance(query, str) else results

    async def get_reranked_documents(
        self,
        query: Union[str, List[str]],
        documents: List[str],
        top_k: int = 5
    ) -> Union[List[str], List[List[str]]]:
        results = await self.rerank(query, documents, top_k)
        if isinstance(query, str):
            return [x['document'].strip() for x in results]
        return [[x['document'].strip() for x in r] for r in results]


class OpenAIEmbeddingReranker(BaseSemanticSearcher):
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None):
        load_dotenv()
        self.api_key = api_key or os.getenv("EMBEDDING_API_KEY")
        self.base_url = base_url or os.getenv("EMBEDDING_BASE_URL")
        self.model = model or os.getenv("EMBEDDING_MODEL_NAME")
        if not self.api_key:
            raise ValueError("No OpenAI API key provided")
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        self.model = model

    async def _get_embeddings(self, texts: List[str]) -> torch.Tensor:
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        embeddings = [e.embedding for e in response.data]
        return torch.tensor(embeddings)

