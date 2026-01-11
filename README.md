## What is VITAP Faculty Hub?

VITAP Faculty Hub is a web application designed to bridge the gap between students and faculty at VIT-AP University. It transforms the faculty directory into an interactive platform where students can discover professors, analyze research interests, and provide constructive feedback, all while maintaining privacy and fostering community.

## Key Features

👨‍🏫 **Comprehensive Faculty Discovery**
- Browse the complete VIT-AP faculty database
- Access detailed profiles including research interests and contact info
- View OpenAlex integrated research projects and publications

⭐ **Interactive Rating System**
- Rate faculty on Teaching, Attendance, and Doubt Clarification
- View average ratings and overall score
- Contribute to a transparent feedback loop

💬 **Anonymous Community & Moderation**
- Engage in public discussions via faculty-specific comments
- **Privacy First:** Users appear as "Anonymous@ID" to other students.
- **Admin Oversight:** Admins can view real names and moderate content.
- **Content Management:** Users can delete their own comments; Admins can delete any comment.

💬 **Real-time Communication**
- Connect directly with peers using real-time Socket.IO chat functionality.
- **WhatsApp-Style UI:** Messages display timestamps dynamically (e.g., "10:30 AM", "Yesterday, 5:00 PM").
- **Admin Visibility:** Messages from Admins are highlighted for easy identification.

🤖 **Smart Recommendations**
- Get faculty recommendations based on your research interests (AI, ML, Robotics, etc.).
- Match keywords with OpenAlex data to find mentors in your field.
- Prioritized scoring based on your rating preferences.

🔐 **Admin & User Management**
- **User Control:** Admins can view all user profiles, grant Admin rights, or Block/Unblock accounts.
- **Data Sync:** Admin integration with OpenAlex API to auto-sync latest publications.
- **Comment Moderation:** Admins can delete inappropriate comments instantly.

## Tech Stack

**Backend:**
- FastAPI (Python web framework)
- MongoDB with Motor for async database operations
- Bcrypt for secure password hashing
- Pandas for CSV data processing
- OpenAlex API for research data synchronization
- Python-Socket.IO for real-time WebSocket communication

**Frontend:**
- React for UI components
- JSX for dynamic page rendering
- Tailwind CSS for styling
- Socket.IO Client for real-time chat
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

4. **Run backend server**
```bash
uvicorn server:socket_app --reload
```

5. **Open a new terminal and open the same virtual environment here as well**
  ```bash
venv\Scripts\activate  # On Linux: source venv/bin/activate
```

6. **Install Dependencies & Start frontend**
```bash
cd frontend
yarn install
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
- DELETE /api/comments/{id} - Delete a comment (Owner or Admin only)

**User Management (Admin):**
- GET /api/admin/users - Get list of all registered users (Admin only)
- PATCH /api/admin/users/{id} - Update user status (Make Admin/Block) (Admin only)
- GET /api/users/{id} - View specific user profile (Self or Admin only)

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

Thanks to OpenAlex for providing open research data, MongoDB for the database, FastAPI for the web framework, and the Socket.IO community for real-time capabilities. We thank you from the bottom of our hearts for helping us complete this project.