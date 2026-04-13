import sys
import asyncio
import os
import logging
import random
import time
import re
import json
import requests
import smtplib
import bcrypt
import socketio
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
import uuid
import pandas as pd
import numpy as np
from better_profanity import profanity
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, APIRouter, HTTPException, Cookie, Response, Request, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import uvicorn
from recommendation_engine import FacultyRecommender

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def send_smtp_email_sync(recipient: str, subject: str, body_html: str):
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASSWORD')

    if not smtp_host or not smtp_user or not smtp_pass:
        logging.error("SMTP credentials not configured. Email skipped.")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = recipient
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipient, msg.as_string())
        logging.info(f"Email sent to {recipient}")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

async def send_email_async(recipient: str, subject: str, body_html: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, send_smtp_email_sync, recipient, subject, body_html)

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

mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'faculty_hub')]

_cors_env = os.environ.get('CORS_ORIGINS', 'http://localhost:3000')
cors_origins = _cors_env.split(',')

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=cors_origins)
app = FastAPI()
socket_app = socketio.ASGIApp(sio, app)
scheduler = AsyncIOScheduler()

api_router = APIRouter(prefix="/api")

VIT_INSTITUTION_LINEAGE = "i4401726783"
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
ADMIN_ENV_EMAIL = os.environ.get('ADMIN_EMAIL')
ADMIN_ENV_PASSWORD = os.environ.get('ADMIN_PASSWORD')

class User(BaseModel):
    model_config = ConfigDict(extra="allow")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    is_admin: bool = False
    blocked: bool = False 
    preferences: List[str] = Field(default_factory=list)
    ai_interests: List[str] = Field(default_factory=list)
    created_at: datetime
    anonymous_id: Optional[str] = None 
    anonymous_chat_id: Optional[str] = None
    anonymous_comment_id: Optional[str] = None
    theme_preference: str = "light"

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
    theme_preference: Optional[str] = None

class UserAdminUpdate(BaseModel):
    is_admin: Optional[bool] = None
    blocked: Optional[bool] = None

class Faculty(BaseModel):
    model_config = ConfigDict(extra="allow")
    faculty_id: str
    name: str
    department: str
    designation: str
    image_url: Optional[str] = None
    scholar_profile: Optional[str] = None
    publications: List[str] = Field(default_factory=list)
    research_interests: List[str] = Field(default_factory=list) 
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
    research_interests: Optional[Union[str, List[str]]] = None 
    openalex_projects: List[Dict[str, Any]] = Field(default_factory=list)

class FacultyUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    image_url: Optional[str] = None
    scholar_profile: Optional[str] = None
    publications: Optional[List[str]] = None
    research_interests: Optional[Union[str, List[str]]] = None
    openalex_projects: Optional[Dict[str, Any]] = None

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
    model_config = ConfigDict(extra="allow")
    message_id: str
    sender_id: str
    sender_anonymous_id: str 
    content: str
    created_at: datetime
    is_admin_sender: bool = False

class ChatParticipant(BaseModel):
    model_config = ConfigDict(extra="allow")
    user_id: str
    anonymous_chat_id: str
    is_admin: bool = False

class Chat(BaseModel):
    model_config = ConfigDict(extra="allow")
    chat_id: str
    participants: List[str]
    messages: List[ChatMessage]
    unread_counts: Dict[str, int] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

class ChatMessageCreate(BaseModel):
    recipient_id: str
    content: str

