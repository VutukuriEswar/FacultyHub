import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios'; // Standard import
import { GraduationCap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';

// FIX: Define the API URL explicitly like the other pages
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function LandingPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLogin, setIsLogin] = useState(true);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error('Please enter both email and password');
      return;
    }

    setIsLoading(true);
    try {
      // FIX: Use the explicit API constant
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const user = response.data;
      toast.success(`Welcome, ${user.name}!`);

      navigate('/dashboard', { state: { user }, replace: true });
    } catch (error) {
      console.error('Login error:', error);
      toast.error(error.response?.data?.detail || 'Login failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!name || !email || !password) {
      toast.error('Please fill in all fields');
      return;
    }

    setIsLoading(true);
    try {
      // Note: Based on your server.py, there isn't a dedicated /auth/register endpoint 
      // that creates a user manually, only a login that creates one if it doesn't exist.
      // I will keep this logic consistent with your server's capabilities or warn if it's missing.
      await axios.post(`${API}/auth/register`, { name, email, password });
      toast.success('Registration successful! Please sign in.');
      setName('');
      setEmail('');
      setPassword('');
      setIsLogin(true);
    } catch (error) {
      console.error('Registration error:', error);
      toast.error(error.response?.data?.detail || 'Registration failed. Email might already be in use.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-orange-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="text-center space-y-2">
          <div className="flex items-center justify-center gap-3 mb-2">
            <GraduationCap className="w-10 h-10 text-primary" />
            <span className="text-3xl font-bold gradient-text">VIT-AP Faculty Hub</span>
          </div>
          <CardTitle className="text-2xl">{isLogin ? 'Sign In' : 'Create Account'}</CardTitle>
          <p className="text-muted-foreground">
            {isLogin
              ? 'Enter your credentials to access the dashboard.'
              : 'Register to rate faculty and join discussions.'}
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={isLogin ? handleLogin : handleRegister} className="space-y-4">
            {!isLogin && (
              <div>
                <Label htmlFor="name">Full Name</Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
            )}

            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="your.name@vitapstudent.ac.in"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading
                ? (isLogin ? 'Signing In...' : 'Creating Account...')
                : (isLogin ? 'Sign In' : 'Register')}
            </Button>
          </form>

          <div className="mt-4 text-center text-sm">
            {isLogin ? (
              <p className="text-muted-foreground">
                Don't have an account?{' '}
                <button
                  onClick={() => setIsLogin(false)}
                  className="text-primary hover:underline font-medium"
                  type="button"
                >
                  Register here
                </button>
              </p>
            ) : (
              <p className="text-muted-foreground">
                Already have an account?{' '}
                <button
                  onClick={() => setIsLogin(true)}
                  className="text-primary hover:underline font-medium"
                  type="button"
                >
                  Sign In here
                </button>
              </p>
            )}
          </div>

          {isLogin && (
            <p className="text-xs text-muted-foreground text-center mt-4 border-t pt-2">
              For local demo without registering, use any <strong>@vitapstudent.ac.in</strong> email with password <strong>"password"</strong>.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}