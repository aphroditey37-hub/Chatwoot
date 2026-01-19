/**
 * PortalLanding - Magic Link Token Handler (/p/:token)
 * 
 * REQUIRED: This route MUST remain functional for magic-link authentication
 * 
 * Flow:
 * 1. Read token from URL
 * 2. Validate with backend
 * 3. On success -> /client/home
 * 4. On auth failure -> show error + "Go to Login" button
 * 5. On network failure -> show retry button
 */

import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { CheckCircle, XCircle, Loader2, RefreshCw, LogIn } from 'lucide-react';

const PortalLanding = () => {
  const { token } = useParams();
  const navigate = useNavigate();
  const { validatePortalToken } = useAuth();
  
  const [status, setStatus] = useState('validating'); // validating | success | error | network_error
  const [errorMessage, setErrorMessage] = useState('');

  const validate = useCallback(async () => {
    if (!token) {
      setStatus('error');
      setErrorMessage('No token provided in link.');
      return;
    }

    setStatus('validating');
    setErrorMessage('');

    const result = await validatePortalToken(token);
    
    if (result.success) {
      setStatus('success');
      // Redirect to client home after brief delay
      setTimeout(() => {
        navigate('/client/home', { replace: true });
      }, 1500);
    } else if (result.isNetworkError) {
      setStatus('network_error');
      setErrorMessage(result.message || 'Server temporarily unavailable.');
    } else {
      setStatus('error');
      setErrorMessage(result.message || 'This link is invalid or has expired.');
    }
  }, [token, validatePortalToken, navigate]);

  useEffect(() => {
    validate();
  }, [validate]);

  const handleRetry = () => {
    validate();
  };

  const handleGoToLogin = () => {
    navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center p-4">
      <div className="bg-[#0d0d12] border border-white/10 rounded-2xl p-8 max-w-md w-full text-center shadow-2xl">
        
        {/* Validating State */}
        {status === 'validating' && (
          <>
            <Loader2 className="w-16 h-16 text-violet-500 animate-spin mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-white mb-2">Signing you in...</h1>
            <p className="text-gray-400">Please wait while we verify your link.</p>
          </>
        )}

        {/* Success State */}
        {status === 'success' && (
          <>
            <CheckCircle className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-white mb-2">Welcome!</h1>
            <p className="text-gray-400">Redirecting to your dashboard...</p>
          </>
        )}

        {/* Auth Error State */}
        {status === 'error' && (
          <>
            <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-white mb-2">Link Invalid</h1>
            <p className="text-gray-400 mb-6">{errorMessage}</p>
            <button
              onClick={handleGoToLogin}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-violet-600 hover:bg-violet-500 text-white font-semibold rounded-xl transition-colors"
              data-testid="go-to-login-btn"
            >
              <LogIn className="w-5 h-5" />
              Go to Login
            </button>
          </>
        )}

        {/* Network Error State */}
        {status === 'network_error' && (
          <>
            <div className="w-16 h-16 bg-yellow-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <RefreshCw className="w-8 h-8 text-yellow-500" />
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">Connection Issue</h1>
            <p className="text-gray-400 mb-6">{errorMessage}</p>
            <div className="flex flex-col gap-3">
              <button
                onClick={handleRetry}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-violet-600 hover:bg-violet-500 text-white font-semibold rounded-xl transition-colors"
                data-testid="retry-btn"
              >
                <RefreshCw className="w-5 h-5" />
                Retry
              </button>
              <button
                onClick={handleGoToLogin}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-white/5 hover:bg-white/10 text-white font-semibold rounded-xl transition-colors border border-white/10"
                data-testid="go-to-login-btn-secondary"
              >
                <LogIn className="w-5 h-5" />
                Go to Login
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default PortalLanding;
