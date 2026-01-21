#src/auth/ueAuth.ts
import { useOktaAuth } from '@okta/okta-react';
import { useCallback, useEffect, useState } from 'react';

export interface UserInfo {
  sub: string;
  name?: string;
  email?: string;
  preferred_username?: string;
  given_name?: string;
  family_name?: string;
}

export function useAuth() {
  const { oktaAuth, authState } = useOktaAuth();
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUserInfo = async () => {
      if (authState?.isAuthenticated) {
        try {
          const user = await oktaAuth.getUser();
          setUserInfo(user as UserInfo);
        } catch (error) {
          console.error('Failed to fetch user info:', error);
        }
      } else {
        setUserInfo(null);
      }
      setLoading(false);
    };

    if (authState) {
      fetchUserInfo();
    }
  }, [authState, oktaAuth]);

  const login = useCallback(async () => {
    await oktaAuth.signInWithRedirect();
  }, [oktaAuth]);

  const logout = useCallback(async () => {
    await oktaAuth.signOut();
  }, [oktaAuth]);

  const getAccessToken = useCallback(async (): Promise<string | undefined> => {
    const tokenManager = oktaAuth.tokenManager;
    const accessToken = await tokenManager.get('accessToken');
    return accessToken?.accessToken;
  }, [oktaAuth]);

  const getIdToken = useCallback(async (): Promise<string | undefined> => {
    const tokenManager = oktaAuth.tokenManager;
    const idToken = await tokenManager.get('idToken');
    return idToken?.idToken;
  }, [oktaAuth]);

  return {
    isAuthenticated: authState?.isAuthenticated ?? false,
    isLoading: !authState || loading,
    userInfo,
    accessToken: authState?.accessToken?.accessToken,
    idToken: authState?.idToken?.idToken,
    login,
    logout,
    getAccessToken,
    getIdToken,
  };
}

#secure/auth/SecureRoute.tsx
import { useEffect } from 'react';
import { useOktaAuth } from '@okta/okta-react';
import { Loader2 } from 'lucide-react';
import type { ReactNode } from 'react';

interface SecureRouteProps {
  children: ReactNode;
}

export function SecureRoute({ children }: SecureRouteProps) {
  const { authState, oktaAuth } = useOktaAuth();

  useEffect(() => {
    // If not authenticated and auth state is loaded, redirect to Okta login
    if (authState && !authState.isAuthenticated) {
      oktaAuth.signInWithRedirect();
    }
  }, [authState, oktaAuth]);

  // Still loading auth state
  if (!authState) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-teal-50 flex items-center justify-center mx-auto mb-4">
            <Loader2 className="h-8 w-8 animate-spin text-teal-600" />
          </div>
          <p className="text-gray-600 font-medium">Loading...</p>
        </div>
      </div>
    );
  }

  // Not authenticated - show redirecting message while oktaAuth.signInWithRedirect() happens
  if (!authState.isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-teal-50 flex items-center justify-center mx-auto mb-4">
            <Loader2 className="h-8 w-8 animate-spin text-teal-600" />
          </div>
          <p className="text-gray-600 font-medium">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  // Authenticated - render children
  return <>{children}</>;
}


#src/auth/LoginCallback.tsx
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOktaAuth } from '@okta/okta-react';
import { Loader2 } from 'lucide-react';

