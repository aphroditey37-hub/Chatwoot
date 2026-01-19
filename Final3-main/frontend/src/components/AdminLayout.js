import React from 'react';
import { Link, useLocation, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  CheckSquare,
  FileText,
  Users,
  Gamepad2,
  Scale,
  Share2,
  Gift,
  BarChart3,
  Settings,
  ScrollText,
  LogOut,
  ChevronRight,
  Menu,
  X,
  DollarSign
} from 'lucide-react';
import { useState } from 'react';

/**
 * ADMIN SIDEBAR - FINAL STRUCTURE
 * 1. Dashboard (read-only overview)
 * 2. Approvals
 * 3. Orders
 * 4. Clients
 * 5. Games
 * 6. Rules (global defaults only)
 * 7. Referrals
 * 8. Promo Codes
 * 9. Balance Control
 * 10. Reports
 * 11. System
 * 12. Audit Logs
 */

const navItems = [
  { path: '/admin', icon: LayoutDashboard, label: 'Dashboard', exact: true },
  { path: '/admin/approvals', icon: CheckSquare, label: 'Approvals' },
  { path: '/admin/orders', icon: FileText, label: 'Orders' },
  { path: '/admin/clients', icon: Users, label: 'Clients' },
  { path: '/admin/games', icon: Gamepad2, label: 'Games' },
  { path: '/admin/rules', icon: Scale, label: 'Rules' },
  { path: '/admin/referrals', icon: Share2, label: 'Referrals' },
  { path: '/admin/promo-codes', icon: Gift, label: 'Promo Codes' },
  { path: '/admin/balance-control', icon: DollarSign, label: 'Balance Control' },
  { path: '/admin/reports', icon: BarChart3, label: 'Reports' },
  { path: '/admin/system', icon: Settings, label: 'System' },
  { path: '/admin/audit-logs', icon: ScrollText, label: 'Audit Logs' },
];

const AdminLayout = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (item) => {
    if (item.exact) {
      return location.pathname === item.path;
    }
    return location.pathname.startsWith(item.path);
  };

  return (
    <div className="min-h-screen bg-gray-950 flex">
      {/* Mobile sidebar toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-gray-900 rounded-lg text-gray-400"
      >
        {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-40
        w-64 bg-gray-900 border-r border-gray-800
        transform transition-transform duration-200 ease-in-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-4 border-b border-gray-800">
            <Link to="/admin" className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-blue-600 rounded-xl flex items-center justify-center">
                <Gamepad2 className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-white text-lg">Admin Panel</h1>
                <p className="text-xs text-gray-500">Game Platform</p>
              </div>
            </Link>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setSidebarOpen(false)}
                  className={`
                    flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                    transition-colors duration-150
                    ${active 
                      ? 'bg-emerald-500/10 text-emerald-400 border-l-2 border-emerald-500' 
                      : 'text-gray-400 hover:text-white hover:bg-gray-800'
                    }
                  `}
                  data-testid={`nav-${item.label.toLowerCase().replace(' ', '-')}`}
                >
                  <Icon className={`w-5 h-5 ${active ? 'text-emerald-400' : ''}`} />
                  {item.label}
                  {active && <ChevronRight className="w-4 h-4 ml-auto" />}
                </Link>
              );
            })}
          </nav>

          {/* User section */}
          <div className="p-4 border-t border-gray-800">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-gray-800 rounded-full flex items-center justify-center">
                <Users className="w-5 h-5 text-gray-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{user?.username}</p>
                <p className="text-xs text-gray-500">Administrator</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
              data-testid="logout-btn"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-h-screen lg:ml-0">
        <div className="p-6 lg:p-8">
          <Outlet />
        </div>
      </main>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
};

export default AdminLayout;
