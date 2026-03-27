import streamlit as st
import requests
import numpy as np
import nltk
import os
from bs4 import BeautifulSoup
from groq import Groq
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pypdf import PdfReader

nltk.download("punkt")

# =========================
# UI CONFIG
# =========================
st.set_page_config(page_title="Medical RAG Assistant", layout="wide")
st.title("🩺 Advanced Public Health RAG Assistant")

# =========================
# GROQ API KEY INPUT
# =========================
api_key = st.sidebar.text_input("Enter Groq API Key", type="password")

if not api_key:
    st.warning("Please enter your Groq API Key to continue.")
    st.stop()

client = Groq(api_key=api_key)

# =========================
# SOURCE URLS
# =========================
SOURCES = {
    "WHO CVD": "https://www.who.int/news-room/fact-sheets/detail/cardiovascular-diseases-(cvds)",
    "WHO Diabetes": "https://www.who.int/news-room/fact-sheets/detail/diabetes",
    "CDC Heart Disease": "https://www.cdc.gov/heartdisease/about.htm",
    "AHA Prevention": "https://www.heart.org/en/healthy-living"
}

# =========================
# SCRAPER
# =========================
def scrape_website(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        paragraphs = soup.find_all("p")
        return " ".join([p.get_text() for p in paragraphs])
    except:
        return ""

# =========================
# CHUNKING
# =========================
def chunk_text(text, chunk_size=800, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

# =========================
# LOAD DOCUMENTS
# =========================
@st.cache_resource
def load_documents():
    documents = []
    doc_names = []

    for name, url in SOURCES.items():
        content = scrape_website(url)
        if len(content) > 500:
            chunks = chunk_text(content)
            for chunk in chunks:
                documents.append(chunk)
                doc_names.append(name)

    # Load local PDFs
    if os.path.exists("documents"):
        for file in os.listdir("documents"):
            if file.endswith(".pdf"):
                reader = PdfReader(os.path.join("documents", file))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                chunks = chunk_text(text)
                for chunk in chunks:
                    documents.append(chunk)
                    doc_names.append(file)

    documents = list(set(documents))
    documents = [d for d in documents if len(d) > 300]

    return documents, doc_names

documents, doc_names = load_documents()

# =========================
# VECTORIZE
# =========================
vectorizer = TfidfVectorizer(stop_words="english")
tfidf_matrix = vectorizer.fit_transform(documents)

# =========================
# RETRIEVAL
# =========================
def hybrid_retrieve(query, top_k=5):
    query_vec = vectorizer.transform([query])
    semantic_scores = cosine_similarity(query_vec, tfidf_matrix)[0]

    keyword_scores = []
    for doc in documents:
        overlap = sum(1 for w in query.lower().split() if w in doc.lower())
        keyword_scores.append(overlap)

    keyword_scores = np.array(keyword_scores)
    if keyword_scores.max() > 0:
        keyword_scores = keyword_scores / keyword_scores.max()

    final_scores = 0.6 * semantic_scores + 0.4 * keyword_scores
    top_indices = final_scores.argsort()[-top_k:][::-1]

    return top_indices, final_scores

# =========================
# RERANKER
# =========================
def rerank(query, indices):
    candidate_docs = [documents[i] for i in indices]
    local_vectorizer = TfidfVectorizer(stop_words="english")
    local_matrix = local_vectorizer.fit_transform(candidate_docs + [query])

    query_vec = local_matrix[-1]
    doc_vecs = local_matrix[:-1]

    scores = cosine_similarity(query_vec, doc_vecs)[0]
    ranked = scores.argsort()[::-1]

    return [indices[i] for i in ranked], scores

# =========================
# PROMPT
# =========================
SYSTEM_PROMPT = """
You are an Indian Public Health Clinical Assistant.

Follow this reasoning internally:
1. Identify condition.
2. Extract evidence-based facts.
3. Do not invent dosages.
4. Escalate emergency cases.

Respond in structured format:

## Overview
## Key Clinical Points
## Treatment
## Prevention
## When to Seek Immediate Care
## Sources
"""

# =========================
# GENERATE RESPONSE
# =========================
def generate_response(query, context, sources, confidence):
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role":"system","content": SYSTEM_PROMPT + "\nContext:\n" + context},
            {"role":"user","content": query}
        ],
        temperature=0.2
    )

    answer = completion.choices[0].message.content
    return answer

# =========================
# UI QUERY
# =========================
query = st.text_input("Ask a health-related question:")

if query:
    with st.spinner("Analyzing and retrieving evidence..."):

        indices, scores = hybrid_retrieve(query)
        reranked_indices, rerank_scores = rerank(query, indices)

        top_docs = reranked_indices[:2]

        context = "\n\n".join([documents[i] for i in top_docs])
        sources = [doc_names[i] for i in top_docs]
        confidence = float(np.mean(rerank_scores))

        response = generate_response(query, context, sources, confidence)

    st.markdown("## 🧠 Assistant Response")
    st.markdown(response)

    st.markdown("### 📊 Confidence Score")
    st.progress(min(confidence, 1.0))

    with st.expander("📚 Retrieved Sources"):
        for s in sources:
            st.write(s)