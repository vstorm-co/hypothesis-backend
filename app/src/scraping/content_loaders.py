from io import BytesIO
from logging import getLogger

from docx import Document
from langchain_community.document_transformers import BeautifulSoupTransformer

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
    from langchain_community.document_loaders import AsyncHtmlLoader

    loader: AsyncHtmlLoader = AsyncHtmlLoader([url])
    docs = loader.load()

    bs_transformer: BeautifulSoupTransformer = BeautifulSoupTransformer()
    docs_transformed = bs_transformer.transform_documents(docs)

    return docs_transformed[0].page_content
