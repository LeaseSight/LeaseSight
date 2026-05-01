'use client';

import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { api } from '@/lib/api';
import { GraphData } from '@/lib/types';
import { BenchmarkGauge } from './BenchmarkGauge';
import dynamic from 'next/dynamic';

// Dynamically import Plotly to avoid SSR issues and bundle size bloat on initial load
const Plot = dynamic(() => import('react-plotly.js'), { 
  ssr: false, 
  loading: () => <div className="flex-1 flex items-center justify-center text-xs" style={{ color: 'var(--text-secondary)' }}><div className="w-4 h-4 border-2 border-[var(--text-secondary)] border-t-transparent rounded-full animate-spin mr-2" />Loading Plotly Engine...</div> 
});

interface NetworkPanelProps {
  selectedDoc: string;
  onClose: () => void;
  isCommitted?: boolean;
  query?: string;
}

export function NetworkPanel({ selectedDoc, onClose, isCommitted, query }: NetworkPanelProps) {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'heatmap' | 'plotly3d' | 'plotly2d'>('plotly3d');

  useEffect(() => {
    setLoading(true);
    if (query) {
      api.queryAnalytics(query, selectedDoc)
        .then(setGraphData)
        .catch(() => setGraphData(null))
        .finally(() => setLoading(false));
      setActiveTab('plotly3d'); // Default to 3D when query changes
    } else {
      api.graphData(selectedDoc)
        .then(setGraphData)
        .catch(() => setGraphData(null))
        .finally(() => setLoading(false));
    }
  }, [selectedDoc, query]);

  const getPlotData = () => {
    if (!graphData?.sufficient) return [];

    const is2D = activeTab === 'plotly2d';

    const archiveTrace: any = {
      x: graphData.archive_coords.map(c => c[0]),
      y: graphData.archive_coords.map(c => c[1]),
      z: is2D ? undefined : graphData.archive_coords.map(c => c[2]),
      text: graphData.names,
      mode: 'markers',
      type: is2D ? 'scatter' : 'scatter3d',
      name: query ? 'Document Chunks' : 'Archive',
      marker: {
        color: query ? 'rgba(59, 130, 246, 0.6)' : 'rgba(203, 213, 225, 0.6)', // Blue for query chunks, slate for archive
        size: is2D ? 10 : 6,
        line: { color: query ? 'rgba(29, 78, 216, 0.8)' : 'rgba(100, 116, 139, 0.8)', width: 1 }
      }
    };

    const newTrace: any = {
      x: [graphData.new_coords[0]],
      y: [graphData.new_coords[1]],
      z: is2D ? undefined : [graphData.new_coords[2]],
      text: [query ? '⭐ YOUR QUERY' : (isCommitted ? 'Current Lease (Archived)' : 'Current Document')],
      mode: 'markers+text',
      type: is2D ? 'scatter' : 'scatter3d',
      name: query ? 'User Query' : 'Current Doc',
      textposition: 'top center',
      marker: {
        color: query ? '#facc15' : (isCommitted ? '#64748b' : '#9333ea'),
        symbol: 'diamond',
        size: is2D ? 16 : 10,
        line: { color: '#ffffff', width: 2 }
      },
      textfont: { color: query ? '#eab308' : (isCommitted ? '#64748b' : '#9333ea'), size: 11, family: 'Inter', weight: 'bold' }
    };

    return [archiveTrace, newTrace];
  };

  const layout: any = {
    margin: { l: 0, r: 0, b: 0, t: 0 },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { color: '#94a3b8', family: 'Inter' },
    showlegend: true,
    legend: { x: 0.02, y: 0.95, font: { size: 10 }, bgcolor: 'rgba(15, 23, 42, 0.5)' },
    scene: activeTab === 'plotly3d' ? {
      xaxis: { showgrid: true, gridcolor: '#334155', zeroline: false, showticklabels: false, backgroundcolor: 'transparent' },
      yaxis: { showgrid: true, gridcolor: '#334155', zeroline: false, showticklabels: false, backgroundcolor: 'transparent' },
      zaxis: { showgrid: true, gridcolor: '#334155', zeroline: false, showticklabels: false, backgroundcolor: 'transparent' },
      camera: { eye: { x: 1.2, y: 1.2, z: 1.2 } }
    } : undefined,
    xaxis: activeTab === 'plotly2d' ? { showgrid: true, gridcolor: '#334155', zeroline: false, showticklabels: false } : undefined,
    yaxis: activeTab === 'plotly2d' ? { showgrid: true, gridcolor: '#334155', zeroline: false, showticklabels: false } : undefined,
  };

  return (
    <div className="h-[300px] border-t flex flex-col"
         style={{ borderColor: 'var(--border-default)', background: 'var(--bg-secondary)' }}>
      {/* Panel Header */}
      <div className="h-10 flex items-center justify-between px-4 border-b shrink-0"
           style={{ borderColor: 'var(--border-default)' }}>
        <div className="flex items-center gap-4 h-full">
          <button
            onClick={() => setActiveTab('heatmap')}
            className={`h-full px-2 text-xs font-medium border-b-2 transition-colors ${activeTab === 'heatmap' ? 'border-[var(--accent-primary)] text-[var(--accent-primary)]' : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
          >
            🎯 Internal Heatmap
          </button>
          
          <button
            onClick={() => setActiveTab('plotly3d')}
            className={`h-full px-2 text-xs font-medium border-b-2 transition-colors ${activeTab === 'plotly3d' ? 'border-[var(--accent-primary)] text-[var(--accent-primary)]' : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
          >
            {query ? '🔭 3D Query Correlation' : '🌐 3D Database Context'}
          </button>

          <button
            onClick={() => setActiveTab('plotly2d')}
            className={`h-full px-2 text-xs font-medium border-b-2 transition-colors ${activeTab === 'plotly2d' ? 'border-[var(--accent-primary)] text-[var(--accent-primary)]' : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
          >
            {query ? '📐 2D Precision Mode' : '📐 2D Archive Mode'}
          </button>
        </div>
        
        <div className="flex items-center gap-6">
          {graphData?.benchmark_score !== undefined && !query && (
            <div className="py-1">
              <BenchmarkGauge score={graphData.benchmark_score} />
            </div>
          )}
          <button onClick={onClose} className="hover:opacity-70">
            <X className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 relative bg-slate-900/50">
        {loading ? (
          <div className="w-full h-full flex items-center justify-center text-xs" style={{ color: 'var(--text-secondary)' }}>
            <div className="w-4 h-4 border-2 border-[var(--text-secondary)] border-t-transparent rounded-full animate-spin mr-2" />
            Loading vector analytics...
          </div>
        ) : activeTab === 'heatmap' ? (
          <div className="w-full h-full p-4 overflow-y-auto">
            {graphData?.internal_similarities && graphData.internal_similarities.length > 0 ? (
              <div>
                <h4 className="text-xs font-semibold mb-3" style={{ color: 'var(--text-secondary)' }}>Internal Document Relevance</h4>
                <div className="grid grid-cols-[repeat(auto-fit,minmax(28px,1fr))] gap-1.5">
                  {graphData.internal_similarities.map((score, i) => {
                    const normalized = Math.max(0, Math.min(1, score));
                    return (
                      <div key={i} 
                           className="aspect-square rounded flex items-center justify-center group relative cursor-pointer"
                           style={{ 
                             backgroundColor: `rgba(16, 185, 129, ${0.1 + normalized * 0.9})`,
                             border: '1px solid rgba(16, 185, 129, 0.2)' 
                           }}>
                        <span className="text-[10px] font-medium opacity-50 group-hover:opacity-100 transition-opacity mix-blend-multiply">
                          {i + 1}
                        </span>
                        <div className="absolute -top-8 left-1/2 -translate-x-1/2 shadow-sm px-2 py-1 rounded text-[10px] opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10"
                             style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)', color: 'var(--text-primary)' }}>
                          Chunk {i + 1}: {(score * 100).toFixed(1)}%
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
               <p className="text-xs text-center mt-10" style={{ color: 'var(--text-secondary)' }}>No internal similarity data available.</p>
            )}
          </div>
        ) : (
          !graphData?.sufficient ? (
            <div className="w-full h-full flex items-center justify-center">
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Not enough vectors mapped to generate Plotly space.
              </p>
            </div>
          ) : (
            <div className="w-full h-full">
              <Plot
                data={getPlotData()}
                layout={layout}
                useResizeHandler={true}
                style={{ width: '100%', height: '100%' }}
                config={{ displayModeBar: false }}
              />
            </div>
          )
        )}
      </div>
    </div>
  );
}
