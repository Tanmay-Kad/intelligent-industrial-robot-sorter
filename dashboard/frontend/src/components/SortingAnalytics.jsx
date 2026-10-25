import React from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  Cell,
  PieChart,
  Pie
} from 'recharts';
import { BarChart2, PieChart as PieIcon, CheckCircle, PackageCheck, ShieldCheck } from 'lucide-react';

export default function SortingAnalytics({ stats }) {
  const redCount = stats.color_counts?.red || 0;
  const greenCount = stats.color_counts?.green || 0;
  const blueCount = stats.color_counts?.blue || 0;
  const totalCount = redCount + greenCount + blueCount || 1;

  const barData = [
    { name: 'Red', count: redCount, color: '#ef4444', bin: 'Red Bin (+Y)' },
    { name: 'Green', count: greenCount, color: '#10b981', bin: 'Green Bin (+X)' },
    { name: 'Blue', count: blueCount, color: '#3b82f6', bin: 'Blue Bin (-Y)' },
  ];

  const pieData = [
    { name: 'Red', value: redCount, color: '#ef4444' },
    { name: 'Green', value: greenCount, color: '#10b981' },
    { name: 'Blue', value: blueCount, color: '#3b82f6' },
  ].filter(d => d.value > 0);

  const binContainment = [
    {
      name: 'RedCollectionBin',
      axis: 'North (+Y)',
      color: 'text-red-400',
      bgColor: 'bg-red-500/10 border-red-500/20',
      count: redCount,
      targetCoord: '[0.00, +1.52, 0.46]m',
      status: 'VERIFIED CONTAINED',
    },
    {
      name: 'GreenCollectionBin',
      axis: 'East (+X)',
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10 border-emerald-500/20',
      count: greenCount,
      targetCoord: '[+1.52, 0.00, 0.46]m',
      status: 'VERIFIED CONTAINED',
    },
    {
      name: 'BlueCollectionBin',
      axis: 'South (-Y)',
      color: 'text-sky-400',
      bgColor: 'bg-sky-500/10 border-sky-500/20',
      count: blueCount,
      targetCoord: '[0.00, -1.52, 0.46]m',
      status: 'VERIFIED CONTAINED',
    },
  ];

  return (
    <div className="bg-industrial-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 border-b border-slate-800">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
            <BarChart2 className="w-4 h-4 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white tracking-wide">
              Sorting Analytics & Distribution
            </h3>
            <p className="text-[11px] text-slate-400 font-mono">
              Live Color Breakdown & Bin Verification
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-1.5 text-xs text-slate-400 font-mono">
          <PackageCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>Total: <strong className="text-white">{stats.total_sorted}</strong></span>
        </div>
      </div>

      {/* Chart Section */}
      <div className="my-4 grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
        {/* Bar Chart */}
        <div className="md:col-span-2 h-44 bg-industrial-950/60 rounded-lg p-2.5 border border-slate-800/80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={barData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
              <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} allowDecimals={false} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '0.5rem',
                  fontSize: '11px',
                  color: '#f8fafc',
                }}
                formatter={(val, name, props) => [`${val} blocks (${props.payload.bin})`, 'Count']}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={45}>
                {barData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Distribution Ratios */}
        <div className="space-y-2 bg-industrial-950/60 p-3 rounded-lg border border-slate-800/80 text-xs font-mono">
          <div className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider pb-1 border-b border-slate-800">
            Color Breakdown
          </div>

          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-red-400">
              <span className="w-2 h-2 rounded-full bg-red-500"></span>
              Red
            </span>
            <span className="text-slate-200 font-bold">
              {redCount} <span className="text-slate-500 text-[10px]">({((redCount / totalCount) * 100).toFixed(0)}%)</span>
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              Green
            </span>
            <span className="text-slate-200 font-bold">
              {greenCount} <span className="text-slate-500 text-[10px]">({((greenCount / totalCount) * 100).toFixed(0)}%)</span>
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-sky-400">
              <span className="w-2 h-2 rounded-full bg-sky-500"></span>
              Blue
            </span>
            <span className="text-slate-200 font-bold">
              {blueCount} <span className="text-slate-500 text-[10px]">({((blueCount / totalCount) * 100).toFixed(0)}%)</span>
            </span>
          </div>

          <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px]">
            <span className="text-slate-400">Success Rate</span>
            <span className="text-emerald-400 font-bold">{stats.success_rate.toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {/* Bin Containment Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 pt-1">
        {binContainment.map((bin, i) => (
          <div key={i} className={`p-2.5 rounded-lg border ${bin.bgColor} space-y-1`}>
            <div className="flex items-center justify-between text-xs">
              <span className={`font-semibold ${bin.color} font-mono text-[11px]`}>
                {bin.name}
              </span>
              <span className="text-slate-300 font-bold font-mono text-xs">
                {bin.count}
              </span>
            </div>
            <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
              <span>{bin.axis}</span>
              <span>{bin.targetCoord}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