export function LoginCallback() {
  const { oktaAuth, authState } = useOktaAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Handle the callback - Okta SDK will process the tokens
        if (oktaAuth.isLoginRedirect()) {
          await oktaAuth.handleLoginRedirect();
        }
      } catch (error) {
        console.error('Login callback error:', error);
        navigate('/login?error=callback_failed');
      }
    };

    handleCallback();
  }, [oktaAuth, navigate]);

  useEffect(() => {
    // Once authenticated, redirect to home
    if (authState?.isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [authState, navigate]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="text-center">
        <div className="w-16 h-16 rounded-full bg-teal-50 flex items-center justify-center mx-auto mb-4">
          <Loader2 className="h-8 w-8 animate-spin text-teal-600" />
        </div>
        <p className="text-gray-600 font-medium">Completing login...</p>
        <p className="text-gray-400 text-sm mt-1">Please wait while we verify your credentials</p>
      </div>
    </div>
  );
}


#src/lib/oktaControl.ts

// Okta Configuration
// Replace these values with your Okta application settings

export const oktaConfig = {
  // Your Okta domain (e.g., https://dev-12345.okta.com)
  issuer: import.meta.env.VITE_OKTA_ISSUER || 'https://{yourOktaDomain}/oauth2/default',

  // Your Okta application's Client ID
  clientId: import.meta.env.VITE_OKTA_CLIENT_ID || '{yourClientId}',

  // The redirect URI configured in your Okta application
  redirectUri: `${window.location.origin}/login/callback`,

  // Scopes requested during authentication
  scopes: ['openid', 'profile', 'email'],

  // Post logout redirect
  postLogoutRedirectUri: window.location.origin,
};

// Validate configuration
export function validateOktaConfig(): boolean {
  const { issuer, clientId } = oktaConfig;

  if (issuer.includes('{yourOktaDomain}')) {
    console.error('Okta Error: Please configure VITE_OKTA_ISSUER in your .env file');
    return false;
  }

  if (clientId.includes('{yourClientId}')) {
    console.error('Okta Error: Please configure VITE_OKTA_CLIENT_ID in your .env file');
    return false;
  }

  return true;
}


#main.tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import { Security } from '@okta/okta-react';
import { OktaAuth, toRelativeUrl } from '@okta/okta-auth-js';
import './index.css';
import App from './App.tsx';
import { LoginCallback } from './auth/LoginCallback.tsx';
import { SecureRoute } from './auth/SecureRoute.tsx';
import { oktaConfig, validateOktaConfig } from './lib/oktaConfig.ts';

// Initialize Okta Auth
const oktaAuth = new OktaAuth({
  issuer: oktaConfig.issuer,
  clientId: oktaConfig.clientId,
  redirectUri: oktaConfig.redirectUri,
  scopes: oktaConfig.scopes,
  pkce: true,
});

// Validate configuration on startup
if (!validateOktaConfig()) {
  console.warn('Okta is not properly configured. Authentication will not work.');
}

function AppWithRouterAccess() {
  const navigate = useNavigate();

  const restoreOriginalUri = async (_oktaAuth: OktaAuth, originalUri: string) => {
    navigate(toRelativeUrl(originalUri || '/', window.location.origin), { replace: true });
  };

  return (
    <Security oktaAuth={oktaAuth} restoreOriginalUri={restoreOriginalUri}>
      <Routes>
        <Route path="/login/callback" element={<LoginCallback />} />
        <Route
          path="/*"
          element={
            <SecureRoute>
              <App />
            </SecureRoute>
          }
        />
      </Routes>
    </Security>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AppWithRouterAccess />
    </BrowserRouter>
  </StrictMode>,
);


#env
# Okta Configuration
# Copy this file to .env and fill in your Okta application values

# Your Okta domain URL with the authorization server
# Format: https://{yourOktaDomain}/oauth2/default
# Example: https://dev-12345678.okta.com/oauth2/default
VITE_OKTA_ISSUER=https://dev-XXXXX.okta.com/oauth2/default

# Your Okta application's Client ID (from Okta Admin Console)
VITE_OKTA_CLIENT_ID=your-client-id-here

# Backend API URL (optional, defaults to http://localhost:8000)
VITE_API_URL=http://localhost:8000



#src/lib/api.ts
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Token getter function - will be set by the auth provider
let getAccessToken: (() => Promise<string | undefined>) | null = null;

export function setTokenGetter(getter: () => Promise<string | undefined>) {
  getAccessToken = getter;
}

// Helper to get auth headers
async function getAuthHeaders(): Promise<HeadersInit> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  if (getAccessToken) {
    try {
      const token = await getAccessToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    } catch (error) {
      console.error('Failed to get access token:', error);
    }
  }

  return headers;
}

// Helper for fetch with auth
async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = await getAuthHeaders();
  return fetch(url, {
    ...options,
    headers: {
      ...headers,
      ...options.headers,
    },
  });
}

