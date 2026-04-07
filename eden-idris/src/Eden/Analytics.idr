||| Pure graph analytics: degree maps, density, connected components.
|||
||| No IO — operates on in-memory lists of edges and nodes.
module Eden.Analytics

import Data.List
import Eden.Types

------------------------------------------------------------------------
-- Degree map
------------------------------------------------------------------------

||| Count edges per node (undirected degree).
export
degreeMap : List Edge -> List (String, Nat)
degreeMap edges =
  let nodeIds = nub (concatMap (\e => [e.srcId, e.dstId]) edges)
  in map (\nid => (nid, length (filter (\e => e.srcId == nid || e.dstId == nid) edges))) nodeIds

------------------------------------------------------------------------
-- Graph density
------------------------------------------------------------------------

||| Graph density: |E| / (|V| * (|V| - 1)).
||| Returns 0.0 for graphs with fewer than 2 nodes.
export
graphDensity : Nat -> Nat -> Double
graphDensity nodes edges =
  if nodes <= 1 then 0.0
  else cast edges / (cast nodes * cast (minus nodes 1))

------------------------------------------------------------------------
-- Connected components (label propagation)
------------------------------------------------------------------------

||| Count connected components in an undirected edge list.
export
connectedComponents : List Edge -> Nat
connectedComponents [] = 0
connectedComponents edges =
  let nodeIds = nub (concatMap (\e => [e.srcId, e.dstId]) edges)
      initial = map (\nid => (nid, nid)) nodeIds
      final   = propagate initial edges
      roots   = nub (map snd final)
  in length roots
  where
    findLabel : List (String, String) -> String -> String
    findLabel [] nid = nid
    findLabel ((k, v) :: rest) nid = if k == nid then v else findLabel rest nid

    propagate : List (String, String) -> List Edge -> List (String, String)
    propagate labels []          = labels
    propagate labels (e :: es)   =
      let srcLbl = findLabel labels e.srcId
          dstLbl = findLabel labels e.dstId
          minLbl = if srcLbl <= dstLbl then srcLbl else dstLbl
          labels' = map (\kv => if snd kv == srcLbl || snd kv == dstLbl
                                then (fst kv, minLbl) else kv) labels
      in propagate labels' es

------------------------------------------------------------------------
-- Average degree
------------------------------------------------------------------------

||| Average degree: 2|E| / |V|.
export
averageDegree : List Edge -> Nat -> Double
averageDegree edges nodes =
  if nodes == 0 then 0.0
  else (2.0 * cast (length edges)) / cast nodes
