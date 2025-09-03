from dotenv import load_dotenv
load_dotenv()

import gradio as gr
import asyncio

from agent import ToolsGraph
from pools import BrowserPool, CrawlerPool

from ultis import QueryRequest, SplitRequest, RerankRequest
from reranker import OpenAIEmbeddingReranker, Chunker, DashscopeReranker


async def search_answer(question: str, engine: str):
    browser_pool = BrowserPool(pool_size=1)
    crawler_pool = CrawlerPool(pool_size=1)
    params = QueryRequest(
        question=question,
        engine=engine,
        split=SplitRequest(chunk_size=512, chunk_overlap=128, separators=["\n\n", "\n"]),
        rerank=RerankRequest(top_k=5)
    )

    chunker = Chunker(chunk_size=params.split.chunk_size, chunk_overlap=params.split.chunk_overlap, separators=params.split.separators)
    reranker = DashscopeReranker(top_k=params.rerank.top_k)
    
    graph = ToolsGraph(browser_pool, crawler_pool, engine=params.engine, chunker=chunker, reranker=reranker)
    graph = ToolsGraph(browser_pool, crawler_pool, engine=engine)
    result = await graph.run(question)
    return result


# 用 sync wrapper 包装 async 函数（Gradio 不直接支持 async）
def sync_search_answer(question, engine):
    return asyncio.run(search_answer(question, engine))

# 启动界面
with gr.Blocks() as demo:
    gr.Markdown("# 🔍 多引擎搜索问答")
    question = gr.Textbox(label="请输入你的问题")
    engine = gr.Radio(["bing", "quark", "baidu", "sougou"], value="bing", label="选择搜索引擎")
    output = gr.Textbox(label="答案")

    btn = gr.Button("提交查询")
    btn.click(fn=sync_search_answer, inputs=[question, engine], outputs=output)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)  # 不要传 share=True

