import os
import logging
from pathlib import Path
import uuid
import random
import json
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, APIRouter, HTTPException, Cookie, Response, Request, Depends
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, ConfigDict, EmailStr
import bcrypt

# --- WEBSOCKET IMPORTS ---
import socketio
from fastapi.staticfiles import StaticFiles

# --- PASSWORD HASHING IMPORTS ---
def get_password_hash(password):
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')

def verify_password(plain_password, hashed_password):
    password_byte_enc = plain_password.encode('utf-8')
    hash_byte_enc = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_byte_enc, hash_byte_enc)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'faculty_hub')]

# --- WEBSOCKET SETUP ---
_cors_env = os.environ.get('CORS_ORIGINS', 'http://localhost:3000')
cors_origins = _cors_env.split(',')

# Create a Socket.IO async server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=cors_origins)
app = FastAPI()
socket_app = socketio.ASGIApp(sio, app)

api_router = APIRouter(prefix="/api")

VIT_INSTITUTION_LINEAGE = "i4401726783"

# --- MODELS ---

class User(BaseModel):
    model_config = ConfigDict(extra="allow")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    is_admin: bool = False
    preferences: List[str] = Field(default_factory=list)
    ai_interests: List[str] = Field(default_factory=list)
    created_at: datetime
    # UNIFIED ANONYMOUS ID
    anonymous_id: Optional[str] = None 
    # Legacy fields for backwards compatibility
    anonymous_chat_id: Optional[str] = None
    anonymous_comment_id: Optional[str] = None

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    picture: Optional[str] = None
    preferences: Optional[List[str]] = None
    ai_interests: Optional[List[str]] = None

class Faculty(BaseModel):
    model_config = ConfigDict(extra="allow")
    faculty_id: str
    name: str
    department: str
    designation: str
    image_url: Optional[str] = None
    scholar_profile: Optional[str] = None
    publications: List[str] = Field(default_factory=list)
    research_interests: List[str] = Field(default_factory=list) # List in New Code
    openalex_projects: List[Dict[str, Any]] = Field(default_factory=list)
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
    openalex_projects: List[Dict[str, Any]] = Field(default_factory=list)

class FacultyUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    image_url: Optional[str] = None
    scholar_profile: Optional[str] = None
    publications: Optional[List[str]] = None
    research_interests: Optional[str] = None
    openalex_projects: Optional[List[Dict[str, Any]]] = None

class Rating(BaseModel):
    model_config = ConfigDict(extra="allow")
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
    model_config = ConfigDict(extra="allow")
    comment_id: str
    faculty_id: str
    user_id: str
    user_name: str 
    anonymous_handle: str 
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
    sender_anonymous_id: str 
    content: str
    created_at: datetime

class Chat(BaseModel):
    model_config = ConfigDict(extra="allow")
    chat_id: str
    participants: List[Dict[str, str]] 
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime

class ChatMessageCreate(BaseModel):
    recipient_id: str
    content: str

