import json
import time
import urllib.request
from urllib.error import URLError, HTTPError
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["GitHub"])

CACHE = {
    "contribs": {"data": None, "timestamp": 0},
    "repo": {"data": None, "timestamp": 0}
}
TTL = 3600  # 1 hour cache to avoid 403 Rate Limit

REPO = "param20h/PDF-Assistant-RAG"


def fetch_github(url: str, cache_key: str):
    """Fetch a GitHub API resource with a short in-memory fallback cache.

    Args:
        url: GitHub REST API URL to request.
        cache_key: Key in the module-level cache that stores the response.

    Returns:
        Parsed JSON data from GitHub, or the cached response when GitHub is
        rate-limited or temporarily unreachable.

    Raises:
        HTTPException: If GitHub fails and no cached data is available.
    """
    now = time.time()
    if CACHE[cache_key]["data"] is not None and now - CACHE[cache_key]["timestamp"] < TTL:
        return CACHE[cache_key]["data"]

    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "PDF-Assistant-RAG"
    })

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            CACHE[cache_key]["data"] = data
            CACHE[cache_key]["timestamp"] = now
            return data
    except HTTPError as e:
        # Fallback to cache if rate limited
        if CACHE[cache_key]["data"] is not None:
            return CACHE[cache_key]["data"]
        raise HTTPException(status_code=e.code, detail="GitHub API Error")
    except URLError as e:
        if CACHE[cache_key]["data"] is not None:
            return CACHE[cache_key]["data"]
        raise HTTPException(status_code=500, detail="Failed to connect to GitHub")


@router.get(
    "/github/stats",
    summary="Get public GitHub repository statistics",
    description=(
        "Returns cached contributor and repository counters for the public "
        "PDF-Assistant-RAG repository. The endpoint does not require user "
        "authentication because it only exposes public GitHub metadata."
    ),
)
def get_github_stats():
    """Return public contributor and repository statistics for the landing page."""
    contribs = fetch_github(f"https://api.github.com/repos/{REPO}/contributors?per_page=30", "contribs")
    repo = fetch_github(f"https://api.github.com/repos/{REPO}", "repo")

    return {
        "contributors": contribs if isinstance(contribs, list) else [],
        "stats": {
            "stargazers_count": repo.get("stargazers_count", 0),
            "forks_count": repo.get("forks_count", 0),
            "open_issues_count": repo.get("open_issues_count", 0)
        }
    }
