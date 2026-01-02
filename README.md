## What is VITAP Faculty Hub?

VITAP Faculty Hub is a web application designed to bridge the gap between students and faculty at VIT-AP University. It transforms the faculty directory into an interactive platform where students can discover professors, analyze research interests, and provide constructive feedback.

## Key Features

👨‍🏫 **Comprehensive Faculty Discovery**
- Browse the complete VIT-AP faculty database
- Access detailed profiles including research interests and contact info

⭐ **Interactive Rating System**
- Rate faculty on Teaching, Attendance, and Doubt Clarification
- View average ratings and overall score
- Contribute to a transparent feedback loop

💬 **Community & Communication**
- Engage in public discussions via faculty-specific comments
- Connect directly with peers using real-time chat functionality
- Share experiences and advice in a secure environment

🤖 **Smart Recommendations**
- Get faculty recommendations based on your research interests
- Match keywords with OpenAlex data to find mentors in your field
- Prioritized scoring based on your preferences and ratings

🔍 **Real-time Research Data**
- Admin integration with OpenAlex API
- Automatically syncs latest publications and projects

## Tech Stack

**Backend:**
- FastAPI (Python web framework)
- MongoDB with Motor for async database operations
- Bcrypt for secure password hashing
- Pandas for CSV data processing
- OpenAlex API for research data synchronization

**Frontend:**
- React for UI components
- JSX for dynamic page rendering
- Tailwind CSS for styling
- Craco for configuration management

## Quick Start Guide

### Prerequisites
- Python 3.8+
- Node.js & npm/yarn
- MongoDB (local or cloud)
- OpenAlex API Key (for admin sync features)

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

4. **Run the backend server**
```bash
uvicorn server:app --reload
```

5. **Open a new terminal and open the same virtual environment here as well**
  ```bash
venv\Scripts\activate  # On Linux: source venv/bin/activate
```

6. **Start frontend**
```bash
cd frontend
yarn start
```


## API Endpoints

**Authentication:**
- POST /api/auth/register - Create new account (@vitapstudent.ac.in only)
- POST /api/auth/login - User login
- GET /api/auth/me - Get current user
- POST /api/auth/logout - User logout

**Faculty Management:**
- GET /api/faculty - View all faculty (filter by department)
- GET /api/faculty/{id} - View specific faculty details
- POST /api/faculty - Add new faculty (Admin only)
- PATCH /api/faculty/{id} - Update faculty details (Admin only)
- DELETE /api/faculty/{id} - Remove faculty (Admin only)

**Ratings & Comments:**
- POST /api/faculty/{id}/ratings - Submit or update rating
- GET /api/faculty/{id}/ratings/me - Get your rating for a faculty
- GET /api/faculty/{id}/comments - View all comments
- POST /api/faculty/{id}/comments - Add a new comment
- DELETE /api/comments/{id} - Delete a comment

**Recommendations & Rankings:**
- GET /api/recommendations - Get personalized faculty suggestions
- GET /api/rankings - View faculty rankings by category

**Communication:**
- GET /api/chats - Get all chat conversations
- POST /api/chats/messages - Send a message

**Admin Features:**
- POST /api/admin/sync-openalex - Sync faculty research data from OpenAlex

## Configuration Details

**MongoDB Setup:**
- Local: Install MongoDB Community Server
- Cloud: Use MongoDB Atlas (free tier available)
- Database initializes automatically with demo data if empty

**OpenAlex API:**
1. Sign up at openalex.org
2. Get your API key
3. Add to `.env` file as `OPENALEX_API_KEY`
4. Used for syncing publications and projects

## Acknowledgments

Thanks to OpenAlex for providing open research data, MongoDB for the database, FastAPI for the web framework. We thank you from the bottom of our hearts for helping us complete this project