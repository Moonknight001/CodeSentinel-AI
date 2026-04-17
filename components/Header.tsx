import React from 'react';
import { useRouter } from 'next/router';
import { NAV_ITEMS } from '@/utils/constants';

// ---------------------------------------------------------------------------
// Bell icon
// ---------------------------------------------------------------------------

const BellIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg
    className={className}
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
    strokeWidth={1.8}
    aria-hidden="true"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
    />
  </svg>
);

// ---------------------------------------------------------------------------
// Header component
// ---------------------------------------------------------------------------

const Header: React.FC = () => {
  const router = useRouter();

  // Derive a human-readable page title from the current route
  const pageTitle =
    NAV_ITEMS.find((item) => router.pathname.startsWith(item.href))
      ?.label ?? 'CodeSentinel AI';

  return (
    <header className="flex items-center justify-between h-16 px-6 bg-white border-b border-gray-200 flex-shrink-0">
      {/* Page title */}
      <div>
        <h1 className="text-lg font-semibold text-gray-900">{pageTitle}</h1>
        <p className="text-xs text-gray-500 mt-0.5">
          AI-powered security analysis
        </p>
      </div>

      {/* Right-side actions */}
      <div className="flex items-center gap-4">
        {/* Notification bell */}
        <button
          type="button"
          className="relative p-2 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="View notifications"
        >
          <BellIcon className="w-5 h-5" />
          {/* Unread indicator */}
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500" />
        </button>

        {/* User avatar */}
        <button
          type="button"
          className="flex items-center gap-2 p-1 rounded-lg hover:bg-gray-100 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Open user menu"
        >
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-sm font-semibold select-none">
            CS
          </div>
          <span className="hidden sm:block text-sm font-medium text-gray-700">
            User
          </span>
        </button>
      </div>
    </header>
  );
};

export default Header;
