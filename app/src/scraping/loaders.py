from typing import AsyncGenerator

from langchain_community.document_loaders import AsyncChromiumLoader
from langchain_core.documents import Document


# Fix the problem with nested async generators by
# overriding the AsyncChromiumLoader class from langchain_community
class CustomAsyncChromiumLoader(AsyncChromiumLoader):
    async def lazy_load(self) -> AsyncGenerator[Document, None]:  # type: ignore
        """
        Lazily load text content from the provided URLs.

        This method yields Documents one at a time as they're scraped,
        instead of waiting to scrape all URLs before returning.

        Yields:
            Document: The scraped content encapsulated within a Document object.

        """
        for url in self.urls:
            html_content = await self.ascrape_playwright(url)
            metadata = {"source": url}
            yield Document(page_content=html_content, metadata=metadata)

    async def load(self) -> list[Document]:  # type: ignore
        """
        Load and return all Documents from the provided URLs.

        Returns:
            List[Document]: A list of Document objects
            containing the scraped content from each URL.

        """
        return [doc async for doc in self.lazy_load()]
