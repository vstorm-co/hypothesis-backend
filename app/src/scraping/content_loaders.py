from io import BytesIO
from logging import getLogger

from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_transformers import BeautifulSoupTransformer

from src.scraping.loaders import AsyncChromiumLoader

logger = getLogger(__name__)


def read_docx_from_bytes(content):
    try:
        doc = Document(BytesIO(content))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        logger.error(f"Failed to read docx file: {e}")
        return None


async def get_content_from_url(url: str):
    loader: AsyncChromiumLoader = AsyncChromiumLoader(urls=[url])
    docs = await loader.load()

    bs_transformer: BeautifulSoupTransformer = BeautifulSoupTransformer()
    docs_transformed = bs_transformer.transform_documents(docs)

    return docs_transformed[0].page_content


async def get_pdf_content_from_url(url: str, headers: dict | None = None):
    loader: PyPDFLoader = PyPDFLoader(url, headers=headers)
    splitter: RecursiveCharacterTextSplitter = (
        RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=127_000,
            chunk_overlap=0,
        )
    )
    pages = loader.load_and_split(text_splitter=splitter)

    if pages:
        return pages[0].page_content

    return ""
