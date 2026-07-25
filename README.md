## What is VITAP Faculty Hub?

VITAP Faculty Hub is a comprehensive web application designed to bridge the gap between students and faculty at VIT-AP University. It transforms the static faculty directory into an interactive platform where students can discover professors, analyze research interests, and provide constructive feedback. The system features automated data synchronization, intelligent recommendation reasoning, and robust privacy controls.

## Key Features

👨‍🏫 **Intelligent Faculty Discovery**
- Browse the complete VIT-AP faculty database powered by automated Selenium scrapers.
- Access detailed profiles including research interests, office addresses, and contact info.
- **Enhanced OpenAlex Integration:** Advanced matching algorithms (tokenization & subset matching) accurately link faculty to their publications and verify VIT-AP affiliation.

⭐ **Interactive Rating System**
- Rate faculty on Teaching, Attendance, Doubt Clarification, and Overall metrics.
- View average ratings calculated using weighted Bayesian estimation to prevent rating skewing.
- Contribute to a transparent, data-driven feedback loop.

💬 **Anonymous Community & Advanced Moderation**
- Engage in discussions via faculty-specific comments.
- **Privacy First:** Users appear as "Anonymous@ID" to other students.
- **Automated Profanity Guard:** The system automatically detects inappropriate language in comments.
- **Instant Alerts:** Administrators receive styled HTML email alerts with direct "Block User" links upon profanity detection.
- **Professional Communication:** Blocked users receive a clear, formatted email explaining the violation and appeal process.

🤖 **Explainable Smart Recommendations**
- Get faculty recommendations based on research interests or rating preferences.
- **Transparent Reasoning:** The engine provides specific reasons for suggestions (e.g., "Matches 'AI' in Research Interests" or "Uses related terminology: 'Machine Learning' instead of 'ML'").
- Match keywords with verified OpenAlex data to find mentors in your field.

🔄 **Automated Background Synchronization**
- **Website Sync:** Scheduled Selenium jobs automatically scrape the official VIT-AP website for new faculty or profile updates every 3 hours.
- **Research Sync:** OpenAlex data is refreshed every 2 hours to keep publication lists current.
- **Vector Store Sync:** The recommendation engine automatically re-indexes faculty data whenever the database changes.

💬 **Real-time Communication**
- Connect directly with peers using real-time Socket.IO chat functionality.
- **WhatsApp-Style UI:** Messages display timestamps dynamically.
- **Admin Visibility:** Messages from Admins are highlighted for easy identification.

🔐 **Robust Admin & User Management**
- **Seeding:** Automatic creation of Admin and Demo accounts from environment variables on first startup.
- **Data Consistency:** Automatic checks ensure all users have unified Anonymous IDs for chats and comments.
- **User Control:** Admins can view profiles, grant rights, or block accounts.

## Tech Stack

**Backend:**
- **FastAPI** (Python web framework)
- **MongoDB** with Motor for async database operations
- **Selenium** & **WebDriver Manager** for automated website scraping
- **APScheduler** for background cron jobs (syncing data)
- **Better-Profanity** for automated content moderation
- **Bcrypt** for secure password hashing
- **Pandas** for CSV data processing
- **Python-Socket.IO** for real-time WebSocket communication

**Frontend:**
- React for UI components
- Tailwind CSS for styling
- Socket.IO Client for real-time chat

## Quick Start Guide

### Prerequisites
- Python 3.8+
- Node.js & npm/yarn
- MongoDB (local or cloud)
- Google Chrome (installed on the server/machine for Selenium scraping)
- OpenAlex API Key (optional, for enhanced research sync)

### Installation Steps

1. **Clone the repository**

2. **Set up virtual environment**
```bash
python -m venv venv
venv\Scripts\activate  # On Linux: source venv/bin/activate
```

3. **Install dependencies**
```bash
cd backend
pip install -r requirements.txt
```

4. **Run backend server**
```bash
uvicorn server:socket_app --reload
```

5. **Install Dependencies & Start frontend**
Open a new terminal:
```bash
cd frontend
yarn install
yarn start
```

## API Endpoints

**Authentication:**
- `POST /api/auth/register` - Create new account (@vitapstudent.ac.in only)
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - User logout

**Faculty Management:**
- `GET /api/faculty` - View all faculty (filter by department)
- `GET /api/faculty/{id}` - View specific faculty details
- `POST /api/faculty` - Add new faculty (Admin only)
- `PATCH /api/faculty/{id}` - Update faculty details (Admin only)
- `DELETE /api/faculty/{id}` - Remove faculty (Admin only)

**Ratings & Comments:**
- `POST /api/faculty/{id}/ratings` - Submit or update rating
- `GET /api/faculty/{id}/ratings/me` - Get your rating for a faculty
- `GET /api/faculty/{id}/comments` - View all comments
- `POST /api/faculty/{id}/comments` - Add a new comment (Profanity checked automatically)
- `DELETE /api/comments/{id}` - Delete a comment (Owner or Admin only)

**User Management (Admin):**
- `GET /api/admin/users` - Get list of all registered users (Admin only)
- `PATCH /api/admin/users/{id}` - Update user status (Admin/Block) (Admin only)

**Recommendations & Rankings:**
- `GET /api/recommendations` - Get personalized faculty suggestions with reasons
- `GET /api/rankings` - View faculty rankings by category

**Communication:**
- `GET /api/chats` - Get all chat conversations
- `POST /api/chats/messages` - Send a message

**Admin Features:**
- `POST /api/admin/sync-website` - Manually trigger VIT-AP website scrape (Selenium)
- `POST /api/admin/sync-openalex` - Manually trigger OpenAlex research data sync

## Configuration Details

**Database Initialization:**
- On startup, if the database is empty, the system checks for `faculty_data.csv`.
- If no CSV is found, it starts the system with an empty database.
- Admin and Demo users are automatically seeded based on `.env` variables.

**OpenAlex Integration:**
- The sync uses advanced name tokenization to match faculty names even if formats differ (e.g., "Dr. J. Smith" vs "John Smith").
- It specifically verifies institutional lineage to ensure only VIT-AP publications are synced.

## License

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for details.

© 2026 Eswar Vutukuri, Kanneganti Lohitha, Mani Deepak, Trisanth Chinta

## Acknowledgments

This project was developed under the guidance of **Prof. Rajesh Duvvuru**, **VIT-AP University**. We sincerely thank our professor for their invaluable guidance, mentorship, and continuous support throughout the development of this project.

Thanks to OpenAlex for providing open research data, MongoDB for the database, FastAPI for the web framework, Render for Deployment of Backend & Frontend, and the Socket.IO community for real-time capabilities. Special thanks to the Selenium project for enabling automated data freshness.
