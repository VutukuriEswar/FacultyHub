import sys
import asyncio
import os
import logging
import random
import time
import re
import json
import requests
import httpx
import smtplib
import bcrypt
import socketio
from jose import jwt as jose_jwt, JWTError
import firebase_admin
from firebase_admin import credentials, auth as fb_auth
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

_FIREBASE_PROJECT_ID = "facultyhub-10942"

_firebase_initialized = False
def _ensure_firebase():
    global _firebase_initialized
    if not _firebase_initialized:
        try:
            firebase_admin.get_app()
        except ValueError:
            project_id = os.environ.get("FIREBASE_PROJECT_ID", _FIREBASE_PROJECT_ID)
            firebase_admin.initialize_app(options={"projectId": project_id})
        _firebase_initialized = True

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
_startup_complete = False

_openalex_sync_running = False
_csv_sync_running = False

OPENALEX_CHECKPOINT_FILE = ROOT_DIR / "openalex_checkpoint.json"
CSV_STAGING_FILE = ROOT_DIR / "faculty_data_staging.csv"

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
    google_linked: bool = False

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    otp: str

class SendOTPRequest(BaseModel):
    email: EmailStr

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    picture: Optional[str] = None
    preferences: Optional[List[str]] = None
    ai_interests: Optional[List[str]] = None
    theme_preference: Optional[str] = None

class GoogleAuthRequest(BaseModel):
    id_token: str

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
    scholar_url: Optional[str] = None
    linkedin_url: Optional[str] = None
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
    scholar_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    publications: List[str] = Field(default_factory=list)
    research_interests: Optional[Union[str, List[str]]] = None 
    openalex_projects: List[Dict[str, Any]] = Field(default_factory=list)

class FacultyUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    image_url: Optional[str] = None
    scholar_url: Optional[str] = None
    linkedin_url: Optional[str] = None
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
    participants: List[Union[ChatParticipant, str]]
    messages: List[ChatMessage]
    unread_counts: Dict[str, int] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

class ChatMessageCreate(BaseModel):
    recipient_id: str
    content: str

def load_faculty_from_csv(file_path=None):
    if file_path is None:
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
            
            linkedin_val = None
            if 'LinkedIn_URL' in df.columns and not pd.isna(row.get('LinkedIn_URL')):
                linkedin_val = str(row['LinkedIn_URL'])
                
            scholar_val = None
            if 'Scholar_URL' in df.columns and not pd.isna(row.get('Scholar_URL')):
                scholar_val = str(row['Scholar_URL'])

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
                "linkedin_url": linkedin_val,
                "scholar_url": scholar_val,
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

    seen_urls = set()
    page_count = 1
    total_saved = 0

    cols = ["Name", "Designation", "Specialisation", "Email", "Office_Address",
            "Image_URL", "Profile_URL", "LinkedIn_URL", "Scholar_URL"]
    pd.DataFrame(columns=cols).to_csv(CSV_STAGING_FILE, index=False)

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

            page_faculty_data = []
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

                    linkedin_url = ""
                    scholar_url = ""
                    for link in driver.find_elements(By.TAG_NAME, "a"):
                        try:
                            href = link.get_attribute("href")
                            if not href:
                                continue
                            if "linkedin.com/in/" in href:
                                linkedin_url = href
                            elif "scholar.google" in href and "user=" in href:
                                scholar_url = href
                        except Exception:
                            continue

                    person["Email"] = email
                    person["Specialisation"] = spec
                    person["Office_Address"] = address
                    person["LinkedIn_URL"] = linkedin_url
                    person["Scholar_URL"] = scholar_url
                    page_faculty_data.append(person)
                except Exception as e:
                    logging.error(f"Error scraping {person.get('Name')}: {e}")

                driver.close()
                driver.switch_to.window(driver.window_handles[0])

            if page_faculty_data:
                df_page = pd.DataFrame(page_faculty_data)
                existing_cols = [c for c in cols if c in df_page.columns]
                df_page = df_page[existing_cols]
                df_page.to_csv(CSV_STAGING_FILE, mode='a', header=False, index=False)
                total_saved += len(df_page)
                logging.info(f"Page {page_count}: saved {len(df_page)} records to staging (total so far: {total_saved}).")

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

    if total_saved > 0:
        import shutil
        shutil.move(str(CSV_STAGING_FILE), str(ROOT_DIR / "faculty_data.csv"))
        logging.info(f"Scraper finished. Saved {total_saved} records to faculty_data.csv.")
        return True
    else:
        logging.warning("Scraper finished with no data. Staging file kept for inspection.")
        return False



