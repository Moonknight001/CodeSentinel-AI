import React from 'react';
import Head from 'next/head';
import Sidebar from './Sidebar';
import Header from './Header';
import { APP_NAME } from '@/utils/constants';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DashboardLayoutProps {
  children: React.ReactNode;
  /** Override the <title> tag for this page */
  pageTitle?: string;
}

// ---------------------------------------------------------------------------
// Layout component
// ---------------------------------------------------------------------------

const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  children,
  pageTitle,
}) => {
  const title = pageTitle
    ? `${pageTitle} — ${APP_NAME}`
    : APP_NAME;

  return (
    <>
      <Head>
        <title>{title}</title>
        <meta name="description" content="AI-powered code security analysis" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* Full-screen flex container */}
      <div className="flex h-screen overflow-hidden bg-gray-50">
        {/* Sidebar – fixed width, full height */}
        <Sidebar />

        {/* Main content area */}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          {/* Top header */}
          <Header />

          {/* Scrollable page content */}
          <main className="flex-1 overflow-y-auto p-6">
            {children}
          </main>
        </div>
      </div>
    </>
  );
};

export default DashboardLayout;
