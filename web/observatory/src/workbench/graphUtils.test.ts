import { describe, expect, it } from "vitest";

import {
  csvForEdges,
  csvForNodes,
  gdfForGraph,
  gexfForGraph,
  gmlForGraph,
  graphMLForGraph,
  graphVizDotForGraph,
  netdrawVnaForGraph,
  pajekNetForGraph,
  tgfForGraph,
  tulipTlpForGraph,
  ucinetDlForGraph,
  visibleGraphForMode,
} from "./graphUtils";

const nodes = [
  {
    id: "meme-1",
    label: "meme key phrase",
    export_label: "Persistent meme semantic content",
    kind: "information",
    entity_type: "author",
    speech_act_mode: "constative",
    storage_kind: "meme",
    domain: "knowledge",
    source_kind: "operator",
    cluster_signature: "cluster-1",
    degree: 2,
    recent_active_set_presence: 1,
  },
  {
    id: "meme-2",
    label: "adaptive key phrase",
    export_label: "Adaptive meme semantic content",
    kind: "meme",
    entity_type: "behavior_meme",
    speech_act_mode: "performative",
    storage_kind: "meme",
    domain: "behavior",
    source_kind: "document",
    cluster_signature: "cluster-2",
    degree: 1,
    recent_active_set_presence: 0,
  },
] as const;

const edges = [
  {
    id: "edge-1",
    source: "meme-1",
    target: "meme-2",
    type: "CO_OCCURS_WITH",
    export_label: "CO_OCCURS_WITH: Persistent meme semantic content -> Adaptive meme semantic content",
    weight: 0.75,
    evidence_label: "OBSERVED",
    assertion_origin: "operator",
    confidence: 0.8,
  },
] as const;

describe("graph export serializers", () => {
  it("uses Gephi-friendly CSV headers for node and edge tables", () => {
    const nodeCsv = csvForNodes([...nodes]);
    const edgeCsv = csvForEdges([...edges]);

    expect(nodeCsv).toContain("Id,Label,Kind,EntityType,SpeechActMode,StorageKind,Domain,SourceKind,ClusterSignature,Degree,RecentActiveSetPresence");
    expect(nodeCsv).toContain("Persistent meme semantic content");
    expect(edgeCsv).toContain("Id,Source,Target,Label,Type,Weight,EvidenceLabel,AssertionOrigin,Confidence");
    expect(edgeCsv).toContain("CO_OCCURS_WITH: Persistent meme semantic content -> Adaptive meme semantic content");
  });

  it("serializes rich Gephi XML and attribute formats", () => {
    const graphml = graphMLForGraph([...nodes], [...edges]);
    const gexf = gexfForGraph([...nodes], [...edges]);
    const gdf = gdfForGraph([...nodes], [...edges]);

    expect(graphml).toContain('<key id="node_label"');
    expect(graphml).toContain("<data key=\"node_label\">Persistent meme semantic content</data>");
    expect(graphml).toContain('<data key="edge_assertion_origin">operator</data>');
    expect(gexf).toContain('<attributes class="edge">');
    expect(gexf).toContain('label="Persistent meme semantic content"');
    expect(gexf).toContain('attvalue for="confidence" value="0.8"');
    expect(gdf).toContain("nodedef>name VARCHAR,label VARCHAR");
    expect(gdf).toContain("edgedef>node1 VARCHAR,node2 VARCHAR,label VARCHAR,weight DOUBLE");
  });

  it("serializes legacy Gephi graph-document formats", () => {
    const gml = gmlForGraph([...nodes], [...edges]);
    const dot = graphVizDotForGraph([...nodes], [...edges]);
    const pajek = pajekNetForGraph([...nodes], [...edges]);
    const vna = netdrawVnaForGraph([...nodes], [...edges]);
    const ucinet = ucinetDlForGraph([...nodes], [...edges]);
    const tulip = tulipTlpForGraph([...nodes], [...edges]);
    const tgf = tgfForGraph([...nodes], [...edges]);

    expect(gml).toContain('graph [');
    expect(gml).toContain('label "Persistent meme semantic content"');
    expect(dot).toContain("digraph eden");
    expect(dot).toContain('label="CO_OCCURS_WITH: Persistent meme semantic content -> Adaptive meme semantic content"');
    expect(pajek).toContain("*Vertices 2");
    expect(pajek).toContain('"Persistent meme semantic content"');
    expect(pajek).toContain("*Arcs");
    expect(vna).toContain("*node data");
    expect(vna).toContain("*tie data");
    expect(ucinet).toContain("dl n=2 format=edgelist1");
    expect(ucinet).toContain("labels:");
    expect(tulip).toContain('(tlp "2.0"');
    expect(tgf).toContain("#");
    expect(tgf).toContain("meme-1 Persistent meme semantic content");
  });

  it("uses the assemblies slice for memode-visible graph modes", () => {
    const payload = {
      semantic_nodes: [...nodes],
      semantic_edges: [...edges],
      assembly_nodes: [
        ...nodes,
        {
          id: "memode-1",
          label: "Persistence Memode",
          kind: "memode",
          entity_type: "memode",
          speech_act_mode: "performative",
          storage_kind: "memode",
          domain: "behavior",
          source_kind: "memode",
        },
      ],
      assembly_edges: [
        ...edges,
        {
          id: "edge-2",
          source: "memode-1",
          target: "meme-1",
          type: "MEMODE_HAS_MEMBER",
          weight: 1,
          evidence_label: "AUTO_DERIVED",
          assertion_origin: "auto_derived",
          confidence: 1,
        },
      ],
      assemblies: [
        {
          id: "memode-1",
          label: "Persistence Memode",
          kind: "memode",
          entity_type: "memode",
          speech_act_mode: "performative",
          storage_kind: "memode",
          domain: "behavior",
          source_kind: "memode",
        },
      ],
      runtime_nodes: [],
      runtime_edges: [],
    };

    const assemblyGraph = visibleGraphForMode(payload, "Assemblies");

    expect(assemblyGraph.nodes.map((node) => node.id)).toContain("memode-1");
    expect(assemblyGraph.edges.map((edge) => edge.type)).toContain("MEMODE_HAS_MEMBER");
  });
});
