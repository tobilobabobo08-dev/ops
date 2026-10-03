# cURL API examples

Examples below use Bash (including WSL). Local cURL requests require the services to be running. From the `dockerts/` directory, start them and wait for the backend health endpoint before making API calls:

```bash
docker compose up -d --build
curl --fail --retry 30 --retry-connrefused --retry-delay 2 http://localhost:8000/healthz
```

If the retry limit expires, check service status and logs with `docker compose ps` and `docker compose logs backend frontend`. For production, replace `https://your-domain.example` with the deployed site origin (scheme + host only; do not add `/healthz` here):

```bash
API=http://localhost:8000
WEB=http://localhost:3000
PROD=https://your-domain.example
```

The backend API is available directly on port `8000`. The frontend exposes a proxy for biodata collection requests on port `3000`.

## Health checks

Append `/healthz` to the production origin to check the deployed frontend and its connection to the backend/database:

```bash
curl -i "$PROD/healthz"
```

For local Docker Compose, check either the backend directly or the frontend URL (which proxies its health check to the backend):

```bash
curl -i "$API/healthz"
curl -i "$WEB/healthz"
```

Healthy response: `200` with `{"status":"ok","database":"ok"}`. An unhealthy database/backend returns `503`. The older backend path `/health` remains available as an alias.

## Biodata records

### Create a record

`Idempotency-Key` is required and must be 8–128 characters. Keep the same key when retrying the same logical submission.

```bash
curl -i -X POST "$API/api/v1/bio-records" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: ada-20260930-001' \
  -d '{
    "full_name": "Ada Lovelace",
    "email": "ada@example.com",
    "phone": "+1-555-0100",
    "date_of_birth": "1990-05-02",
    "sex": "female",
    "height_cm": 170.0,
    "weight_kg": 62.5,
    "blood_type": "O+",
    "allergies": null,
    "medical_notes": "",
    "country": "GB"
  }'
```

The first request returns `201`; repeating the identical request with the same key returns `200` and the same record. Reusing that key with a different request body returns `409`. The response includes the record `id`, derived `age` and `bmi`, and timestamps.

### List records

```bash
curl -i "$API/api/v1/bio-records?limit=20&offset=0"
```

`limit` is 1–100 (default 20); `offset` must be non-negative (default 0).

### Get one record

Replace `RECORD_ID` with the UUID returned by the create or list request:

```bash
curl -i "$API/api/v1/bio-records/RECORD_ID"
```

An unknown UUID returns `404`.

## Contacts

### Create a contact

```bash
curl -i -X POST "$API/api/v1/contacts" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Ada Lovelace",
    "phone_number": "+1-555-0100"
  }'
```

### List contacts

```bash
curl -i "$API/api/v1/contacts?limit=20&offset=0"
```

Pagination accepts `limit` from 1–100 and a non-negative `offset`.

## Request-response logs

The middleware automatically logs API requests other than health/docs and the request-response collection itself. These endpoints let you list the generated logs or add a log manually.

### Add a log entry

`request_body` and `response_body` are strings (or `null`), not nested JSON objects.

```bash
curl -i -X POST "$API/api/v1/request-responses" \
  -H 'Content-Type: application/json' \
  -d '{
    "method": "POST",
    "path": "/api/v1/contacts",
    "status_code": 201,
    "request_body": "{\"name\":\"Ada Lovelace\",\"phone_number\":\"+1-555-0100\"}",
    "response_body": "{\"name\":\"Ada Lovelace\",\"phone_number\":\"+1-555-0100\"}"
  }'
```

### List log entries

```bash
curl -i "$API/api/v1/request-responses?limit=20&offset=0"
```

Pagination accepts `limit` from 1–100 and a non-negative `offset`.

## Frontend biodata proxy

These are the browser-facing Next.js routes. The proxy forwards to the backend and passes through its JSON response and status. Its `POST` also requires an 8–128 character `Idempotency-Key`.

### Create through the frontend

```bash
curl -i -X POST "$WEB/api/bio-records" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: ada-web-20260930-001' \
  -d '{
    "full_name": "Ada Lovelace",
    "email": "ada@example.com",
    "date_of_birth": "1990-05-02",
    "sex": "female",
    "height_cm": 170.0,
    "weight_kg": 62.5
  }'
```

### List through the frontend

```bash
curl -i "$WEB/api/bio-records?limit=20&offset=0"
```

The frontend proxy currently exposes only these two biodata operations; contacts and request-response log routes are backend-only.

## FastAPI interactive API documentation

FastAPI also serves its generated API docs:

```bash
curl -i "$API/openapi.json"
curl -i "$API/docs"
curl -i "$API/redoc"
```
