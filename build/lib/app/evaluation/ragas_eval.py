"""Optional adapter: install ragas separately using a version validated for your dataset."""


def run_eval(dataset):
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, faithfulness

    return evaluate(dataset, metrics=[faithfulness, answer_relevancy])


def retrieval_recall(expected_document_ids, citations):
    expected = set(expected_document_ids)
    if not expected:
        raise ValueError("Expected document IDs cannot be empty")
    retrieved = {citation["document_id"] for citation in citations}
    return len(expected & retrieved) / len(expected)