def load_faculty_from_csv():
    file_path = ROOT_DIR / 'faculty_data.csv'
    if not file_path.exists():
        return None
    try:
        df = pd.read_csv(file_path)
        faculty_list = []
        
        def get_col_val(target_names):
            for name in target_names:
                if name in df.columns:
                    return df[name]
                for col in df.columns:
                    if col.strip().lower() == name.lower():
                        return df[col]
            return pd.Series([None] * len(df), index=df.index)

        names = get_col_val(['Name'])
        designations = get_col_val(['Designation'])
        profile_urls = get_col_val(['Profile_URL', 'Profile Link', 'Link'])
        images = get_col_val(['Image_URL', 'Image', 'Image URL', 'Profile Picture'])
        research_ints = get_col_val(['Specialisation', 'Specialization', 'Research Interests', 'Research'])
        office_addrs = get_col_val(['Office_Address', 'Address', 'Office'])
        emails = get_col_val(['Email', 'Email Address'])
        phones = get_col_val(['Phone', 'Mobile', 'Contact', 'Mobile Number'])

        for index, row in df.iterrows():
            raw_name = names.iloc[index]
            if pd.isna(raw_name): continue
            raw_des = designations.iloc[index]
            
            prefixes_to_remove = ["dr.", "mr.", "ms.", "mrs.", "prof.", "dr", "prof", "assistant professor", "associate professor", "dean", "hod"]
            clean_faculty_name = str(raw_name)
            for prefix in prefixes_to_remove:
                if clean_faculty_name.lower().startswith(prefix):
                    clean_faculty_name = clean_faculty_name[len(prefix):].strip()
            
            if not clean_faculty_name:
                logging.error(f"Skipping faculty {raw_name}: Name became empty")
                continue
            
            dept_val = "Unknown"
            raw_profile_url = profile_urls.iloc[index] if 'profile_urls' in locals() else None
            raw_email = emails.iloc[index]
            
            if raw_profile_url and not pd.isna(raw_profile_url):
                url_str = str(raw_profile_url).upper()
                if "(SCOPE)" in url_str: dept_val = "SCOPE"
                elif "(SENSE)" in url_str: dept_val = "SENSE"
                elif "(SMEC)" in url_str: dept_val = "SMEC"
                elif "(SAS)" in url_str: dept_val = "SAS"
                elif "(VSB)" in url_str: dept_val = "VSB"
                elif "(VSL)" in url_str: dept_val = "VSL"
                elif "(VISH)" in url_str: dept_val = "VISH"

            if dept_val == "Unknown" and not pd.isna(raw_des):
                des_text = str(raw_des).upper()
                tokens = des_text.replace(',', ' ').replace(';', ' ').split()
                valid_depts = ["SCOPE", "SENSE", "SMEC", "SAS", "VSB", "VSL", "VISH"]
                for token in tokens:
                    if token in valid_depts:
                        dept_val = token
                        break

            if dept_val == "Unknown" and not pd.isna(raw_email):
                email_text = str(raw_email).upper()
                if "SCOPE" in email_text: dept_val = "SCOPE"
                elif "SENSE" in email_text: dept_val = "SENSE"
                elif "SMEC" in email_text: dept_val = "SMEC"
                elif "SAS" in email_text: dept_val = "SAS"
                elif "VSB" in email_text: dept_val = "VSB"
                elif "VSL" in email_text: dept_val = "VSL"
                elif "VISH" in email_text: dept_val = "VISH"

            if pd.notna(raw_des):
                parts = str(raw_des).split(',')
                parts = [p.strip() for p in parts if p.strip() != '']
                cleaned_parts = []
                for part in parts:
                    if part not in ["SCOPE", "SENSE", "SMEC", "SAS", "VSB", "VSL", "VISH", "REGISTRAR", "VICE CHANCELLOR"]:
                        cleaned_parts.append(part)
                cleaned_des = ", ".join(cleaned_parts) if cleaned_parts else str(raw_des)
            else:
                cleaned_des = "Unknown"
            
            faculty_id = f"csv_{index}_{uuid.uuid4().hex[:8]}"            
            img_raw = images.iloc[index]
            img_val = None if pd.isna(img_raw) or str(img_raw).strip() == "" else str(img_raw).strip()
            raw_res = research_ints.iloc[index]
            research_list = []
            if raw_res and pd.notna(raw_res):
                raw_res_str = str(raw_res).strip()
                if raw_res_str.upper() != "N/A":
                    research_list = [s.strip() for s in raw_res_str.split(',')]
            
            addr_val = None if pd.isna(office_addrs.iloc[index]) else office_addrs.iloc[index]
            email_val = None if pd.isna(emails.iloc[index]) else emails.iloc[index]
            phone_val = None if pd.isna(phones.iloc[index]) else phones.iloc[index]

            faculty_data = {
                "faculty_id": faculty_id,
                "name": clean_faculty_name,
                "department": dept_val,
                "designation": cleaned_des,
                "image_url": img_val,
                "created_at": datetime.now(timezone.utc),
                "avg_ratings": {"teaching": 0, "attendance": 0, "doubt_clarification": 0, "overall": 0},
                "rating_counts": {"teaching": 0, "attendance": 0, "doubt_clarification": 0, "overall": 0},
                "research_interests": research_list, 
                "office_address": addr_val,
                "email": email_val,
                "phone": phone_val,
            }
            
            skipped_cols = ['Name', 'Name of Faculty', 'Faculty Name', 'Department', 'Dept', 'School Name', 'School Name', 'Designation', 'Title', 'Position', 'Role', 'Image', 'Image URL', 'Profile Picture', 'Photo', 'Picture', 'Image_URL', 'Specialisation', 'Specialization', 'Research Interests', 'Research', 'Area of Specialization', 'Office Address', 'Office_Address', 'Address', 'Office', 'Location', 'Email', 'Email Address', 'Phone', 'Mobile', 'Contact', 'Mobile Number', 'Profile URL', 'Profile_URL', 'Profile', 'Link', 'faculty_id']
            
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
                "Email": f"{name.split(' ')[1].lower()}@vitapstudent.ac.in",
                "Phone": f"+91 98765 432{i}",
                "openalex_projects": [],
                **base_data
            })
        return facs

    all_faculty = []
    all_faculty.extend(gen_dept_faculty('SCOPE', ["Dr. Ada Lovelace", "Prof. Alan Turing", "Dr. Grace Hopper", "Prof. Donald Knuth", "Dr. Linus Torvalds", "Prof. Tim Berners-Lee", "Dr. Margaret Hamilton", "Prof. Dennis Ritchie", "Dr. Sophie Wilson", "Prof. Guido van Rossum"], ["Professor", "Associate Professor", "Assistant Professor", "HOD"]))
    all_faculty.extend(gen_dept_faculty('SENSE', ["Dr. Nikola Tesla", "Prof. Michael Faraday", "Dr. Guglielmo Marconi", "Prof. Samuel Morse", "Dr. Claude Shannon", "Prof. Jack Kilby", "Dr. Robert Noyce", "Prof. Gordon Moore", "Dr. Andrew Grove", "Prof. Robert Hall"], ["Dean", "Professor", "Associate Professor", "Assistant Professor"]))
    all_faculty.extend(gen_dept_faculty('SMEC', ["Dr. Henry Ford", "Prof. Karl Benz", "Prof. Rudolf Diesel", "Dr. James Watt", "Prof. George Stephenson", "Dr. Isambard Brunel", "Prof. Nikolaus Otto", "Dr. Elijah McCoy", "Prof. Gottlieb Daimler", "Dr. Charles Kettering"], ["Professor", "HOD", "Associate Professor", "Assistant Professor"]))
    all_faculty.extend(gen_dept_faculty('SAS', ["Dr. Marie Curie", "Prof. Albert Einstein", "Dr. Isaac Newton", "Prof. Galileo Galilei", "Dr. Richard Feynman", "Prof. Stephen Hawking", "Dr. Neil deGrasse Tyson", "Prof. Rosalind Franklin", "Dr. Dmitri Mendeleev", "Prof. Louis Pasteur"], ["Senior Professor", "Professor", "Associate Professor", "Assistant Professor"]))
    all_faculty.extend(gen_dept_faculty('VSB', ["Dr. Peter Drucker", "Prof. Adam Smith", "Dr. Warren Buffett", "Prof. John Keynes", "Dr. Michael Porter", "Prof. Philip Kotler", "Dr. Jack Welch", "Prof. Henry Mintzberg", "Dr. Jim Collins", "Prof. Clayton Christensen"], ["Professor", "Dean", "Associate Professor", "Assistant Professor"]))
    all_faculty.extend(gen_dept_faculty('VSL', ["Dr. Ruth Bader Ginsburg", "Prof. Oliver Wendell Holmes", "Dr. Thurgood Marshall", "Prof. Sandra Day O'Connor", "Dr. William Blackstone", "Prof. Hugo Black", "Dr. Learned Hand", "Prof. Benjamin Cardozo", "Dr. John Marshall", "Prof. Antonin Scalia"], ["Senior Advocate", "Professor", "Associate Professor", "HOD"]))
    all_faculty.extend(gen_dept_faculty('VISH', ["Dr. Sigmund Freud", "Prof. Carl Jung", "Dr. B.F. Skinner", "Prof. Jean Piaget", "Dr. Noam Chomsky", "Prof. Jane Goodall", "Dr. Margaret Mead", "Prof. Sigmund Freud", "Dr. Abraham Maslow", "Prof. Erik Erikson"], ["Professor", "Assistant Professor", "Associate Professor", "Dean"]))
    return all_faculty

