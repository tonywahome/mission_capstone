from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import hashlib
import secrets
from datetime import datetime
from database import get_admin_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str  # 'landowner' or 'business'
    company_name: Optional[str] = None

class AuthResponse(BaseModel):
    user: dict
    token: str

def hash_password(password: str) -> str:
    """Simple password hashing (in production, use bcrypt or similar)."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return hash_password(password) == hashed

def generate_token() -> str:
    """Generate a simple session token."""
    return secrets.token_urlsafe(32)

@router.post("/signup", response_model=AuthResponse)
async def signup(data: SignupRequest):
    """Create a new user account."""
    try:
        db = get_admin_client()
        
        # Validate role
        if data.role not in ["landowner", "business", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be 'landowner', 'business', or 'admin'"
            )
        
        # Check if email already exists
        existing = db.table("users").select("*").eq("email", data.email).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user
        user_data = {
            "email": data.email,
            "password_hash": hash_password(data.password),
            "full_name": data.full_name,
            "role": data.role,
            "company_name": data.company_name,
            "created_at": datetime.now().isoformat(),
        }
        
        result = db.table("users").insert(user_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        user = result.data[0]
        token = generate_token()
        
        # Store token (in production, use a proper session store)
        db.table("sessions").insert({
            "user_id": user["id"],
            "token": token,
            "created_at": datetime.now().isoformat(),
        }).execute()
        
        # Remove password hash from response
        user_response = {k: v for k, v in user.items() if k != "password_hash"}
        
        logger.info(f"User created: {user['email']} (role: {user['role']})")
        
        return AuthResponse(user=user_response, token=token)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account"
        )

@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest):
    """Authenticate user and return session token."""
    try:
        db = get_admin_client()
        
        logger.info(f"Login attempt for email: {data.email}")
        
        # Find user by email
        result = db.table("users").select("*").eq("email", data.email).execute()
        
        if not result.data:
            logger.warning(f"Login failed: User not found for email {data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user = result.data[0]
        logger.info(f"User found: {user['email']}, checking password...")
        
        # Verify password
        if not verify_password(data.password, user.get("password_hash", "")):
            logger.warning(f"Login failed: Invalid password for email {data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        logger.info(f"Password verified for {user['email']}")
        
        # Generate token
        token = generate_token()
        
        # Store session
        db.table("sessions").insert({
            "user_id": user["id"],
            "token": token,
            "created_at": datetime.now().isoformat(),
        }).execute()
        
        # Remove password hash from response
        user_response = {k: v for k, v in user.items() if k != "password_hash"}
        
        logger.info(f"User logged in successfully: {user['email']}")
        
        return AuthResponse(user=user_response, token=token)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/logout")
async def logout(token: str):
    """Logout user and invalidate token."""
    try:
        db = get_admin_client()
        db.table("sessions").delete().eq("token", token).execute()
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.get("/me")
async def get_current_user(token: str):
    """Get current user from token."""
    try:
        db = get_admin_client()
        
        # Find session
        session_result = db.table("sessions").select("user_id").eq("token", token).execute()
        
        if not session_result.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        user_id = session_result.data[0]["user_id"]
        
        # Get user
        user_result = db.table("users").select("*").eq("id", user_id).execute()
        
        if not user_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = user_result.data[0]
        user_response = {k: v for k, v in user.items() if k != "password_hash"}
        
        return user_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user"
        )


@router.get("/user-by-email")
async def get_user_by_email(email: str):
    """Get user by email address (for internal use)."""
    try:
        db = get_admin_client()
        
        # Get user by email
        user_result = db.table("users").select("*").eq("email", email).execute()
        
        if not user_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = user_result.data[0]
        user_response = {k: v for k, v in user.items() if k != "password_hash"}
        
        return user_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user by email error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user by email"
        )