async def perform_csv_sync_and_db_update():
    global _csv_sync_running
    if _csv_sync_running:
        logging.info("CSV sync already running. Skipping this trigger.")
        return {"status": "skipped", "message": "Sync already in progress"}
    _csv_sync_running = True
    logging.info("Executing Scheduled CSV Sync...")

    try:
        loop = asyncio.get_event_loop()
        scrape_success = await loop.run_in_executor(None, _run_selenium_scraper_sync)

        if not scrape_success:
            if CSV_STAGING_FILE.exists():
                logging.warning("Scraping failed but staging CSV found. Applying partial data from previous partial scrape.")
                csv_source = CSV_STAGING_FILE
            else:
                logging.warning("Scraping failed and no staging data available. DB update aborted.")
                return {"status": "failed", "message": "Scraping failed"}
        else:
            csv_source = ROOT_DIR / "faculty_data.csv"

        csv_faculty = load_faculty_from_csv(csv_source)
        if not csv_faculty:
            logging.warning("CSV loaded empty after scrape.")
            return {"status": "failed", "message": "Empty CSV"}


        db_faculty = await db.faculty.find({}, {"faculty_id": 1, "name": 1, "department": 1, "designation": 1, "email": 1, "image_url": 1, "office_address": 1, "research_interests": 1, "linkedin_url": 1, "scholar_url": 1}).to_list(None)
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
                if csv_data.get('linkedin_url') and csv_data['linkedin_url'] != db_doc.get('linkedin_url'):
                    updates['linkedin_url'] = csv_data['linkedin_url']
                if csv_data.get('scholar_url') and csv_data['scholar_url'] != db_doc.get('scholar_url'):
                    updates['scholar_url'] = csv_data['scholar_url']

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

        if CSV_STAGING_FILE.exists():
            CSV_STAGING_FILE.unlink()

        return {
            "status": "success", 
            "new_count": len(new_faculty), 
            "missing_count": len(missing_faculty), 
            "updated_count": len(updated_faculty)
        }

    except Exception as e:
        logging.error(f"CSV sync error: {e}", exc_info=True)
        return {"status": "failed", "message": str(e)}
    finally:
        _csv_sync_running = False

async def _openalex_get(client: httpx.AsyncClient, url: str, params: dict, headers: dict, max_retries: int = 4) -> httpx.Response:
    last_response = None
    for attempt in range(max_retries):
        try:
            response = await client.get(url, params=params, headers=headers, timeout=30.0)
            last_response = response

            remaining = response.headers.get("X-RateLimit-Remaining", "")


            if response.status_code != 429:
                if remaining.isdigit() and int(remaining) < 50:
                    logging.warning(f"X-RateLimit-Remaining is low ({remaining}). Pausing 10s.")
                    await asyncio.sleep(10)
                return response

            backoff = min(2 ** (attempt + 1), 60)
            logging.warning(
                f"429 Too Many Requests (per-second limit) at attempt {attempt + 1}/{max_retries}. "
                f"Sleeping {backoff}s. (Remaining daily budget: {remaining})"
            )
            await asyncio.sleep(backoff)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            wait = min(2 ** attempt, 30)
            logging.warning(f"Network error on attempt {attempt + 1}/{max_retries}: {e}. Retrying in {wait}s.")
            await asyncio.sleep(wait)
    return last_response

