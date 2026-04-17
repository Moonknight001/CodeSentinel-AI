import React, { useState } from 'react';
import DashboardLayout from '@/components/DashboardLayout';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SettingsState {
  notifications: boolean;
  autoScan: boolean;
  reportFormat: 'pdf' | 'json' | 'csv';
  theme: 'light' | 'dark' | 'system';
  apiKey: string;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface ToggleProps {
  enabled: boolean;
  onChange: (val: boolean) => void;
  id: string;
  label: string;
  description?: string;
}

const Toggle: React.FC<ToggleProps> = ({
  enabled,
  onChange,
  id,
  label,
  description,
}) => (
  <div className="flex items-center justify-between py-4">
    <div className="flex-1 min-w-0">
      <label htmlFor={id} className="text-sm font-medium text-gray-900 cursor-pointer">
        {label}
      </label>
      {description && (
        <p className="text-xs text-gray-500 mt-0.5">{description}</p>
      )}
    </div>
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={enabled}
      onClick={() => onChange(!enabled)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
        enabled ? 'bg-blue-600' : 'bg-gray-200'
      }`}
    >
      <span className="sr-only">{label}</span>
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-200 ${
          enabled ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  </div>
);

interface SectionProps {
  title: string;
  children: React.ReactNode;
}

const Section: React.FC<SectionProps> = ({ title, children }) => (
  <div className="card">
    <h3 className="text-base font-semibold text-gray-900 mb-1">{title}</h3>
    <div className="divide-y divide-gray-100">{children}</div>
  </div>
);

// ---------------------------------------------------------------------------
// Settings page
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsState>({
    notifications: true,
    autoScan: false,
    reportFormat: 'pdf',
    theme: 'light',
    apiKey: '',
  });
  const [saved, setSaved] = useState(false);

  const update = <K extends keyof SettingsState>(
    key: K,
    value: SettingsState[K]
  ) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: persist via saveSettings(settings) from services/api.ts
    setSaved(true);
  };

  return (
    <DashboardLayout pageTitle="Settings">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Page heading */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Settings</h2>
          <p className="text-sm text-gray-500 mt-1">
            Configure your CodeSentinel AI preferences.
          </p>
        </div>

        <form onSubmit={handleSave} className="space-y-6">
          {/* Notifications */}
          <Section title="Notifications">
            <Toggle
              id="notifications"
              label="Email notifications"
              description="Receive an email when a scan completes."
              enabled={settings.notifications}
              onChange={(v) => update('notifications', v)}
            />
            <Toggle
              id="autoScan"
              label="Auto-scan on upload"
              description="Automatically start analysis after file upload."
              enabled={settings.autoScan}
              onChange={(v) => update('autoScan', v)}
            />
          </Section>

          {/* Reports */}
          <Section title="Reports">
            <div className="py-4">
              <label
                htmlFor="reportFormat"
                className="text-sm font-medium text-gray-900"
              >
                Default report format
              </label>
              <p className="text-xs text-gray-500 mt-0.5 mb-3">
                Choose the format used when exporting scan reports.
              </p>
              <select
                id="reportFormat"
                value={settings.reportFormat}
                onChange={(e) =>
                  update('reportFormat', e.target.value as SettingsState['reportFormat'])
                }
                className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="pdf">PDF</option>
                <option value="json">JSON</option>
                <option value="csv">CSV</option>
              </select>
            </div>
          </Section>

          {/* Appearance */}
          <Section title="Appearance">
            <div className="py-4">
              <label
                htmlFor="theme"
                className="text-sm font-medium text-gray-900"
              >
                Theme
              </label>
              <p className="text-xs text-gray-500 mt-0.5 mb-3">
                Select the colour scheme for the dashboard.
              </p>
              <select
                id="theme"
                value={settings.theme}
                onChange={(e) =>
                  update('theme', e.target.value as SettingsState['theme'])
                }
                className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="system">System</option>
              </select>
            </div>
          </Section>

          {/* API */}
          <Section title="Backend API">
            <div className="py-4">
              <label
                htmlFor="apiKey"
                className="text-sm font-medium text-gray-900"
              >
                API Key
              </label>
              <p className="text-xs text-gray-500 mt-0.5 mb-3">
                Used to authenticate requests to the backend analysis engine.
              </p>
              <input
                id="apiKey"
                type="password"
                placeholder="Enter your API key"
                value={settings.apiKey}
                onChange={(e) => update('apiKey', e.target.value)}
                className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                autoComplete="off"
              />
            </div>
          </Section>

          {/* Save */}
          <div className="flex items-center gap-4">
            <button type="submit" className="btn-primary">
              Save settings
            </button>
            {saved && (
              <span className="flex items-center gap-1.5 text-sm text-green-600 font-medium">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                Saved!
              </span>
            )}
          </div>
        </form>
      </div>
    </DashboardLayout>
  );
}
