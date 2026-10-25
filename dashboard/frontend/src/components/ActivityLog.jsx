import React, { useState } from 'react';
import { 
  ScrollText, 
  Terminal, 
  CheckCircle2, 
  AlertTriangle, 
  Bot, 
  Boxes, 
  Search,
  Filter,
  ShieldAlert
} from 'lucide-react';

export default function ActivityLog({ logs }) {
  const [filterType, setFilterType] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const getLogBadge = (type) => {
    switch (type) {
      case 'spawn':
        return { label: 'SPAWN', bg: 'bg-sky-500/10 text-sky-400 border-sky-500/30', icon: Boxes };
      case 'detect':
        return { label: 'VISION', bg: 'bg-purple-500/10 text-purple-400 border-purple-500/30', icon: Bot };
      case 'pick':
        return { label: 'PICK', bg: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30', icon: Bot };
      case 'place':
        return { label: 'PLACE', bg: 'bg-blue-500/10 text-blue-400 border-blue-500/30', icon: Bot };
      case 'sorted':
        return { label: 'SORTED', bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30', icon: CheckCircle2 };
      case 'recovery':
        return { label: 'RECOVERY', bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30', icon: ShieldAlert };
      case 'warning':
        return { label: 'WARNING', bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30', icon: AlertTriangle };
      case 'error':
        return { label: 'ERROR', bg: 'bg-red-500/10 text-red-400 border-red-500/30', icon: AlertTriangle };
      default:
        return { label: 'SYSTEM', bg: 'bg-slate-700/20 text-slate-400 border-slate-700/40', icon: Terminal };
    }
  };

  const filteredLogs = logs.filter((log) => {
    const matchesType = filterType === 'all' || log.type === filterType;
    const matchesSearch =
      !searchQuery ||
      log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (log.details && JSON.stringify(log.details).toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesType && matchesSearch;
  });

  return (
    <div className="bg-industrial-900 border border-slate-800 rounded-xl p-5 flex flex-col h-full">
      {/* Header & Filter Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3.5 border-b border-slate-800 gap-3 shrink-0">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 rounded-lg bg-sky-500/10 border border-sky-500/20">
            <ScrollText className="w-4 h-4 text-sky-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white tracking-wide">
              Factory Activity Log
            </h3>
            <p className="text-[11px] text-slate-400 font-mono">
              Chronological Audit Trail (Last {logs.length} events)
            </p>
          </div>
        </div>

        {/* Filter bar */}
        <div className="flex items-center space-x-2">
          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search events..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-industrial-950 border border-slate-800 text-xs text-slate-200 pl-8 pr-2.5 py-1 rounded-lg focus:outline-none focus:border-sky-500 font-mono w-36 sm:w-44"
            />
          </div>

          {/* Type filter */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="bg-industrial-950 border border-slate-800 text-xs text-slate-300 px-2 py-1 rounded-lg focus:outline-none focus:border-sky-500 font-mono"
          >
            <option value="all">All Events</option>
            <option value="spawn">Spawns</option>
            <option value="detect">Vision</option>
            <option value="pick">Picks</option>
            <option value="place">Placements</option>
            <option value="sorted">Sorted</option>
            <option value="recovery">Recoveries</option>
            <option value="error">Errors</option>
          </select>
        </div>
      </div>

      {/* Log Entries Stream */}
      <div className="mt-3 overflow-y-auto space-y-1.5 pr-1 max-h-[360px] font-mono text-xs">
        {filteredLogs.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-xs">
            No events matching filter criteria.
          </div>
        ) : (
          filteredLogs.map((log) => {
            const badge = getLogBadge(log.type);
            const Icon = badge.icon;
            return (
              <div
                key={log.id}
                className="flex items-start space-x-3 p-2 rounded-lg bg-industrial-950/70 border border-slate-800/80 hover:border-slate-700/80 transition"
              >
                {/* Timestamp */}
                <span className="text-slate-500 text-[11px] shrink-0 pt-0.5">
                  [{log.timestamp}]
                </span>

                {/* Badge */}
                <span
                  className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-semibold tracking-wider border shrink-0 ${badge.bg}`}
                >
                  <Icon className="w-2.5 h-2.5" />
                  {badge.label}
                </span>

                {/* Message & Details */}
                <div className="flex-1 min-w-0">
                  <span className="text-slate-200 text-xs leading-relaxed">
                    {log.message}
                  </span>
                  {log.details && Object.keys(log.details).length > 0 && (
                    <div className="text-[10px] text-slate-500 mt-0.5 truncate">
                      {JSON.stringify(log.details)}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