def load_faculty_from_csv():
    """
    Loads faculty from CSV using ROBUST logic.
    Ensures research_interests is a List.
    Prevents CSV from overwriting generated faculty_id.
    """
    file_path = ROOT_DIR / 'faculty_data.csv'
    
    if not file_path.exists():
        return None

    try:
        df = pd.read_csv(file_path)
        
        # Drop profile column
        profile_cols = ['Profile_URL', 'Profile URL', 'Profile', 'Link']
        for col in profile_cols:
            if col in df.columns:
                df = df.drop(columns=[col])
            
        faculty_list = []
        
        # Helper to find column regardless of case or spaces
        def get_col_val(target_names):
            for name in target_names:
                if name in df.columns:
                    return df[name]
                for col in df.columns:
                    if col.strip().lower() == name.lower():
                        return df[col]
            return pd.Series([None] * len(df), index=df.index)

        # Extract columns
        names = get_col_val(['Name'])
        departments = get_col_val(['Department'])
        designations = get_col_val(['Designation'])
        images = get_col_val(['Image', 'Image URL', 'Profile Picture'])
        research_ints = get_col_val(['Specialisation', 'Specialization', 'Research Interests', 'Research'])
        office_addrs = get_col_val(['Office Address', 'Address', 'Office'])
        emails = get_col_val(['Email', 'Email Address'])
        phones = get_col_val(['Phone', 'Mobile', 'Contact', 'Mobile Number'])

        KNOWN_DEPTS = ['SCOPE', 'SENSE', 'SMEC', 'SAS', 'VSB', 'VSL', 'VISH']

        for index, row in df.iterrows():
            # --- GENERATE ID FIRST ---
            faculty_id = f"csv_{index}_{uuid.uuid4().hex[:8]}"
            
            # Name
            raw_name = names.iloc[index]
            name_val = "Unknown" if pd.isna(raw_name) or str(raw_name).strip() == "" else raw_name

            # Department
            raw_dept = departments.iloc[index]
            dept_val = "Unknown" if pd.isna(raw_dept) else raw_dept

            # Designation
            raw_des = designations.iloc[index]
            if dept_val == "Unknown" and not pd.isna(raw_des) and isinstance(raw_des, str):
                for d in KNOWN_DEPTS:
                    if d in raw_des:
                        dept_val = d 
                        break
            
            if not pd.isna(raw_des) and isinstance(raw_des, str):
                parts = raw_des.split(',')
                parts = [p.strip() for p in parts if p.strip() != str(dept_val) and p.strip() != '']
                cleaned_des = ", ".join(parts)
                if not cleaned_des: cleaned_des = raw_des
            else:
                cleaned_des = "Unknown"

            # Image
            img_raw = images.iloc[index]
            if pd.isna(img_raw) or str(img_raw).strip() == "":
                img_val = None
            else:
                img_val = str(img_raw).strip()
            
            # Research Interests (Convert String to List)
            res_val = None if pd.isna(research_ints.iloc[index]) else research_ints.iloc[index]
            research_list = []
            if res_val and pd.notna(res_val):
                raw_res_str = str(res_val).strip()
                if raw_res_str.upper() != "N/A":
                    research_list = [s.strip() for s in raw_res_str.split(',')]

            addr_val = None if pd.isna(office_addrs.iloc[index]) else office_addrs.iloc[index]
            email_val = None if pd.isna(emails.iloc[index]) else emails.iloc[index]
            phone_val = None if pd.isna(phones.iloc[index]) else phones.iloc[index]

            faculty_data = {
                "faculty_id": faculty_id, # Explicitly set
                "name": name_val,
                "department": dept_val,
                "designation": cleaned_des,
                "image_url": img_val,
                "created_at": datetime.now(timezone.utc),
                "avg_ratings": {"teaching": 0, "attendance": 0, "doubt_clarification": 0, "overall": 0},
                "rating_counts": {"teaching": 0, "attendance": 0, "doubt_clarification": 0, "overall": 0}, # FIXED SYNTAX ERROR HERE
                "research_interests": research_list, # List
                "office_address": addr_val,
                "email": email_val,
                "phone": phone_val,
            }
            
            # Dynamic Columns
            skipped_cols = ['Name', 'Name of Faculty', 'Faculty Name', 
                            'Department', 'Dept', 'School Name', 'School Name',
                            'Designation', 'Title', 'Position', 'Role',
                            'Image', 'Image URL', 'Profile Picture', 'Photo', 'Picture',
                            'Specialisation', 'Specialization', 'Research Interests', 'Research', 'Area of Specialization',
                            'Office Address', 'Office_Address', 'Address', 'Office', 'Location',
                            'Email', 'Email Address', 
                            'Phone', 'Mobile', 'Contact', 'Mobile Number',
                            'Profile URL', 'Profile_URL', 'Profile', 'Link',
                            'faculty_id'] # Added faculty_id to skipped_cols
            
            for col in df.columns:
                should_skip = False
                col_clean = col.strip().lower()
                for skip_name in skipped_cols:
                    if col_clean == skip_name.lower():
                        should_skip = True
                        break
                if not should_skip:
                    val = row.get(col)
                    if pd.notna(val):
                        faculty_data[col] = val
            
            faculty_list.append(faculty_data)
            
        return faculty_list
        
    except Exception as e:
        logging.error(f"Error loading CSV: {e}")
        return None

