def trace(query, docs, answer):
    return {
        "query": query,
        "doc_ids": [d.metadata.get("doc_id") for d in docs],
        "answer_length": len(answer)
    }
