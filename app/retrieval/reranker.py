class Reranker:
    def __init__(self, model_name=None, revision=None):
        self.model = None
        if model_name:
            from sentence_transformers import CrossEncoder

            self.model = CrossEncoder(model_name, revision=revision, trust_remote_code=False)

    def rerank(self, query, docs, top_k):
        if not docs:
            return []
        if self.model:
            scores = self.model.predict([[query, doc.page_content] for doc in docs])
            # Explicit key prevents comparing Document objects when scores tie.
            return [
                doc for _, doc in sorted(zip(scores, docs), key=lambda pair: pair[0], reverse=True)
            ][:top_k]
        return sorted(docs, key=lambda doc: doc.score, reverse=True)[:top_k]