async def _process_one_faculty(client: httpx.AsyncClient, faculty: dict, local_api_key: str, processed_names: list) -> str:
    raw_name = faculty["name"]
    prefixes = ["dr.", "mr.", "ms.", "mrs.", "prof.", "dr", "prof",
                "assistant professor", "associate professor", "dean", "hod"]
    clean_faculty_name = raw_name
    for prefix in prefixes:
        if clean_faculty_name.lower().startswith(prefix):
            clean_faculty_name = clean_faculty_name[len(prefix):].strip()

    if not clean_faculty_name:
        logging.error(f"Skipping faculty {raw_name}: Name became empty")
        return 'skipped'

    def clean_name_string(name_str):
        return name_str.lower().replace(",", "").replace(".", "").strip()

    faculty_tokens = set(clean_name_string(clean_faculty_name).split())
    if not faculty_tokens:
        return 'skipped'

    if clean_faculty_name in processed_names:
        logging.info(f"Skipping duplicate query for: {clean_faculty_name}")
        return 'skipped'
    processed_names.append(clean_faculty_name)

    headers = {"x-api-key": local_api_key}
    target_author_id = None

    try:
        url_author_search = "https://api.openalex.org/authors"
        params_author = {
            "filter": f"last_known_institutions.lineage:{VIT_INSTITUTION_LINEAGE}",
            "search": clean_faculty_name,
            "per_page": 10,
            "mailto": "admin@vitapstudent.ac.in"
        }

        logging.info(f"Searching for '{clean_faculty_name}' in VIT-AP authors...")
        response_author = await _openalex_get(client, url_author_search, params_author, headers)

        if response_author is None:
            logging.error(f"No response received for '{raw_name}'")
            return 'failed'

        if response_author.status_code == 429:
            logging.error(f"Still 429 after all retries for '{raw_name}'. Marking as failed.")
            return 'failed'

        if response_author.status_code == 200:
            data_author = response_author.json()
            vit_authors = data_author.get("results", [])

            if not vit_authors:
                logging.info(f"No OpenAlex record found for '{clean_faculty_name}'. Skipping.")
                return 'skipped'

            found_match = False
            for author in vit_authors:
                author_display = author.get("display_name", "")
                author_id = author.get("id", "")
                author_tokens = set(clean_name_string(author_display).split())

                if faculty_tokens == author_tokens:
                    target_author_id = author_id
                    logging.info(f"Exact Match: '{raw_name}' <-> '{author_display}'")
                    found_match = True
                    break

                if faculty_tokens.issubset(author_tokens) or author_tokens.issubset(faculty_tokens):
                    overlap = len(faculty_tokens & author_tokens)
                    if overlap >= min(len(faculty_tokens), len(author_tokens)):
                        target_author_id = author_id
                        logging.info(f"Subset Match: '{raw_name}' <-> '{author_display}'")
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
                        logging.info(f"Initial Match: '{raw_name}' <-> '{author_display}'")
                        found_match = True
                        break

            if not found_match:
                logging.info(f"Faculty '{raw_name}' NOT found in VIT-AP authors list.")
                return 'skipped'
        else:
            logging.warning(f"Author search failed for '{raw_name}'. Status: {response_author.status_code}")
            return 'failed'

        if not target_author_id:
            logging.info(f"No author ID found for '{raw_name}' at VIT-AP. Skipping.")
            return 'skipped'

        url_works_final = "https://api.openalex.org/works"
        params_final = {
            "filter": f"authorships.author.id:{target_author_id}",
            "per_page": 200,
            "sort": "publication_year:desc",
            "mailto": "admin@vitapstudent.ac.in"
        }

        response_works = await _openalex_get(client, url_works_final, params_final, headers)

        if response_works is None or response_works.status_code != 200:
            status = response_works.status_code if response_works else "no response"
            logging.error(f"Error fetching works for '{raw_name}' (author {target_author_id}): HTTP {status}")
            return 'failed'

        data_works = response_works.json()
        clean_projects = []

        for res in data_works.get("results", []):
            if not isinstance(res, dict):
                continue
            openalex_id = str(res.get("id", ""))
            title = str(res.get("title", ""))
            year_data = res.get("publication_year")
            pub_year = str(year_data) if year_data else "Unknown"
            pub_type = str(res.get("type", "") or "article")
            citation_count = int(res.get("cited_by_count", 0))

            is_vitap_work = False
            for authorship in res.get("authorships", []):
                if authorship.get("author", {}).get("id", "") == target_author_id:
                    for inst in authorship.get("institutions", []):
                        for lineage_item in inst.get("lineage", []):
                            if VIT_INSTITUTION_LINEAGE in str(lineage_item):
                                is_vitap_work = True
                                break
                        if is_vitap_work:
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
            logging.info(f"Updated '{raw_name}' with {len(clean_projects)} publications.")
            return 'updated'
        else:
            logging.info(f"No publications found for '{raw_name}'")
            return 'skipped'

    except Exception as e:
        logging.error(f"Unexpected error processing '{faculty.get('name')}': {e}", exc_info=True)
        return 'failed'

