from fastapi import APIRouter
from pydantic import BaseModel
from database import find_user
from typing import Optional

auth_router = APIRouter()

class UserLoginRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = None

class AuthenticationResponse(BaseModel):
    success: bool
    message: str = ""
    branch: Optional[str] = "BCA"
    role: Optional[str] = "student"

async def verify_user_credentials(username, password_attempt, expected_role=None):
    user = await find_user(username)
    if not user:
        return False, "Username not found", "BCA", "student"

    if user["password"] != password_attempt:
        return False, "Incorrect password", "BCA", "student"

    db_role = user.get("role", "student")
    if expected_role and db_role.lower() != expected_role.lower():
        role_map = {"student": "Student", "teacher": "Teacher"}
        display_role = role_map.get(db_role.lower(), db_role)
        return False, f"Please try logging in as {display_role}", "BCA", "student"

    return True, "Login successful", user.get("branch", "BCA"), db_role

@auth_router.post("/login", response_model=AuthenticationResponse)
async def process_login_request(data: UserLoginRequest):
    is_valid, msg, branch, role = await verify_user_credentials(
        data.username,
        data.password,
        data.role
    )

    return AuthenticationResponse(success=is_valid, message=msg, branch=branch, role=role)
