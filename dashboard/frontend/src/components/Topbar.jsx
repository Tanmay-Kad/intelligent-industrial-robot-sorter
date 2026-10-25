import React from 'react';
import { 
  Play, 
  Pause, 
  Square, 
  RotateCcw, 
  Activity, 
  Clock, 
  AlertCircle,
  CheckCircle2,
  Cpu
} from 'lucide-react';

export default function Topbar({ 
  stats, 
  loadingAction, 
  onStart, 
  onPause, 
  onResume, 
  onStop, 
  onReset 
}) {
  const getStatusBadge = () => {
    switch (stats.factory_state) {
      case 'RUNNING':
        return (
          <div className="flex items-center space-x-2 px-3 py-1 bg-emerald-500/10 border border-emerald-500/30 rounded-full text-emerald-400 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>SYSTEM ACTIVE (RUNNING)</span>
          </div>
        );
      case 'PAUSED':
        return (
          <div className="flex items-center space-x-2 px-3 py-1 bg-amber-500/10 border border-amber-500/30 rounded-full text-amber-400 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-amber-400"></span>
            <span>SYSTEM PAUSED</span>
          </div>
        );
      case 'STOPPED':
        return (
          <div className="flex items-center space-x-2 px-3 py-1 bg-slate-700/30 border border-slate-700 rounded-full text-slate-400 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-slate-500"></span>
            <span>CELL STOPPED</span>
          </div>
        );
      case 'ERROR':
        return (
          <div className="flex items-center space-x-2 px-3 py-1 bg-red-500/10 border border-red-500/30 rounded-full text-red-400 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-red-400 animate-ping"></span>
            <span>FAULT DETECTED</span>
          </div>
        );
      default:
        return (
          <div className="flex items-center space-x-2 px-3 py-1 bg-sky-500/10 border border-sky-500/30 rounded-full text-sky-400 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-sky-400"></span>
            <span>SYSTEM READY</span>
          </div>
        );
    }
  };

  const formatUptime = (sec) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <header className="h-16 bg-industrial-900 border-b border-slate-800 px-6 flex items-center justify-between shrink-0">
      {/* State & Operation Banner */}
      <div className="flex items-center space-x-4">
        {getStatusBadge()}

        <div className="hidden lg:flex items-center space-x-2 pl-3 border-l border-slate-800 text-xs text-slate-300">
          <Activity className="w-4 h-4 text-sky-400 animate-pulse" />
          <span className="text-slate-400">Current Task:</span>
          <span className="font-mono text-slate-100 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">
            {stats.current_operation}
          </span>
        </div>
      </div>

      {/* Control Actions & Clock */}
      <div className="flex items-center space-x-3">
        {/* Run Controls */}
        <div className="flex items-center bg-industrial-950 p-1 rounded-lg border border-slate-800 space-x-1">
          {stats.factory_state === 'PAUSED' ? (
            <button
              onClick={onResume}
              disabled={loadingAction !== null}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-medium transition disabled:opacity-50 shadow-sm"
              title="Resume sorting automation"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Resume</span>
            </button>
          ) : (
            <button
              onClick={onStart}
              disabled={stats.factory_state === 'RUNNING' || loadingAction !== null}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-medium transition shadow-sm ${
                stats.factory_state === 'RUNNING'
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                  : 'bg-sky-600 hover:bg-sky-500 text-white'
              }`}
              title="Start continuous sorting"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Start</span>
            </button>
          )}

          <button
            onClick={onPause}
            disabled={stats.factory_state !== 'RUNNING' || loadingAction !== null}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-medium transition ${
              stats.factory_state === 'RUNNING'
                ? 'bg-slate-800 hover:bg-amber-600 text-amber-300 hover:text-white'
                : 'bg-slate-800/50 text-slate-500 cursor-not-allowed'
            }`}
            title="Safe pause at cycle boundary"
          >
            <Pause className="w-3.5 h-3.5 fill-current" />
            <span>Pause</span>
          </button>

          <button
            onClick={onStop}
            disabled={stats.factory_state === 'STOPPED' || stats.factory_state === 'IDLE' || loadingAction !== null}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-medium transition ${
              stats.factory_state === 'RUNNING' || stats.factory_state === 'PAUSED'
                ? 'bg-slate-800 hover:bg-red-600 text-red-300 hover:text-white'
                : 'bg-slate-800/50 text-slate-500 cursor-not-allowed'
            }`}
            title="Safe stop (return arm home and stop conveyors)"
          >
            <Square className="w-3.5 h-3.5 fill-current" />
            <span>Stop</span>
          </button>

          <button
            onClick={onReset}
            disabled={loadingAction !== null}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded text-xs font-medium transition"
            title="Reset scene to clean baseline"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset</span>
          </button>
        </div>

        {/* Uptime Badge */}
        <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1.5 bg-slate-800/60 border border-slate-700/60 rounded text-xs text-slate-300 font-mono">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>{formatUptime(stats.uptime_seconds)}</span>
        </div>
      </div>
    </header>
  );
}