def _load_openalex_checkpoint() -> dict:
    if OPENALEX_CHECKPOINT_FILE.exists():
        try:
            with open(OPENALEX_CHECKPOINT_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"processed_ids": [], "failed_ids": []}

def _save_openalex_checkpoint(processed_ids: list, failed_ids: list):
    try:
        with open(OPENALEX_CHECKPOINT_FILE, "w") as f:
            json.dump({"processed_ids": processed_ids, "failed_ids": failed_ids}, f)
    except Exception as e:
        logging.warning(f"Could not save OpenAlex checkpoint: {e}")

def _clear_openalex_checkpoint():
    try:
        if OPENALEX_CHECKPOINT_FILE.exists():
            OPENALEX_CHECKPOINT_FILE.unlink()
    except Exception as e:
        logging.warning(f"Could not clear OpenAlex checkpoint: {e}")

async def perform_sync_openalex():
    global _openalex_sync_running
    if _openalex_sync_running:
        logging.info("OpenAlex sync already running. Skipping this trigger (checkpoint run has priority).")
        return
    _openalex_sync_running = True

    logging.info("Executing OpenAlex Sync...")
    local_api_key = os.environ.get('OPENALEX_API_KEY')
    if not local_api_key:
        logging.warning("OpenAlex API key missing for scheduled job.")
        _openalex_sync_running = False
        return

    checkpoint = _load_openalex_checkpoint()
    already_processed_ids = set(checkpoint.get("processed_ids", []))
    if already_processed_ids:
        logging.info(f"Resuming from checkpoint: {len(already_processed_ids)} faculty already processed, skipping them.")

    all_faculty_data = await db.faculty.find({}, {"_id": 0}).to_list(1000)

    updated_count = 0
    skipped_count = 0
    failed_count = 0
    failed_faculty = []
    processed_names = []
    processed_ids = list(already_processed_ids) 

    try:
        async with httpx.AsyncClient() as client:
            for faculty in all_faculty_data:
                fid = faculty.get("faculty_id", "")
                if fid in already_processed_ids:
                    skipped_count += 1
                    continue

                result = await _process_one_faculty(client, faculty, local_api_key, processed_names)

                if result == 'updated':
                    updated_count += 1
                    processed_ids.append(fid)
                    _save_openalex_checkpoint(processed_ids, [f.get("faculty_id") for f in failed_faculty])
                elif result == 'failed':
                    failed_count += 1
                    failed_faculty.append(faculty)
                else:
                    skipped_count += 1
                    processed_ids.append(fid)
                await asyncio.sleep(0.5)

            if failed_faculty:
                logging.info(
                    f"Starting retry pass for {len(failed_faculty)} failed records. "
                    f"Sleeping 15s before beginning..."
                )
                await asyncio.sleep(15)
                retry_updated = 0
                retry_still_failed = 0
                for faculty in failed_faculty:
                    result = await _process_one_faculty(client, faculty, local_api_key, processed_names)
                    fid = faculty.get("faculty_id", "")
                    if result == 'updated':
                        updated_count += 1
                        failed_count -= 1
                        retry_updated += 1
                        processed_ids.append(fid)
                        _save_openalex_checkpoint(processed_ids, [])
                    elif result == 'failed':
                        retry_still_failed += 1
                    else:
                        failed_count -= 1
                        skipped_count += 1
                        processed_ids.append(fid)
                    await asyncio.sleep(5)
                logging.info(
                    f"Retry pass complete. Recovered: {retry_updated}, "
                    f"Still failed: {retry_still_failed}"
                )

        if failed_count == 0:
            logging.info(f"OpenAlex Sync completed cleanly. Updated: {updated_count}, Skipped: {skipped_count}.")
            _clear_openalex_checkpoint()
        else:
            logging.warning(f"OpenAlex Sync finished but {failed_count} records STILL failed. Preserving checkpoint and scheduling a resume in 30 minutes.")
            remaining_failed_ids = [f.get("faculty_id") for f in failed_faculty if f.get("faculty_id") not in processed_ids]
            _save_openalex_checkpoint(processed_ids, remaining_failed_ids)
            try:
                scheduler.add_job(
                    perform_sync_openalex, 'date',
                    run_date=datetime.now(timezone.utc) + timedelta(minutes=30),
                    id='openalex_checkpoint_resume', replace_existing=True
                )
            except Exception as e:
                logging.error(f"Failed to schedule resume: {e}")

        try:
            recommender = FacultyRecommender.get_instance()
            if updated_count > 0:
               fresh_faculty = await db.faculty.find({}, {"_id": 0}).to_list(None)
               loop = asyncio.get_event_loop()
               await loop.run_in_executor(None, recommender.sync_all_faculty, fresh_faculty)
        except Exception as e:
            logging.error(f"Vector sync after OpenAlex failed: {e}")

    except Exception as e:
        logging.error(f"OpenAlex sync crashed: {e}", exc_info=True)
        logging.info("Checkpoint preserved. Next run will resume from where this run left off.")
    finally:
        _openalex_sync_running = False




