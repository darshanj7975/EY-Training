import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
#from langchain.schema import Document
from langchain_groq import ChatGroq

# 🔑 API KEY (better: use env variable)
os.environ["GROQ_API_KEY"] = "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"

faqs = [
"Return policy: 7 days refund",
"Shipping takes 3-5 days",
"UPI, cards accepted",
"Account deletion via support",
"Track order using ID",
"24/7 customer support",
"Warranty covers defects",
"Cancel within 2 hours",
"COD available in selected cities",
"Login reset via OTP"
]

# 🔍 Embeddings (offline)
emb = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

db = FAISS.from_documents(
    [Document(page_content=f) for f in faqs],
    emb
)

# 🤖 Groq LLM (FIXED)
llm = ChatGroq(
    model="llama3-70b-8192",
    api_key=os.environ["GROQ_API_KEY"]
)

print("Smart FAQ Bot ready (type exit to stop)")

while True:
    q = input("\nYou: ")
    if q.lower() == "exit":
        break

    docs = db.similarity_search_with_score(q, k=2)

    context = "\n".join([d[0].page_content for d in docs])
    scores = [round(d[1], 3) for d in docs]

    prompt = f"""
Answer ONLY using context below.

Context:
{context}

Question: {q}

Give a short and precise answer.
"""

    ans = llm.invoke(prompt).content

    print("\nBot:", ans)
    print("Similarity scores:", scores)