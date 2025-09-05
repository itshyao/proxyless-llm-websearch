from abc import ABC, abstractmethod
from typing import List, Dict, Union, Optional, Tuple
from openai import AsyncOpenAI
import numpy as np
import os


def _softmax_stable(x: np.ndarray, axis: int = -1) -> np.ndarray:
    x_max = np.max(x, axis=axis, keepdims=True)
    exp_x = np.exp(x - x_max)
    return exp_x / np.sum(exp_x, axis=axis, keepdims=True)


class BaseSemanticSearcher(ABC):
    @abstractmethod
    async def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Return a 2D NumPy array of shape (len(texts), embedding_dim)."""
        pass

    async def calculate_scores(
        self,
        queries: List[str],
        documents: List[str],
    ) -> np.ndarray:
        query_embeddings = await self._get_embeddings(queries)   # (Q, D)
        doc_embeddings = await self._get_embeddings(documents)   # (N, D)
        scores = query_embeddings @ doc_embeddings.T             # (Q, N)
        scores = _softmax_stable(scores, axis=-1)
        return scores

    async def rerank(
        self,
        query: Union[str, List[str]],
        documents: List[str],
        top_k: Optional[int] = None,   # <= 改：可选，默认用实例的 self.top_k
    ) -> Union[
        List[Dict[str, Union[str, float, int]]],
        List[List[Dict[str, Union[str, float, int]]]]
    ]:
        """
        每项包含:
          - index: 在原始 documents 中的索引 (int)
          - document: 文本 (str)
          - score: 分数 (float)
        """
        queries = [query] if isinstance(query, str) else query
        scores = await self.calculate_scores(queries, documents)  # (Q, N)

        # 优先使用调用时的 top_k，否则回退到实例属性 self.top_k，再不行用 5
        k_conf = top_k if top_k is not None else getattr(self, "top_k", 5)

        results: List[List[Dict[str, Union[str, float, int]]]] = []
        for q_scores in scores:  # (N,)
            k = min(int(k_conf), len(documents))
            top_indices = np.argsort(-q_scores)[:k]
            query_results = [
                {
                    "index": int(idx),
                    "document": documents[int(idx)].strip(),
                    "score": float(q_scores[int(idx)]),
                }
                for idx in top_indices
            ]
            results.append(query_results)

        return results[0] if isinstance(query, str) else results

    async def get_reranked_documents(
        self,
        query: Union[str, List[str]],
        documents: List[str],
        top_k: Optional[int] = None,   # <= 同样可选，默认走实例的 self.top_k
    ) -> Union[
        Tuple[List[str], List[int]],
        Tuple[List[List[str]], List[List[int]]]
    ]:
        """
        返回二元组：(docs, indices)
        - 若 query 是 str： (List[str], List[int])
        - 若 query 是 List[str]： (List[List[str]], List[List[int]])
        """
        results = await self.rerank(query, documents, top_k=top_k)

        if isinstance(query, str):
            docs_out = [x["document"] for x in results]          # type: ignore[index]
            idxs_out = [int(x["index"]) for x in results]         # type: ignore[index]
            return docs_out, idxs_out

        docs_out = [[x["document"] for x in r] for r in results]  # type: ignore[index]
        idxs_out = [[int(x["index"]) for x in r] for r in results] # type: ignore[index]
        return docs_out, idxs_out


class OpenAIEmbeddingReranker(BaseSemanticSearcher):
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        top_k: int = 5,   # <= 在实例化时传入
    ):
        self.api_key = api_key or os.getenv("EMBEDDING_API_KEY")
        self.base_url = base_url or os.getenv("EMBEDDING_BASE_URL")
        self.model = model or os.getenv("EMBEDDING_MODEL_NAME")
        self.top_k = int(top_k)  # 挂到实例上，供基类方法使用
        if not self.api_key:
            raise ValueError("No OpenAI API key provided")
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        embeddings = [e.embedding for e in response.data]
        return np.asarray(embeddings, dtype=np.float32)
