from fastapi import APIRouter

router = APIRouter()

users = []

@router.post("/register")
def register(username: str, password: str):
    users.append({"username": username, "password": password})
    return {"message": f"User {username} registered successfully"}

@router.post("/login")
def loginn(username: str, password: str):
    for user in users: 
        if user["username"] == username and user["password"] == password:
            return {"message": "Login successful"}
    return {"message": "Invalid credentials"}