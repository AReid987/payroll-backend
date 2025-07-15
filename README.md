# Payroll Backend

This is a FastAPI backend for payroll management, now using Auth0 authentication via [fastapi-auth0](https://github.com/auth0/fastapi-auth0).

## Auth0 Setup

1. Create a free Auth0 account at https://auth0.com/.
2. Create a new API in the Auth0 dashboard. Note the API Identifier (used as AUTH0_AUDIENCE).
3. Go to Applications > APIs > [Your API] > Quick Start for FastAPI for more details.
4. Set the following environment variables:

```
AUTH0_DOMAIN=your-auth0-domain.auth0.com
AUTH0_AUDIENCE=your-api-identifier
```

## Required Environment Variables
- `AUTH0_DOMAIN`: Your Auth0 domain (e.g., `dev-xxxxxx.auth0.com`)
- `AUTH0_AUDIENCE`: Your Auth0 API audience/identifier

## Running the App

1. Install dependencies (using [pdm](https://pdm.fming.dev/)):
   ```
pdm install
   ```
2. Set the required environment variables:
   ```
export AUTH0_DOMAIN=your-auth0-domain.auth0.com
export AUTH0_AUDIENCE=your-api-identifier
   ```
3. Run the app using FastAPI CLI:
   ```
pdm run fastapi run app/main.py --reload
   ```
   Or with uvicorn:
   ```
pdm run uvicorn app.main:app --reload
   ```

## Testing Auth0 Authentication

1. Obtain a JWT access token from your Auth0 tenant (e.g., using the Auth0 dashboard or your frontend app).
2. Use the token in the `Authorization` header for protected endpoints:
   ```
   Authorization: Bearer <your-access-token>
   ```
3. Test endpoints with curl or an API client:
   ```
curl -H "Authorization: Bearer <your-access-token>" http://localhost:8000/users/me
   ```

## Notes
- All protected endpoints require a valid Auth0 JWT access token.
- Admin-only endpoints require the user to have the `admin` permission in their Auth0 token claims.
- The app is compatible with FastAPI CLI and pdm.

## Project Structure
- `app/auth/dependencies.py`: Auth0 integration and authentication dependencies
- `app/routers/`: API routers (users, payroll, time-tracking, etc.)
- `app/main.py`: FastAPI app entry point