SELECTORS = {
    "card_link": "//a[contains(@href, '/faculty/')]",
    "card_name": ".//h1[contains(@class, 'text-[16px]')]",
    "card_desig": ".//h1[contains(@class, 'text-[12px]')]",
    "card_img": ".//img",
    "next_button": "//div[contains(@class, 'bg-[#DCCED0]')]//div[contains(@class, 'cursor-pointer')][last()]",
    "email_link": "//a[contains(@href, 'mailto:')]",
    "specialisation_label": "Specialisation",
    "address_label": "Office Address"
}

def _get_text_after_label(driver, label_text):
    try:
        elem = driver.find_element(By.XPATH, f"//*[contains(text(), '{label_text}')]/..")
        full_text = elem.text
        return full_text.replace(label_text, "").replace(":", "").strip()
    except:
        return "N/A"

def _run_selenium_scraper_sync():
    logging.info("Starting Selenium Scraper to update faculty_data.csv...")
    options = webdriver.ChromeOptions()
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()
    driver.get("https://vitap.ac.in/allfaculty")
    
    all_faculty_data = []
    seen_urls = set()
    page_count = 1

    try:
        while True:
            logging.info(f"Scraping Page {page_count}...")
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, SELECTORS["card_link"])))
            except:
                logging.info("No cards found. Ending.")
                break

            cards = driver.find_elements(By.XPATH, SELECTORS["card_link"])
            
            try:
                first_card_url = cards[0].get_attribute("href")
                if first_card_url in seen_urls:
                    logging.info("Loop detected. Stopping script.")
                    break
            except Exception:
                pass

            page_listings = []
            for card in cards:
                try:
                    url = card.get_attribute("href")
                    seen_urls.add(url)
                    name = card.find_element(By.XPATH, SELECTORS["card_name"]).text.strip()
                    desig = card.find_element(By.XPATH, SELECTORS["card_desig"]).text.strip()
                    img_src = card.find_element(By.XPATH, SELECTORS["card_img"]).get_attribute("src")
                    
                    page_listings.append({
                        "Name": name,
                        "Designation": desig,
                        "Image_URL": img_src,
                        "Profile_URL": url
                    })
                except Exception:
                    pass

            for person in page_listings:
                time.sleep(random.uniform(1.0, 2.0))
                driver.execute_script(f"window.open('{person['Profile_URL']}', '_blank');")
                driver.switch_to.window(driver.window_handles[1])
                
                try:
                    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    
                    try:
                        email = driver.find_element(By.XPATH, SELECTORS["email_link"]).text.strip()
                    except:
                        email = _get_text_after_label(driver, "Email")
                        
                    spec = _get_text_after_label(driver, SELECTORS["specialisation_label"])
                    address = _get_text_after_label(driver, SELECTORS["address_label"])

                    person["Email"] = email
                    person["Specialisation"] = spec
                    person["Office_Address"] = address
                    
                    all_faculty_data.append(person)
                except Exception as e:
                    logging.error(f"Error scraping {person.get('Name')}: {e}")
                
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

            try:
                next_btn = driver.find_element(By.XPATH, SELECTORS["next_button"])
                time.sleep(random.uniform(2.0, 3.0))
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(3)
                page_count += 1
            except Exception:
                logging.info("Next button issue or end of pagination. Stopping.")
                break

    except Exception as e:
        logging.error(f"Critical Scraper Error: {e}")
    finally:
        driver.quit()
        
    if all_faculty_data:
        df = pd.DataFrame(all_faculty_data)
        cols = ["Name", "Designation", "Specialisation", "Email", "Office_Address", "Image_URL", "Profile_URL"]
        existing_cols = [c for c in cols if c in df.columns]
        df = df[existing_cols]
        df.to_csv(ROOT_DIR / "faculty_data.csv", index=False)
        logging.info(f"Scraper finished. Saved {len(df)} records to faculty_data.csv.")
        return True
    else:
        logging.warning("Scraper finished with no data.")
        return False

