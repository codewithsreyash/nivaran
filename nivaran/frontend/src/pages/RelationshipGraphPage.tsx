import { useEffect, useState, useCallback } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { graphAPI, bureausAPI, usersAPI } from '../lib/api';
import { Search, Filter, X, ChevronDown, Users, Building2, FileText, AlertTriangle } from 'lucide-react';
import type { Bureau, User } from '../types';
import toast from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import { PageErrorState } from '../components/PageState';

export default function RelationshipGraphPage() {
  const { isAdmin } = useAuth();
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [analytics, setAnalytics] = useState<any>(null);
  const [bureaus, setBureaus] = useState<Bureau[]>([]);
  const [officers, setOfficers] = useState<User[]>([]);

  // Filters
  const [focusComplaintId, setFocusComplaintId] = useState<string>('');
  const [selectedBureau, setSelectedBureau] = useState<string>('');
  const [selectedOfficer, setSelectedOfficer] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [selectedPriority, setSelectedPriority] = useState<string>('');
  const [relationshipType, setRelationshipType] = useState<string>('');
  const [confirmedOnly, setConfirmedOnly] = useState(false);
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [inactiveOnly, setInactiveOnly] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    setAnalytics(null);
    setNodes([]);
    setEdges([]);
    try {
      const params: any = {};
      if (focusComplaintId) params.focus_complaint_id = Number(focusComplaintId);
      if (selectedBureau) params.bureau_id = Number(selectedBureau);
      if (selectedOfficer) params.officer_id = Number(selectedOfficer);
      if (selectedStatus) params.status = selectedStatus;
      if (selectedPriority) params.priority = selectedPriority;
      if (relationshipType) params.relationship_type = relationshipType;
      if (confirmedOnly) params.confirmed_only = true;
      if (overdueOnly) params.overdue_only = true;
      if (inactiveOnly) params.inactive_only = true;

      const [gRes, aRes] = await Promise.all([
        graphAPI.get(params),
        graphAPI.getAnalytics(),
      ]);

      // Convert backend nodes to ReactFlow nodes
      const flowNodes: Node[] = gRes.data.nodes.map((n: any) => ({
        id: n.id,
        type: 'default',
        position: { x: 0, y: 0 }, // Will be auto-positioned
        data: {
          label: n.label,
          ...n,
        },
        style: getNodeStyle(n.type),
      }));

      // Convert backend edges to ReactFlow edges
      const flowEdges: Edge[] = gRes.data.edges.map((e: any) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        type: e.confirmed ? 'smoothstep' : 'default',
        style: getEdgeStyle(e.type, e.confirmed),
        animated: !e.confirmed,
        markerEnd: { type: 'arrowclosed' },
      }));

      setNodes(flowNodes);
      setEdges(flowEdges);
      setAnalytics(aRes.data);
    } catch (error) {
      setLoadError(true);
      toast.error('Failed to load graph data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [focusComplaintId, selectedBureau, selectedOfficer, selectedStatus, selectedPriority, relationshipType, confirmedOnly, overdueOnly, inactiveOnly, setNodes, setEdges]);

  useEffect(() => {
    void loadGraph();
  }, [loadGraph]);

  useEffect(() => {
    bureausAPI.list().then((r) => setBureaus(r.data)).catch(() => setBureaus([]));
    if (isAdmin) usersAPI.list().then((r) => setOfficers(r.data)).catch(() => setOfficers([]));
    else setOfficers([]);
  }, [isAdmin]);

  const clearFilters = () => {
    setFocusComplaintId('');
    setSelectedBureau('');
    setSelectedOfficer('');
    setSelectedStatus('');
    setSelectedPriority('');
    setRelationshipType('');
    setConfirmedOnly(false);
    setOverdueOnly(false);
    setInactiveOnly(false);
  };

  const getNodeStyle = (type: string) => {
    switch (type) {
      case 'complaint':
        return { background: '#1d4ed8', color: '#fff', border: '2px solid #1e40af' };
      case 'institution':
        return { background: '#15803d', color: '#fff', border: '2px solid #166534' };
      case 'bureau':
        return { background: '#a65008', color: '#fff', border: '2px solid #854d0e' };
      case 'officer':
        return { background: '#405d7c', color: '#fff', border: '2px solid #294663' };
      default:
        return { background: '#64748b', color: '#fff' };
    }
  };

  const getEdgeStyle = (type: string, confirmed: boolean) => {
    if (!confirmed) {
      return { stroke: '#94a3b8', strokeDasharray: '5,5', strokeWidth: 2 };
    }
    switch (type) {
      case 'confirmed_duplicate':
        return { stroke: '#b42335', strokeWidth: 3 };
      case 'related_independent':
        return { stroke: '#a65008', strokeWidth: 2 };
      default:
        return { stroke: '#1d4ed8', strokeWidth: 2 };
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 bg-white">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="page-title">Complaint relationship graph</h1>
            <p className="page-subtitle">Explore connections between visible complaints and related records.</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowFilters(!showFilters)} className="btn-secondary text-xs flex items-center gap-2" aria-expanded={showFilters} aria-controls="graph-filters">
              <Filter size={14} /> Filters {showFilters ? <ChevronDown size={14} /> : <ChevronDown size={14} className="rotate-180" />}
            </button>
            <button onClick={loadGraph} className="btn-primary text-xs">Refresh</button>
          </div>
        </div>

        {/* Analytics */}
        {analytics && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2 mb-4">
            {[
              ['Complaints', analytics.complaints, FileText],
              ['Institutions', analytics.institutions, Building2],
              ['Bureaus', analytics.bureaus, Building2],
              ['Officers', analytics.officers, Users],
              ['Possible Duplicates', analytics.possible_duplicates, AlertTriangle],
              ['Confirmed Duplicates', analytics.confirmed_duplicates, AlertTriangle],
              ['Related', analytics.related_independent, AlertTriangle],
              ['Unassigned', analytics.unassigned_complaints, AlertTriangle],
            ].map(([label, value, Icon]) => (
              <div key={String(label)} className="p-2 rounded bg-slate-800/40 border border-slate-700/50">
                <div className="flex items-center gap-1 text-[10px] text-slate-500 mb-1">
                  <Icon size={10} /> {label}
                </div>
                <p className="text-lg font-bold text-slate-200">{value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Filters */}
        {showFilters && (
          <div id="graph-filters" className="p-4 rounded-lg bg-slate-800/30 border border-slate-700/50 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-300">Filters</h3>
              <button onClick={clearFilters} className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
                <X size={12} /> Clear All
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3">
              <div>
                <label className="text-[11px] text-slate-500 mb-1 block">Focus Complaint ID</label>
                <input
                  className="input text-xs w-full"
                  aria-label="Focus on complaint ID"
                  placeholder="Enter complaint ID..."
                  value={focusComplaintId}
                  onChange={(e) => setFocusComplaintId(e.target.value)}
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-500 mb-1 block">Bureau</label>
                <select className="select text-xs w-full" aria-label="Filter graph by bureau" value={selectedBureau} onChange={(e) => setSelectedBureau(e.target.value)}>
                  <option value="">All Bureaus</option>
                  {bureaus.map((b) => (
                    <option key={b.id} value={b.id}>{b.name}</option>
                  ))}
                </select>
              </div>
              {isAdmin && <div>
                <label className="text-[11px] text-slate-500 mb-1 block">Officer</label>
                <select className="select text-xs w-full" aria-label="Filter graph by officer" value={selectedOfficer} onChange={(e) => setSelectedOfficer(e.target.value)}>
                  <option value="">All Officers</option>
                  {officers.map((o) => (
                    <option key={o.id} value={o.id}>{o.full_name}</option>
                  ))}
                </select>
              </div>}
              <div>
                <label className="text-[11px] text-slate-500 mb-1 block">Status</label>
                <select className="select text-xs w-full" aria-label="Filter graph by complaint status" value={selectedStatus} onChange={(e) => setSelectedStatus(e.target.value)}>
                  <option value="">All Statuses</option>
                  <option value="registered">Registered</option>
                  <option value="under_initial_review">Under Initial Review</option>
                  <option value="under_process">Under Process</option>
                  <option value="awaiting_information">Awaiting Information</option>
                  <option value="escalated">Escalated</option>
                  <option value="disposed">Disposed</option>
                  <option value="closed">Closed</option>
                </select>
              </div>
              <div>
                <label className="text-[11px] text-slate-500 mb-1 block">Priority</label>
                <select className="select text-xs w-full" aria-label="Filter graph by priority" value={selectedPriority} onChange={(e) => setSelectedPriority(e.target.value)}>
                  <option value="">All Priorities</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
              <div>
                <label className="text-[11px] text-slate-500 mb-1 block">Relationship Type</label>
                <select className="select text-xs w-full" aria-label="Filter graph by relationship type" value={relationshipType} onChange={(e) => setRelationshipType(e.target.value)}>
                  <option value="">All Types</option>
                  <option value="possible_duplicate">Possible Duplicate</option>
                  <option value="confirmed_duplicate">Confirmed Duplicate</option>
                  <option value="related_independent">Related Independent</option>
                </select>
              </div>
              <div className="flex items-end gap-2">
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={confirmedOnly}
                    onChange={(e) => setConfirmedOnly(e.target.checked)}
                    className="w-4 h-4 rounded"
                  />
                  Confirmed Only
                </label>
              </div>
              <div className="flex items-end gap-2">
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={overdueOnly}
                    onChange={(e) => setOverdueOnly(e.target.checked)}
                    className="w-4 h-4 rounded"
                  />
                  Overdue Only
                </label>
              </div>
              <div className="flex items-end gap-2">
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={inactiveOnly}
                    onChange={(e) => setInactiveOnly(e.target.checked)}
                    className="w-4 h-4 rounded"
                  />
                  Inactive Only
                </label>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Graph */}
      {loadError && <PageErrorState message="Relationship graph data could not be loaded." onRetry={() => void loadGraph()} />}
      <div className="relative h-[65vh] min-h-[520px] max-h-[850px]">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          className="bg-slate-50"
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
          <Controls />
          <MiniMap
            nodeColor={(node) => {
              switch (node.data.type) {
                case 'complaint': return '#1d4ed8';
                case 'institution': return '#15803d';
                case 'bureau': return '#a65008';
                case 'officer': return '#405d7c';
                default: return '#64748b';
              }
            }}
            className="!bg-slate-900 !border-slate-700"
          />
        </ReactFlow>

        {!loadError && nodes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <p className="text-slate-400 text-sm">No nodes found matching your filters</p>
              <button onClick={clearFilters} className="mt-2 text-xs text-indigo-400 hover:text-indigo-300">
                Clear filters to view all data
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
