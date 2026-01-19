from langchain.document_loaders import PyPDFLoader

def load_pdf(path: str):
    loader = PyPDFLoader(path)
    return loader.load()
