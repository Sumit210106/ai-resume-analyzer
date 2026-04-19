from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

def create_chunks(text):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=30
    )
    return splitter.split_text(text)

def create_vectorstore(chunks):
    return FAISS.from_texts(chunks, embeddings)


def retrieve_chunks(vectorstore, query):
    docs = vectorstore.similarity_search(query, k=2)
    return "\n\n".join([doc.page_content for doc in docs])