def get_demo_faculty():
    departments = ['SCOPE', 'SENSE', 'SMEC', 'SAS', 'VSB', 'VSL', 'VISH']
    base_data = {
        'created_at': datetime.now(timezone.utc),
        'avg_ratings': {"teaching": 0, "attendance": 0, "doubt_clarification": 0, "overall": 0},
        'rating_counts': {"teaching": 0, "attendance": 0, "doubt_clarification": 0, "overall": 0}
    }
    
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
                "Specialisation": f"AI & ML in {dept}",
                "Office Address": f"Block {i+1}, Room {100+i}",
                "Email": f"{name.split(' ')[1].lower()}@vitap.ac.in",
                "Phone": f"+91 98765 432{i}",
                "openalex_projects": [],
                **base_data
            })
        return facs

    all_faculty = []
    
    # SCOPE
    all_faculty.extend(gen_dept_faculty('SCOPE', [
        "Dr. Ada Lovelace", "Prof. Alan Turing", "Dr. Grace Hopper", "Prof. Donald Knuth",
        "Dr. Linus Torvalds", "Prof. Tim Berners-Lee", "Dr. Margaret Hamilton", "Prof. Dennis Ritchie",
        "Dr. Sophie Wilson", "Prof. Guido van Rossum"
    ], ["Professor", "Associate Professor", "Assistant Professor", "HOD"]))

    # SENSE
    all_faculty.extend(gen_dept_faculty('SENSE', [
        "Dr. Nikola Tesla", "Prof. Michael Faraday", "Dr. Guglielmo Marconi", "Prof. Samuel Morse",
        "Dr. Claude Shannon", "Prof. Jack Kilby", "Dr. Robert Noyce", "Prof. Gordon Moore",
        "Dr. Andrew Grove", "Prof. Robert Hall"
    ], ["Dean", "Professor", "Associate Professor", "Assistant Professor"]))

    # SMEC
    all_faculty.extend(gen_dept_faculty('SMEC', [
        "Dr. Henry Ford", "Prof. Karl Benz", "Prof. Rudolf Diesel", "Dr. James Watt",
        "Prof. George Stephenson", "Dr. Isambard Brunel", "Prof. Nikolaus Otto", "Dr. Elijah McCoy",
        "Prof. Gottlieb Daimler", "Dr. Charles Kettering"
    ], ["Professor", "HOD", "Associate Professor", "Assistant Professor"]))

    # SAS
    all_faculty.extend(gen_dept_faculty('SAS', [
        "Dr. Marie Curie", "Prof. Albert Einstein", "Dr. Isaac Newton", "Prof. Galileo Galilei",
        "Dr. Richard Feynman", "Prof. Stephen Hawking", "Dr. Neil deGrasse Tyson", "Prof. Rosalind Franklin",
        "Dr. Dmitri Mendeleev", "Prof. Louis Pasteur"
    ], ["Senior Professor", "Professor", "Associate Professor", "Assistant Professor"]))

    # VSB
    all_faculty.extend(gen_dept_faculty('VSB', [
        "Dr. Peter Drucker", "Prof. Adam Smith", "Dr. Warren Buffett", "Prof. John Keynes",
        "Dr. Michael Porter", "Prof. Philip Kotler", "Dr. Jack Welch", "Prof. Henry Mintzberg",
        "Dr. Jim Collins", "Prof. Clayton Christensen"
    ], ["Professor", "Dean", "Associate Professor", "Assistant Professor"]))

    # VSL
    all_faculty.extend(gen_dept_faculty('VSL', [
        "Dr. Ruth Bader Ginsburg", "Prof. Oliver Wendell Holmes", "Dr. Thurgood Marshall", "Prof. Sandra Day O'Connor",
        "Dr. William Blackstone", "Prof. Hugo Black", "Dr. Learned Hand", "Prof. Benjamin Cardozo",
        "Dr. John Marshall", "Prof. Antonin Scalia"
    ], ["Senior Advocate", "Professor", "Associate Professor", "HOD"]))

    # VISH
    all_faculty.extend(gen_dept_faculty('VISH', [
        "Dr. Sigmund Freud", "Prof. Carl Jung", "Dr. B.F. Skinner", "Prof. Jean Piaget",
        "Dr. Noam Chomsky", "Prof. Jane Goodall", "Dr. Margaret Mead", "Prof. Sigmund Freud",
        "Dr. Abraham Maslow", "Prof. Erik Erikson"
    ], ["Professor", "Assistant Professor", "Associate Professor", "Dean"]))

    return all_faculty

