/**
 * EmptyState - Empty State Component
 */

import React from 'react';
import { Inbox, RefreshCw } from 'lucide-react';
import Button from './Button';

const EmptyState = ({
  icon: Icon = Inbox,
  title = 'No data found',
  description = '',
  action,
  actionLabel = 'Retry',
  className = '',
}) => (
  <div className={`flex flex-col items-center justify-center p-8 text-center ${className}`}>
    <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mb-4">
      <Icon className="w-8 h-8 text-gray-600" />
    </div>
    <h3 className="text-base font-medium text-gray-300 mb-1">{title}</h3>
    {description && (
      <p className="text-sm text-gray-500 max-w-sm">{description}</p>
    )}
    {action && (
      <Button
        variant="secondary"
        size="sm"
        onClick={action}
        icon={RefreshCw}
        className="mt-4"
      >
        {actionLabel}
      </Button>
    )}
  </div>
);

export default EmptyState;
