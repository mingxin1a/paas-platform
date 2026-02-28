# API Error Codes

| code | HTTP | Description |
|------|------|-------------|
| BAD_REQUEST | 400 | Invalid request |
| MISSING_HEADER | 400 | Missing required header |
| UNAUTHORIZED | 401 | Invalid token |
| INVALID_APP_KEY | 401 | Invalid X-App-Key |
| NOT_FOUND | 404 | Resource not found |
| RATE_LIMIT | 429 | Rate limited |
| CELL_NOT_FOUND | 503 | Cell not registered |
| CIRCUIT_OPEN | 503 | Circuit breaker open |