@app.on_event("startup")
async def startup_event():
    logging.info("Checking database for faculty data...")
    count = await db.faculty.count_documents({})
    
    if count == 0:
        logging.info("Database is empty. Initializing data...")
        csv_data = load_faculty_from_csv()
        
        if csv_data:
            logging.info(f"Found CSV with {len(csv_data)} records. Importing to DB...")
            await db.faculty.insert_many(csv_data)
            logging.info("CSV Import complete.")
        else:
            logging.info("No CSV found or CSV error. Loading Demo Data...")
            demo_data = get_demo_faculty()
            await db.faculty.insert_many(demo_data)
            logging.info(f"Imported {len(demo_data)} demo faculty records.")
    else:
        logging.info(f"Database already contains {count} faculty records. Skipping import.")

    logging.info("Checking for seeded users and unified anonymous IDs...")
    
    users_cursor = db.users.find({})
    async for user_doc in users_cursor:
        update_data = {}
        
        # 1. Generate Unified ID if missing
        if not user_doc.get('anonymous_id'):
            new_id = str(random.randint(1000, 9999))
            update_data['anonymous_id'] = new_id
            update_data['anonymous_chat_id'] = new_id # Sync Chat ID
            update_data['anonymous_comment_id'] = new_id # Sync Comment ID
            logging.info(f"Generated unified Anonymous ID {new_id} for user {user_doc.get('email')}")
        
        # 2. If Unified ID exists but other fields are mismatched (legacy data), fix them
        elif user_doc.get('anonymous_chat_id') != user_doc.get('anonymous_id'):
             update_data['anonymous_chat_id'] = user_doc.get('anonymous_id')
        
        elif user_doc.get('anonymous_comment_id') != user_doc.get('anonymous_id'):
             update_data['anonymous_comment_id'] = user_doc.get('anonymous_id')
            
        if update_data:
            await db.users.update_one({'_id': user_doc['_id']}, {'$set': update_data})

    admin_email = "admin@vitapstudent.ac.in"
    admin_pass = "Admin123"
    admin_doc = await db.users.find_one({"email": admin_email})
    if not admin_doc:
        logging.info(f"Creating Admin user: {admin_email}")
        unified_id = str(random.randint(1000, 9999))
        await db.users.insert_one({
            "user_id": f"user_admin_{uuid.uuid4().hex[:12]}",
            "email": admin_email,
            "name": "System Administrator",
            "password_hash": get_password_hash(admin_pass),
            "is_admin": True,
            "preferences": [],
            "ai_interests": [],
            "created_at": datetime.now(timezone.utc),
            "anonymous_id": unified_id,
            "anonymous_chat_id": unified_id,
            "anonymous_comment_id": unified_id
        })
    
    demo_email = "demo@vitapstudent.ac.in"
    demo_pass = "Demo123"
    demo_doc = await db.users.find_one({"email": demo_email})
    if not demo_doc:
        logging.info(f"Creating Demo user: {demo_email}")
        unified_id = str(random.randint(1000, 9999))
        await db.users.insert_one({
            "user_id": f"user_demo_{uuid.uuid4().hex[:12]}",
            "email": demo_email,
            "name": "Demo User",
            "password_hash": get_password_hash(demo_pass),
            "is_admin": False,
            "preferences": [],
            "ai_interests": [],
            "created_at": datetime.now(timezone.utc),
            "anonymous_id": unified_id,
            "anonymous_chat_id": unified_id,
            "anonymous_comment_id": unified_id
        })

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
@api_router.post("/auth/register")
async def register_user(user_data: UserRegister):
    if not user_data.email.endswith("@vitapstudent.ac.in"):
        raise HTTPException(status_code=400, detail="Registration restricted to @vitapstudent.ac.in emails")

    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    unified_id = str(random.randint(1000, 9999))
    
    new_user = {
        "user_id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "password_hash": get_password_hash(user_data.password),
        "picture": None,
        "is_admin": False, 
        "preferences": [],
        "ai_interests": [],
        "created_at": datetime.now(timezone.utc),
        "anonymous_id": unified_id,
        "anonymous_chat_id": unified_id,
        "anonymous_comment_id": unified_id
    }
    
    await db.users.insert_one(new_user)
    return {"message": "User registered successfully", "user_id": user_id}

@api_router.post("/auth/login")
async def login_user(response: Response, login_data: UserLogin):
    user_doc = await db.users.find_one({"email": login_data.email}, {"_id": 0})
    
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(login_data.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

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
    query = {}
    if department:
        query["department"] = {"$regex": f"^{department}$", "$options": "i"}

    cursor = db.faculty.find(query, {"_id": 0})
    faculty_list = await cursor.to_list(1000)
    
    for f in faculty_list:
        if isinstance(f["created_at"], str):
            f["created_at"] = datetime.fromisoformat(f["created_at"])
            
    return faculty_list

@api_router.get("/faculty/{faculty_id}", response_model=Faculty)
async def get_faculty(faculty_id: str):
    faculty_doc = await db.faculty.find_one({"faculty_id": faculty_id}, {"_id": 0})
    
    if not faculty_doc:
        raise HTTPException(status_code=404, detail="Faculty not found")

    if isinstance(faculty_doc["created_at"], str):
        faculty_doc["created_at"] = datetime.fromisoformat(faculty_doc["created_at"])
    
    return Faculty(**faculty_doc)

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
        "openalex_projects": [],
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.faculty.insert_one(faculty_doc)
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

@api_router.post("/faculty/{faculty_id}/ratings", response_model=Rating)
async def submit_rating(faculty_id: str, rating: RatingSubmit, current_user: User = Depends(get_current_user)):
    
    faculty_doc = await db.faculty.find_one({"faculty_id": faculty_id}, {"_id": 0})
    
    if not faculty_doc:
        raise HTTPException(status_code=404, detail="Faculty not found")
    
    existing_rating = await db.ratings.find_one({"faculty_id": faculty_id, "user_id": current_user.user_id}, {"_id": 0})
    
    now = datetime.now(timezone.utc)
    
    if existing_rating:
        rating_id = existing_rating["rating_id"]
        old_values = {k: existing_rating.get(k) for k in ["teaching", "attendance", "doubt_clarification", "overall"]}
        
        update_data = {k: v for k, v in rating.model_dump().items() if v is not None}
        update_data["updated_at"] = now
        
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
            "created_at": now,
            "updated_at": now
        }
        
        await db.ratings.insert_one(rating_doc)
        
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