export interface CurrentUser {
  sub: string;
  email: string;
  name: string;
  preferred_username: string;
  given_name?: string;
  family_name?: string;
}

// API Functions
export const api = {
  // Get current authenticated user info from backend
  getCurrentUser: async (): Promise<CurrentUser> => {
    const response = await fetchWithAuth(`${API_BASE_URL}/me`);
    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Unauthorized');
      }
      throw new Error('Failed to fetch current user');
    }
    return await response.json();
  },

    const response = await fetchWithAuth(`${API_BASE_URL}/statuses`);


#src/components/layout/Sidebar.tsx
import { Home, LayoutDashboard, Users, Filter, Upload, Loader2, Check, ChevronDown, X, LogOut, User } from 'lucide-react';

interface UserInfo {
  name?: string;
  email?: string;
  preferred_username?: string;
}
interface SidebarProps {
  activeScreen: string;
  onScreenChange: (screen: string) => void;
  onLoadData: (departments: string[], statuses: string[]) => Promise<void>;
  loading: boolean;
  userInfo?: UserInfo | null;
  onLogout?: () => void;
}



  {/* User Section */}
      {userInfo && (
        <div className="p-4 border-t border-gray-100 bg-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-teal-100 flex items-center justify-center">
              <User className="w-5 h-5 text-teal-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {userInfo.name || userInfo.preferred_username || 'User'}
              </p>
              <p className="text-xs text-gray-500 truncate">
                {userInfo.email || ''}
              </p>
            </div>
            {onLogout && (
              <button
                onClick={onLogout}
                className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}


#src/App.tsx

import { useState, useEffect } from 'react';
import { api, setTokenGetter, type TableConfig } from '@/lib/api';
import { useAuth } from '@/auth/useAuth';



function App() {
  const { userInfo, logout, getAccessToken, isLoading: authLoading } = useAuth();

 useEffect(() => {
    setTokenGetter(getAccessToken);
  }, [getAccessToken]);

 const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout error:', error);
      toast.error('Failed to logout');
    }
  };

  // Show loading while auth is initializing
  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-teal-50 flex items-center justify-center mx-auto mb-4">
            <Loader2 className="h-8 w-8 animate-spin text-teal-600" />
          </div>
          <p className="text-gray-600 font-medium">Initializing...</p>
        </div>
      </div>
    );
  }
 <Sidebar
        activeScreen={activeScreen}
        onScreenChange={setActiveScreen}
        onLoadData={loadDataFromAPI}
        loading={loading}
        userInfo={userInfo}
        onLogout={handleLogout}
      />


#app/auth.py
"""
Okta JWT Authentication Module for FastAPI

This module provides JWT token validation for Okta-issued tokens.
It fetches JWKS from Okta and validates Bearer tokens from the Authorization header.
"""

import os
from typing import Optional
from functools import lru_cache

import httpx
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode
from pydantic import BaseModel

# Security scheme for Bearer token
security = HTTPBearer(auto_error=False)


class OktaConfig(BaseModel):
    """Okta configuration loaded from environment variables"""
    issuer: str
    audience: str
    client_id: str

    @classmethod
    def from_env(cls) -> "OktaConfig":
        issuer = os.getenv("OKTA_ISSUER")
        audience = os.getenv("OKTA_AUDIENCE", "api://default")
        client_id = os.getenv("OKTA_CLIENT_ID")

        if not issuer:
            raise ValueError("OKTA_ISSUER environment variable is required")
        if not client_id:
            raise ValueError("OKTA_CLIENT_ID environment variable is required")

        return cls(issuer=issuer, audience=audience, client_id=client_id)


class CurrentUser(BaseModel):
    """Represents the current authenticated user from the JWT token"""
    sub: str
    email: Optional[str] = None
    name: Optional[str] = None
    preferred_username: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None