async def perform_csv_sync_and_db_update():
    logging.info("Executing Scheduled CSV Sync...")
    
    loop = asyncio.get_event_loop()
    scrape_success = await loop.run_in_executor(None, _run_selenium_scraper_sync)
    
    if not scrape_success:
        logging.warning("Scraping failed. DB update aborted.")
        return {"status": "failed", "message": "Scraping failed"}

    csv_faculty = load_faculty_from_csv()
    if not csv_faculty:
        logging.warning("CSV loaded empty after scrape.")
        return {"status": "failed", "message": "Empty CSV"}

    db_faculty = await db.faculty.find({}, {"faculty_id": 1, "name": 1, "department": 1, "designation": 1, "email": 1, "image_url": 1, "office_address": 1, "research_interests": 1}).to_list(None)
    db_map = {f['name'].lower().strip(): f for f in db_faculty}
    
    csv_map = {f['name'].lower().strip(): f for f in csv_faculty}
    
    new_faculty = []
    missing_faculty = []
    updated_faculty = []

    for name_lower, csv_data in csv_map.items():
        if name_lower not in db_map:
            new_faculty.append(csv_data)
        else:
            db_doc = db_map[name_lower]
            updates = {}
            
            if csv_data.get('designation') and csv_data['designation'] != db_doc.get('designation'):
                updates['designation'] = csv_data['designation']
            if csv_data.get('email') and csv_data['email'] != db_doc.get('email'):
                updates['email'] = csv_data['email']
            if csv_data.get('image_url') and csv_data['image_url'] != db_doc.get('image_url'):
                updates['image_url'] = csv_data['image_url']
            if csv_data.get('office_address') and csv_data['office_address'] != db_doc.get('office_address'):
                updates['office_address'] = csv_data['office_address']
            if csv_data.get('department') and csv_data['department'] != db_doc.get('department'):
                updates['department'] = csv_data['department']
            if csv_data.get('research_interests') and csv_data['research_interests'] != db_doc.get('research_interests'):
                updates['research_interests'] = csv_data['research_interests']

            if updates:
                updated_faculty.append({"id": db_doc["faculty_id"], "name": db_doc["name"], "updates": updates})

    for name_lower, db_doc in db_map.items():
        if name_lower not in csv_map and not db_doc['faculty_id'].startswith("demo_"):
            missing_faculty.append(db_doc)

    if new_faculty:
        logging.info(f"Found {len(new_faculty)} new faculty. Inserting...")
        await db.faculty.insert_many(new_faculty)
        if ADMIN_ENV_EMAIL:
            names_list = "<br>".join([f"- {f['name']} ({f['department']})" for f in new_faculty])
            body = f"<h3>New Faculty Detected:</h3><p>{names_list}</p>"
            await send_email_async(ADMIN_ENV_EMAIL, "New Faculty Added - VIT-AP Faculty Hub", body)
            
    if updated_faculty:
        logging.info(f"Found {len(updated_faculty)} faculty updates.")
        for u in updated_faculty:
            await db.faculty.update_one({"faculty_id": u["id"]}, {"$set": u["updates"]})

    if missing_faculty:
        logging.info(f"Found {len(missing_faculty)} faculty missing in CSV.")
        if ADMIN_ENV_EMAIL:
            names_list = "<br>".join([f"- {f['name']} ({f['department']})" for f in missing_faculty])
            body = f"<h3>Missing Faculty Alert:</h3><p>The following are in DB but missing in CSV:</p><p>{names_list}</p>"
            await send_email_async(ADMIN_ENV_EMAIL, "Missing Faculty Alert - VIT-AP Faculty Hub", body)
            
    try:
        recommender = FacultyRecommender.get_instance()
        fresh_faculty = await db.faculty.find({}, {"_id": 0}).to_list(None)
        await loop.run_in_executor(None, recommender.sync_all_faculty, fresh_faculty)
    except Exception as e:
        logging.error(f"Vector sync failed: {e}")

    return {
        "status": "success", 
        "new_count": len(new_faculty), 
        "missing_count": len(missing_faculty), 
        "updated_count": len(updated_faculty)
    }

async def perform_sync_openalex():
    logging.info("Executing Scheduled OpenAlex Sync...")
    local_api_key = os.environ.get('OPENALEX_API_KEY')
    if not local_api_key:
        logging.warning("OpenAlex API key missing for scheduled job.")
        return

    all_faculty_data = await db.faculty.find({}, {"_id": 0}).to_list(1000)
    
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    processed_names = []

    def clean_name_string(name_str):
        return name_str.lower().replace(",", "").replace(".", "").strip()

    for faculty in all_faculty_data:
        raw_name = faculty["name"]
        prefixes = ["dr.", "mr.", "ms.", "mrs.", "prof.", "dr", "prof", "assistant professor", "associate professor", "dean", "hod"]
        clean_faculty_name = raw_name
        for prefix in prefixes:
            if clean_faculty_name.lower().startswith(prefix):
                clean_faculty_name = clean_faculty_name[len(prefix):].strip()
        
        if not clean_faculty_name:
            logging.error(f"Skipping faculty {raw_name}: Name became empty")
            skipped_count += 1
            continue
            
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
            url_author_search = "https://api.openalex.org/authors"
            params_author = {
                "filter": f"last_known_institutions.lineage:{VIT_INSTITUTION_LINEAGE}",
                "search": clean_faculty_name,
                "per_page": 10,
                "mailto": "admin@vitapstudent.ac.in"
            }
            headers = {"x-api-key": local_api_key}

            logging.info(f"Searching for '{clean_faculty_name}' in VIT-AP authors...")
            
            response_author = requests.get(url_author_search, params=params_author, headers=headers)
            
            if response_author.status_code == 200 and response_author.json().get("results"):
                data_author = response_author.json()
                vit_authors = data_author["results"]
                
                found_match = False
                for author in vit_authors:
                    author_display = author.get("display_name", "")
                    author_id = author.get("id", "")
                    author_tokens = set(clean_name_string(author_display).split())

                    if faculty_tokens == author_tokens:
                        target_author_id = author_id
                        logging.info(f"Exact Match Found: '{raw_name}' <-> '{author_display}'")
                        found_match = True
                        break
                    
                    if faculty_tokens.issubset(author_tokens) or author_tokens.issubset(faculty_tokens):
                        overlap = len(faculty_tokens & author_tokens)
                        if overlap >= min(len(faculty_tokens), len(author_tokens)):
                            target_author_id = author_id
                            logging.info(f"Subset Match Found: '{raw_name}' <-> '{author_display}'")
                            found_match = True
                            break

                    full_author_tokens = [t for t in author_tokens if len(t) > 1]
                    if any(t not in faculty_tokens for t in full_author_tokens):
                        continue
                    
                    initial_author_tokens = [t for t in author_tokens if len(t) == 1]
                    match_possible = True
                    for initial in initial_author_tokens:
                        if not any(f_token.startswith(initial) for f_token in faculty_tokens):
                            match_possible = False
                            break
                    
                    if match_possible:
                        longest_author = max(author_tokens, key=len)
                        if longest_author in faculty_tokens:
                            target_author_id = author_id
                            logging.info(f"Initial Match Found: '{raw_name}' <-> '{author_display}'")
                            found_match = True
                            break
                
                if not found_match:
                    logging.info(f"Faculty '{raw_name}' NOT found in VIT-AP authors list.")
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
                logging.info(f"No author ID found for '{raw_name}' at VIT-AP. Skipping.")
                skipped_count += 1
                continue

            url_works_final = "https://api.openalex.org/works"
            params_final = {
                "filter": f"authorships.author.id:{target_author_id}", 
                "per_page": 200,
                "sort": "publication_year:desc",
                "mailto": "admin@vitapstudent.ac.in"
            }

            response_works = requests.get(url_works_final, params=params_final, headers=headers)

            if response_works.status_code != 200:
                logging.error(f"Error fetching works for {target_author_id}: {response_works.text[:100]}")
                failed_count += 1
                continue

            data_works = response_works.json()
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
                        citation_count = int(res.get("cited_by_count", 0))
                        
                        is_vitap_work = False 
                        authorships = res.get("authorships", [])
                        for authorship in authorships:
                            if authorship.get("author", {}).get("id", "") == target_author_id:
                                institutions = authorship.get("institutions", [])
                                for inst in institutions:
                                    lineages = inst.get("lineage", [])
                                    for lineage_item in lineages:
                                        if VIT_INSTITUTION_LINEAGE in str(lineage_item):
                                            is_vitap_work = True
                                            break
                                if is_vitap_work:
                                    break

                        clean_projects.append({
                            "openalex_id": openalex_id,
                            "title": title,
                            "publication_year": pub_year,
                            "type": pub_type,
                            "is_vitap": is_vitap_work,
                            "cited_by_count": citation_count
                        })
            
            if clean_projects:
                await db.faculty.update_one(
                    {"faculty_id": faculty["faculty_id"]},
                    {"$set": {"openalex_projects": clean_projects}}
                )
                updated_count += 1
                logging.info(f"Updated {raw_name} with {len(clean_projects)} publications.")
            else:
                logging.info(f"No VIT-AP publications found for {raw_name}")
                skipped_count += 1

        except Exception as e:
            logging.error(f"Error processing faculty {faculty.get('name')}: {e}")
            failed_count += 1

    logging.info(f"OpenAlex Sync completed. Updated: {updated_count}, Skipped: {skipped_count}, Failed: {failed_count}")
    
    try:
        recommender = FacultyRecommender.get_instance()
        if updated_count > 0:
           fresh_faculty = await db.faculty.find({}, {"_id": 0}).to_list(None)
           loop = asyncio.get_event_loop()
           await loop.run_in_executor(None, recommender.sync_all_faculty, fresh_faculty)
    except Exception as e:
        logging.error(f"Vector sync after OpenAlex failed: {e}")

