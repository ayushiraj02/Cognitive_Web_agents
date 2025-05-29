import os
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import TextLoader
# langchain_community.document_loaders.TextLoader

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
print("GOOGLE_API_KEY:", GOOGLE_API_KEY)

# Directory constants
def make_file():
    VECTOR_STORE_DIR = "vectorstore"
    TEMP_DIR = "temp"
    SCRAPED_DATA_DIR = "scraped_data"
    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(SCRAPED_DATA_DIR, exist_ok=True)
    return VECTOR_STORE_DIR, TEMP_DIR, SCRAPED_DATA_DIR

VECTOR_STORE_DIR, TEMP_DIR, SCRAPED_DATA_DIR = make_file()

def scrape_website(base_url, client_name):
    try:
        response = requests.get(base_url)
        if response.status_code != 200:
            print(f"Failed to load base URL: {base_url}")
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all('a', href=True)

        base_domain = urlparse(base_url).netloc
        hrefs = set()

            

        for link in links:
            href = link['href']
            if href.startswith('#'):
                continue
            full_url = urljoin(base_url, href)
            if urlparse(full_url).netloc == base_domain:
                hrefs.add(full_url)

        scraped_texts = []
        combined_text = ""

        client_folder = os.path.join(SCRAPED_DATA_DIR, client_name)
        os.makedirs(client_folder, exist_ok=True)
        file_path = os.path.join(client_folder, "combined_scrape.txt")

        for url in hrefs:
            try:
                page_response = requests.get(url)
                if page_response.status_code == 200:
                    page_soup = BeautifulSoup(page_response.text, "html.parser")
                    page_text = page_soup.get_text(separator="\n", strip=True)

                combined_text += f"\n\n===== {url} =====\n\n{page_text}"
                scraped_texts.append({'url': url, 'text': page_text})
                print(f"Fetched: {url}")
            except Exception as page_error:
                print(f"Error fetching {url}: {page_error}")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(combined_text)
        print(f"Saved combined content to: {file_path}")

        return scraped_texts
    
    except Exception as e:
        print(f"Main scrape error: {e}")
        return []




# def scrape_and_create_bot(company_url, bot_name, username, api_key,app):
#     try:
#         print(f"[THREAD] Scraping content from URL: {company_url}")
#         content = scrape_website(company_url, bot_name)

#         if not content:
#             print("No content scraped.")
#             return
        
#         all_text = " ".join([item['text'] for item in content])
#         clean_text = preprocess_text(all_text)
#         print(f"[THREAD] Cleaned text preview: {clean_text[:100]}...")

#         store_vectors(clean_text, bot_name)

#         app = create_app() 
#         with app.app_context(): 
#             # from app import db
#             new_bot = Bot(
#                 name=bot_name,
#                 owner=username,
#                 url=company_url,
#                 apikey=api_key
#             )
            
#             db.session.add(new_bot)
#             db.session.commit()

#         print(f"[THREAD] Bot created with ID: {new_bot.id}")

#     except Exception as e:
#         print(f"[THREAD] Error: {e}")

def preprocess_text(text):
    """Clean and preprocess text by removing unnecessary whitespaces and non-text elements."""
    # Remove extra whitespace, newlines and tabs
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_store_path(store_name: str) -> str:
    return os.path.join(VECTOR_STORE_DIR, store_name)

def store_exists(store_name: str) -> bool:
    return os.path.exists(get_store_path(store_name))

def text_file(filename: str, data: str) -> str:
    filepath = os.path.join(TEMP_DIR, f'{filename}.txt')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(data)
    return filepath

def store_vectors(text_data: str, store_name: str):
    embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    textfile = text_file(store_name, text_data)
    loader = TextLoader(textfile)
    docs = loader.load()
    print(f"Loaded {len(docs)} documents.")
    for doc in docs:
        print(f"Doc content type: {type(doc.page_content)} | Length: {len(doc.page_content)}")
    if not docs:
        print("No documents loaded. Exiting vector store creation.")
        return
    print(f"Creating vector store for {store_name} with {len(docs)} documents.")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = splitter.split_documents(docs)
    persist_dir = get_store_path(store_name)
    print(f"Number of splits: {len(splits)}")

    vectorstore = FAISS.from_documents(splits, embedding)
    vectorstore.save_local(persist_dir)
    os.remove(textfile)

def load_vectors(store_name: str):
    persist_dir = get_store_path(store_name)
    embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return FAISS.load_local(persist_dir, embedding, allow_dangerous_deserialization=True)

def create_qa_chain(vector_store):
    retriever = vector_store.as_retriever(search_type="similarity", k=3)
    llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0.2
    )
    return RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    return_source_documents=True
    )

def answer_query(store_name, question):
    vector_store = load_vectors(store_name)
    qa_chain = create_qa_chain(vector_store)
    return ask_rag(question, qa_chain)

def ask_rag(question: str, qa_chain):
    response = qa_chain.invoke({"query": question})

    return response["result"].strip()