class OktaJWTValidator:
    """
    Validates Okta JWT tokens using JWKS (JSON Web Key Set)
    """

    def __init__(self, config: OktaConfig):
        self.config = config
        self.jwks_uri = f"{config.issuer}/v1/keys"
        self._jwks_cache: Optional[dict] = None

    async def get_jwks(self) -> dict:
        """Fetch JWKS from Okta (with caching)"""
        if self._jwks_cache:
            return self._jwks_cache

        async with httpx.AsyncClient() as client:
            response = await client.get(self.jwks_uri)
            response.raise_for_status()
            self._jwks_cache = response.json()
            return self._jwks_cache

    def _get_signing_key(self, token: str, jwks: dict) -> dict:
        """Extract the signing key from JWKS that matches the token's kid"""
        try:
            unverified_header = jwt.get_unverified_header(token)
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token header")

        kid = unverified_header.get("kid")
        if not kid:
            raise HTTPException(status_code=401, detail="Token missing key ID")

        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key

        raise HTTPException(status_code=401, detail="Signing key not found")

    async def validate_token(self, token: str) -> CurrentUser:
        """
        Validate the JWT token and return the current user info

        Args:
            token: The JWT token string (without 'Bearer ' prefix)

        Returns:
            CurrentUser object with user information from the token

        Raises:
            HTTPException: If token validation fails
        """
        try:
            # Get JWKS
            jwks = await self.get_jwks()

            # Get the signing key
            signing_key = self._get_signing_key(token, jwks)

            # Decode and validate the token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.config.audience,
                issuer=self.config.issuer,
                options={
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_exp": True,
                }
            )

            # Extract user info from the token
            return CurrentUser(
                sub=payload.get("sub", ""),
                email=payload.get("email"),
                name=payload.get("name"),
                preferred_username=payload.get("preferred_username"),
                given_name=payload.get("given_name"),
                family_name=payload.get("family_name"),
            )

        except JWTError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Token validation failed: {str(e)}"
            )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Unable to fetch JWKS: {str(e)}"
            )


# Global validator instance (initialized lazily)
_validator: Optional[OktaJWTValidator] = None


def get_validator() -> OktaJWTValidator:
    """Get or create the JWT validator instance"""
    global _validator
    if _validator is None:
        config = OktaConfig.from_env()
        _validator = OktaJWTValidator(config)
    return _validator


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> CurrentUser:
    """
    FastAPI dependency that validates the Bearer token and returns the current user.

    Usage:
        @app.get("/protected")
        async def protected_route(user: CurrentUser = Depends(get_current_user)):
            return {"user": user.email}
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    validator = get_validator()
    return await validator.validate_token(credentials.credentials)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Optional[CurrentUser]:
    """
    FastAPI dependency that optionally validates the Bearer token.
    Returns None if no token is provided, but validates if one is present.

    Usage:
        @app.get("/maybe-protected")
        async def maybe_protected(user: Optional[CurrentUser] = Depends(get_current_user_optional)):
            if user:
                return {"user": user.email}
            return {"message": "anonymous"}
    """
    if not credentials:
        return None

    validator = get_validator()
    return await validator.validate_token(credentials.credentials)

#env.example
# Database Configuration
DATABASE_URL=postgresql+psycopg://admin:password@localhost:5432/datamanager

# API Server Configuration
API_PORT=8000
API_HOST=0.0.0.0

# Okta Configuration
# Your Okta domain URL with the authorization server
# Format: https://{yourOktaDomain}/oauth2/default
# Example: https://dev-12345678.okta.com/oauth2/default
OKTA_ISSUER=https://dev-XXXXX.okta.com/oauth2/default

# Your Okta application's Client ID
OKTA_CLIENT_ID=your-client-id-here

# The audience for token validation (usually 'api://default' for Okta default authorization server)
OKTA_AUDIENCE=api://default


#src/app/main.py
from .auth import get_current_user, get_current_user_optional, CurrentUser

@app.get("/api/me")
async def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """
    Get the current authenticated user's information.

    This endpoint requires a valid Okta JWT token in the Authorization header.
    Returns user information extracted from the token claims.
    """
    return {
        "sub": current_user.sub,
        "email": current_user.email,
        "name": current_user.name,
        "preferred_username": current_user.preferred_username,
        "given_name": current_user.given_name,
        "family_name": current_user.family_name,
    }


current_user: CurrentUser = Depends(get_current_user)



