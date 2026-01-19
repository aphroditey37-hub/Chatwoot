import React, { useState } from 'react';
import { X, Copy, Share2, Check } from 'lucide-react';

const InviteModal = ({ isOpen, onClose, referralCode }) => {
  const [copiedCode, setCopiedCode] = useState(false);

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'Join me!',
          text: `Use my referral code: ${referralCode}`,
        });
      } catch (err) {
        console.log('Share cancelled or failed');
      }
    } else {
      copyToClipboard(referralCode);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-end sm:items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-gray-900 rounded-t-3xl sm:rounded-2xl border border-gray-800 w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
        data-testid="invite-modal"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white">Share Your Code</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-gray-400" />
          </button>
        </div>

        <p className="text-gray-400 mb-6">
          Share your referral code with friends and earn commissions!
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Your Referral Code
            </label>
            <div className="flex gap-2">
              <div className="flex-1 px-4 py-3 bg-black border border-gray-700 rounded-lg text-white font-mono text-lg text-center">
                {referralCode || 'N/A'}
              </div>
              <button
                onClick={() => copyToClipboard(referralCode)}
                className="px-4 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
              >
                {copiedCode ? (
                  <Check className="w-5 h-5 text-emerald-400" />
                ) : (
                  <Copy className="w-5 h-5 text-gray-400" />
                )}
              </button>
            </div>
          </div>

          <button
            onClick={handleShare}
            className="w-full py-3 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-semibold rounded-lg hover:from-emerald-600 hover:to-teal-700 transition-all flex items-center justify-center gap-2"
          >
            <Share2 className="w-5 h-5" />
            Share Code
          </button>
        </div>
      </div>
    </div>
  );
};

export default InviteModal;