@app.on_event("startup")
async def run_initialization():
    global _startup_complete
    try:
        logging.info("Starting background initialization...")
        
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
                logging.info("No CSV found. Database will remain empty until sync.")
        else:
            logging.info(f"Database contains {count} faculty records. Model loading will follow...")

        logging.info("Initializing Vector Store (Loading ML Models)...")
        loop = asyncio.get_event_loop()
        def init_recommender_sync():
            return FacultyRecommender.get_instance()
        
        recommender = await loop.run_in_executor(None, init_recommender_sync)
        all_faculty = await db.faculty.find({}, {"_id": 0}).to_list(None)
        
        logging.info("Syncing faculty to vector store...")
        await loop.run_in_executor(None, recommender.sync_all_faculty, all_faculty)
        logging.info("Vector Store sync finished.")

        logging.info("Initializing Schedulers...")
        scheduler.add_job(perform_csv_sync_and_db_update, 'interval', days=2, id='csv_sync', replace_existing=True)
        scheduler.add_job(perform_sync_openalex, 'interval', days=2, id='openalex_sync', replace_existing=True)
        try:
            if not scheduler.running:
                scheduler.start()
        except Exception:
            pass

        if OPENALEX_CHECKPOINT_FILE.exists():
            logging.info("OpenAlex checkpoint detected from a previous interrupted run. Scheduling resume in 30 minutes.")
            scheduler.add_job(
                perform_sync_openalex, 'date',
                run_date=datetime.now(timezone.utc) + timedelta(minutes=30),
                id='openalex_checkpoint_resume', replace_existing=True
            )


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
                logging.info(f"Creating Admin user: {ADMIN_ENV_EMAIL}")
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

        _startup_complete = True
        logging.info("Startup complete. Server ready and fully initialized.")
    except Exception as e:
        logging.error(f"Critical initialization error: {e}")
        import traceback
        logging.error(traceback.format_exc())

@app.on_event("startup")
async def startup_event():
    logging.info("Server process starting. Port binding should occur now.")
    asyncio.create_task(run_initialization())

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

