import asyncio


async def main():
    # url = "https://via.hypothes.is/https://www.youtube.com/watch?v=OuoIehtMHsE"
    url = "https://www.youtube.com/watch?v=OuoIehtMHsE"

    # get the data from the url
    from langchain_community.document_loaders import YoutubeLoader

    loader = YoutubeLoader.from_youtube_url(url, add_video_info=False)
    docs = loader.load()

    res = ""
    for doc in docs:
        res += doc.page_content

    return 0


if __name__ == "__main__":
    asyncio.run(main())