@api_router.get("/faculty/{faculty_id}/comments", response_model=List[Comment])
async def get_comments(faculty_id: str):
    comments = await db.comments.find({"faculty_id": faculty_id}, {"_id": 0}).to_list(1000)
    
    for comment in comments:
        if isinstance(comment["created_at"], str):
            comment["created_at"] = datetime.fromisoformat(comment["created_at"])
    
    return comments

@api_router.post("/faculty/{faculty_id}/comments")
async def create_comment(faculty_id: str, comment: CommentCreate, current_user: User = Depends(get_current_user)):
    # GATE: Check if user has rated this faculty
    rating_doc = await db.ratings.find_one({"faculty_id": faculty_id, "user_id": current_user.user_id})
    if not rating_doc:
        raise HTTPException(status_code=403, detail="You must rate this faculty before commenting.")

    comment_id = f"comment_{uuid.uuid4().hex[:12]}"
    
    # FIX: Use UNIFIED anonymous_id
    anonymous_handle = f"Anonymous@{current_user.anonymous_id}"
    
    comment_doc = {
        "comment_id": comment_id,
        "faculty_id": faculty_id,
        "user_id": current_user.user_id,
        "user_name": current_user.name, 
        "anonymous_handle": anonymous_handle,
        "user_picture": current_user.picture,
        "content": comment.content,
        "parent_comment_id": comment.parent_comment_id,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.comments.insert_one(comment_doc)
    
    return {"message": "Comment created successfully", "comment_id": comment_id}

@api_router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str, current_user: User = Depends(get_current_user)):
    comment_doc = await db.comments.find_one({"comment_id": comment_id}, {"_id": 0})
    
    if not comment_doc:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment_doc["user_id"] != current_user.user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.comments.delete_one({"comment_id": comment_id})
    return {"message": "Comment deleted successfully"}

@api_router.get("/chats", response_model=List[Chat])
async def get_chats(current_user: User = Depends(get_current_user)):
    chats_cursor = db.chats.find({"participants": current_user.user_id}, {"_id": 0})
    chats_list = await chats_cursor.to_list(100)
    
    for chat in chats_list:
        participant_ids = chat.get("participants", [])
        resolved_participants = []
        
        for pid in participant_ids:
            if pid == current_user.user_id:
                resolved_participants.append({
                    "user_id": pid,
                    "anonymous_chat_id": "You"
                })
            else:
                other_user = await db.users.find_one({"user_id": pid}, {"_id": 0, "anonymous_chat_id": 1})
                handle = other_user.get("anonymous_chat_id", "Unknown") if other_user else "Unknown"
                resolved_participants.append({
                    "user_id": pid,
                    "anonymous_chat_id": f"Anonymous@{handle}" # Format return as Anonymous@ID
                })
        
        chat["participants"] = resolved_participants

        if isinstance(chat["created_at"], str):
            chat["created_at"] = datetime.fromisoformat(chat["created_at"])
        if isinstance(chat["updated_at"], str):
            chat["updated_at"] = datetime.fromisoformat(chat["updated_at"])
        for msg in chat.get("messages", []):
            if isinstance(msg["created_at"], str):
                msg["created_at"] = datetime.fromisoformat(msg["created_at"])
            if "sender_anonymous_id" not in msg:
                sender = await db.users.find_one({"user_id": msg["sender_id"]}, {"_id": 0, "anonymous_chat_id": 1})
                msg["sender_anonymous_id"] = f"Anonymous@{sender.get('anonymous_chat_id', 'Unknown')}" if sender else "Unknown"
    
    return chats_list

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
        # FIX: Use UNIFIED anonymous_id
        "sender_anonymous_id": f"Anonymous@{current_user.anonymous_id}",
        "content": message.content,
        "created_at": datetime.now(timezone.utc)
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
    
    # WEBSOCKET EMIT
    room = f"chat_{chat_id}"
    await sio.emit(room, new_message)
    
    return {"chat_id": chat_id, "message": new_message}

