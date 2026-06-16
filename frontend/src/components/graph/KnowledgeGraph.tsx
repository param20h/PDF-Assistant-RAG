/**
 * KnowledgeGraph — interactive entity relationship visualiser.
 *
 * Uses @xyflow/react (React Flow v12, fully React-19-compatible).
 * Fetches graph data from GET /api/v1/graph/{documentId} and renders
 * a force-positioned node-link diagram with zoom, pan, and node-click.
 *
 * Props
 * -----
 * documentId  – UUID of the active document
 * onClose     – called when the user dismisses the panel
 */
"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeMouseHandler,
  type OnConnect,
  BackgroundVariant,
  Panel,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { X, RefreshCw, Info } from "lucide-react";
import { api } from "@/lib/api";

// ── API types ─────────────────────────────────────────────────────────────────

interface GraphNode {
  id: string;
  name: string;
  label: string;
  mentions: number;
  pages: number[];
}

interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  pages: number[];
}

interface GraphData {
  document_id: string;
  document_name: string;
  node_count: number;
  edge_count: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ── NER label colour palette ──────────────────────────────────────────────────
// Deliberately constrained: enough to distinguish entity types at a glance,
// chosen for legibility on both light and dark backgrounds.

const LABEL_COLOURS: Record<
  string,
  { bg: string; border: string; text: string }
> = {
  PERSON: { bg: "#dbeafe", border: "#3b82f6", text: "#1e3a8a" },
  ORG: { bg: "#dcfce7", border: "#22c55e", text: "#14532d" },
  GPE: { bg: "#fef9c3", border: "#eab308", text: "#713f12" },
  LOC: { bg: "#ffedd5", border: "#f97316", text: "#7c2d12" },
  DATE: { bg: "#f3e8ff", border: "#a855f7", text: "#4a1d96" },
  MONEY: { bg: "#fce7f3", border: "#ec4899", text: "#831843" },
  PRODUCT: { bg: "#e0f2fe", border: "#0ea5e9", text: "#0c4a6e" },
  EVENT: { bg: "#fff7ed", border: "#fb923c", text: "#7c2d12" },
  LAW: { bg: "#f1f5f9", border: "#64748b", text: "#0f172a" },
  UNKNOWN: { bg: "#f8fafc", border: "#94a3b8", text: "#334155" },
};

function colourFor(label: string) {
  return LABEL_COLOURS[label] ?? LABEL_COLOURS.UNKNOWN;
}

// ── Force-layout helpers ──────────────────────────────────────────────────────
// Simple deterministic radial + jitter layout so the graph isn't a pile-up
// on first render. React Flow's built-in dragging lets users reorganise.

const CENTRE_X = 500;
const CENTRE_Y = 350;

function radialPosition(index: number, total: number, radius: number) {
  const angle = (2 * Math.PI * index) / total - Math.PI / 2;
  return {
    x: CENTRE_X + radius * Math.cos(angle) + (Math.random() - 0.5) * 40,
    y: CENTRE_Y + radius * Math.sin(angle) + (Math.random() - 0.5) * 40,
  };
}

// ── Node detail panel ─────────────────────────────────────────────────────────

interface NodeDetailProps {
  node: GraphNode;
  connectedNames: string[];
  onClose: () => void;
}

function NodeDetail({ node, connectedNames, onClose }: NodeDetailProps) {
  const colour = colourFor(node.label);
  return (
    <div
      className="absolute bottom-4 left-4 z-20 w-64 rounded-xl border shadow-lg bg-white dark:bg-zinc-900 overflow-hidden"
      style={{ borderColor: colour.border }}
    >
      {/* Header */}
      <div
        className="flex items-start justify-between px-3 py-2"
        style={{ backgroundColor: colour.bg }}
      >
        <div className="min-w-0">
          <p
            className="text-xs font-semibold uppercase tracking-widest"
            style={{ color: colour.border }}
          >
            {node.label}
          </p>
          <p
            className="text-sm font-bold leading-tight mt-0.5 truncate"
            style={{ color: colour.text }}
          >
            {node.name}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="ml-2 mt-0.5 shrink-0 rounded p-0.5 hover:bg-black/10 transition-colors"
          aria-label="Close node detail"
        >
          <X className="h-3.5 w-3.5" style={{ color: colour.text }} />
        </button>
      </div>

      {/* Stats */}
      <div className="px-3 py-2 space-y-2 text-xs text-zinc-600 dark:text-zinc-400">
        <div className="flex justify-between">
          <span>Mentions</span>
          <span className="font-semibold text-zinc-900 dark:text-zinc-100">
            {node.mentions}
          </span>
        </div>
        <div className="flex justify-between">
          <span>Pages</span>
          <span className="font-semibold text-zinc-900 dark:text-zinc-100">
            {node.pages.length > 0
              ? node.pages.slice(0, 6).join(", ") +
                (node.pages.length > 6 ? "…" : "")
              : "—"}
          </span>
        </div>
        {connectedNames.length > 0 && (
          <div>
            <p className="mb-1">Connected to</p>
            <ul className="space-y-0.5">
              {connectedNames.slice(0, 5).map((name) => (
                <li
                  key={name}
                  className="truncate font-medium text-zinc-800 dark:text-zinc-200"
                >
                  · {name}
                </li>
              ))}
              {connectedNames.length > 5 && (
                <li className="text-zinc-400">
                  +{connectedNames.length - 5} more
                </li>
              )}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Legend ────────────────────────────────────────────────────────────────────

function Legend({ labels }: { labels: string[] }) {
  if (labels.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {labels.map((label) => {
        const c = colourFor(label);
        return (
          <span
            key={label}
            className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium border"
            style={{
              backgroundColor: c.bg,
              borderColor: c.border,
              color: c.text,
            }}
          >
            {label}
          </span>
        );
      })}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface KnowledgeGraphProps {
  documentId: string;
  onClose: () => void;
}

export default function KnowledgeGraph({
  documentId,
  onClose,
}: KnowledgeGraphProps) {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // ── Fetch graph data ────────────────────────────────────────────────────────

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSelectedNode(null);

    let data: GraphData | null = null;
    let fetchError: string | null = null;

    try {
      data = await api.get<GraphData>(`/api/v1/graph/${documentId}`);
    } catch (err) {
      fetchError =
        err instanceof Error ? err.message : "Failed to load knowledge graph";
    }

    // All setState calls happen after the await, satisfying the linter
    if (fetchError || !data) {
      setError(fetchError ?? "No data returned");
      setNodes([]);
      setEdges([]);
      setLoading(false);
      return;
    }

    setGraphData(data);

    const maxMentions = Math.max(...data.nodes.map((n) => n.mentions), 1);
    const radius = Math.min(Math.max(data.nodes.length * 18, 200), 500);

    const rfNodes: Node[] = data.nodes.map((n, i) => {
      const colour = colourFor(n.label);
      const size = 36 + Math.round((n.mentions / maxMentions) * 36);
      const pos = radialPosition(i, data!.nodes.length, radius);
      return {
        id: n.id,
        position: pos,
        data: {
          label: (
            <div
              className="flex items-center justify-center text-center font-semibold leading-tight px-1"
              style={{ fontSize: Math.max(9, size * 0.22), color: colour.text }}
              title={n.name}
            >
              {n.name.length > 14 ? n.name.slice(0, 13) + "…" : n.name}
            </div>
          ),
          _raw: n,
        },
        style: {
          width: size,
          height: size,
          borderRadius: "50%",
          backgroundColor: colour.bg,
          border: `2px solid ${colour.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          boxShadow: "0 1px 4px rgba(0,0,0,0.12)",
        },
      };
    });

    const maxWeight = Math.max(...data.edges.map((e) => e.weight), 1);
    const rfEdges: Edge[] = data.edges.map((e, i) => {
      const opacity = 0.2 + 0.6 * (e.weight / maxWeight);
      const strokeWidth = 1 + Math.round((e.weight / maxWeight) * 3);
      return {
        id: `e-${i}`,
        source: e.source,
        target: e.target,
        animated: false,
        style: { stroke: `rgba(100,116,139,${opacity})`, strokeWidth },
        data: { _raw: e },
      };
    });

    setNodes(rfNodes);
    setEdges(rfEdges);
    setLoading(false);
  }, [documentId, setNodes, setEdges]);

  useEffect(() => {
    const timer = setTimeout(() => {
      void fetchGraph();
    }, 0);

    return () => clearTimeout(timer);
  }, [fetchGraph]);

  // ── Node click → show detail panel ─────────────────────────────────────────

  const onNodeClick = useCallback<NodeMouseHandler>((_event, node) => {
    const raw = (node.data as { _raw?: GraphNode })._raw;
    if (raw) setSelectedNode(raw);
  }, []);

  // Names of nodes connected to the selected node
  const connectedNames = useMemo(() => {
    if (!selectedNode || !graphData) return [];
    const nodeMap = Object.fromEntries(
      graphData.nodes.map((n) => [n.id, n.name]),
    );
    return graphData.edges
      .filter(
        (e) => e.source === selectedNode.id || e.target === selectedNode.id,
      )
      .map((e) => nodeMap[e.source === selectedNode.id ? e.target : e.source])
      .filter(Boolean);
  }, [selectedNode, graphData]);

  // Distinct NER labels present in this graph
  const presentLabels = useMemo(
    () => [...new Set((graphData?.nodes ?? []).map((n) => n.label))].sort(),
    [graphData],
  );

  const onConnect = useCallback<OnConnect>(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/50 bg-card/50 shrink-0">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold truncate">
            Knowledge Graph
            {graphData && (
              <span className="ml-2 text-xs font-normal text-muted-foreground">
                {graphData.node_count} entities · {graphData.edge_count}{" "}
                connections
              </span>
            )}
          </h2>
          {graphData && (
            <p className="text-xs text-muted-foreground truncate">
              {graphData.document_name}
            </p>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0 ml-3">
          <button
            type="button"
            onClick={fetchGraph}
            disabled={loading}
            className="rounded-md p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors disabled:opacity-50"
            aria-label="Refresh graph"
            title="Refresh"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            aria-label="Close knowledge graph"
            title="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 relative overflow-hidden">
        {/* Loading */}
        {loading && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-background/80 backdrop-blur-sm">
            <RefreshCw className="h-8 w-8 animate-spin text-primary/60" />
            <p className="text-sm text-muted-foreground">
              Building knowledge graph…
            </p>
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-4 px-8 text-center">
            <div className="w-12 h-12 rounded-2xl bg-muted flex items-center justify-center">
              <Info className="h-6 w-6 text-muted-foreground" />
            </div>
            <div>
              <p className="text-sm font-medium mb-1">Graph not available</p>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {error}
              </p>
            </div>
            <button
              type="button"
              onClick={fetchGraph}
              className="text-xs px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Try again
            </button>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && nodes.length === 0 && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 px-8 text-center">
            <div className="w-12 h-12 rounded-2xl bg-muted flex items-center justify-center">
              <Info className="h-6 w-6 text-muted-foreground" />
            </div>
            <div>
              <p className="text-sm font-medium mb-1">No entities found</p>
              <p className="text-xs text-muted-foreground leading-relaxed">
                No named entities were extracted from this document. Try a
                document with named people, organisations, or places.
              </p>
            </div>
          </div>
        )}

        {/* React Flow canvas */}
        {!loading && !error && nodes.length > 0 && (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={() => setSelectedNode(null)}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.2}
            maxZoom={3}
            nodesDraggable
            nodesConnectable={false}
            elementsSelectable
            attributionPosition="bottom-right"
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={20}
              size={1}
              color="hsl(var(--border))"
            />
            <Controls
              showInteractive={false}
              className="!border-border !bg-card !shadow-sm [&>button]:!border-border [&>button]:!bg-card [&>button]:!text-foreground"
            />
            <MiniMap
              nodeColor={(n) => {
                const raw = (n.data as { _raw?: GraphNode })._raw;
                return raw ? colourFor(raw.label).border : "#94a3b8";
              }}
              maskColor="rgba(0,0,0,0.06)"
              className="!border-border !bg-card !rounded-lg overflow-hidden"
            />

            {/* Legend panel */}
            <Panel position="top-left">
              <div className="rounded-lg border border-border/60 bg-card/90 backdrop-blur-sm px-2.5 py-2 shadow-sm">
                <Legend labels={presentLabels} />
              </div>
            </Panel>
          </ReactFlow>
        )}

        {/* Node detail panel */}
        {selectedNode && (
          <NodeDetail
            node={selectedNode}
            connectedNames={connectedNames}
            onClose={() => setSelectedNode(null)}
          />
        )}
      </div>
    </div>
  );
}
