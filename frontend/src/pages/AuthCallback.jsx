import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function AuthCallback() {
  const navigate = useNavigate();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processSession = async () => {
      try {
        const hash = window.location.hash.substring(1);
        const params = new URLSearchParams(hash);
        const sessionId = params.get('session_id');

        if (!sessionId) {
          toast.error('Authentication failed');
          navigate('/', { replace: true });
          return;
        }

        const response = await axios.post(`${API}/auth/session`, null, {
          headers: { 'X-Session-ID': sessionId }
        });

        const user = response.data;
        toast.success(`Welcome, ${user.name}!`);
        navigate('/dashboard', { state: { user }, replace: true });
      } catch (error) {
        console.error('Auth error:', error);
        if (error.response?.status === 403) {
          toast.error('Only @vitapstudent.ac.in email addresses are allowed');
        } else {
          toast.error('Authentication failed. Please try again.');
        }
        navigate('/', { replace: true });
      }
    };

    processSession();
  }, [navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent mx-auto mb-4"></div>
        <p className="text-muted-foreground">Completing authentication...</p>
      </div>
    </div>
  );
}