@api_router.get("/recommendations")
async def get_recommendations(current_user: User = Depends(get_current_user)):
    if current_user.is_admin:
        return []

    user_ai_interests = current_user.ai_interests or []
    user_rating_prefs = current_user.preferences or []
    
    if not user_rating_prefs and not user_ai_interests:
        return []

    faculty_list = await get_all_faculty()
    
    recommendations = []
    
    for fac in faculty_list:
        # --- PART 1: PREFERENCES (RATINGS) ---
        # Calculate Compatibility Score ONLY based on preferences (ratings)
        rating_compatibility = 0.0
        rating_count = 0
        
        for pref in user_rating_prefs:
            pref_key = pref.lower().replace(" ", "_")
            if pref_key in fac['avg_ratings']:
                rating = fac['avg_ratings'][pref_key]
                if rating > 0:
                    rating_compatibility += rating
                    rating_count += 1
        
        # Normalize to 0-100. Max rating is 5.
        # FIX: If user has rating preferences, score is determined by ratings (Part 1).
        # Fallback to 'overall' if specific category is 0
        normalized_rating_score = 0
        if rating_count > 0:
            normalized_rating_score = (rating_compatibility / rating_count) * 20 
        else:
             # No ratings in selected categories, check for fallback to Overall
             if 'overall' in fac['avg_ratings'] and fac['avg_ratings']['overall'] > 0:
                 normalized_rating_score = fac['avg_ratings']['overall'] * 20

        # --- PART 2: RESEARCH INTERESTS (INTELLIGENT KEYWORD MATCHING) ---
        # This determines IF faculty appears in list, not their score
        match_found = False
        reason = ""
        
        if user_ai_interests:
            # Combine search text: Research Interests + All Project Titles
            search_text = ""
            
            # Handle None values safely
            res_interests = fac.get('research_interests') or []
            # Handle List correctly
            if isinstance(res_interests, list):
                search_text += " ".join(res_interests) + " "
            else:
                search_text += str(res_interests) + " "
            
            projects = fac.get('openalex_projects') or []
            for p in projects:
                search_text += p.get('title', '') + " "
            
            search_text = search_text.lower()
            
            # Intelligent Matching Loop
            for interest in user_ai_interests:
                interest_lower = interest.lower()
                
                # 1. Direct Match
                if interest_lower in search_text:
                    match_found = True
                    reason = f"Matched '{interest}' in Research/Projects."
                    # Check if it was in a specific project for better feedback
                    for p in projects:
                        if interest_lower in p.get('title', '').lower():
                            reason = f"Matched '{interest}' in project: '{p.get('title', '')[:30]}...'"
                            break
                    if not match_found:
                        reason = f"Matched '{interest}' in research interests."
                    break

        # --- COMBINATION LOGIC ---
        # Priority:
        # 1. If User selected Preferences -> Score is based on Ratings (Part 1).
        # 2. If User selected Research Interests AND Matched -> Give default score if no ratings.
        
        final_score = 0
        show_reason = False
        
        # SCENARIO 1: ONLY AI INTERESTS
        # Requirement: Don't show compatibility percentage
        if not user_rating_prefs and user_ai_interests:
            if match_found:
                # Give a default score for relevance (e.g., 85)
                final_score = 85 # Used for sorting only
                show_reason = True
        
        # SCENARIO 2: ONLY RATING PREFERENCES (Ratings)
        # Requirement: Show score.
        elif user_rating_prefs and not user_ai_interests:
            if rating_count > 0:
                final_score = normalized_rating_score
                show_reason = True
        
        # SCENARIO 3: BOTH INTERESTS AND RATINGS
        # Requirement: Priority to Ratings. Show score.
        elif user_rating_prefs and user_ai_interests:
            if rating_count > 0:
                # If ratings exist, use rating score, ignore AI score
                final_score = normalized_rating_score
                show_reason = True
            elif match_found:
                # Fallback: If no ratings, use AI score
                final_score = 85
                show_reason = True

        if show_reason:
            rec_data = {
                **fac,
                "recommendation_reason": reason
            }
            
            # Requirement: Show compatibility percentage ONLY if Rating Prefs are involved
            if user_rating_prefs:
                rec_data["compatibility_percentage"] = round(final_score, 1)
            
            recommendations.append(rec_data)

    # Sort by compatibility percentage descending
    # If AI only, compatibility_percentage won't exist, so sort by 0 (fallback) or rely on order
    recommendations.sort(key=lambda x: x.get("compatibility_percentage", 0), reverse=True)
    
    return recommendations[:10]


