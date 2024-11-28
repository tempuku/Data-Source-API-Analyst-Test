### Troubleshooting Guide for call api

This guide helps identify and resolve potential issues when using the call api function.

---

#### **1. Issue: Unauthorized Access (401 or 403 Errors)**

- **Symptoms**:
  - call api returns `APIError(401, "Unauthorized access")` or `APIError(403, "...")`.

- **Possible Causes**:
  1. Invalid or missing authentication token.
  2. The token lacks the necessary permissions for the API endpoint.

- **Steps to Resolve**:
  - Confirm that the `Authorization` header includes a valid token.
  - Verify token permissions in your API account settings.
  - Regenerate the token if unsure about its validity.
  - Test the token manually with tools like `curl`:
    ```bash
    curl -H "Authorization: token YOUR_TOKEN" https://api.github.com
    ```

---

#### **2. Issue: Slow or Blocked Requests**

- **Symptoms**:
  - Requests hang or take too long, and retries consume a lot of time.

- **Possible Causes**:
  1. API rate limiting (e.g., hitting GitHub's rate limit).
  2. Poor internet connectivity.
  3. Large `retry_delay` combined with retries for 503 errors.

- **Steps to Resolve**:
  - Check API rate limits:
    ```bash
    curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit
    ```
  - Reduce `max_retries` or `retry_delay` in the function arguments.
  - Log retry attempts and delays:
    ```python
    print(f"Retrying... Attempt: {attempt + 1}, Delay: {retry_delay}s")
    ```

---

#### **3. Issue: Misinterpreted Server Errors (500+ Status)**

- **Symptoms**:
  - Repeated 500+ errors without resolution.
  - call api doesn't recover even after retries.

- **Possible Causes**:
  1. API server is down or under maintenance.
  2. Your request payload or headers contain errors.

- **Steps to Resolve**:
  - Validate the request payload:
    ```python
    print(f"Payload: {kwargs.get('json')}")
    ```
  - Verify server status using API provider's status page (e.g., GitHub Status).
  - Use exponential backoff for retries to avoid overloading:
    ```python
    await asyncio.sleep(retry_delay * (2 ** attempt))
    ```

---

#### **4. Issue: Max Retries Reached Without Success**

- **Symptoms**:
  - call api consistently returns `APIError(0, "Max retries reached without success")`.

- **Possible Causes**:
  1. Persistent API errors (e.g., server issues, invalid payload).
  2. Large `max_retries` leading to hitting the retry limit unnecessarily.

- **Steps to Resolve**:
  - Inspect the API responses logged during retries.
  - Reduce `max_retries` for faster debugging.
  - Add logging inside the loop to debug each attempt:
    ```python
    print(f"Attempt {attempt + 1}/{max_retries}, Status: {response.status}")
    ```
