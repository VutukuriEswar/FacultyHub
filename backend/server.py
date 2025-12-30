from fastapi import FastAPI, APIRouter, HTTPException, Cookie, Response, Request, Depends
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'faculty_hub')]

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Models
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    is_admin: bool = False
    preferences: List[str] = Field(default_factory=list)
    created_at: datetime

class UserUpdate(BaseModel):
    name: Optional[str] = None
    picture: Optional[str] = None
    preferences: Optional[List[str]] = None

class Faculty(BaseModel):
    model_config = ConfigDict(extra="ignore")
    faculty_id: str
    name: str
    department: str
    designation: str
    image_url: Optional[str] = None
    scholar_profile: Optional[str] = None
    publications: List[str] = Field(default_factory=list)
    research_interests: Optional[str] = None
    avg_ratings: Dict[str, float] = Field(default_factory=lambda: {"teaching": 0, "attendance": 0, "doubt_clarification": 0, "overall": 0})
    rating_counts: Dict[str, int] = Field(default_factory=lambda: {"teaching": 0, "attendance": 0, "doubt_clarification": 0, "overall": 0})
    created_at: datetime

class FacultyCreate(BaseModel):
    name: str
    department: str
    designation: str
    image_url: Optional[str] = None
    scholar_profile: Optional[str] = None
    publications: List[str] = Field(default_factory=list)
    research_interests: Optional[str] = None

class FacultyUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    image_url: Optional[str] = None
    scholar_profile: Optional[str] = None
    publications: Optional[List[str]] = None
    research_interests: Optional[str] = None