@app.on_event("startup")
async def startup_event():
    logging.info("Checking database for faculty data...")
    
    # Explicitly load profanity word list
    profanity.load_censor_words()
    logging.info("Profanity filter initialized.")

    count = await db.faculty.count_documents({})
    
    if count == 0:
        logging.info("Database is empty. Checking for CSV data...")
        csv_data = load_faculty_from_csv()
        if csv_data:
            logging.info(f"Found {len(csv_data)} records in CSV. Importing...")
            await db.faculty.insert_many(csv_data)
        else:
            logging.info("No CSV found. Falling back to Demo Data.")
            demo_data = get_demo_faculty()
            await db.faculty.insert_many(demo_data)
    else:
        logging.info(f"Database already contains {count} faculty records.")

    logging.info("Initializing Vector Store...")
    try:
        loop = asyncio.get_event_loop()
        def init_recommender_sync():
            return FacultyRecommender.get_instance()
        recommender = await loop.run_in_executor(None, init_recommender_sync)
        all_faculty = await db.faculty.find({}, {"_id": 0}).to_list(None)
        logging.info("Syncing faculty to vector store...")
        await loop.run_in_executor(None, recommender.sync_all_faculty, all_faculty)
        logging.info("Vector Store sync finished.")
    except Exception as e:
        logging.error(f"Failed to initialize Vector Store: {e}")

    logging.info("Initializing Schedulers...")
    scheduler.add_job(perform_csv_sync_and_db_update, 'interval', hours=3, id='csv_sync')
    scheduler.add_job(perform_sync_openalex, 'interval', hours=2, id='openalex_sync')
    scheduler.start()

    logging.info("Checking for seeded users...")
    users_cursor = db.users.find({})
    async for user_doc in users_cursor:
        update_data = {}
        if not user_doc.get('anonymous_id'):
            new_id = str(random.randint(1000, 9999))
            update_data['anonymous_id'] = new_id
            update_data['anonymous_chat_id'] = new_id
            update_data['anonymous_comment_id'] = new_id
        elif user_doc.get('anonymous_chat_id') != user_doc.get('anonymous_id'):
             update_data['anonymous_chat_id'] = user_doc.get('anonymous_id')
        elif user_doc.get('anonymous_comment_id') != user_doc.get('anonymous_id'):
             update_data['anonymous_comment_id'] = user_doc.get('anonymous_id')
        if 'blocked' not in user_doc: update_data['blocked'] = False
        if 'theme_preference' not in user_doc: update_data['theme_preference'] = 'light'
        if update_data: await db.users.update_one({'_id': user_doc['_id']}, {'$set': update_data})

    admin_exists = await db.users.find_one({"is_admin": True})
    if not admin_exists:
        if ADMIN_ENV_EMAIL and ADMIN_ENV_PASSWORD:
            logging.info(f"Creating Admin user from .env: {ADMIN_ENV_EMAIL}")
            unified_id = str(random.randint(1000, 9999))
            await db.users.insert_one({
                "user_id": f"user_admin_{uuid.uuid4().hex[:12]}",
                "email": ADMIN_ENV_EMAIL,
                "name": "System Administrator",
                "password_hash": get_password_hash(ADMIN_ENV_PASSWORD),
                "is_admin": True, "blocked": False, "preferences": [], "ai_interests": [],
                "created_at": datetime.now(timezone.utc),
                "anonymous_id": unified_id, "anonymous_chat_id": unified_id, "anonymous_comment_id": unified_id,
                "theme_preference": "light"
            })
        else:
            logging.warning("ADMIN_EMAIL and ADMIN_PASSWORD not found in .env. No admin created.")
    



async def get_current_user(request: Request, session_token: Optional[str] = Cookie(None)) -> User:
    token = session_token or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token: raise HTTPException(status_code=401, detail="Not authenticated")
    session_doc = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session_doc: raise HTTPException(status_code=401, detail="Invalid session")
    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str): expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None: expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc): raise HTTPException(status_code=401, detail="Session expired")
    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc: raise HTTPException(status_code=404, detail="User not found")
    if user_doc.get("blocked", False): raise HTTPException(status_code=403, detail="Your account has been blocked by administrator.")
    if isinstance(user_doc["created_at"], str): user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    return User(**user_doc)

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
        "blocked": False, 
        "preferences": [],
        "ai_interests": [],
        "created_at": datetime.now(timezone.utc),
        "anonymous_id": unified_id,
        "anonymous_chat_id": unified_id,
        "anonymous_comment_id": unified_id,
        "theme_preference": "light"
    }
    
    await db.users.insert_one(new_user)
    return {"message": "User registered successfully", "user_id": user_id}