@api_router.post("/auth/send-otp")
async def send_otp(request: SendOTPRequest):
    if not request.email.endswith("@vitapstudent.ac.in"):
        raise HTTPException(status_code=400, detail="Registration restricted to @vitapstudent.ac.in emails")
        
    existing_user = await db.users.find_one({"email": request.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
        
    otp = str(random.randint(100000, 999999))
    expiration = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    await db.otps.update_one(
        {"email": request.email},
        {"$set": {"otp": otp, "expires_at": expiration}},
        upsert=True
    )
    
    subject = "Your FacultyHub Verification Code"
    body = f"""
    <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
                <h3 style="color: #0f766e;">Welcome to VIT-AP Faculty Hub!</h3>
                <p>Your email verification code is:</p>
                <div style="background-color: #f1f5f9; padding: 16px; font-size: 24px; font-weight: bold; text-align: center; letter-spacing: 4px; border-radius: 8px; margin: 20px 0;">
                    {otp}
                </div>
                <p style="color: #64748b; font-size: 14px;">This code will expire in 10 minutes. If you didn't request this, you can safely ignore this email.</p>
            </div>
        </body>
    </html>
    """
    await send_email_async(request.email, subject, body)
    return {"message": "OTP sent successfully"}

@api_router.post("/auth/register")
async def register_user(user_data: UserRegister):
    if not user_data.email.endswith("@vitapstudent.ac.in"):
        raise HTTPException(status_code=400, detail="Registration restricted to @vitapstudent.ac.in emails")

    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    otp_record = await db.otps.find_one({"email": user_data.email, "otp": user_data.otp})
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    expires_at = otp_record.get("expires_at")
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
        
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

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
    await db.otps.delete_one({"email": user_data.email})
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
    
    is_production = "RENDER" in os.environ
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=is_production,
        samesite="none" if is_production else "lax",
        max_age=7*24*60*60,
        path="/"
    )
    
    if isinstance(user_doc["created_at"], str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    
    return {"user": User(**user_doc), "token": session_token}

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@api_router.post("/auth/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    if session_token:
        await db.user_sessions.delete_many({"session_token": session_token})
    
    is_production = "RENDER" in os.environ
    response.delete_cookie(
        key="session_token", 
        path="/",
        secure=is_production,
        samesite="none" if is_production else "lax"
    )
    return {"message": "Logged out successfully"}

_firebase_pubkeys: Dict[str, str] = {}
_firebase_pubkeys_fetched_at: float = 0.0
_FIREBASE_CERTS_URL = (
    "https://www.googleapis.com/robot/v1/metadata/x509/"
    "securetoken@system.gserviceaccount.com"
)

def _get_firebase_pubkeys() -> Dict[str, str]:
    global _firebase_pubkeys, _firebase_pubkeys_fetched_at
    if time.time() - _firebase_pubkeys_fetched_at < 3600 and _firebase_pubkeys:
        return _firebase_pubkeys
    resp = requests.get(_FIREBASE_CERTS_URL, timeout=10)
    resp.raise_for_status()
    _firebase_pubkeys = resp.json()
    _firebase_pubkeys_fetched_at = time.time()
    return _firebase_pubkeys

def _verify_firebase_id_token(id_token: str, project_id: str) -> dict:
    try:
        unverified_header = jose_jwt.get_unverified_header(id_token)
    except JWTError as exc:
        raise ValueError(f"Bad JWT header: {exc}")

    kid = unverified_header.get("kid")
    pubkeys = _get_firebase_pubkeys()
    if kid not in pubkeys:
        raise ValueError(f"Unknown Firebase key id: {kid}")

    cert_pem = pubkeys[kid]
    try:
        claims = jose_jwt.decode(
            id_token,
            cert_pem,
            algorithms=["RS256"],
            audience=project_id,
            issuer=f"https://securetoken.google.com/{project_id}",
            options={"verify_exp": True},
        )
    except JWTError as exc:
        raise ValueError(f"JWT verification failed: {exc}")

    return claims

@api_router.post("/auth/google")
async def google_auth(response: Response, body: GoogleAuthRequest):
    firebase_project = os.environ.get("FIREBASE_PROJECT_ID", _FIREBASE_PROJECT_ID)
    try:
        loop = asyncio.get_event_loop()
        decoded = await loop.run_in_executor(
            None, lambda: _verify_firebase_id_token(body.id_token, firebase_project)
        )
    except Exception as e:
        logging.error(f"Firebase token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid Google token")

    email: str = decoded.get("email", "")
    if not email:
        raise HTTPException(status_code=400, detail="No email in Google token")

    if not email.endswith("@vitapstudent.ac.in"):
        raise HTTPException(
            status_code=403,
            detail="Only @vitapstudent.ac.in Google accounts are allowed."
        )

    user_doc = await db.users.find_one({"email": email}, {"_id": 0})

    is_new_user = False
    if user_doc:
        if user_doc.get("blocked", False):
            raise HTTPException(status_code=403, detail="Account blocked")
        if not user_doc.get("google_linked"):
            await db.users.update_one(
                {"user_id": user_doc["user_id"]},
                {"$set": {"google_linked": True}}
            )
            user_doc["google_linked"] = True
    else:
        is_new_user = True
        unified_id = str(random.randint(1000, 9999))
        display_name = decoded.get("name") or email.split("@")[0]
        picture = decoded.get("picture")
        user_doc = {
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "email": email,
            "name": display_name,
            "picture": picture,
            "is_admin": False,
            "blocked": False,
            "preferences": [],
            "ai_interests": [],
            "created_at": datetime.now(timezone.utc),
            "anonymous_id": unified_id,
            "anonymous_chat_id": unified_id,
            "anonymous_comment_id": unified_id,
            "theme_preference": "light",
            "google_linked": True,
        }
        await db.users.insert_one(dict(user_doc))

    session_token = f"sess_{uuid.uuid4().hex}"
    await db.user_sessions.insert_one({
        "user_id": user_doc["user_id"],
        "session_token": session_token,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        "created_at": datetime.now(timezone.utc)
    })

    is_production = "RENDER" in os.environ
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=is_production,
        samesite="none" if is_production else "lax",
        max_age=7 * 24 * 60 * 60,
        path="/"
    )

    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])

    return {"user": User(**user_doc), "token": session_token, "is_new_user": is_new_user}

