import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { GraduationCap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import { signInWithGoogle } from '@/firebase';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

axios.defaults.withCredentials = true;

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
      <path fill="none" d="M0 0h48v48H0z" />
    </svg>
  );
}

export default function LandingPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [isLogin, setIsLogin] = useState(true);
  const [otp, setOtp] = useState('');
  const [otpSent, setOtpSent] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error('Please enter both email and password');
      return;
    }

    setIsLoading(true);
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { user, token } = response.data;
      if (token) {
        localStorage.setItem('session_token', token);
      }
      toast.success(`Welcome, ${user.name}!`);
      navigate('/dashboard', { state: { user }, replace: true });
    } catch (error) {
      console.error('Login error:', error);
      toast.error(error.response?.data?.detail || 'Invalid credentials. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendOTP = async (e) => {
    e.preventDefault();
    if (!name || !email || !password) {
      toast.error('Please fill in all fields');
      return;
    }

    if (!email.endsWith('@vitapstudent.ac.in')) {
      toast.error('Registration is restricted to @vitapstudent.ac.in emails only.');
      return;
    }

    setIsLoading(true);
    try {
      await axios.post(`${API}/auth/send-otp`, { email });
      setOtpSent(true);
      toast.success('Verification code sent to your email.');
    } catch (error) {
      console.error('OTP error:', error);
      toast.error(error.response?.data?.detail || 'Failed to send OTP. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!otp) {
      toast.error('Please enter the verification code');
      return;
    }

    setIsLoading(true);
    try {
      await axios.post(`${API}/auth/register`, { name, email, password, otp });
      toast.success('Registration successful! Please sign in.');
      setName('');
      setEmail('');
      setPassword('');
      setOtp('');
      setOtpSent(false);
      setIsLogin(true);
    } catch (error) {
      console.error('Registration error:', error);
      toast.error(error.response?.data?.detail || 'Registration failed. Email might already be in use or OTP expired.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    setIsGoogleLoading(true);
    try {
      const { idToken } = await signInWithGoogle();
      const response = await axios.post(`${API}/auth/google`, { id_token: idToken });
      const { user, token } = response.data;
      if (token) {
        localStorage.setItem('session_token', token);
      }
      toast.success(`Welcome, ${user.name}!`);
      navigate('/dashboard', { state: { user }, replace: true });
    } catch (error) {
      console.error('Google sign-in error:', error);
      toast.error(error.response?.data?.detail || 'Google Sign-In failed. Make sure you use your @vitapstudent.ac.in account.');
    } finally {
      setIsGoogleLoading(false);
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
            <div className="mb-4">
              <Button
                type="button"
                variant="outline"
                className="w-full flex items-center justify-center gap-3 h-11 border-2 border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition-all duration-200 font-medium text-slate-700"
                onClick={handleGoogleSignIn}
                disabled={isGoogleLoading}
              >
                {isGoogleLoading ? (
                  <span className="w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <GoogleIcon />
                )}
                {isGoogleLoading ? (isLogin ? 'Signing in...' : 'Signing up...') : (isLogin ? 'Continue with Google' : 'Sign up with Google')}
              </Button>

              <div className="flex items-center gap-3 my-4">
                <div className="flex-1 h-px bg-border" />
                <span className="text-xs text-muted-foreground font-medium">{isLogin ? 'or sign in with email' : 'or sign up with email'}</span>
                <div className="flex-1 h-px bg-border" />
              </div>
            </div>

          <form onSubmit={isLogin ? handleLogin : (otpSent ? handleRegister : handleSendOTP)} className="space-y-4">
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
                  disabled={otpSent}
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
                 disabled={!isLogin && otpSent}
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
                disabled={!isLogin && otpSent}
              />
            </div>

            {!isLogin && otpSent && (
              <div>
                <Label htmlFor="otp">Verification Code</Label>
                <Input
                  id="otp"
                  type="text"
                  placeholder="123456"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  required
                  maxLength={6}
                />
              </div>
            )}

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading
                ? (isLogin ? 'Signing In...' : (otpSent ? 'Creating Account...' : 'Sending OTP...'))
                : (isLogin ? 'Sign In' : (otpSent ? 'Verify & Create Account' : 'Send Verification Code'))}
            </Button>
          </form>

          <div className="mt-4 text-center text-sm">
            {isLogin ? (
              <p className="text-muted-foreground">
                Don't have an account?{' '}
                <button
                  onClick={() => { setIsLogin(false); setOtpSent(false); setOtp(''); }}
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
                  onClick={() => { setIsLogin(true); setOtpSent(false); setOtp(''); }}
                  className="text-primary hover:underline font-medium"
                  type="button"
                >
                  Sign In here
                </button>
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}