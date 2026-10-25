import React, { useState } from 'react';
import { X, Sliders, Check, RotateCcw, Save } from 'lucide-react';

export default function SettingsModal({ isOpen, onClose, onSaveConfig }) {
  const [maxObjects, setMaxObjects] = useState(12);
  const [infeedSpeed, setInfeedSpeed] = useState(0.15);
  const [outputSpeed, setOutputSpeed] = useState(0.25);
  const [redDist, setRedDist] = useState(33);
  const [greenDist, setGreenDist] = useState(33);
  const [blueDist, setBlueDist] = useState(34);
  const [sequenceText, setSequenceText] = useState('');
  const [savedFeedback, setSavedFeedback] = useState(false);

  if (!isOpen) return null;

  const handleSave = () => {
    const totalDist = redDist + greenDist + blueDist || 100;
    const distribution = {
      red: redDist / totalDist,
      green: greenDist / totalDist,
      blue: blueDist / totalDist,
    };

    let sequence = null;
    if (sequenceText.trim()) {
      sequence = sequenceText
        .split(/[,\s]+/)
        .map((s) => s.trim().toLowerCase())
        .filter((s) => ['red', 'green', 'blue'].includes(s));
    }

    onSaveConfig({
      max_objects: parseInt(maxObjects, 10),
      input_conveyor_vel: parseFloat(infeedSpeed),
      output_conveyor_vel: parseFloat(outputSpeed),
      color_distribution: distribution,
      color_sequence: sequence && sequence.length > 0 ? sequence : null,
    });

    setSavedFeedback(true);
    setTimeout(() => {
      setSavedFeedback(false);
      onClose();
    }, 600);
  };

  const handleResetDefaults = () => {
    setMaxObjects(12);
    setInfeedSpeed(0.15);
    setOutputSpeed(0.25);
    setRedDist(33);
    setGreenDist(33);
    setBlueDist(34);
    setSequenceText('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-industrial-900 border border-slate-700 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-5 text-slate-100">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/20">
              <Sliders className="w-5 h-5 text-sky-400" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-wide">
                Factory Cell Configuration
              </h2>
              <p className="text-xs text-slate-400 font-mono">
                CoppeliaSim Spawner & Velocity Parameters
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <div className="space-y-4 text-xs font-mono">
          {/* Max Objects */}
          <div className="bg-industrial-950 p-3.5 rounded-xl border border-slate-800 space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-slate-300 font-semibold uppercase text-[11px]">
                Maximum Dynamic Blocks
              </label>
              <span className="text-sky-400 font-bold text-sm">{maxObjects} blocks</span>
            </div>
            <input
              type="range"
              min="1"
              max="50"
              value={maxObjects}
              onChange={(e) => setMaxObjects(e.target.value)}
              className="w-full accent-sky-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>1 (Single)</span>
              <span>12 (Stress Default)</span>
              <span>50 (High-Volume)</span>
            </div>
          </div>

          {/* Conveyor Velocities */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-industrial-950 p-3 rounded-xl border border-slate-800 space-y-1.5">
              <label className="text-slate-400 text-[10px] uppercase font-semibold">
                Infeed Conveyor
              </label>
              <div className="flex items-center space-x-1.5">
                <input
                  type="number"
                  step="0.05"
                  min="0.05"
                  max="0.50"
                  value={infeedSpeed}
                  onChange={(e) => setInfeedSpeed(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 px-2 py-1.5 rounded text-white font-mono focus:border-sky-500"
                />
                <span className="text-slate-500 text-[10px]">m/s</span>
              </div>
            </div>

            <div className="bg-industrial-950 p-3 rounded-xl border border-slate-800 space-y-1.5">
              <label className="text-slate-400 text-[10px] uppercase font-semibold">
                Discharge Conveyors
              </label>
              <div className="flex items-center space-x-1.5">
                <input
                  type="number"
                  step="0.05"
                  min="0.05"
                  max="0.60"
                  value={outputSpeed}
                  onChange={(e) => setOutputSpeed(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 px-2 py-1.5 rounded text-white font-mono focus:border-sky-500"
                />
                <span className="text-slate-500 text-[10px]">m/s</span>
              </div>
            </div>
          </div>

          {/* Color Distribution */}
          <div className="bg-industrial-950 p-3.5 rounded-xl border border-slate-800 space-y-2.5">
            <label className="text-slate-300 font-semibold uppercase text-[11px] block">
              Dynamic Color Distribution Weights (%)
            </label>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <span className="text-[10px] text-red-400 block mb-1">Red</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={redDist}
                  onChange={(e) => setRedDist(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-red-500/30 px-2 py-1 rounded text-red-300 text-center font-mono"
                />
              </div>
              <div>
                <span className="text-[10px] text-emerald-400 block mb-1">Green</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={greenDist}
                  onChange={(e) => setGreenDist(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-emerald-500/30 px-2 py-1 rounded text-emerald-300 text-center font-mono"
                />
              </div>
              <div>
                <span className="text-[10px] text-sky-400 block mb-1">Blue</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={blueDist}
                  onChange={(e) => setBlueDist(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-sky-500/30 px-2 py-1 rounded text-sky-300 text-center font-mono"
                />
              </div>
            </div>
          </div>

          {/* Custom Sequence Override */}
          <div className="bg-industrial-950 p-3 rounded-xl border border-slate-800 space-y-1.5">
            <label className="text-slate-400 text-[10px] uppercase font-semibold">
              Optional Color Sequence Override (Comma-separated)
            </label>
            <input
              type="text"
              placeholder="e.g. red, green, blue, blue, red"
              value={sequenceText}
              onChange={(e) => setSequenceText(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 px-2.5 py-1.5 rounded text-slate-200 font-mono text-xs focus:border-sky-500"
            />
            <p className="text-[10px] text-slate-500">
              Leave blank to use weighted dynamic selection.
            </p>
          </div>
        </div>

        {/* Footer Buttons */}
        <div className="flex items-center justify-between pt-3 border-t border-slate-800">
          <button
            onClick={handleResetDefaults}
            className="flex items-center space-x-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Defaults</span>
          </button>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className={`flex items-center space-x-1.5 px-4 py-2 rounded-lg text-xs font-semibold text-white transition shadow-sm ${
                savedFeedback ? 'bg-emerald-600' : 'bg-sky-600 hover:bg-sky-500'
              }`}
            >
              {savedFeedback ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
              <span>{savedFeedback ? 'Saved!' : 'Apply Configuration'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