@api_router.post("/admin/sync-openalex")
async def sync_openalex_data(current_user: User = Depends(get_current_user)):
    """
    Admin-only route to fetch OpenAlex projects for VIT-AP University faculty.
    Strategy:
    1. Clean faculty name (remove titles).
    2. Search VIT-AP University authors.
    3. Match Faculty Name to OpenAlex Author Name (Handling reordering & initials).
    4. Fetch works (Filtered by VIT-AP).
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    api_key = os.environ.get('OPENALEX_API_KEY')
    if not api_key:
        logging.error("DEBUG: OPENALEX_API_KEY is MISSING in .env file!")
        raise HTTPException(status_code=400, detail="OPENALEX_API_KEY not found in environment variables.")
    
    logging.info("Starting OpenAlex Sync (VIT-AP University Only)...")
    
    # 1. Get all faculty to sync
    all_faculty_data = await db.faculty.find({}, {"_id": 0}).to_list(1000)
    
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    processed_names = []

    def clean_name_string(name_str):
        """Lowercase, remove punctuation."""
        return name_str.lower().replace(",", "").replace(".", "").strip()

    for faculty in all_faculty_data:
        
        # --- STEP 1: Clean Faculty Name ---
        raw_name = faculty["name"]
        prefixes_to_remove = [
            "dr.", "mr.", "ms.", "mrs.", "prof.", "dr", "prof", 
            "assistant professor", "associate professor", "dean", "hod"
        ]
        clean_faculty_name = raw_name
        for prefix in prefixes_to_remove:
            if clean_faculty_name.lower().startswith(prefix):
                clean_faculty_name = clean_faculty_name[len(prefix):].strip()
        
        if not clean_faculty_name:
            logging.error(f"Skipping faculty {faculty.get('name')}: Name became empty after cleaning")
            skipped_count += 1
            continue
            
        # Create a set of tokens for the faculty
        faculty_tokens = set(clean_name_string(clean_faculty_name).split())
        
        if not faculty_tokens:
            continue
            
        if clean_faculty_name in processed_names:
            logging.info(f"Skipping duplicate query for: {clean_faculty_name}")
            skipped_count += 1
            continue
        processed_names.append(clean_faculty_name)

        target_author_id = None

        try:
            # --- STEP 2: Search for Author Affiliated with VIT-AP University ---
            url_author_search = "https://api.openalex.org/authors"
            params_author = {
                "filter": f"last_known_institutions.lineage:{VIT_INSTITUTION_LINEAGE}",
                "search": clean_faculty_name,
                "per_page": 10,
                "mailto": "admin@vitapstudent.ac.in"
            }
            headers = {"x-api-key": api_key}

            logging.info(f"Searching for '{clean_faculty_name}' in VIT-AP authors...")
            
            response_author = requests.get(url_author_search, params=params_author, headers=headers, timeout=15.0)
            
            # Search through VIT-AP authors to find name match
            if response_author.status_code == 200 and response_author.json().get("results"):
                data_author = response_author.json()
                vit_authors = data_author["results"]
                
                found_match = False
                for author in vit_authors:
                    author_display = author.get("display_name", "")
                    author_id = author.get("id", "")
                    
                    # --- NEW SMART MATCHING LOGIC ---
                    author_tokens = set(clean_name_string(author_display).split())

                    # 1. Exact Set Match (Handles "Anil Vitthalrao Turukmane" <-> "Turukmane Anil Vitthalrao")
                    if faculty_tokens == author_tokens:
                        target_author_id = author_id
                        logging.info(f"✓ Exact Match Found: '{raw_name}' <-> '{author_display}'")
                        found_match = True
                        break
                    
                    # 2. Subset Match (Handles missing middle names)
                    if faculty_tokens.issubset(author_tokens) or author_tokens.issubset(faculty_tokens):
                         # Check similarity ratio loosely to avoid false positives
                        overlap = len(faculty_tokens & author_tokens)
                        if overlap >= min(len(faculty_tokens), len(author_tokens)):
                            target_author_id = author_id
                            logging.info(f"✓ Subset Match Found: '{raw_name}' <-> '{author_display}'")
                            found_match = True
                            break

                    # 3. Initial Matching (Handles "Anil Vitthalrao Turukmane" <-> "A V Turukmane")
                    # We verify that all full tokens in author exist in faculty
                    full_author_tokens = [t for t in author_tokens if len(t) >1]
                    if any(t not in faculty_tokens for t in full_author_tokens):
                        continue # Author has a full name (e.g. "Amit") that Faculty doesn't have (e.g. "Anil")
                    
                    # We verify that initials in author match first letters of faculty names
                    initial_author_tokens = [t for t in author_tokens if len(t) == 1]
                    match_possible = True
                    for initial in initial_author_tokens:
                        # Check if faculty has a name starting with this initial
                        if not any(f_token.startswith(initial) for f_token in faculty_tokens):
                            match_possible = False
                            break
                    
                    if match_possible:
                        # Additional check: ensure the core name (longest token) matches
                        # e.g., "Turukmane" is definitely present
                        longest_author = max(author_tokens, key=len)
                        if longest_author in faculty_tokens:
                            target_author_id = author_id
                            logging.info(f"✓ Initial Match Found: '{raw_name}' <-> '{author_display}'")
                            found_match = True
                            break
                
                if not found_match:
                    logging.info(f"✗ Faculty '{raw_name}' NOT found in VIT-AP authors list.")
                    skipped_count += 1
                    continue
            else:
                if response_author.status_code != 200:
                    logging.warning(f"Could not search VIT-AP authors. Status: {response_author.status_code}")
                else:
                    logging.info(f"No OpenAlex record found for '{clean_faculty_name}'. Skipping.")
                skipped_count += 1
                continue

            if not target_author_id:
                logging.info(f"✗ No author ID found for '{raw_name}' at VIT-AP. Skipping.")
                skipped_count += 1
                continue

            # --- STEP 3: Fetch Works for the Matched Author ---
            url_works_final = "https://api.openalex.org/works"

            # --- LOGIC 2: Fetch ONLY VIT-AP works (Active) ---
            params_final = {
                # Filter by Author ID AND VIT-AP Institution Lineage
                "filter": f"authorships.author.id:{target_author_id},authorships.institutions.lineage:{VIT_INSTITUTION_LINEAGE}",
                "per_page": 200,
                "sort": "publication_year:desc",
                "mailto": "admin@vitapstudent.ac.in"
            }

            logging.info(f"Fetching VIT-AP publications for {raw_name} (ID: {target_author_id})...")
            
            response_works = requests.get(url_works_final, params=params_final, headers=headers, timeout=15.0)

            if response_works.status_code != 200:
                logging.error(f"Error fetching works for {target_author_id}: {response_works.text[:100]}")
                failed_count += 1
                continue

            data_works = response_works.json()
            
            # --- PROCESS WORKS ---
            clean_projects = []
            
            if "results" in data_works and data_works["results"]:
                raw_results = data_works["results"]
                for res in raw_results:
                    if isinstance(res, dict):
                        openalex_id = str(res.get("id", ""))
                        title = str(res.get("title", ""))
                        year_data = res.get("publication_year")
                        pub_year = str(year_data) if year_data else "Unknown"
                        pub_type = str(res.get("type", "") or "article")
                        
                        clean_projects.append({
                            "openalex_id": openalex_id,
                            "title": title,
                            "publication_year": pub_year,
                            "type": pub_type
                        })
            
            if clean_projects:
                await db.faculty.update_one(
                    {"faculty_id": faculty["faculty_id"]},
                    {"$set": {"openalex_projects": clean_projects}}
                )
                updated_count += 1
                logging.info(f"✓ Updated {raw_name} with {len(clean_projects)} publications.")
            else:
                logging.info(f"No VIT-AP publications found for {raw_name}")
                skipped_count += 1

        except Exception as e:
            logging.error(f"Error processing faculty {faculty.get('name')}: {e}")
            failed_count += 1

    logging.info(f"OpenAlex Sync completed. Updated: {updated_count}, Skipped: {skipped_count}, Failed: {failed_count}")
    return {
        "message": "Sync completed",
        "total_processed": len(all_faculty_data),
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count
    }

@api_router.get("/rankings")
async def get_rankings(department: Optional[str] = None, category: str = "overall", method: str = "weighted", current_user: User = Depends(get_current_user)):
    # Admin Logic: Admins do not need rankings
    if current_user.is_admin:
        return []

    faculty_list = await get_all_faculty(department=department)
    
    total_ratings = sum(f['avg_ratings'].get(category, 0) * f['rating_counts'].get(category, 0) for f in faculty_list)
    total_count = sum(f['rating_counts'].get(category, 0) for f in faculty_list)
    mean_rating = total_ratings / total_count if total_count > 0 else 3.0
    
    C = 10
    
    rankings = []
    for fac in faculty_list:
        avg_rating = fac['avg_ratings'].get(category, 0)
        num_ratings = fac['rating_counts'].get(category, 0)
        
        if method == "weighted":
            if num_ratings == 0:
                score = 0.0
            else:
                score = (avg_rating * num_ratings + C * mean_rating) / (num_ratings + C)
        else:
            score = avg_rating
        
        rankings.append({
            **fac,
            "score": round(score, 2),
            "rank": 0
        })
    
    rankings.sort(key=lambda x: x["score"], reverse=True)
    
    for i, ranking in enumerate(rankings, 1):
        ranking["rank"] = i
    
    return rankings

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins, 
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