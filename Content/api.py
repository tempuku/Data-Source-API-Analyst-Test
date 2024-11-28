import asyncio
import os
from typing import Any, Dict, List, Optional

import aiohttp

# Type aliases for clarity
Headers = Dict[str, str]
JsonData = Dict[str, Any]


class APIError:
    """Represents an API error with status code and message."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message

    def __str__(self) -> str:
        return f"Error {self.status_code}: {self.message}"

    def __repr__(self) -> str:
        return f"Error {self.status_code}: {self.message}"


class Response:
    """Abstract class for HTTP responses."""

    @property
    def status(self) -> int:
        raise NotImplementedError

    @property
    def headers(self) -> Headers:
        raise NotImplementedError

    async def text(self) -> str:
        raise NotImplementedError

    async def json(self) -> List[JsonData]:
        raise NotImplementedError


class aiohttpResponse(Response):
    """Adapter for aiohttp.ClientResponse."""

    def __init__(self, response: aiohttp.ClientResponse) -> None:
        self._response = response

    @property
    def status(self) -> int:
        return self._response.status

    @property
    def headers(self) -> Headers:
        return dict(self._response.headers)

    async def text(self) -> str:
        return await self._response.text()

    async def json(self) -> List[JsonData]:
        return await self._response.json()


class Session:
    """Abstract class for HTTP sessions."""

    async def request(
        self, method: str, url: str, **kwargs: Any
    ) -> Response | APIError:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError


class aiohttpSession(Session):
    """Implementation of Session using aiohttp."""

    def __init__(self) -> None:
        self._session = aiohttp.ClientSession()

    async def request(
        self, method: str, url: str, **kwargs: Any
    ) -> Response | APIError:
        try:
            response = await self._session.request(method, url, **kwargs)
            return aiohttpResponse(response)
        except aiohttp.ClientError as e:
            return APIError(0, f"Request failed: {str(e)}")

    async def close(self) -> None:
        await self._session.close()


class SessionManager:
    """Context manager for handling sessions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    async def __aenter__(self) -> Session:
        return self._session

    async def __aexit__(
        self, exc_type: Optional[type], exc: Optional[Exception], tb: Optional[Any]
    ) -> None:
        await self._session.close()


async def request_dispatcher(
    session: Session, method: str, url: str, **kwargs: Any
) -> Response | APIError:
    """Handles retries and error responses for requests."""
    max_retries = kwargs.pop("max_retries", 5)
    retry_delay = kwargs.pop("retry_delay", 60)

    for attempt in range(max_retries):
        response = await session.request(method, url, **kwargs)
        if isinstance(response, APIError):
            return response

        if response.status == 200:
            return response
        elif response.status == 401:
            return APIError(401, "Unauthorized access. Check your token.")
        elif response.status == 403:
            retry_after = int(response.headers.get("Retry-After", retry_delay))
            await asyncio.sleep(retry_after)
        elif response.status == 404:
            return APIError(404, "Resource not found.")
        elif response.status >= 500:
            await asyncio.sleep(retry_delay)
        else:
            return APIError(
                response.status, f"Unexpected error: {await response.text()}"
            )

    return APIError(0, "Max retries reached without success.")


async def fetch_paginated_data(
    session: Session,
    url: str,
    headers: Headers,
    params: Optional[Dict[str, Any]] = None,
    max_pages: int = 5,
    per_page: int = 30,
    **kwargs: Any,
) -> List[JsonData] | APIError:
    """Fetches paginated data from an API."""
    results = []
    page_count = 0

    while url and page_count < max_pages:
        if params is None:
            params = {}
        params["per_page"] = per_page

        response = await request_dispatcher(
            session, "GET", url, headers=headers, params=params, **kwargs
        )
        if isinstance(response, APIError):
            return response

        data = await response.json()
        results.append(data)

        # Fetch next page URL from "Link" header
        url = get_next_page_url(response)
        page_count += 1

    return results


def get_next_page_url(response: Response) -> str:
    """Parses the 'Link' header to find the URL for the next page."""
    link_header = response.headers.get("Link", "")
    if link_header:
        for link in link_header.split(","):
            if 'rel="next"' in link:
                return link[link.find("<") + 1 : link.find(">")]
    return ""


def generate_headers(auth_token: str, app_name: str, api_version: str) -> Headers:
    """Generates headers for GitHub API requests."""
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {auth_token}",
        "User-Agent": app_name,
        "X-GitHub-Api-Version": api_version,
    }


def parse_repositories(data: List[JsonData]) -> List[JsonData]:
    repos_info = []
    for page in data:
        for item in page["items"]:
            repos_info.append({"name": item["name"], "html_url": item["html_url"]})

    return repos_info


async def search_repositories(
    session: Session,
    headers: Headers,
    query: str,
    max_pages: int = 5,
    per_page: int = 30,
) -> List[JsonData] | APIError:
    """Searches for repositories matching a query."""
    url = "https://api.github.com/search/repositories"
    params = {"q": query}
    response = await fetch_paginated_data(
        session, url, headers, params, max_pages, per_page
    )
    if isinstance(response, APIError):
        return response
    return parse_repositories(response)


def parse_commit_data(data: List[JsonData]) -> List[JsonData]:
    commits_info = []
    for page in data:
        for commit in page:
            commits_info.append(
                {
                    "author": {
                        "name": commit["commit"]["author"]["name"],
                        "email": commit["commit"]["author"]["email"],
                        "date": commit["commit"]["author"]["date"],
                    },
                    "sha": commit["sha"],
                    "message": commit["commit"]["message"],
                }
            )
    return commits_info


async def get_commits(
    session: Session,
    headers: Headers,
    owner: str,
    repo: str,
    max_pages: int = 5,
    per_page: int = 30,
) -> List[JsonData] | APIError:
    """Fetches commit history for a repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    response = await fetch_paginated_data(
        session, url, headers, None, max_pages, per_page
    )
    if isinstance(response, APIError):
        return response
    return parse_commit_data(response)


async def parse_content_info(data: List[JsonData]) -> List[JsonData]:
    files_info = []
    for item in data:
        files_info.append({"path": item["path"], "download_link": item["download_url"]})
    return files_info


async def get_contents(
    session: Session,
    headers: Headers,
    owner: str,
    repo: str,
    path: str,
) -> JsonData | APIError:
    """Fetches the contents of a file or directory in a repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    response = await request_dispatcher(session, "GET", url, headers=headers)
    if isinstance(response, APIError):
        return response
    return await parse_content_info(await response.json())


async def main() -> None:
    """Main function to demonstrate API usage."""
    auth_token = os.getenv("GITHUB_TOKEN")
    if not auth_token:
        raise ValueError(
            "GitHub token not found. Set the GITHUB_TOKEN environment variable."
        )

    app_name = "GitHub-API-Client"
    api_version = os.getenv("GITHUB_API_VERSION")
    if not api_version:
        api_version = "2022-11-28"
    headers = generate_headers(auth_token, app_name, api_version)

    async with SessionManager(aiohttpSession()) as session:
        tasks = [
            search_repositories(
                session, headers, "machine learning", max_pages=3, per_page=3
            ),
            get_commits(
                session, headers, "octocat", "Hello-World", max_pages=2, per_page=3
            ),
            get_contents(session, headers, "octocat", "Hello-World", ""),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, APIError):
                print(f"API Error: {result}")
            else:
                print(result)


if __name__ == "__main__":
    asyncio.run(main())
