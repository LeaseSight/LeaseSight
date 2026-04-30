'use client';

import { useEffect, useState, useRef } from 'react';
import { X } from 'lucide-react';
import { api } from '@/lib/api';
import { GraphData } from '@/lib/types';

interface NetworkPanelProps {
  selectedDoc: string;
  onClose: () => void;
}

export function NetworkPanel({ selectedDoc, onClose }: NetworkPanelProps) {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
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
    ctx.fillStyle = '#0a0a1a';
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
    const newProjected = { ...project(graphData.new_coords), name: 'Current Document', type: 'new' as const };

    // Sort by z for painter's algorithm
    const allPoints = [...archiveProjected, newProjected].sort((a, b) => a.z - b.z);

    for (const pt of allPoints) {
      if (pt.type === 'archive') {
        const size = 3 * pt.s;
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(65, 105, 225, ${0.3 + pt.s * 0.2})`;
        ctx.fill();
        ctx.strokeStyle = 'rgba(65, 105, 225, 0.5)';
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
        ctx.fillStyle = '#ef4444';
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        // Label
        ctx.fillStyle = '#ef4444';
        ctx.font = '11px Inter, system-ui';
        ctx.textAlign = 'center';
        ctx.fillText('📄 CURRENT', pt.x, pt.y - size - 6);
      }
    }

    // Legend
    ctx.fillStyle = 'rgba(15, 23, 42, 0.8)';
    ctx.fillRect(10, H - 50, 180, 40);
    ctx.strokeStyle = 'var(--border-default)';
    ctx.strokeRect(10, H - 50, 180, 40);

    ctx.beginPath(); ctx.arc(24, H - 35, 4, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(65, 105, 225, 0.6)'; ctx.fill();
    ctx.fillStyle = '#94a3b8'; ctx.font = '10px Inter'; ctx.textAlign = 'left';
    ctx.fillText(`Archive (${graphData.archive_coords.length})`, 34, H - 31);

    ctx.beginPath();
    ctx.moveTo(120, H - 39); ctx.lineTo(125, H - 35); ctx.lineTo(120, H - 31); ctx.lineTo(115, H - 35);
    ctx.closePath(); ctx.fillStyle = '#ef4444'; ctx.fill();
    ctx.fillStyle = '#94a3b8'; ctx.fillText('Current', 132, H - 31);

  }, [graphData, rotation]);

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
      <div className="h-8 flex items-center justify-between px-4 border-b"
           style={{ borderColor: 'var(--border-default)' }}>
        <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
          🌐 Document Similarity Network (PCA 3D)
        </span>
        <button onClick={onClose} className="hover:opacity-70">
          <X className="w-3.5 h-3.5" style={{ color: 'var(--text-secondary)' }} />
        </button>
      </div>

      {/* Canvas */}
      <div className="flex-1 flex items-center justify-center">
        {loading ? (
          <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
            <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            Building similarity network...
          </div>
        ) : !graphData?.sufficient ? (
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            Not enough documents in archive to generate a map
          </p>
        ) : (
          <canvas
            ref={canvasRef}
            width={900}
            height={220}
            className="w-full h-full cursor-grab active:cursor-grabbing"
            style={{ background: '#0a0a1a' }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          />
        )}
      </div>
    </div>
  );
}
