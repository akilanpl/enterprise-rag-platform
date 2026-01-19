from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy

def run_eval(dataset):
    return evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy]
    )
