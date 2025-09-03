from typing import List, Dict, Union, Optional, Tuple
import os
import dashscope

class DashscopeReranker:
    """
    DashScope TextReRank 重排器：
      - rerank 返回与 OpenAIEmbeddingReranker 一致的结构：含 index/document/score
      - get_reranked_documents 返回 (docs, indices) 二元组
    """
    def __init__(self, top_k: int = 5, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("RERANK_API_KEY")
        self.model = model or os.getenv("RERANK_MODEL")
        self.top_k = top_k
        if not self.api_key:
            raise ValueError("No DashScope API key provided (RERANK_API_KEY).")

    async def _call_once(
        self, query: str, documents: List[str], top_k: int
    ) -> List[Dict[str, Union[str, float, int]]]:
        dashscope.api_key = self.api_key
        resp = dashscope.TextReRank.call(
            model=self.model,
            query=query,
            documents=documents,
            top_n=top_k,
            return_documents=True,
        )
        # 健壮性检查
        if not resp or "output" not in resp or "results" not in resp["output"]:
            msg = getattr(resp, "message", None) or getattr(resp, "code", None) or "Unknown DashScope rerank error"
            raise RuntimeError(f"DashScope rerank failed: {msg}")

        results = resp["output"]["results"]
        out: List[Dict[str, Union[str, float, int]]] = []
        for r in results:
            idx = r.get("index")
            score = r.get("relevance_score")
            if idx is None or score is None:
                continue
            out.append({
                "index": int(idx),
                "document": documents[int(idx)].strip(),
                "score": float(score),
            })

        # 稳妥起见再按分数降序
        out.sort(key=lambda x: x["score"], reverse=True)
        return out

    async def rerank(
        self,
        query: Union[str, List[str]],
        documents: List[str],
        top_k: Optional[int] = None,
    ) -> Union[
        List[Dict[str, Union[str, float, int]]],
        List[List[Dict[str, Union[str, float, int]]]],
    ]:
        """
        - query 为 str -> 返回 List[{"index": int, "document": str, "score": float}]
        - query 为 List[str] -> 返回 List[List[...]]，与 queries 对齐
        """
        if isinstance(query, str):
            ranked = await self._call_once(query, documents, top_k)
            return ranked[:top_k]

        all_results: List[List[Dict[str, Union[str, float, int]]]] = []
        for q in query:
            ranked = await self._call_once(q, documents, top_k)
            all_results.append(ranked[:top_k])
        return all_results

    async def get_reranked_documents(
        self,
        query: Union[str, List[str]],
        documents: List[str],
    ) -> Union[
        Tuple[List[str], List[int]],
        Tuple[List[List[str]], List[List[int]]],
    ]:
        """
        一次性返回 (docs, indices)
        - 单查询: (List[str], List[int])
        - 多查询: (List[List[str]], List[List[int]])
        """
        results = await self.rerank(query, documents, top_k=self.top_k)

        if isinstance(query, str):
            docs_out = [x["document"] for x in results]          # type: ignore[index]
            idxs_out = [int(x["index"]) for x in results]         # type: ignore[index]
            return docs_out, idxs_out

        docs_out = [[x["document"] for x in r] for r in results]  # type: ignore[index]
        idxs_out = [[int(x["index"]) for x in r] for r in results] # type: ignore[index]
        return docs_out, idxs_out
