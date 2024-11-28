Data-Source-API-Analyst-Test

# GitHub API Endpoints

## Search Repositories
**Endpoint**: `GET /search/repositories`
[Docs](https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28#search-repositories)

### Required Parameters:
- `q`: The query string to search for repositories (e.g., "machine learning").

### Optional Parameters:
- `sort`: Sort the results (e.g., by `stars`, `forks`).
- `order`: Order the results (`desc` or `asc`).
- `page`: The page number for pagination.
- `per_page`: The number of results per page.

### Example Request:
```http
GET https://api.github.com/search/repositories?q=machine+learning&sort=stars&order=desc&page=1&per_page=10
```
---

## Get Commits
**Endpoint**: `GET /repos/{owner}/{repo}/commits`
[Docs](https://docs.github.com/en/rest/commits/commits)

### Required Parameters:
- `owner`: The repository owner (e.g., "octocat").
- `repo`: The repository name (e.g., "Hello-World").

### Optional Parameters:
- `sha`: The commit SHA, branch name, or tag.
- `path`: Restricts commits to a specific file path.
- `author`: Restricts commits to a specific author.
- `per_page`: The number of results per page.

### Example Request:
```http
GET https://api.github.com/repos/octocat/Hello-World/commits?sha="7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"&author=johndoe&per_page=10
```

---

## Get Contents
**Endpoint**: `GET /repos/{owner}/{repo}/contents/{path}`
[Docs](https://docs.github.com/en/rest/repos/contents)

### Required Parameters:
- `owner`: The repository owner (e.g., "octocat").
- `repo`: The repository name (e.g., "Hello-World").
- `path`: The path of the file or directory (e.g., "README.md").

### Example Request:
```http
GET https://api.github.com/repos/octocat/Hello-World/contents/README.md?ref=master
```