class Rating(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rating_id: str
    faculty_id: str
    user_id: str
    teaching: Optional[int] = None
    attendance: Optional[int] = None
    doubt_clarification: Optional[int] = None
    overall: Optional[int] = None
    created_at: datetime
    updated_at: datetime

class RatingSubmit(BaseModel):
    teaching: Optional[int] = Field(None, ge=1, le=5)
    attendance: Optional[int] = Field(None, ge=1, le=5)
    doubt_clarification: Optional[int] = Field(None, ge=1, le=5)
    overall: int = Field(..., ge=1, le=5)

class Comment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    comment_id: str
    faculty_id: str
    user_id: str
    user_name: str
    user_picture: Optional[str] = None
    content: str
    parent_comment_id: Optional[str] = None
    created_at: datetime

class CommentCreate(BaseModel):
    content: str
    parent_comment_id: Optional[str] = None

class ChatMessage(BaseModel):
    message_id: str
    sender_id: str
    content: str
    created_at: datetime

class Chat(BaseModel):
    model_config = ConfigDict(extra="ignore")
    chat_id: str
    participants: List[str]
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime

class ChatMessageCreate(BaseModel):
    recipient_id: str
    content: str

# --- DEMO DATA SOURCE ---

def get_demo_faculty():
    """Returns a static list of 70 demo faculty (10 per department)."""
    departments = ['SCOPE', 'SENSE', 'SMEC', 'SAS', 'VSB', 'VSL', 'VISH']
    base_data = {
        'created_at': datetime.now(timezone.utc),
        'avg_ratings': {"teaching": 0, "attendance": 0, "doubt_clarification": 0, "overall": 0},
        'rating_counts': {"teaching": 0, "attendance": 0, "doubt_clarification": 0, "overall": 0}
    }
    
    # Generators for data to keep code concise but populated
    def gen_dept_faculty(dept, names, designations):
        facs = []
        for i, name in enumerate(names):
            facs.append({
                "faculty_id": f"demo_{dept}_{i}",
                "name": name,
                "department": dept,
                "designation": designations[i % len(designations)],
                "image_url": f"https://randomuser.me/api/portraits/{'men' if i % 2 == 0 else 'women'}/{i+10}.jpg",
                "scholar_profile": None,
                "publications": [],
                "research_interests": f"Research in {dept}",
                **base_data
            })
        return facs

    all_faculty = []
    
    # SCOPE (Computer Science)
    all_faculty.extend(gen_dept_faculty('SCOPE', [
        "Dr. Ada Lovelace", "Prof. Alan Turing", "Dr. Grace Hopper", "Prof. Donald Knuth",
        "Dr. Linus Torvalds", "Prof. Tim Berners-Lee", "Dr. Margaret Hamilton", "Prof. Dennis Ritchie",
        "Dr. Sophie Wilson", "Prof. Guido van Rossum"
    ], ["Professor", "Associate Professor", "Assistant Professor", "HOD"]))

    # SENSE (Electronics)
    all_faculty.extend(gen_dept_faculty('SENSE', [
        "Dr. Nikola Tesla", "Prof. Michael Faraday", "Dr. Guglielmo Marconi", "Prof. Samuel Morse",
        "Dr. Claude Shannon", "Prof. Jack Kilby", "Dr. Robert Noyce", "Prof. Gordon Moore",
        "Dr. Andrew Grove", "Prof. Robert Hall"
    ], ["Dean", "Professor", "Associate Professor", "Assistant Professor"]))

    # SMEC (Mechanical)
    all_faculty.extend(gen_dept_faculty('SMEC', [
        "Dr. Henry Ford", "Prof. Karl Benz", "Prof. Rudolf Diesel", "Dr. James Watt",
        "Prof. George Stephenson", "Dr. Isambard Brunel", "Prof. Nikolaus Otto", "Dr. Elijah McCoy",
        "Prof. Gottlieb Daimler", "Dr. Charles Kettering"
    ], ["Professor", "HOD", "Associate Professor", "Assistant Professor"]))

    # SAS (Advanced Science)
    all_faculty.extend(gen_dept_faculty('SAS', [
        "Dr. Marie Curie", "Prof. Albert Einstein", "Dr. Isaac Newton", "Prof. Galileo Galilei",
        "Dr. Richard Feynman", "Prof. Stephen Hawking", "Dr. Neil deGrasse Tyson", "Prof. Rosalind Franklin",
        "Dr. Dmitri Mendeleev", "Prof. Louis Pasteur"
    ], ["Senior Professor", "Professor", "Associate Professor", "Assistant Professor"]))

    # VSB (Business)
    all_faculty.extend(gen_dept_faculty('VSB', [
        "Dr. Peter Drucker", "Prof. Adam Smith", "Dr. Warren Buffett", "Prof. John Keynes",
        "Dr. Michael Porter", "Prof. Philip Kotler", "Dr. Jack Welch", "Prof. Henry Mintzberg",
        "Dr. Jim Collins", "Prof. Clayton Christensen"
    ], ["Professor", "Dean", "Associate Professor", "Assistant Professor"]))

    # VSL (Law)
    all_faculty.extend(gen_dept_faculty('VSL', [
        "Dr. Ruth Bader Ginsburg", "Prof. Oliver Wendell Holmes", "Dr. Thurgood Marshall", "Prof. Sandra Day O'Connor",
        "Dr. William Blackstone", "Prof. Hugo Black", "Dr. Learned Hand", "Prof. Benjamin Cardozo",
        "Dr. John Marshall", "Prof. Antonin Scalia"
    ], ["Senior Advocate", "Professor", "Associate Professor", "HOD"]))

    # VISH (Social Science)
    all_faculty.extend(gen_dept_faculty('VISH', [
        "Dr. Sigmund Freud", "Prof. Carl Jung", "Dr. B.F. Skinner", "Prof. Jean Piaget",
        "Dr. Noam Chomsky", "Prof. Jane Goodall", "Dr. Margaret Mead", "Prof. Sigmund Freud",
        "Dr. Abraham Maslow", "Prof. Erik Erikson"
    ], ["Professor", "Assistant Professor", "Associate Professor", "Dean"]))

    return all_faculty

# Auth Helper
async def get_current_user(request: Request, session_token: Optional[str] = Cookie(None)) -> User:
    token = session_token or request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session_doc = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    if isinstance(user_doc["created_at"], str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    
    return User(**user_doc)

# Auth Routes
@api_router.post("/auth/login")
async def login_user(response: Response, login_data: dict):
    email = login_data.get("email")
    password = login_data.get("password")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    
    if not email.endswith("@vitapstudent.ac.in") or password != "password":
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_doc = await db.users.find_one({"email": email}, {"_id": 0})
    
    if not user_doc:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user_doc = {
            "user_id": user_id,
            "email": email,
            "name": email.split('@')[0].capitalize(),
            "picture": None,
            "is_admin": email == "admin@vitapstudent.ac.in",
            "preferences": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user_doc.copy())
    else:
        user_id = user_doc["user_id"]

    session_token = f"sess_{uuid.uuid4().hex}"
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        "created_at": datetime.now(timezone.utc)
    })
    
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=7*24*60*60,
        path="/"
    )
    
    if isinstance(user_doc["created_at"], str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    
    return User(**user_doc)

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@api_router.post("/auth/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    if session_token:
        await db.user_sessions.delete_many({"session_token": session_token})
    
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}

# User Routes
@api_router.patch("/users/me", response_model=User)
async def update_profile(update: UserUpdate, current_user: User = Depends(get_current_user)):
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    
    if update_data:
        await db.users.update_one(
            {"user_id": current_user.user_id},
            {"$set": update_data}
        )
    
    user_doc = await db.users.find_one({"user_id": current_user.user_id}, {"_id": 0})
    if isinstance(user_doc["created_at"], str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    
    return User(**user_doc)

# Faculty Routes
@api_router.get("/faculty", response_model=List[Faculty])
async def get_all_faculty(department: Optional[str] = None):
    # 1. Get Demo Data
    demo_list = get_demo_faculty()
    
    # 2. Merge with DB Ratings (Persistence)
    faculty_ids = [f["faculty_id"] for f in demo_list]
    cursor = db.faculty.find({"faculty_id": {"$in": faculty_ids}}, {"_id": 0})
    db_faculty_data = await cursor.to_list(1000)
    
    ratings_map = {f["faculty_id"]: f for f in db_faculty_data}
    
    final_list = []
    for demo_f in demo_list:
        if department and department.lower() not in demo_f["department"].lower():
            continue
            
        if demo_f["faculty_id"] in ratings_map:
            db_f = ratings_map[demo_f["faculty_id"]]
            demo_f["avg_ratings"] = db_f.get("avg_ratings", demo_f["avg_ratings"])
            demo_f["rating_counts"] = db_f.get("rating_counts", demo_f["rating_counts"])
            
        final_list.append(demo_f)
        
    return final_list

@api_router.get("/faculty/{faculty_id}", response_model=Faculty)
async def get_faculty(faculty_id: str):
    demo_list = get_demo_faculty()
    fac = next((f for f in demo_list if f["faculty_id"] == faculty_id), None)
    
    if not fac:
        raise HTTPException(status_code=404, detail="Faculty not found")

    # Merge ratings
    db_fac = await db.faculty.find_one({"faculty_id": faculty_id}, {"_id": 0})
    if db_fac:
        fac["avg_ratings"] = db_fac.get("avg_ratings", fac["avg_ratings"])
        fac["rating_counts"] = db_fac.get("rating_counts", fac["rating_counts"])
    
    return Faculty(**fac)

@api_router.post("/faculty", response_model=Faculty)
async def create_faculty(faculty: FacultyCreate, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    faculty_id = f"faculty_{uuid.uuid4().hex[:12]}"
    faculty_doc = {
        "faculty_id": faculty_id,
        **faculty.model_dump(),
        "avg_ratings": {"teaching": 0, "attendance": 0, "doubt_clarification": 0, "overall": 0},
        "rating_counts": {"teaching": 0, "attendance": 0, "doubt_clarification": 0, "overall": 0},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.faculty.insert_one(faculty_doc.copy())
    
    faculty_doc["created_at"] = datetime.fromisoformat(faculty_doc["created_at"])
    return Faculty(**faculty_doc)

@api_router.patch("/faculty/{faculty_id}", response_model=Faculty)
async def update_faculty(faculty_id: str, update: FacultyUpdate, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    
    if update_data:
        result = await db.faculty.update_one(
            {"faculty_id": faculty_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Faculty not found")
    
    faculty_doc = await db.faculty.find_one({"faculty_id": faculty_id}, {"_id": 0})
    if isinstance(faculty_doc["created_at"], str):
        faculty_doc["created_at"] = datetime.fromisoformat(faculty_doc["created_at"])
    
    return Faculty(**faculty_doc)

@api_router.delete("/faculty/{faculty_id}")
async def delete_faculty(faculty_id: str, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.faculty.delete_one({"faculty_id": faculty_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Faculty not found")
    
    return {"message": "Faculty deleted successfully"}

# Rating Routes
@api_router.post("/faculty/{faculty_id}/ratings", response_model=Rating)
async def submit_rating(faculty_id: str, rating: RatingSubmit, current_user: User = Depends(get_current_user)):
    faculty_doc = await db.faculty.find_one({"faculty_id": faculty_id}, {"_id": 0})
    
    if not faculty_doc:
        await db.faculty.insert_one({
            "faculty_id": faculty_id,
            "name": "Demo Faculty", 
            "department": "General",
            "designation": "Faculty",
            "avg_ratings": {"teaching": 0, "attendance": 0, "doubt_clarification": 0, "overall": 0},
            "rating_counts": {"teaching": 0, "attendance": 0, "doubt_clarification": 0, "overall": 0},
            "created_at": datetime.now(timezone.utc)
        })
        faculty_doc = await db.faculty.find_one({"faculty_id": faculty_id}, {"_id": 0})
    
    existing_rating = await db.ratings.find_one({"faculty_id": faculty_id, "user_id": current_user.user_id}, {"_id": 0})
    
    now = datetime.now(timezone.utc)
    
    if existing_rating:
        rating_id = existing_rating["rating_id"]
        old_values = {k: existing_rating.get(k) for k in ["teaching", "attendance", "doubt_clarification", "overall"]}
        
        update_data = {k: v for k, v in rating.model_dump().items() if v is not None}
        update_data["updated_at"] = now.isoformat()
        
        await db.ratings.update_one(
            {"rating_id": rating_id},
            {"$set": update_data}
        )
        
        for category in ["teaching", "attendance", "doubt_clarification", "overall"]:
            new_val = update_data.get(category)
            old_val = old_values.get(category)
            
            if new_val is not None:
                current_avg = faculty_doc["avg_ratings"].get(category, 0)
                current_count = faculty_doc["rating_counts"].get(category, 0)
                
                if old_val is not None:
                    total = current_avg * current_count
                    new_total = total - old_val + new_val
                    new_avg = new_total / current_count if current_count > 0 else new_val
                else:
                    total = current_avg * current_count
                    new_total = total + new_val
                    current_count += 1
                    new_avg = new_total / current_count
                
                await db.faculty.update_one(
                    {"faculty_id": faculty_id},
                    {"$set": {
                        f"avg_ratings.{category}": new_avg,
                        f"rating_counts.{category}": current_count
                    }}
                )
    else:
        rating_id = f"rating_{uuid.uuid4().hex[:12]}"
        rating_doc = {
            "rating_id": rating_id,
            "faculty_id": faculty_id,
            "user_id": current_user.user_id,
            **rating.model_dump(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        await db.ratings.insert_one(rating_doc.copy())
        
        for category in ["teaching", "attendance", "doubt_clarification", "overall"]:
            val = rating.model_dump().get(category)
            if val is not None:
                current_avg = faculty_doc["avg_ratings"].get(category, 0)
                current_count = faculty_doc["rating_counts"].get(category, 0)
                
                total = current_avg * current_count
                new_total = total + val
                current_count += 1
                new_avg = new_total / current_count
                
                await db.faculty.update_one(
                    {"faculty_id": faculty_id},
                    {"$set": {
                        f"avg_ratings.{category}": new_avg,
                        f"rating_counts.{category}": current_count
                    }}
                )
    
    rating_doc = await db.ratings.find_one({"rating_id": rating_id}, {"_id": 0})
    if isinstance(rating_doc["created_at"], str):
        rating_doc["created_at"] = datetime.fromisoformat(rating_doc["created_at"])
    if isinstance(rating_doc["updated_at"], str):
        rating_doc["updated_at"] = datetime.fromisoformat(rating_doc["updated_at"])
    
    return Rating(**rating_doc)

@api_router.get("/faculty/{faculty_id}/ratings/me")
async def get_my_rating(faculty_id: str, current_user: User = Depends(get_current_user)):
    rating_doc = await db.ratings.find_one(
        {"faculty_id": faculty_id, "user_id": current_user.user_id},
        {"_id": 0}
    )
    
    if not rating_doc:
        return None
    
    if isinstance(rating_doc["created_at"], str):
        rating_doc["created_at"] = datetime.fromisoformat(rating_doc["created_at"])
    if isinstance(rating_doc["updated_at"], str):
        rating_doc["updated_at"] = datetime.fromisoformat(rating_doc["updated_at"])
    
    return Rating(**rating_doc)

# Comment Routes
@api_router.get("/faculty/{faculty_id}/comments", response_model=List[Comment])
async def get_comments(faculty_id: str):
    comments = await db.comments.find({"faculty_id": faculty_id}, {"_id": 0}).to_list(1000)
    
    for comment in comments:
        if isinstance(comment["created_at"], str):
            comment["created_at"] = datetime.fromisoformat(comment["created_at"])
    
    return comments

@api_router.post("/faculty/{faculty_id}/comments", response_model=Comment)
async def create_comment(faculty_id: str, comment: CommentCreate, current_user: User = Depends(get_current_user)):
    comment_id = f"comment_{uuid.uuid4().hex[:12]}"
    comment_doc = {
        "comment_id": comment_id,
        "faculty_id": faculty_id,
        "user_id": current_user.user_id,
        "user_name": current_user.name,
        "user_picture": current_user.picture,
        "content": comment.content,
        "parent_comment_id": comment.parent_comment_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.comments.insert_one(comment_doc.copy())
    
    comment_doc["created_at"] = datetime.fromisoformat(comment_doc["created_at"])
    return Comment(**comment_doc)

@api_router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str, current_user: User = Depends(get_current_user)):
    comment_doc = await db.comments.find_one({"comment_id": comment_id}, {"_id": 0})
    
    if not comment_doc:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment_doc["user_id"] != current_user.user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.comments.delete_one({"comment_id": comment_id})
    return {"message": "Comment deleted successfully"}

# Chat Routes
@api_router.get("/chats", response_model=List[Chat])
async def get_chats(current_user: User = Depends(get_current_user)):
    chats = await db.chats.find(
        {"participants": current_user.user_id},
        {"_id": 0}
    ).to_list(100)
    
    for chat in chats:
        if isinstance(chat["created_at"], str):
            chat["created_at"] = datetime.fromisoformat(chat["created_at"])
        if isinstance(chat["updated_at"], str):
            chat["updated_at"] = datetime.fromisoformat(chat["updated_at"])
        for msg in chat.get("messages", []):
            if isinstance(msg["created_at"], str):
                msg["created_at"] = datetime.fromisoformat(msg["created_at"])
    
    return chats

@api_router.post("/chats/messages")
async def send_message(message: ChatMessageCreate, current_user: User = Depends(get_current_user)):
    participants = sorted([current_user.user_id, message.recipient_id])
    
    chat_doc = await db.chats.find_one(
        {"participants": participants},
        {"_id": 0}
    )
    
    new_message = {
        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "sender_id": current_user.user_id,
        "content": message.content,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    if chat_doc:
        await db.chats.update_one(
            {"chat_id": chat_doc["chat_id"]},
            {
                "$push": {"messages": new_message},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
        chat_id = chat_doc["chat_id"]
    else:
        chat_id = f"chat_{uuid.uuid4().hex[:12]}"
        await db.chats.insert_one({
            "chat_id": chat_id,
            "participants": participants,
            "messages": [new_message],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })
    
    return {"chat_id": chat_id, "message": new_message}

# Recommendations
@api_router.get("/recommendations")
async def get_recommendations(current_user: User = Depends(get_current_user)):
    if not current_user.preferences:
        return []
    
    faculty_list = await get_all_faculty()
    
    recommendations = []
    for fac in faculty_list:
        total_score = 0
        count = 0
        
        for pref in current_user.preferences:
            pref_key = pref.lower().replace(" ", "_")
            if pref_key in fac['avg_ratings']:
                rating = fac['avg_ratings'][pref_key]
                if rating > 0:
                    total_score += rating
                    count += 1
        
        if count > 0:
            compatibility = (total_score / count) * 20
            recommendations.append({
                **fac, # FIX: Spread dictionary directly
                "compatibility_percentage": round(compatibility, 1)
            })
    
    recommendations.sort(key=lambda x: x["compatibility_percentage"], reverse=True)
    return recommendations[:10]

# Rankings
# Rankings
@api_router.get("/rankings")
async def get_rankings(department: Optional[str] = None, category: str = "overall", method: str = "weighted"):
    faculty_list = await get_all_faculty()
    
    if department:
        faculty_list = [f for f in faculty_list if department.lower() in f['department'].lower()]
    
    # Calculate global mean for Bayesian calculation
    total_ratings = sum(f['avg_ratings'].get(category, 0) * f['rating_counts'].get(category, 0) for f in faculty_list)
    total_count = sum(f['rating_counts'].get(category, 0) for f in faculty_list)
    mean_rating = total_ratings / total_count if total_count > 0 else 3.0
    
    C = 10
    
    rankings = []
    for fac in faculty_list:
        avg_rating = fac['avg_ratings'].get(category, 0)
        num_ratings = fac['rating_counts'].get(category, 0)
        
        if method == "weighted":
            # FIX: If no one has rated this professor, score is 0.0
            if num_ratings == 0:
                score = 0.0
            else:
                # Apply Bayesian average only if there are ratings
                score = (avg_rating * num_ratings + C * mean_rating) / (num_ratings + C)
        else:
            # Simple average is naturally 0 if num_ratings is 0
            score = avg_rating
        
        rankings.append({
            **fac,
            "score": round(score, 2),
            "rank": 0
        })
    
    # Sort by score descending (0 scores will naturally fall to the bottom)
    rankings.sort(key=lambda x: x["score"], reverse=True)
    
    for i, ranking in enumerate(rankings, 1):
        ranking["rank"] = i
    
    return rankings

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()