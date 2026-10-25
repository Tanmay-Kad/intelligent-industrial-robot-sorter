import React from 'react';
import { Camera, Radio, Crosshair, Box, Sparkles, AlertCircle } from 'lucide-react';

export default function LiveCamera({ vision }) {
  const getColorBadge = (color) => {
    switch (color?.toLowerCase()) {
      case 'red':
        return {
          label: 'RED OBJECT',
          bg: 'bg-red-500/10 border-red-500/30 text-red-400',
          dot: 'bg-red-500 shadow-neon-red',
          conveyor: 'OutputConveyorRed',
          bin: 'RedCollectionBin (+Y)',
        };
      case 'green':
        return {
          label: 'GREEN OBJECT',
          bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
          dot: 'bg-emerald-500 shadow-neon-green',
          conveyor: 'OutputConveyorGreen',
          bin: 'GreenCollectionBin (+X)',
        };
      case 'blue':
        return {
          label: 'BLUE OBJECT',
          bg: 'bg-sky-500/10 border-sky-500/30 text-sky-400',
          dot: 'bg-sky-500 shadow-neon-blue',
          conveyor: 'OutputConveyorBlue',
          bin: 'BlueCollectionBin (-Y)',
        };
      default:
        return {
          label: 'EMPTY INSPECTION ZONE',
          bg: 'bg-slate-800/40 border-slate-700/40 text-slate-400',
          dot: 'bg-slate-500',
          conveyor: 'None (Standby)',
          bin: 'None',
        };
    }
  };

  const badgeInfo = getColorBadge(vision.color);

  return (
    <div className="bg-industrial-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 border-b border-slate-800">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 rounded-lg bg-sky-500/10 border border-sky-500/20">
            <Camera className="w-4 h-4 text-sky-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white tracking-wide">
              Live Inspection Camera
            </h3>
            <p className="text-[11px] text-slate-400 font-mono">
              /InspectionCamera (Overhead FOV 45°)
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <span className="flex h-2.5 w-2.5 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
          <span className="text-[11px] font-mono text-emerald-400 font-semibold uppercase tracking-wider">
            STREAMING (10Hz)
          </span>
        </div>
      </div>

      {/* Camera Viewport & Overlay */}
      <div className="my-4 relative bg-black/90 rounded-lg border border-slate-800 overflow-hidden flex items-center justify-center aspect-square max-h-[300px] mx-auto w-full group shadow-inner">
        {vision.image_base64 ? (
          <img
            src={`data:image/jpeg;base64,${vision.image_base64}`}
            alt="Live /InspectionCamera Stream"
            className="w-full h-full object-contain image-rendering-pixelated"
          />
        ) : (
          <div className="flex flex-col items-center justify-center p-8 text-center space-y-2">
            <Radio className="w-8 h-8 text-slate-600 animate-pulse" />
            <p className="text-xs text-slate-400 font-mono">
              Acquiring frame from CoppeliaSim vision sensor...
            </p>
          </div>
        )}

        {/* Optical HUD Grid Overlay */}
        <div className="absolute inset-0 pointer-events-none border border-sky-500/10 grid grid-cols-2 grid-rows-2">
          <div className="border-r border-b border-sky-500/10"></div>
          <div className="border-b border-sky-500/10"></div>
          <div className="border-r border-sky-500/10"></div>
          <div></div>
        </div>

        {/* Corner Viewport Reticles */}
        <div className="absolute top-2 left-2 text-[9px] font-mono text-sky-400/60 bg-black/40 px-1 rounded">
          ROI: [50, 20, 92, 110]
        </div>
        <div className="absolute bottom-2 right-2 text-[9px] font-mono text-slate-400 bg-black/60 px-1 rounded">
          128 x 128 px
        </div>
      </div>

      {/* Detection Telemetry Metadata */}
      <div className="space-y-2.5 bg-industrial-950/70 p-3.5 rounded-lg border border-slate-800/80">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className={`w-2.5 h-2.5 rounded-full ${badgeInfo.dot}`}></span>
            <span className="text-xs font-semibold tracking-wider font-mono text-white">
              {badgeInfo.label}
            </span>
          </div>
          <span className="text-xs font-mono font-bold text-sky-400">
            {vision.confidence ? `${(vision.confidence * 100).toFixed(1)}% CONF` : '0.0%'}
          </span>
        </div>

        {/* Confidence Meter Bar */}
        <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              vision.color === 'red'
                ? 'bg-red-500'
                : vision.color === 'green'
                ? 'bg-emerald-500'
                : vision.color === 'blue'
                ? 'bg-sky-500'
                : 'bg-slate-600'
            }`}
            style={{ width: `${Math.min(100, (vision.confidence || 0) * 100)}%` }}
          ></div>
        </div>

        {/* Geometry & Routing Grid */}
        <div className="grid grid-cols-2 gap-2 pt-1 text-[11px] font-mono">
          <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
            <span className="text-slate-400 block text-[10px] uppercase">Bounding Box</span>
            <span className="text-slate-200">
              {vision.bbox ? `[${vision.bbox.join(', ')}]` : 'No object'}
            </span>
          </div>

          <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
            <span className="text-slate-400 block text-[10px] uppercase">Centroid / Area</span>
            <span className="text-slate-200">
              {vision.center ? `(${vision.center[0]}, ${vision.center[1]}) / ${vision.contour_area}px` : '--'}
            </span>
          </div>

          <div className="bg-slate-900/60 p-2 rounded border border-slate-800 col-span-2 flex items-center justify-between">
            <span className="text-slate-400 text-[10px] uppercase">Destination Route</span>
            <span className="text-sky-300 font-semibold">
              {badgeInfo.conveyor} &rarr; {badgeInfo.bin}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
