"use client";

import React, { useEffect, useState, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { api } from "@/lib/api";
import { Loader2, Share2, Info } from "lucide-react";
import { toast } from "sonner";

interface Props {
  documentId: string;
}

interface GraphData {
  nodes: Array<{ id: string; name?: string; label?: string; mentions?: number }>;
  links: Array<{ source: string; target: string; weight?: number }>;
}

export default function KnowledgeGraph({ documentId }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadGraph = async () => {
      setLoading(true);
      try {
        const data = await api.get<GraphData>(`/api/v1/documents/${documentId}/graph`);
        
        // Transform NetworkX node-link data to React Flow format
        const initialNodes: Node[] = data.nodes.map((node, i) => ({
          id: node.id,
          data: { label: node.name || node.id },
          position: { 
            x: Math.cos(i) * 300 + 400, 
            y: Math.sin(i) * 300 + 300 
          },
          style: {
            background: "var(--primary)",
            color: "var(--primary-foreground)",
            borderRadius: "12px",
            padding: "10px",
            width: 150,
            fontSize: "12px",
            fontWeight: "bold",
            textAlign: "center",
            boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)",
          },
        }));

        const initialEdges: Edge[] = data.links.map((link) => ({
          id: `e-${link.source}-${link.target}`,
          source: link.source,
          target: link.target,
          label: link.weight ? `w: ${link.weight}` : undefined,
          animated: true,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: "var(--primary)",
          },
          style: {
            stroke: "var(--primary)",
            strokeWidth: 2,
            opacity: 0.6,
          },
        }));

        setNodes(initialNodes);
        setEdges(initialEdges);
      } catch (err) {
        console.error("Failed to load graph:", err);
        toast.error("Could not load knowledge graph");
      } finally {
        setLoading(false);
      }
    };

    if (documentId) {
      loadGraph();
    }
  }, [documentId, setNodes, setEdges]);

  if (loading) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center bg-card/30 backdrop-blur-sm rounded-xl border border-border/50">
        <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
        <p className="text-sm font-medium text-muted-foreground animate-pulse">Building graph view...</p>
      </div>
    );
  }

  return (
    <div className="h-full w-full bg-background rounded-xl border border-border/50 overflow-hidden relative shadow-inner">
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
        <div className="px-3 py-1.5 bg-card/80 backdrop-blur-md rounded-lg border border-border shadow-sm flex items-center gap-2">
          <Info className="w-4 h-4 text-primary" />
          <span className="text-xs font-bold uppercase tracking-wider">Knowledge Graph</span>
        </div>
      </div>
      
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        colorMode="system"
      >
        <Background gap={20} color="var(--border)" />
        <Controls showInteractive={false} className="bg-card border-border" />
        <MiniMap 
          nodeColor="var(--primary)" 
          maskColor="rgba(var(--background), 0.7)"
          className="bg-card border-border rounded-lg"
        />
      </ReactFlow>
    </div>
  );
}
