// App.js

import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import axios from 'axios';
import '@/App.css';
import { Toaster } from '@/components/ui/sonner';

// The AuthCallback import has been REMOVED
import LandingPage from '@/pages/LandingPage';
import Dashboard from '@/pages/Dashboard';
import FacultyProfile from '@/pages/FacultyProfile';
import Rankings from '@/pages/Rankings';
import AdminPanel from '@/pages/AdminPanel';
import Profile from '@/pages/Profile';
import Chats from '@/pages/Chats';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

axios.defaults.withCredentials = true;

const ProtectedRoute = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(null);
  const [user, setUser] = useState(null);
  const location = useLocation();

  useEffect(() => {
    // Check if user data is passed from the login page
    if (location.state?.user) {
      setUser(location.state.user);
      setIsAuthenticated(true);
      return;
    }

    // Otherwise, verify the session cookie
    const checkAuth = async () => {
      try {
        const response = await axios.get(`${API}/auth/me`);
        setUser(response.data);
        setIsAuthenticated(true);
      } catch (error) {
        setIsAuthenticated(false);
      }
    };

    checkAuth();
  }, [location.state]);

  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <>{typeof children === 'function' ? children({ user }) : children}</>;
};

function AppRouter() {
  // The logic for handling the Emergent OAuth callback has been REMOVED.
  // The app now directly renders the routes.

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            {({ user }) => <Dashboard user={user} />}
          </ProtectedRoute>
        }
      />
      <Route
        path="/faculty/:facultyId"
        element={
          <ProtectedRoute>
            {({ user }) => <FacultyProfile user={user} />}
          </ProtectedRoute>
        }
      />
      <Route
        path="/rankings"
        element={
          <ProtectedRoute>
            {({ user }) => <Rankings user={user} />}
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            {({ user }) => <AdminPanel user={user} />}
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            {({ user }) => <Profile user={user} />}
          </ProtectedRoute>
        }
      />
      <Route
        path="/chats"
        element={
          <ProtectedRoute>
            {({ user }) => <Chats user={user} />}
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AppRouter />
        <Toaster position="top-right" />
      </BrowserRouter>
    </div>
  );
}

export default App;