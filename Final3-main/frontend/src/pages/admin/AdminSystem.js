import React from 'react';
import { Link } from 'react-router-dom';
import { 
  Settings, Zap, CreditCard, Send, Key, Webhook, 
  BookOpen, ChevronRight, Power, DollarSign, Shield, Gift, QrCode, Wallet, Bot
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';

/**
 * SYSTEM HUB PAGE
 * Central configuration and management hub
 */

const AdminSystem = () => {
  const systemSections = [
    {
      title: 'Telegram Bots',
      description: 'Multi-bot notification system - add bots, configure permissions, event subscriptions',
      icon: Bot,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
      path: '/admin/system/telegram-bots',
      badge: 'NEW'
    },
    {
      title: 'Payment QR Codes',
      description: 'Manage QR codes for wallet funding - upload, enable/disable, set default per method',
      icon: QrCode,
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10',
      path: '/admin/system/payment-qr'
    },
    {
      title: 'Wallet Load Requests',
      description: 'Review and approve/reject client wallet funding requests',
      icon: Wallet,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
      path: '/admin/system/wallet-loads',
      badge: 'REVIEW'
    },
    {
      title: 'Automations',
      description: 'Toggle ON/OFF/MANUAL for auto-approvals, bonus engine, referral rewards, and more',
      icon: Zap,
      color: 'text-yellow-400',
      bgColor: 'bg-yellow-500/10',
      path: '/admin/system/automations'
    },
    {
      title: 'Rewards',
      description: 'Define and manage automatic rewards for clients (account setup, first login, etc.)',
      icon: Gift,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10',
      path: '/admin/system/rewards'
    },
    {
      title: 'Payment Methods',
      description: 'Manage payment methods, tags, and rotation settings',
      icon: CreditCard,
      color: 'text-gray-400',
      bgColor: 'bg-gray-500/10',
      path: '/admin/system/payment-methods'
    },
    {
      title: 'Legacy Telegram Setup',
      description: 'Old single-bot setup (deprecated - use Telegram Bots instead)',
      icon: Send,
      color: 'text-gray-500',
      bgColor: 'bg-gray-600/10',
      path: '/admin/system/telegram'
    },
    {
      title: 'Webhooks',
      description: 'Register webhook URLs, select events, enable/disable, view delivery logs',
      icon: Webhook,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
      path: '/admin/system/webhooks'
    },
    {
      title: 'API Access',
      description: 'Generate API keys, manage scopes, revoke/rotate keys, track usage',
      icon: Key,
      color: 'text-orange-400',
      bgColor: 'bg-orange-500/10',
      path: '/admin/system/api-access'
    },
    {
      title: 'Documentation',
      description: 'Internal admin docs: flows, rules, logic, client-visible vs admin-only',
      icon: BookOpen,
      color: 'text-pink-400',
      bgColor: 'bg-pink-500/10',
      path: '/admin/system/documentation'
    }
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Settings className="w-7 h-7 text-gray-400" />
            System Configuration
          </h1>
          <p className="text-gray-400 text-sm mt-1">Central control tower for platform operations</p>
        </div>
      </div>

      {/* System Sections Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {systemSections.map((section) => {
          const Icon = section.icon;
          return (
            <Link key={section.path} to={section.path} className="group">
              <Card className="bg-gray-900 border-gray-800 hover:border-gray-700 transition-all h-full">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className={`p-3 rounded-xl ${section.bgColor}`}>
                      <Icon className={`w-6 h-6 ${section.color}`} />
                    </div>
                    <div className="flex items-center gap-2">
                      {section.badge && (
                        <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                          section.badge === 'NEW' ? 'bg-emerald-500/20 text-emerald-400' :
                          section.badge === 'REVIEW' ? 'bg-yellow-500/20 text-yellow-400' :
                          'bg-gray-500/20 text-gray-400'
                        }`}>
                          {section.badge}
                        </span>
                      )}
                      <ChevronRight className="w-5 h-5 text-gray-600 group-hover:text-gray-400 group-hover:translate-x-1 transition-all" />
                    </div>
                  </div>
                  <CardTitle className="text-lg mt-3">{section.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-500 text-sm leading-relaxed">{section.description}</p>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>

      {/* Quick Status Overview */}
      <Card className="bg-gradient-to-r from-gray-900 to-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Power className="w-5 h-5 text-emerald-400" />
            System Health
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                <span className="text-gray-400 text-sm">API Status</span>
              </div>
              <p className="text-white font-semibold">Operational</p>
            </div>
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Shield className="w-4 h-4 text-blue-400" />
                <span className="text-gray-400 text-sm">Security</span>
              </div>
              <p className="text-white font-semibold">All checks passed</p>
            </div>
            <div>
              <div className="flex items-center gap-2 mb-2">
                <DollarSign className="w-4 h-4 text-emerald-400" />
                <span className="text-gray-400 text-sm">Transactions</span>
              </div>
              <p className="text-white font-semibold">Processing normally</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminSystem;
