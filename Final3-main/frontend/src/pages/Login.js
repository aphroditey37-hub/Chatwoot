/**
 * Login Page - SINGLE CLIENT LOGIN ENTRY POINT
 * 
 * Features:
 * - Handles network errors gracefully (shows friendly message)
 * - Uses centralized API via AuthContext
 * - GuestGuard handles redirect if already authenticated
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getErrorMessage } from '../api/http';
import { LogIn, Eye, EyeOff, AlertCircle, User, UserPlus, RefreshCw, WifiOff } from 'lucide-react';

const Login = () => {
  const navigate = useNavigate();
  const { login, serverUnavailable, clearServerError } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isNetworkError, setIsNetworkError] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsNetworkError(false);
    setLoading(true);

    const result = await login(username, password);
    
    if (result.success) {
      // Redirect based on role
      if (result.user?.role === 'admin') {
        navigate('/admin');
      } else {
        navigate('/client/home');
      }
    } else {
      setError(result.message || 'Login failed. Please check your credentials.');
      setIsNetworkError(result.isNetworkError || false);
    }
    
    setLoading(false);
  };

  const handleRetry = () => {
    setError('');
    setIsNetworkError(false);
    clearServerError();
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center p-4">
      <div className="bg-[#0d0d12] border border-white/10 rounded-2xl p-8 w-full max-w-md shadow-2xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Welcome Back</h1>
          <p className="text-gray-400">Sign in to access your dashboard</p>
        </div>

        {/* Server Unavailable Banner */}
        {(serverUnavailable || isNetworkError) && (
          <div className="mb-6 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-xl">
            <div className="flex items-center gap-3 mb-2">
              <WifiOff className="w-5 h-5 text-yellow-400" />
              <p className="text-yellow-400 font-medium">Server Temporarily Unavailable</p>
            </div>
            <p className="text-yellow-400/70 text-sm mb-3">
              We're having trouble connecting to our servers. Please try again.
            </p>
            <button
              onClick={handleRetry}
              className="flex items-center gap-2 px-4 py-2 bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-400 text-sm font-medium rounded-lg transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Retry Connection
            </button>
          </div>
        )}

        {/* Error Message */}
        {error && !isNetworkError && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Username
            </label>
            <div className="relative">
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-4 py-3 pl-11 bg-black/50 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-violet-500 transition-colors"
                placeholder="Enter your username"
                required
                data-testid="login-username"
              />
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-black/50 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-violet-500 transition-colors pr-12"
                placeholder="Enter your password"
                required
                data-testid="login-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-300"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-violet-500 to-indigo-600 text-white font-semibold rounded-xl hover:from-violet-600 hover:to-indigo-700 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            data-testid="login-submit"
          >
            {loading ? (
              <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-white"></div>
            ) : (
              <>
                <LogIn className="w-5 h-5" />
                Sign In
              </>
            )}
          </button>
        </form>

        <div className="mt-6">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/10"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-[#0d0d12] text-gray-400">or</span>
            </div>
          </div>
          
          <button
            onClick={() => navigate('/register')}
            className="mt-4 w-full py-3 bg-white/5 border border-violet-500/50 text-violet-400 font-semibold rounded-xl hover:bg-violet-500/10 hover:border-violet-500 transition-all flex items-center justify-center gap-2"
            data-testid="create-account-button"
          >
            <UserPlus className="w-5 h-5" />
            Create New Account
          </button>
        </div>

        {/* 30% Referral Offer Banner */}
        <div className="mt-6 p-4 bg-gradient-to-r from-violet-600/20 via-fuchsia-600/20 to-emerald-500/20 border border-violet-500/30 rounded-xl">
          <div className="text-center">
            <p className="text-amber-400 font-bold text-lg mb-1">💰 Earn 30% Cash Lifetime</p>
            <p className="text-white/80 text-sm">Invite friends & earn 30% of their deposits forever!</p>
            <p className="text-gray-400 text-xs mt-2">Sign up now to get your referral code</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
