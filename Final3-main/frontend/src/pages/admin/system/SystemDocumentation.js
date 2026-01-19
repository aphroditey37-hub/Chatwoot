import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card';
import { BookOpen, ArrowRight, DollarSign, TrendingUp, AlertTriangle, CheckCircle, XCircle, Users } from 'lucide-react';

const SystemDocumentation = () => {
  const sections = [
    {
      title: 'Deposit Flow',
      icon: DollarSign,
      color: 'emerald',
      content: [
        { step: '1. User submits deposit request', detail: 'Amount, game, payment proof' },
        { step: '2. System applies rules', detail: 'CLIENT > GAME > GLOBAL priority' },
        { step: '3. Bonus calculation', detail: 'Based on active rules and user eligibility' },
        { step: '4. Approval routing', detail: 'Auto-approve or manual based on risk flags' },
        { step: '5. Telegram notification', detail: 'Admin receives approval request if manual' },
        { step: '6. Balance update', detail: 'Cash + Play Credits + Bonus awarded' }
      ]
    },
    {
      title: 'Withdrawal Flow',
      icon: TrendingUp,
      color: 'blue',
      content: [
        { step: '1. User requests withdrawal', detail: 'Amount, game, payout details' },
        { step: '2. Balance consumption order', detail: 'Cash → Play Credits → Bonus' },
        { step: '3. Cashout multiplier check', detail: 'Validate against min/max multipliers' },
        { step: '4. Risk assessment', detail: 'Suspicious patterns, velocity checks' },
        { step: '5. Approval/Void decision', detail: 'Admin approves or voids with reason' },
        { step: '6. Payout calculation', detail: 'Final amount after multiplier application' }
      ]
    },
    {
      title: 'Bonus Rules',
      icon: CheckCircle,
      color: 'purple',
      content: [
        { step: 'Rule Priority', detail: 'CLIENT > GAME > GLOBAL (first match wins)' },
        { step: 'Signup Bonus', detail: 'One-time bonus on first deposit' },
        { step: 'Deposit Bonus', detail: 'Percentage-based on deposit amount' },
        { step: 'Referral Bonus', detail: 'Up to 30% lifetime commission on referred users' },
        { step: 'Bonus Consumption', detail: 'Used last in withdrawal flow (after Cash & Play Credits)' },
        { step: 'Promo Codes', detail: 'Add Play Credits only, no bonus percentage' }
      ]
    },
    {
      title: 'Void Logic',
      icon: XCircle,
      color: 'red',
      content: [
        { step: 'When to Void', detail: 'Insufficient play, rule violations, suspicious activity' },
        { step: 'Void Amount Calculation', detail: 'Bonus portion + excess play credits' },
        { step: 'Payout Amount', detail: 'Original deposit + legitimate winnings' },
        { step: 'Void Reason Required', detail: 'Admin must provide explanation' },
        { step: 'User Notification', detail: 'Transparent breakdown sent to user' },
        { step: 'Audit Trail', detail: 'All voids logged for compliance' }
      ]
    },
    {
      title: 'Approval Behavior',
      icon: AlertTriangle,
      color: 'orange',
      content: [
        { step: 'Auto-Approve Triggers', detail: 'Clean history, within limits, no risk flags' },
        { step: 'Manual Approval Triggers', detail: 'First deposit, large amount, flagged user' },
        { step: 'Telegram Queue', detail: 'Failed Telegram sends go to fallback queue' },
        { step: 'Approval Timeout', detail: 'Pending orders expire after 48 hours' },
        { step: 'Admin Override', detail: 'Can approve/reject with custom reason anytime' },
        { step: 'Bulk Actions', detail: 'Approve/reject multiple orders simultaneously' }
      ]
    },
    {
      title: 'Client-Visible vs Admin-Only',
      icon: Users,
      color: 'gray',
      content: [
        { step: 'Client Sees', detail: 'Total balance, bonus amount, available for withdrawal' },
        { step: 'Client Does NOT See', detail: 'Void reasons, risk flags, internal notes' },
        { step: 'Admin Sees', detail: 'Full balance breakdown: Cash | Play Credits | Bonus' },
        { step: 'Admin Controls', detail: 'All rules, overrides, approval actions, void logic' },
        { step: 'Transparent Info', detail: 'Deposit/withdrawal status, transaction history' },
        { step: 'Hidden Info', detail: 'Risk scores, flagging reasons, internal calculations' }
      ]
    }
  ];

  const getColorClasses = (color) => {
    const colors = {
      emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
      blue: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
      purple: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
      red: 'bg-red-500/10 text-red-400 border-red-500/30',
      orange: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
      gray: 'bg-gray-500/10 text-gray-400 border-gray-500/30'
    };
    return colors[color] || colors.gray;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <BookOpen className="w-6 h-6 text-yellow-400" />
          System Documentation
        </h1>
        <p className="text-gray-400 text-sm mt-1">Internal admin reference for platform operations</p>
      </div>

      {/* Documentation Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {sections.map((section, idx) => {
          const Icon = section.icon;
          return (
            <Card key={idx} className="bg-gray-900 border-gray-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <div className={`p-2 rounded-lg ${getColorClasses(section.color)}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="text-lg">{section.title}</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {section.content.map((item, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <ArrowRight className="w-4 h-4 text-gray-600 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-white text-sm font-medium">{item.step}</p>
                        <p className="text-gray-500 text-xs mt-0.5">{item.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Quick Reference */}
      <Card className="bg-gradient-to-r from-gray-900 to-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle>Quick Reference</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <h4 className="text-emerald-400 font-semibold mb-2 flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                Balance Breakdown
              </h4>
              <ul className="text-gray-400 text-sm space-y-1">
                <li>• Cash: Real money deposited</li>
                <li>• Play Credits: Promo codes + bonuses</li>
                <li>• Bonus: Deposit/referral bonuses</li>
              </ul>
            </div>
            <div>
              <h4 className="text-blue-400 font-semibold mb-2 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Risk Flags
              </h4>
              <ul className="text-gray-400 text-sm space-y-1">
                <li>• Manual approval required</li>
                <li>• Bonus disabled</li>
                <li>• Withdrawal disabled</li>
                <li>• Suspicious activity</li>
              </ul>
            </div>
            <div>
              <h4 className="text-purple-400 font-semibold mb-2 flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                Automation States
              </h4>
              <ul className="text-gray-400 text-sm space-y-1">
                <li>• ON: Fully automated</li>
                <li>• MANUAL: Requires approval</li>
                <li>• OFF: Feature disabled</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SystemDocumentation;