@api_router.post("/auth/login")
async def login_user(response: Response, login_data: UserLogin):
    user_doc = await db.users.find_one({"email": login_data.email}, {"_id": 0})
    
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user_doc.get("blocked", False):
         raise HTTPException(status_code=403, detail="Account blocked")

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

@api_router.get("/admin/users")
async def get_all_users(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    cursor = db.users.find({}, {"password_hash": 0, "_id": 0})
    users = await cursor.to_list(1000)
    
    for u in users:
        if isinstance(u.get("created_at"), str):
            u["created_at"] = datetime.fromisoformat(u["created_at"])
            
    return users

@api_router.patch("/admin/users/{target_user_id}")
async def admin_update_user(target_user_id: str, update: UserAdminUpdate, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if current_user.user_id == target_user_id:
        raise HTTPException(status_code=400, detail="You cannot modify your own account.")
        
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    if "is_admin" in update_data and update_data["is_admin"] is False:
        raise HTTPException(status_code=400, detail="Revoking admin rights is not allowed.")

    if "blocked" in update_data and update_data["blocked"] is True:
        target_user = await db.users.find_one({"user_id": target_user_id})
        if target_user:
            subject = "Account Blocked - Faculty Hub"
            body = f"""
            <html>
              <body>
                <h2>Your account has been blocked.</h2>
                <p>Dear {target_user.get('name', 'User')},</p>
                <p>This is to inform you that your account on the Faculty Hub platform has been blocked by the administrator.</p>
                <p><b>Reason:</b> Violation of community guidelines (inappropriate language/content).</p>
                <p>If you believe this is a mistake, or if you wish to appeal this decision, please reply to this email explaining your situation.</p>
                <p>Please ensure you do not use inappropriate language in the future.</p>
                <br>
                <p>Regards,<br>Faculty Hub Admin</p>
              </body>
            </html>
            """
            background_tasks.add_task(send_email_async, target_user['email'], subject, body)
        
    result = await db.users.update_one(
        {"user_id": target_user_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {"message": "User updated successfully"}

@api_router.get("/users/{target_user_id}", response_model=User)
async def get_user_profile(target_user_id: str, current_user: User = Depends(get_current_user)):
    if current_user.user_id != target_user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="You can only view your own profile")
    
    user_doc = await db.users.find_one({"user_id": target_user_id}, {"password_hash": 0, "_id": 0})
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
        
    if isinstance(user_doc["created_at"], str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
        
    return User(**user_doc)

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
    research_list = []
    if faculty.research_interests:
        if isinstance(faculty.research_interests, str):
            research_list = [s.strip() for s in faculty.research_interests.split(',') if s.strip()]
        elif isinstance(faculty.research_interests, list):
            research_list = faculty.research_interests

    faculty_doc = {
        "faculty_id": faculty_id,
        **faculty.model_dump(exclude_unset=True),
        "research_interests": research_list,
        "avg_ratings": {"teaching": 0, "attendance": 0, "doubt_clarification": 0, "overall": 0},
        "rating_counts": {"teaching": 0, "attendance": 0, "doubt_clarification": 0, "overall": 0},
        "openalex_projects": [],
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.faculty.insert_one(faculty_doc)
    created_doc = await db.faculty.find_one({"faculty_id": faculty_id}, {"_id": 0})
    
    if not created_doc:
        raise HTTPException(status_code=500, detail="Failed to retrieve created faculty")
    
    try:
        recommender = FacultyRecommender.get_instance()
        recommender.upsert_faculty(created_doc)
    except Exception as e:
        logging.error(f"Vector upsert failed: {e}")

    return Faculty(**created_doc)

@api_router.patch("/faculty/{faculty_id}", response_model=Faculty)
async def update_faculty(faculty_id: str, update: FacultyUpdate, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_data = {k: v for k, v in update.model_dump(exclude_unset=True).items() if v is not None}
    
    if "research_interests" in update_data:
        raw_interests = update_data["research_interests"]
        if isinstance(raw_interests, str):
            update_data["research_interests"] = [s.strip() for s in raw_interests.split(',') if s.strip()]
    
    if update_data:
        result = await db.faculty.update_one(
            {"faculty_id": faculty_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Faculty not found")

    faculty_doc = await db.faculty.find_one({"faculty_id": faculty_id}, {"_id": 0})
    
    if not faculty_doc:
         raise HTTPException(status_code=404, detail="Faculty not found")
         
    if isinstance(faculty_doc["created_at"], str):
        faculty_doc["created_at"] = datetime.fromisoformat(faculty_doc["created_at"])
    
    try:
        recommender = FacultyRecommender.get_instance()
        recommender.upsert_faculty(faculty_doc)
    except Exception as e:
        logging.error(f"Vector upsert failed: {e}")

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
                    current_count +=1
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
                current_count +=1
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
async def get_comments(faculty_id: str, current_user: User = Depends(get_current_user)):
    comments = await db.comments.find({"faculty_id": faculty_id}, {"_id": 0}).to_list(1000)
    
    for comment in comments:
        if isinstance(comment["created_at"], str):
            comment["created_at"] = datetime.fromisoformat(comment["created_at"])
        
        commenter_id = comment.get("user_id")
        commenter_name = comment.get("user_name", "Unknown")
        is_commenter_admin = False

        if commenter_id == current_user.user_id:
            if current_user.is_admin:
                is_commenter_admin = True
        else:
            commenter = await db.users.find_one({"user_id": commenter_id}, {"_id": 0, "is_admin": 1})
            if commenter and commenter.get("is_admin"):
                is_commenter_admin = True

        if is_commenter_admin:
            comment["anonymous_handle"] = commenter_name
            comment["is_admin_commenter"] = True
        elif current_user.is_admin:
            comment["anonymous_handle"] = commenter_name
    
    return comments

@api_router.post("/faculty/{faculty_id}/comments")
async def create_comment(faculty_id: str, comment: CommentCreate, current_user: User = Depends(get_current_user)):
    rating_doc = await db.ratings.find_one({"faculty_id": faculty_id, "user_id": current_user.user_id})
    if not rating_doc:
        raise HTTPException(status_code=403, detail="You must rate this faculty before commenting.")

    faculty_doc = await db.faculty.find_one({"faculty_id": faculty_id})
    detected_profanity = False
    
    # Strip HTML tags and check profanity
    clean_content = re.sub(r'<[^>]+>', '', comment.content)
    
    if profanity.contains_profanity(clean_content):
        detected_profanity = True
        logging.warning(f"Profanity detected from user {current_user.email} on faculty {faculty_id}")
        
        admin_email = ADMIN_ENV_EMAIL if ADMIN_ENV_EMAIL else "admin@vitapstudent.ac.in"        
        admin_link = f"{FRONTEND_URL}/admin/users" 
        subject = f"Profanity Alert: User {current_user.name}"
        body = f"""
        <html>
          <body>
            <h3>Profanity Detected in Comment</h3>
            <p><b>Faculty:</b> {faculty_doc['name'] if faculty_doc else 'Unknown'}</p>
            <p><b>User:</b> {current_user.name} ({current_user.email})</p>
            <p><b>Offending Comment:</b> "{comment.content}"</p>
            <hr>
            <p>Please review this user. You can block them directly from the dashboard:</p>
            <a href="{admin_link}" style="padding: 10px; background-color: #d9534f; color: white; text-decoration: none; border-radius: 5px;">View User & Block</a>
          </body>
        </html>
        """
        asyncio.create_task(send_email_async(admin_email, subject, body))

    comment_id = f"comment_{uuid.uuid4().hex[:12]}"    
    is_commenter_admin = current_user.is_admin
    anonymous_handle = current_user.name if is_commenter_admin else f"Anonymous@{current_user.anonymous_id}"
    
    comment_doc = {
        "comment_id": comment_id,
        "faculty_id": faculty_id,
        "user_id": current_user.user_id,
        "user_name": current_user.name, 
        "anonymous_handle": anonymous_handle,
        "is_admin_commenter": is_commenter_admin,
        "user_picture": current_user.picture,
        "content": comment.content,
        "parent_comment_id": comment.parent_comment_id,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.comments.insert_one(comment_doc)
    
    return {"message": "Comment created successfully", "comment_id": comment_id, "profanity_detected": detected_profanity}

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
        
        unread_counts = chat.get("unread_counts", {})
        my_unread_count = unread_counts.get(current_user.user_id, 0)
        chat["unread_count"] = my_unread_count
        
        for pid in participant_ids:
            if pid == current_user.user_id:
                resolved_participants.append(
                    ChatParticipant(user_id=pid, anonymous_chat_id="You", is_admin=False)
                )
            else:
                other_user = await db.users.find_one({"user_id": pid}, {"_id": 0, "name": 1, "is_admin": 1, "anonymous_chat_id": 1})
                if other_user:
                    if current_user.is_admin:
                        handle = other_user.get("name", "Unknown")
                    else:
                        if other_user.get("is_admin"):
                            handle = other_user.get("name")
                        else:
                            handle = other_user.get("anonymous_chat_id", "Unknown")
                            handle = f"Anonymous@{handle}" if handle != "Admin" else "Admin"
                    
                    resolved_participants.append(
                        ChatParticipant(user_id=pid, anonymous_chat_id=handle, is_admin=other_user.get("is_admin", False))
                    )
                else:
                    resolved_participants.append(
                        ChatParticipant(user_id=pid, anonymous_chat_id="Unknown", is_admin=False)
                    )
        
        chat["participants"] = resolved_participants

        if isinstance(chat["created_at"], str):
            chat["created_at"] = datetime.fromisoformat(chat["created_at"])
        if isinstance(chat["updated_at"], str):
            chat["updated_at"] = datetime.fromisoformat(chat["updated_at"])
        
        for msg in chat.get("messages", []):
            if isinstance(msg["created_at"], str):
                msg["created_at"] = datetime.fromisoformat(msg["created_at"])
            
            if msg["sender_id"] == current_user.user_id:
                if not msg.get("is_admin_sender"):
                    msg["is_admin_sender"] = current_user.is_admin
                continue

            sender = await db.users.find_one({"user_id": msg["sender_id"]}, {"_id": 0, "name": 1, "is_admin": 1})
            if sender:
                if sender.get("is_admin"):
                    msg["sender_anonymous_id"] = sender.get("name")
                    msg["is_admin_sender"] = True
                elif not msg.get("is_admin_sender"):
                    msg["is_admin_sender"] = False
    
    return chats_list

@api_router.post("/chats/messages")
async def send_message(message: ChatMessageCreate, current_user: User = Depends(get_current_user)):
    participants = sorted([current_user.user_id, message.recipient_id])
    
    chat_doc = await db.chats.find_one(
        {"participants": participants},
        {"_id": 0}
    )
    
    is_admin_sender = current_user.is_admin
    display_name = current_user.name if is_admin_sender else f"Anonymous@{current_user.anonymous_id}"
    
    new_message = {
        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "sender_id": current_user.user_id,
        "sender_anonymous_id": display_name,
        "is_admin_sender": is_admin_sender,
        "content": message.content,
        "created_at": datetime.now(timezone.utc)
    }
    
    if chat_doc:
        recipient_id = message.recipient_id
        
        await db.chats.update_one(
            {"chat_id": chat_doc["chat_id"]},
            {
                "$push": {"messages": new_message},
                "$set": {"updated_at": datetime.now(timezone.utc)},
                "$inc": {f"unread_counts.{recipient_id}": 1}
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
            "updated_at": datetime.now(timezone.utc),
            "unread_counts": {message.recipient_id: 1}
        })
    
    room = f"chat_{chat_id}"
    
    try:
        await sio.emit("message", new_message, room=room)
    except Exception as e:
        logging.error(f"Socket emit failed for room {room}: {e}")
    
    return {"chat_id": chat_id, "message": new_message}

@api_router.get("/chats/unread-count")
async def get_unread_count(current_user: User = Depends(get_current_user)):
    chats_cursor = db.chats.find({"participants": current_user.user_id}, {"_id": 0, "unread_counts": 1})
    chats_list = await chats_cursor.to_list(100)
    
    total_unread = 0
    for chat in chats_list:
        unread_counts = chat.get("unread_counts", {})
        total_unread += unread_counts.get(current_user.user_id, 0)
        
    return {"total_unread": total_unread}

@api_router.post("/chats/{chat_id}/read")
async def mark_chat_read(chat_id: str, current_user: User = Depends(get_current_user)):
    chat_doc = await db.chats.find_one({"chat_id": chat_id}, {"_id": 0})
    if not chat_doc:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if current_user.user_id not in chat_doc.get("participants", []):
        raise HTTPException(status_code=403, detail="You are not a participant in this chat")
        
    await db.chats.update_one(
        {"chat_id": chat_id},
        {"$set": {f"unread_counts.{current_user.user_id}": 0}}
    )
    return {"message": "Marked as read"}

@api_router.get("/recommendations")
async def get_recommendations(
    interests: str = Query(None),
    preferences: str = Query(None),
    current_user: User = Depends(get_current_user)
):
    if current_user.is_admin:
        return []

    target_interests = []
    if interests:
        target_interests = [i.strip().lower() for i in interests.split(",") if i.strip()]

    user_rating_prefs = []
    if preferences:
        user_rating_prefs = [p.strip().lower() for p in preferences.split(",") if p.strip()]
    
    if not user_rating_prefs and not target_interests:
        return []

    try:
        recommender = FacultyRecommender.get_instance()
    except Exception as e:
        logging.error(f"Recommender not initialized: {e}")
        return []

    faculty_list = await db.faculty.find({}, {"_id": 0}).to_list(1000)
    
    recommendations = []

    if target_interests:
        query_text = ", ".join(target_interests)
        vector_matches = recommender.search_faculty(query_text, top_k=len(faculty_list))
        match_map = {m["faculty_id"]: m for m in vector_matches}

        for fac in faculty_list:
            fid = fac["faculty_id"]
            vector_data = match_map.get(fid)
            
            if not vector_data:
                continue

            base_score = vector_data["similarity_pct"]
            
            found_in_interests = []
            found_in_projects = []
            
            faculty_interests_raw = fac.get("research_interests", [])
            if isinstance(faculty_interests_raw, str):
                faculty_interests_list = [faculty_interests_raw]
            else:
                faculty_interests_list = faculty_interests_raw
            
            for interest in target_interests:
                if any(interest in fi.lower() for fi in faculty_interests_list):
                    found_in_interests.append(interest.title())
            
            projects = fac.get("openalex_projects", [])
            for interest in target_interests:
                for p in projects:
                    title = p.get("title", "").lower()
                    if interest in title:
                        if interest.title() not in found_in_interests and interest.title() not in found_in_projects:
                            found_in_projects.append(interest.title())
                        break
            
            keyword_boost = 0.0
            matched_keywords = len(found_in_interests) + len(found_in_projects)
            total_keywords = len(target_interests)
            
            if total_keywords > 0:
                keyword_boost = (matched_keywords / total_keywords) * 15.0
            
            final_score = base_score + keyword_boost
            
            rating_boost = 0.0
            if user_rating_prefs:
                rating_score = 0.0
                count = 0
                for pref in user_rating_prefs:
                    val = fac['avg_ratings'].get(pref, 0)
                    if val > 0:
                        rating_score += val
                        count += 1
                if count > 0:
                    avg_rating = rating_score / count
                    rating_boost = (avg_rating / 5.0) * 10.0
            
            final_score = min(100, final_score + rating_boost)
            
            if final_score <= 0:
                continue

            reason_parts = []
            if found_in_interests:
                reason_parts.append(f"Matches '{', '.join(found_in_interests)}' in Research Interests")
            if found_in_projects:
                reason_parts.append(f"Matches '{', '.join(found_in_projects)}' in Projects/Publications")
            
            final_reason = ". ".join(reason_parts)
            
            if not final_reason:
                if faculty_interests_list:
                    best_fac_term = faculty_interests_list[0]
                    best_user_term = target_interests[0].title()
                    final_reason = f"Uses related terminology: '{best_fac_term}' instead of '{best_user_term}'."
                elif fac.get("department") and any(i in fac["department"].lower() for i in target_interests):
                    final_reason = f"Belongs to the {fac.get('department')} department."
                else:
                    if final_score > 60:
                        final_reason = "Strong semantic match with your interests."
                    else:
                        final_reason = "Relevant based on overall profile similarity."

            recommendations.append({
                **fac,
                "compatibility_percentage": round(final_score, 1),
                "recommendation_reason": final_reason
            })
    
    elif user_rating_prefs:
        for fac in faculty_list:
            rating_score = 0.0
            count = 0
            for pref in user_rating_prefs:
                val = fac['avg_ratings'].get(pref, 0)
                if val > 0:
                    rating_score += val
                    count += 1
            
            final_score = 0
            if count > 0:
                avg_rating = rating_score / count
                final_score = (avg_rating / 5.0) * 100
            
            if final_score <= 0:
                continue

            recommendations.append({
                **fac,
                "compatibility_percentage": round(final_score, 1),
                "recommendation_reason": None
            })
    
    recommendations.sort(key=lambda x: x.get("compatibility_percentage", 0), reverse=True)
    return recommendations

@api_router.post("/admin/sync-openalex")
async def sync_openalex_data(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    api_key = os.environ.get('OPENALEX_API_KEY')
    if not api_key:
        logging.error("DEBUG: OPENALEX_API_KEY is MISSING in .env file!")
        raise HTTPException(status_code=400, detail="OPENALEX_API_KEY not found in environment variables.")
    
    asyncio.create_task(perform_sync_openalex())
    return {"message": "OpenAlex Sync started in background"}

@api_router.post("/admin/sync-website")
async def sync_website_data(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin: raise HTTPException(status_code=403, detail="Admin access required")
    result = await perform_csv_sync_and_db_update()
    if result.get("status") == "failed": raise HTTPException(status_code=500, detail="Sync failed")
    return {
        "message": "Sync Completed", 
        "new_count": result.get("new_count"), 
        "missing_count": result.get("missing_count"),
        "updated_count": result.get("updated_count")
    }

@api_router.get("/rankings")
async def get_rankings(department: Optional[str] = None, category: str = "overall", method: str = "weighted", current_user: User = Depends(get_current_user)):
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
    scheduler.shutdown()
    client.close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Serve socket_app (ASGI) which includes both FastAPI and Socket.IO
    uvicorn.run("server:socket_app", host="0.0.0.0", port=port, log_level="info")