@api_router.post("/auth/link-google")
async def link_google_account(body: GoogleAuthRequest, current_user: User = Depends(get_current_user)):
    if current_user.google_linked:
        raise HTTPException(status_code=400, detail="Google account is already linked.")

    firebase_project = os.environ.get("FIREBASE_PROJECT_ID", _FIREBASE_PROJECT_ID)
    try:
        loop = asyncio.get_event_loop()
        decoded = await loop.run_in_executor(
            None, lambda: _verify_firebase_id_token(body.id_token, firebase_project)
        )
    except Exception as e:
        logging.error(f"Firebase token verification failed during link: {e}")
        raise HTTPException(status_code=401, detail="Invalid Google token")

    google_email: str = decoded.get("email", "")
    if not google_email:
        raise HTTPException(status_code=400, detail="No email in Google token")

    if google_email != current_user.email:
        raise HTTPException(
            status_code=400,
            detail=f"The Google account ({google_email}) does not match your registered email ({current_user.email})."
        )

    picture = decoded.get("picture") or current_user.picture
    await db.users.update_one(
        {"user_id": current_user.user_id},
        {"$set": {"google_linked": True, "picture": picture}}
    )

    return {"message": "Google account linked successfully.", "google_linked": True}

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

            has_keyword_match = bool(found_in_interests or found_in_projects)
            match_type = "keyword" if has_keyword_match else "semantic"

            recommendations.append({
                **fac,
                "compatibility_percentage": round(final_score, 1),
                "recommendation_reason": final_reason,
                "match_type": match_type
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
                "recommendation_reason": None,
                "match_type": "keyword"
            })
    
    recommendations.sort(key=lambda x: x.get("compatibility_percentage", 0), reverse=True)
    return recommendations

@api_router.post("/admin/sync-openalex")
async def sync_openalex_data(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    if _openalex_sync_running:
        return {"message": "OpenAlex sync already in progress. Please wait for it to complete."}

    api_key = os.environ.get('OPENALEX_API_KEY')
    if not api_key:
        logging.error("DEBUG: OPENALEX_API_KEY is MISSING in .env file!")
        raise HTTPException(status_code=400, detail="OPENALEX_API_KEY not found in environment variables.")

    try:
        scheduler.reschedule_job('openalex_sync', trigger='interval', days=2)
        logging.info("OpenAlex scheduler reset: next auto-run in 2 days from now.")
    except Exception:
        pass

    asyncio.create_task(perform_sync_openalex())
    return {"message": "OpenAlex Sync started in background. Next scheduled auto-run reset to 2 days from now."}

@api_router.post("/admin/sync-website")
async def sync_website_data(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    if _csv_sync_running:
        return {"message": "Website sync already in progress. Please wait for it to complete.", "status": "skipped"}

    try:
        scheduler.reschedule_job('csv_sync', trigger='interval', days=2)
        logging.info("CSV scheduler reset: next auto-run in 2 days from now.")
    except Exception:
        pass

    result = await perform_csv_sync_and_db_update()
    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail="Sync failed")
    return {
        "message": "Sync Completed. Next scheduled auto-run reset to 2 days from now.",
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

@app.get("/health")
@app.get("/api/health")
async def health_check():
    if not _startup_complete:
        raise HTTPException(status_code=503, detail="Starting up")
    return Response(content="ok", media_type="text/plain")

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
    port = int(os.environ.get("PORT", 10000 if "RENDER" in os.environ else 8000))
    logging.info(f"Starting server on port {port}...")
    uvicorn.run("server:socket_app", host="0.0.0.0", port=port, log_level="info")