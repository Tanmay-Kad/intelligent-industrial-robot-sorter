import React, { useState } from 'react';
import { useFactorySocket } from './hooks/useFactorySocket';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import StatusCards from './components/StatusCards';
import LiveCamera from './components/LiveCamera';
import SortingAnalytics from './components/SortingAnalytics';
import ActivityLog from './components/ActivityLog';
import SettingsModal from './components/SettingsModal';
import { AlertTriangle, WifiOff, X } from 'lucide-react';

export default function App() {
  const [currentTab, setCurrentTab] = useState('overview');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const {
    connected,
    stats,
    vision,
    logs,
    loadingAction,
    errorMsg,
    startSorting,
    pauseSorting,
    resumeSorting,
    stopSorting,
    resetFactory,
    updateConfig,
  } = useFactorySocket();

  return (
    <div className="flex h-screen w-screen bg-industrial-950 text-slate-100 overflow-hidden font-sans">
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        stats={stats}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar Controls */}
        <Topbar
          stats={stats}
          loadingAction={loadingAction}
          onStart={() => startSorting()}
          onPause={pauseSorting}
          onResume={resumeSorting}
          onStop={stopSorting}
          onReset={resetFactory}
        />

        {/* Global Error Notice */}
        {errorMsg && (
          <div className="bg-red-500/10 border-b border-red-500/30 px-6 py-2 flex items-center justify-between text-xs text-red-400">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          </div>
        )}

        {/* Disconnected Simulator Banner */}
        {!stats.connected && (
          <div className="bg-amber-500/10 border-b border-amber-500/30 px-6 py-2 flex items-center space-x-2 text-xs text-amber-300">
            <WifiOff className="w-4 h-4 shrink-0" />
            <span>CoppeliaSim ZeroMQ server offline. Please ensure CoppeliaSim is running with ZeroMQ Remote API on port 23000.</span>
          </div>
        )}

        {/* Scrollable Dashboard View */}
        <main className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Top Status Metric Cards */}
          <StatusCards stats={stats} />

          {/* Tab View: Overview */}
          {currentTab === 'overview' && (
            <div className="space-y-5">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <LiveCamera vision={vision} />
                <SortingAnalytics stats={stats} />
              </div>

              <div className="h-[400px]">
                <ActivityLog logs={logs} />
              </div>
            </div>
          )}

          {/* Tab View: Live Camera Only */}
          {currentTab === 'camera' && (
            <div className="max-w-4xl mx-auto">
              <LiveCamera vision={vision} />
            </div>
          )}

          {/* Tab View: Sorting Analytics Only */}
          {currentTab === 'analytics' && (
            <div className="max-w-5xl mx-auto space-y-5">
              <SortingAnalytics stats={stats} />
            </div>
          )}

          {/* Tab View: Activity Log Only */}
          {currentTab === 'logs' && (
            <div className="h-[calc(100vh-220px)]">
              <ActivityLog logs={logs} />
            </div>
          )}
        </main>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSaveConfig={updateConfig}
      />
    </div>
  );
}
