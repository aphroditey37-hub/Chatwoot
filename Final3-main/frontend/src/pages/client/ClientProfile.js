import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'sonner';
import { 
  User, Mail, Lock, Eye, EyeOff, LogOut, Save, Shield, Gift, ChevronRight
} from 'lucide-react';

// New centralized API imports
import { authApi, getErrorMessage } from '../../api';
import { ClientBottomNav } from '../../features/shared/ClientBottomNav';

// Client Profile Page
const ClientProfile = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('profile');
  
  // Profile form
  const [displayName, setDisplayName] = useState(user?.display_name || '');
  const [email, setEmail] = useState(user?.email || '');
  
  // Password form
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      await authApi.updateProfile({ display_name: displayName, email });
      toast.success('Profile updated successfully');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to update profile'));
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    
    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match');
      return;
    }
    
    if (newPassword.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }
    
    setLoading(true);
    
    try {
      await authApi.changePassword(currentPassword, newPassword);
      toast.success('Password changed successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to change password'));
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-black pb-20">
      {/* Header */}
      <div className="bg-gradient-to-b from-violet-600/20 to-transparent">
        <div className="max-w-lg mx-auto px-4 pt-6 pb-8">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold text-white">Profile & Settings</h1>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 px-4 py-2 bg-red-500/10 text-red-400 rounded-lg hover:bg-red-500/20 transition-colors"
              data-testid="logout-button"
            >
              <LogOut className="w-4 h-4" />
              <span className="text-sm font-medium">Logout</span>
            </button>
          </div>

          {/* User Info Card */}
          <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-gradient-to-br from-violet-500 to-indigo-600 rounded-full flex items-center justify-center">
                <User className="w-8 h-8 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">{user?.display_name || user?.username}</h2>
                <p className="text-gray-400 text-sm">@{user?.username}</p>
                {user?.role === 'admin' && (
                  <div className="flex items-center gap-1 mt-1">
                    <Shield className="w-3 h-3 text-violet-400" />
                    <span className="text-xs text-violet-400 font-medium">Administrator</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Quick Links */}
          <button
            onClick={() => navigate('/client/rewards')}
            className="w-full mt-4 p-4 bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 rounded-2xl flex items-center justify-between hover:border-amber-500/50 transition-all group"
            data-testid="rewards-link"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-500/20 rounded-xl flex items-center justify-center">
                <Gift className="w-5 h-5 text-amber-400" />
              </div>
              <div className="text-left">
                <p className="font-semibold text-white">Rewards Hub</p>
                <p className="text-xs text-amber-400/70">Bonuses, promos & earnings</p>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-amber-400 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="max-w-lg mx-auto px-4 mb-6">
        <div className="flex gap-2 bg-white/5 p-1 rounded-lg">
          <button
            onClick={() => setActiveTab('profile')}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'profile'
                ? 'bg-violet-500 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Profile Info
          </button>
          <button
            onClick={() => setActiveTab('security')}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'security'
                ? 'bg-violet-500 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Security
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-lg mx-auto px-4 space-y-4">
        {activeTab === 'profile' && (
          <form onSubmit={handleUpdateProfile} className="space-y-4">
            {/* Username (Read-only) */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl p-4">
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Username
              </label>
              <div className="flex items-center gap-3 px-4 py-3 bg-white/5 rounded-lg border border-white/5">
                <User className="w-5 h-5 text-gray-500" />
                <input
                  type="text"
                  value={user?.username}
                  disabled
                  className="flex-1 bg-transparent text-gray-300 outline-none"
                />
                <span className="text-xs text-gray-500">Cannot change</span>
              </div>
            </div>

            {/* Display Name */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl p-4">
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Display Name
              </label>
              <div className="flex items-center gap-3 px-4 py-3 bg-black/50 rounded-lg border border-white/10 focus-within:border-violet-500 transition-colors">
                <User className="w-5 h-5 text-gray-500" />
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Enter your display name"
                  className="flex-1 bg-transparent text-white outline-none placeholder-gray-500"
                  data-testid="display-name-input"
                />
              </div>
            </div>

            {/* Email */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl p-4">
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Email Address
              </label>
              <div className="flex items-center gap-3 px-4 py-3 bg-black/50 rounded-lg border border-white/10 focus-within:border-violet-500 transition-colors">
                <Mail className="w-5 h-5 text-gray-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your.email@example.com"
                  className="flex-1 bg-transparent text-white outline-none placeholder-gray-500"
                  data-testid="email-input"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-violet-500 to-indigo-600 text-white font-semibold rounded-xl hover:from-violet-600 hover:to-indigo-700 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              data-testid="save-profile-button"
            >
              {loading ? (
                <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-white"></div>
              ) : (
                <>
                  <Save className="w-5 h-5" />
                  Save Changes
                </>
              )}
            </button>
          </form>
        )}

        {activeTab === 'security' && (
          <form onSubmit={handleChangePassword} className="space-y-4">
            {/* Current Password */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl p-4">
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Current Password
              </label>
              <div className="flex items-center gap-3 px-4 py-3 bg-black/50 rounded-lg border border-white/10 focus-within:border-violet-500 transition-colors">
                <Lock className="w-5 h-5 text-gray-500" />
                <input
                  type={showCurrentPassword ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Enter current password"
                  className="flex-1 bg-transparent text-white outline-none placeholder-gray-500"
                  data-testid="current-password-input"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  {showCurrentPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* New Password */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl p-4">
              <label className="block text-sm font-medium text-gray-400 mb-2">
                New Password
              </label>
              <div className="flex items-center gap-3 px-4 py-3 bg-black/50 rounded-lg border border-white/10 focus-within:border-violet-500 transition-colors">
                <Lock className="w-5 h-5 text-gray-500" />
                <input
                  type={showNewPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  className="flex-1 bg-transparent text-white outline-none placeholder-gray-500"
                  data-testid="new-password-input"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  {showNewPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-2">Minimum 6 characters</p>
            </div>

            {/* Confirm Password */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl p-4">
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Confirm New Password
              </label>
              <div className="flex items-center gap-3 px-4 py-3 bg-black/50 rounded-lg border border-white/10 focus-within:border-violet-500 transition-colors">
                <Lock className="w-5 h-5 text-gray-500" />
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  className="flex-1 bg-transparent text-white outline-none placeholder-gray-500"
                  data-testid="confirm-password-input"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-violet-500 to-indigo-600 text-white font-semibold rounded-xl hover:from-violet-600 hover:to-indigo-700 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              data-testid="change-password-button"
            >
              {loading ? (
                <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-white"></div>
              ) : (
                <>
                  <Lock className="w-5 h-5" />
                  Change Password
                </>
              )}
            </button>
          </form>
        )}
      </div>

      {/* Bottom Navigation - Using shared component */}
      <ClientBottomNav active="profile" />
    </div>
  );
};

export default ClientProfile;
