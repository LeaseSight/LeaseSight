'use client';

import { useEffect, useState, useRef } from 'react';
import { X } from 'lucide-react';
import { api } from '@/lib/api';
import { GraphData } from '@/lib/types';
import { BenchmarkGauge } from './BenchmarkGauge';

interface NetworkPanelProps {
  selectedDoc: string;
  onClose: () => void;
  isCommitted?: boolean;
}

export function NetworkPanel({ selectedDoc, onClose, isCommitted }: NetworkPanelProps) {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'heatmap' | '3d'>('heatmap');
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [rotation, setRotation] = useState({ x: 0.3, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const lastMouse = useRef({ x: 0, y: 0 });

  useEffect(() => {
    setLoading(true);
    api.graphData(selectedDoc)
      .then(setGraphData)
      .catch(() => setGraphData(null))
      .finally(() => setLoading(false));
  }, [selectedDoc]);

  // 3D rendering with Canvas2D (lightweight, no Three.js dep issues)
  useEffect(() => {
    if (!canvasRef.current || !graphData?.sufficient) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    const cx = W / 2;
    const cy = H / 2;
    const scale = Math.min(W, H) * 0.3;

    // Rotation matrix (Y then X)
    const cosY = Math.cos(rotation.y);
    const sinY = Math.sin(rotation.y);
    const cosX = Math.cos(rotation.x);
    const sinX = Math.sin(rotation.x);

    const project = (p: number[]) => {
      // Rotate Y
      const x1 = p[0] * cosY - p[2] * sinY;
      const z1 = p[0] * sinY + p[2] * cosY;
      // Rotate X
      const y1 = p[1] * cosX - z1 * sinX;
      const z2 = p[1] * sinX + z1 * cosX;
      // Perspective
      const fov = 3;
      const s = fov / (fov + z2 * 0.5);
      return { x: cx + x1 * scale * s, y: cy + y1 * scale * s, z: z2, s };
    };

    // Clear
    ctx.fillStyle = '#f8fafc'; // Light background
    ctx.fillRect(0, 0, W, H);

    // Draw grid lines (subtle)
    ctx.strokeStyle = 'rgba(51, 65, 85, 0.15)';
    ctx.lineWidth = 0.5;
    for (let i = -2; i <= 2; i++) {
      const a = project([i, 0, -2]);
      const b = project([i, 0, 2]);
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      const c = project([-2, 0, i]);
      const d = project([2, 0, i]);
      ctx.beginPath(); ctx.moveTo(c.x, c.y); ctx.lineTo(d.x, d.y); ctx.stroke();
    }

    // Draw archive points
    const archiveProjected = graphData.archive_coords.map((p, i) => ({
      ...project(p), name: graphData.names[i], type: 'archive' as const
    }));
    const newProjected = { 
      ...project(graphData.new_coords), 
      name: isCommitted ? 'Current Lease (Archived)' : 'Current Document', 
      type: 'new' as const 
    };

    // Sort by z for painter's algorithm
    const allPoints = [...archiveProjected, newProjected].sort((a, b) => a.z - b.z);

    for (const pt of allPoints) {
      if (pt.type === 'archive') {
        const size = 3 * pt.s;
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(203, 213, 225, ${0.4 + pt.s * 0.3})`; // #cbd5e1 (Slate Grey)
        ctx.fill();
        ctx.strokeStyle = 'rgba(203, 213, 225, 0.8)';
        ctx.lineWidth = 0.5;
        ctx.stroke();
      } else {
        const size = 7 * pt.s;
        // Diamond shape
        ctx.beginPath();
        ctx.moveTo(pt.x, pt.y - size);
        ctx.lineTo(pt.x + size, pt.y);
        ctx.lineTo(pt.x, pt.y + size);
        ctx.lineTo(pt.x - size, pt.y);
        ctx.closePath();
        // If committed, color it Slate Grey (same as archive but solid) otherwise Lavender
        ctx.fillStyle = isCommitted ? '#64748b' : '#9333ea';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        // Label
        ctx.fillStyle = isCommitted ? '#64748b' : '#9333ea';
        ctx.font = '11px Inter, system-ui';
        ctx.textAlign = 'center';
        ctx.fillText(isCommitted ? '✅ VERIFIED ARCHIVE' : '📄 CURRENT', pt.x, pt.y - size - 6);
      }
    }

    // Legend
    ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
    ctx.fillRect(10, H - 50, 180, 40);
    ctx.strokeStyle = 'var(--border-default)';
    ctx.strokeRect(10, H - 50, 180, 40);

    ctx.beginPath(); ctx.arc(24, H - 35, 4, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(203, 213, 225, 0.8)'; ctx.fill();
    ctx.fillStyle = '#64748b'; ctx.font = '10px Inter'; ctx.textAlign = 'left';
    ctx.fillText(`Archive (${graphData.archive_coords.length})`, 34, H - 31);

    ctx.beginPath();
    ctx.moveTo(120, H - 39); ctx.lineTo(125, H - 35); ctx.lineTo(120, H - 31); ctx.lineTo(115, H - 35);
    ctx.closePath(); ctx.fillStyle = isCommitted ? '#64748b' : '#9333ea'; ctx.fill();
    ctx.fillStyle = '#64748b'; ctx.fillText(isCommitted ? 'Current (Archived)' : 'Current', 132, H - 31);

  }, [graphData, rotation, isCommitted]);

  // Mouse drag for rotation
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    lastMouse.current = { x: e.clientX, y: e.clientY };
  };
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    const dx = e.clientX - lastMouse.current.x;
    const dy = e.clientY - lastMouse.current.y;
    setRotation(r => ({ x: r.x + dy * 0.005, y: r.y + dx * 0.005 }));
    lastMouse.current = { x: e.clientX, y: e.clientY };
  };
  const handleMouseUp = () => setIsDragging(false);

  // Auto-rotate
  useEffect(() => {
    if (isDragging || !graphData?.sufficient) return;
    const interval = setInterval(() => {
      setRotation(r => ({ ...r, y: r.y + 0.003 }));
    }, 16);
    return () => clearInterval(interval);
  }, [isDragging, graphData]);

  return (
    <div className="h-64 border-t flex flex-col"
         style={{ borderColor: 'var(--border-default)', background: 'var(--bg-secondary)' }}>
      {/* Panel Header */}
      <div className="h-10 flex items-center justify-between px-4 border-b"
           style={{ borderColor: 'var(--border-default)' }}>
        <div className="flex items-center gap-4 h-full">
          <button
            onClick={() => setActiveTab('heatmap')}
            className={`h-full px-2 text-xs font-medium border-b-2 transition-colors ${activeTab === 'heatmap' ? 'border-[var(--accent-primary)] text-[var(--accent-primary)]' : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
          >
            🎯 Query Heatmap
          </button>
          <button
            onClick={() => setActiveTab('3d')}
            className={`h-full px-2 text-xs font-medium border-b-2 transition-colors ${activeTab === '3d' ? 'border-[var(--accent-primary)] text-[var(--accent-primary)]' : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
          >
            🌐 Database Context
          </button>
        </div>
        
        <div className="flex items-center gap-6">
          {graphData?.benchmark_score !== undefined && (
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
      <div className="flex-1 flex items-center justify-center relative">
        {loading ? (
          <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
            <div className="w-4 h-4 border-2 border-[var(--text-secondary)] border-t-transparent rounded-full animate-spin" />
            Loading similarity data...
          </div>
        ) : activeTab === '3d' ? (
          !graphData?.sufficient ? (
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              Not enough documents in archive to generate a 3D map
            </p>
          ) : (
            <canvas
              ref={canvasRef}
              width={900}
              height={220}
              className="w-full h-full cursor-grab active:cursor-grabbing"
              style={{ background: '#f8fafc' }}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
            />
          )
        ) : (
          <div className="w-full h-full p-4 overflow-y-auto">
            {graphData?.internal_similarities && graphData.internal_similarities.length > 0 ? (
              <div>
                <h4 className="text-xs font-semibold mb-3" style={{ color: 'var(--text-secondary)' }}>Internal Document Relevance</h4>
                <div className="grid grid-cols-[repeat(auto-fit,minmax(28px,1fr))] gap-1.5">
                  {graphData.internal_similarities.map((score, i) => {
                    const normalized = Math.max(0, Math.min(1, score));
                    // Mint Green scale (GnBu approximation)
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
        )}
      </div>
    </div>
  );
}
