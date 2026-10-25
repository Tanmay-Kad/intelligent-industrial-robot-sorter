import React from 'react';
import { 
  Bot, 
  Layers, 
  Camera, 
  BarChart3, 
  ScrollText, 
  Sliders, 
  Cpu, 
  Wifi, 
  WifiOff, 
  ShieldCheck, 
  Boxes 
} from 'lucide-react';

export default function Sidebar({ currentTab, setCurrentTab, stats, onOpenSettings }) {
  const navItems = [
    { id: 'overview', label: 'Factory Overview', icon: Layers },
    { id: 'camera', label: 'Live Camera', icon: Camera },
    { id: 'analytics', label: 'Sorting Analytics', icon: BarChart3 },
    { id: 'logs', label: 'Activity Log', icon: ScrollText },
  ];

  return (
    <aside className="w-64 bg-industrial-900 border-r border-slate-800 flex flex-col justify-between shrink-0">
      <div>
        {/* Branding */}
        <div className="p-5 border-b border-slate-800 flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-neon-blue">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-wide flex items-center gap-1.5">
              INDUCTO<span className="text-sky-400 font-black">SORT</span>
            </h1>
            <p className="text-[10px] text-slate-400 uppercase tracking-widest font-mono">
              Industrial Cell v1.0
            </p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentTab(item.id)}
                className={`w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  active
                    ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? 'text-sky-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Hardware Connection Status */}
      <div className="p-4 border-t border-slate-800 space-y-3">
        <div className="bg-industrial-950/80 rounded-lg p-3 border border-slate-800/80 space-y-2">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
            <span>Cell Hardware</span>
            <span className="text-[10px] text-slate-400 font-mono">Port 23000</span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-300 flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-slate-400" />
              CoppeliaSim
            </span>
            <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold ${
              stats.connected 
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                : 'bg-red-500/10 text-red-400 border border-red-500/20'
            }`}>
              {stats.connected ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-300 flex items-center gap-1.5">
              {stats.connected ? <Wifi className="w-3.5 h-3.5 text-sky-400" /> : <WifiOff className="w-3.5 h-3.5 text-red-400" />}
              ZeroMQ Remote API
            </span>
            <span className="text-slate-400 text-[10px] font-mono">4.10.0</span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-300 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
              Robot Arm
            </span>
            <span className="text-indigo-400 text-[10px] font-mono">UR5 + RG2</span>
          </div>
        </div>

        {/* Settings button */}
        <button
          onClick={onOpenSettings}
          className="w-full flex items-center justify-center space-x-2 px-3 py-2 bg-slate-800 hover:bg-slate-700/80 text-slate-300 rounded-lg text-xs font-medium border border-slate-700 transition"
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>Factory Configuration</span>
        </button>
      </div>
    </aside>
  );
}
