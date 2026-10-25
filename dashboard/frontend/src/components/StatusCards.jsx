import React from 'react';
import { 
  Boxes, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Gauge, 
  Layers, 
  ArrowUpRight,
  TrendingUp
} from 'lucide-react';

export default function StatusCards({ stats }) {
  const cards = [
    {
      title: 'Total Spawned',
      value: stats.total_spawned,
      unit: 'blocks',
      icon: Boxes,
      color: 'text-sky-400',
      bgColor: 'bg-sky-500/10 border-sky-500/20',
      badge: 'Infeed',
    },
    {
      title: 'Successfully Sorted',
      value: stats.total_sorted,
      unit: `(${stats.success_rate.toFixed(1)}%)`,
      icon: CheckCircle2,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10 border-emerald-500/20',
      badge: 'Bin Verified',
    },
    {
      title: 'Sorting Failures',
      value: stats.total_failed,
      unit: 'exceptions',
      icon: AlertTriangle,
      color: stats.total_failed > 0 ? 'text-red-400' : 'text-slate-400',
      bgColor: stats.total_failed > 0 ? 'bg-red-500/10 border-red-500/20' : 'bg-slate-800/40 border-slate-700/50',
      badge: 'Faults',
    },
    {
      title: 'Queue Pending',
      value: stats.pending_objects,
      unit: 'in transit',
      icon: Layers,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10 border-amber-500/20',
      badge: 'Belt Buffer',
    },
    {
      title: 'Avg Cycle Time',
      value: stats.avg_cycle_time_s.toFixed(2),
      unit: 'sec / block',
      icon: Clock,
      color: 'text-indigo-400',
      bgColor: 'bg-indigo-500/10 border-indigo-500/20',
      badge: 'Kinematics',
    },
    {
      title: 'System Throughput',
      value: stats.throughput_bpm.toFixed(1),
      unit: 'blocks / min',
      icon: Gauge,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10 border-purple-500/20',
      badge: 'Real-time',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3.5">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className="bg-industrial-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between hover:border-slate-700 transition relative overflow-hidden group"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                {card.title}
              </span>
              <div className={`p-1.5 rounded-lg border ${card.bgColor}`}>
                <Icon className={`w-3.5 h-3.5 ${card.color}`} />
              </div>
            </div>

            <div className="mt-3 flex items-baseline space-x-1.5">
              <span className="text-2xl font-bold font-mono text-white tracking-tight">
                {card.value}
              </span>
              <span className="text-xs text-slate-400 font-mono">
                {card.unit}
              </span>
            </div>

            <div className="mt-2.5 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px]">
              <span className="text-slate-400 font-medium">Status</span>
              <span className="text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded font-mono border border-slate-700/60">
                {card.badge}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
