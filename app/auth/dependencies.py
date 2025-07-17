import os
from fastapi import Depends, HTTPException, status
from fastapi_auth0 import Auth0, Auth0User

AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
AUTH0_AUDIENCE = os.getenv('AUTH0_AUDIENCE')

if not AUTH0_DOMAIN or not AUTH0_AUDIENCE:
    raise RuntimeError('AUTH0_DOMAIN and AUTH0_AUDIENCE environment variables must be set')

auth0 = Auth0(domain=AUTH0_DOMAIN, api_audience=AUTH0_AUDIENCE)

get_current_user = auth0.get_user

def require_admin(user: Auth0User = Depends(get_current_user)):
    # Customize this check based on your Auth0 claims/roles
    permissions = getattr(user, 'permissions', None) or []
    if 'admin' not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Admin privileges required'
        )
    return user
