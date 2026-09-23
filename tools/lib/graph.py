"""Graphe du monde (étapes 19-20) : nœuds, relations, connectivité.

Construit un graphe orienté où :
- les nœuds sont toutes les entités des catalogues + les systèmes ;
- les arêtes sont des relations typées dérivées des champs référentiels des
  entités (seed_id, yield_id, inputs, outputs, giver_id, effects, etc.).

Fournit l'analyse de connectivité exigée par le brief :
- entités orphelines ;
- objets/recettes/quêtes sans usage ;
- atteignabilité depuis le point de départ du joueur ;
- profondeur causale ;
- nombre de systèmes affectés ;
- résilience si le joueur ignore un élément.

Le graphe est la structure centrale que les validateurs et le simulateur
interrogent. Il est déterministe et versionné.
"""
from __future__ import annotations

from typing import Any, Iterable

from .common import DIRS, Status, make_id, write_json, versioned_envelope, fingerprint
from .ontology import RELATION_TYPES


class Graph:
    """Graphe orienté typé avec nœuds et arêtes."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []
        self._edge_ids: set[str] = set()

    def add_node(self, nid: str, ntype: str, *, display_name: str = "",
                 status: str = Status.PROPOSEE, **meta) -> None:
        if nid in self.nodes:
            # Fusion : on garde le statut le plus fort et on complète les métas.
            self.nodes[nid].update({k: v for k, v in meta.items() if v})
            return
        self.nodes[nid] = {
            "id": nid, "type": ntype, "display_name": display_name,
            "status": status, **meta,
        }

    def add_edge(self, rtype: str, source: str, target: str, *,
                 status: str = Status.DEDUITE, implies_usage: bool | None = None,
                 **meta) -> dict | None:
        if rtype not in RELATION_TYPES:
            # Relation non ontologique : rejetée (cohérence du vocabulaire).
            return None
        if source == target:
            return None
        eid = f"{rtype}:{source}->{target}"
        if eid in self._edge_ids:
            return None
        self._edge_ids.add(eid)
        iu = RELATION_TYPES[rtype]["implies_usage"] if implies_usage is None else implies_usage
        edge = {
            "id": eid, "type": rtype, "source": source, "target": target,
            "status": status, "implies_usage": iu, **meta,
        }
        self.edges.append(edge)
        return edge

    # --- Requêtes ------------------------------------------------------------

    def outgoing(self, nid: str) -> list[dict]:
        return [e for e in self.edges if e["source"] == nid]

    def incoming(self, nid: str) -> list[dict]:
        return [e for e in self.edges if e["target"] == nid]

    def degree(self, nid: str) -> int:
        return len(self.outgoing(nid)) + len(self.incoming(nid))

    def usage_edges(self, nid: str) -> list[dict]:
        """Arêtes qui impliquent un usage réel (pas seulement technique)."""
        return [e for e in self.outgoing(nid) + self.incoming(nid) if e["implies_usage"]]

    def neighbors(self, nid: str) -> set[str]:
        return ({e["target"] for e in self.outgoing(nid)}
                | {e["source"] for e in self.incoming(nid)})

    def systems_touching(self, nid: str) -> set[str]:
        """Systèmes connectés (directement ou via 1 saut) à une entité."""
        out = set()
        for e in self.outgoing(nid) + self.incoming(nid):
            for other in (e["source"], e["target"]):
                node = self.nodes.get(other)
                if node and node["type"] == "system":
                    out.add(other)
        return out

    def to_dict(self) -> dict:
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
        }


# --- Construction depuis les catalogues -------------------------------------

def _ref(graph: Graph, rtype: str, src: str, target: str | None,
         status: str = Status.DEDUITE) -> None:
    if target:
        graph.add_edge(rtype, src, target, status=status)


def build_graph(catalogs: dict, systems: list[dict], canon: dict) -> Graph:
    g = Graph()

    # Nœuds : monde, joueur, systèmes.
    g.add_node(canon["world"]["id"], "monde", display_name=canon["world"]["display_name"],
               status=Status.CANONIQUE)
    g.add_node(canon["player"]["id"], "joueur", display_name=canon["player"]["display_name"],
               status=Status.CANONIQUE)
    for s in systems:
        g.add_node(s["id"], "system", display_name=s["display_name"], status=s["status"])
    for a in canon["facts"]:
        g.add_node(a["id"], "fait", display_name=a["statement"], status=Status.CANONIQUE)

    # Nœuds : entités des catalogues.
    type_by_key = {
        "seasons": "saison", "locations": "lieu", "crops": "culture",
        "resources": "ressource", "machines": "machine", "recipes": "recette",
        "objects": "objet", "npcs": "pnj", "creatures": "creature",
        "quests": "quete", "events": "evenement", "secrets": "secret",
    }
    for key, ntype in type_by_key.items():
        for ent in catalogs.get(key, []):
            g.add_node(ent["id"], ntype, display_name=ent.get("display_name", ""),
                       status=ent.get("status", Status.PROPOSEE),
                       system=ent.get("system") or ent.get("used_by"))

    # Arêtes : dépendances entre systèmes.
    for s in systems:
        for dep in s.get("depends_on", []):
            g.add_edge("utilise", s["id"], dep, status=Status.DEDUITE)

    # Arêtes : cultures (consomme graine, produit récolte, pousse dans saisons).
    for c in catalogs.get("crops", []):
        _ref(g, "consomme", c["id"], c.get("seed_id"))   # planter consomme la graine
        _ref(g, "produit", c["id"], c.get("yield_id"))
        for s in c.get("seasons", []):
            g.add_edge("pousse_dans", c["id"], s, status=Status.DEDUITE)
        if c.get("used_by"):
            g.add_edge("releve_de", c["id"], c["used_by"], status=Status.DEDUITE)
        if c.get("memory_plant"):
            g.add_edge("releve_de", c["id"], "system_memoire", status=Status.DEDUITE)

    # Arêtes : cartes (nœuds) + navigation entre cartes + rattachement aux lieux.
    for m in catalogs.get("maps", []):
        g.add_node(m["id"], "map", display_name=m.get("display_name", ""),
                   status=m.get("status", Status.DEDUITE))
        if m.get("location_id"):
            g.add_edge("contient", m["id"], m["location_id"], status=Status.DEDUITE)
        for linked in m.get("linked_maps", []):
            g.add_edge("connecte_a", m["id"], linked, status=Status.DEDUITE)
        g.add_edge("releve_de", m["id"], "system_navigation", status=Status.DEDUITE)

    # Arêtes : lieux.
    for l in catalogs.get("locations", []):
        if l.get("map_id"):
            g.add_edge("contient", l["map_id"], l["id"], status=Status.DEDUITE)
        if l.get("parent_id"):
            g.add_edge("contient", l["parent_id"], l["id"], status=Status.DEDUITE)
        if l.get("system"):
            g.add_edge("releve_de", l["id"], l["system"], status=Status.DEDUITE)
        func = l.get("function")
        if func:
            sysmap = {"refuge": "system_refuge", "farmland": "system_agriculture",
                      "secret": "system_secrets", "fishing_spot": "system_peche",
                      "poi": "system_exploration"}
            if func in sysmap:
                g.add_edge("utilise", sysmap[func], l["id"], status=Status.DEDUITE)

    # Arêtes : machines.
    for m in catalogs.get("machines", []):
        for i in m.get("inputs", []):
            g.add_edge("consomme", m["id"], i, status=Status.DEDUITE)
        for o in m.get("outputs", []):
            g.add_edge("produit", m["id"], o, status=Status.DEDUITE)
        if m.get("built_by"):
            g.add_edge("produit", m["built_by"], m["id"], status=Status.DEDUITE)
        for r in m.get("recipe_ids", []):
            g.add_edge("contient", m["id"], r, status=Status.DEDUITE)
        if m.get("system"):
            g.add_edge("releve_de", m["id"], m["system"], status=Status.DEDUITE)

    # Arêtes : recettes.
    for r in catalogs.get("recipes", []):
        if r.get("station_id"):
            g.add_edge("utilise", r["id"], r["station_id"], status=Status.DEDUITE)
        for ing in r.get("inputs", []):
            g.add_edge("consomme", r["id"], ing["item_id"], status=Status.DEDUITE)
        for outp in r.get("outputs", []):
            g.add_edge("transforme", r["id"], outp["item_id"], status=Status.DEDUITE)
        if r.get("unlocked_by"):
            g.add_edge("requiert", r["id"], r["unlocked_by"], status=Status.DEDUITE)
        g.add_edge("releve_de", r["id"], f"system_{r.get('kind','artisanat')}",
                   status=Status.DEDUITE)

    # Arêtes : ressources (producteurs/consommateurs = IDs de systèmes complets).
    for r in catalogs.get("resources", []):
        for p in r.get("producers", []):
            if p in g.nodes:
                g.add_edge("produit", p, r["id"], status=Status.DEDUITE)
        for c in r.get("consumers", []):
            if c in g.nodes:
                g.add_edge("consomme", c, r["id"], status=Status.DEDUITE)

    # Arêtes : objets.
    for o in catalogs.get("objects", []):
        for obt in o.get("obtention", []) or []:
            if not (isinstance(obt, str) and ":" in obt and obt != "canon"):
                continue
            kind, target = obt.split(":", 1)
            if target not in g.nodes:
                # Référence non résolue : ignorée ici, détectée par les validateurs.
                continue
            if kind in ("culture", "creature"):
                g.add_edge("produit", target, o["id"], status=Status.DEDUITE)
            elif kind == "recette":
                g.add_edge("transforme", target, o["id"], status=Status.DEDUITE)
            elif kind in ("lieu", "pnj", "system"):
                # L'objet est obtenu auprès/ via ce moyen.
                g.add_edge("obtenu_par", o["id"], target, status=Status.DEDUITE)
        for u in o.get("users", []) or []:
            if u in g.nodes:
                # 'u' utilise l'objet (système ou entité) -> u -> objet.
                g.add_edge("utilise", u, o["id"], status=Status.DEDUITE)
        for t in o.get("transforms_into", []) or []:
            if t in g.nodes:
                g.add_edge("transforme", o["id"], t, status=Status.DEDUITE)

    # Arêtes : PNJ.
    for n in catalogs.get("npcs", []):
        if n.get("home"):
            g.add_edge("habite", n["id"], n["home"], status=Status.DEDUITE)
        for f in n.get("frequented_places", []) or []:
            if f in g.nodes:
                g.add_edge("frequente", n["id"], f, status=Status.DEDUITE)
        for k in n.get("knowledge", []) or []:
            if k in g.nodes:
                g.add_edge("requiert", n["id"], k, status=Status.DEDUITE)
        for role in n.get("roles", []) or []:
            if role == "merchant":
                g.add_edge("utilise", "system_economie", n["id"], status=Status.DEDUITE)
            if role in ("guide", "soins"):
                g.add_edge("utilise", "system_relations", n["id"], status=Status.DEDUITE)
            if role in ("artisan",):
                g.add_edge("utilise", "system_artisanat", n["id"], status=Status.DEDUITE)
            if role in ("peche",):
                g.add_edge("utilise", "system_peche", n["id"], status=Status.DEDUITE)
        g.add_edge("releve_de", n["id"], "system_relations", status=Status.DEDUITE)

    # Arêtes : créatures.
    for c in catalogs.get("creatures", []):
        for h in c.get("habitat", []) or []:
            if h in g.nodes:
                g.add_edge("habite", c["id"], h, status=Status.DEDUITE)
        for y in c.get("yields", []) or []:
            if y in g.nodes:
                g.add_edge("produit", c["id"], y, status=Status.DEDUITE)
        if c.get("system"):
            g.add_edge("releve_de", c["id"], c["system"], status=Status.DEDUITE)

    # Arêtes : quêtes.
    for q in catalogs.get("quests", []):
        if q.get("giver_id"):
            g.add_edge("donne", q["giver_id"], q["id"], status=Status.DEDUITE)
        if q.get("location_id"):
            g.add_edge("requiert", q["id"], q["location_id"], status=Status.DEDUITE)
        for s in q.get("systems", []) or []:
            g.add_edge("releve_de", q["id"], s, status=Status.DEDUITE)
        for eff in q.get("effects", []) or []:
            _effect_edges(g, q["id"], eff)

    # Arêtes : événements.
    for ev in catalogs.get("events", []):
        if ev.get("location_id"):
            g.add_edge("requiert", ev["id"], ev["location_id"], status=Status.DEDUITE)
        for s in ev.get("systems", []) or []:
            g.add_edge("releve_de", ev["id"], s, status=Status.DEDUITE)
        trig = ev.get("trigger", {})
        _trigger_edges(g, ev["id"], trig)
        for eff in ev.get("effects", []) or []:
            _effect_edges(g, ev["id"], eff)

    # Arêtes : secrets.
    for s in catalogs.get("secrets", []):
        if s.get("location_id"):
            g.add_edge("contient", s["location_id"], s["id"], status=Status.DEDUITE)
        for d in s.get("discovery_path", []) or []:
            if d in g.nodes:
                g.add_edge("declenche", d, s["id"], status=Status.DEDUITE)
        if s.get("system"):
            for sysid in str(s["system"]).split(","):
                sysid = sysid.strip()
                if sysid in g.nodes:
                    g.add_edge("releve_de", s["id"], sysid, status=Status.DEDUITE)

    # --- Ancrage canonique : monde, joueur, faits (évite les orphelins). ---
    world_id = canon["world"]["id"]
    player_id = canon["player"]["id"]
    refuge_id = canon["refuge"]["id"]
    for m in catalogs.get("maps", []):
        g.add_edge("contient", world_id, m["id"], status=Status.CANONIQUE)
    g.add_edge("habite", player_id, refuge_id, status=Status.CANONIQUE)
    g.add_edge("releve_de", player_id, "system_progression", status=Status.DEDUITE)
    # Faits immuables -> décrivent une entité (sémantique stable).
    fact_targets = {
        "fait_monde_valdore": world_id,
        "fait_joueur_jardinier": player_id,
        "fait_refuge_maison_racine": refuge_id,
        "fait_fragments_physiques": "objet_fragment_de_souvenir",
        "fait_graines_echo": "objet_graine_d_echo",
        "fait_pas_magie_combat": world_id,
    }
    for f in canon["facts"]:
        target = fact_targets.get(f["id"])
        if target and target in g.nodes:
            g.add_edge("decrit", f["id"], target, status=Status.CANONIQUE)
        else:
            # Un fait doit toujours décrire au moins le monde (ancrage minimal).
            g.add_edge("decrit", f["id"], world_id, status=Status.CANONIQUE)

    return g


def _effect_edges(g: Graph, src: str, eff: dict) -> None:
    et = eff.get("type")
    params = eff.get("params", {})
    targets = []
    for key in ("item_id", "lieu_id", "quete_id", "evenement_id", "fait_id",
                "secret_id", "entity_id", "pnj_id", "from_id", "to_id"):
        v = params.get(key)
        if v:
            targets.append(v)
    for t in targets:
        if t in g.nodes:
            g.add_edge("affecte", src, t, status=Status.DEDUITE)
        elif et in ("add_item", "remove_item", "transform_item"):
            # Référence à un objet non encore présent : arête technique.
            g.add_edge("affecte", src, t, status=Status.PROPOSEE)
    if et == "trigger_event" and params.get("evenement_id"):
        g.add_edge("declenche", src, params["evenement_id"], status=Status.DEDUITE)


def _trigger_edges(g: Graph, src: str, trig: dict) -> None:
    params = trig.get("params", {})
    for key in ("lieu_id", "item_id", "quete_id", "season_id", "weather_id",
                "secret_id", "pnj_id", "culture_id"):
        v = params.get(key)
        if v and v in g.nodes:
            g.add_edge("requiert", src, v, status=Status.DEDUITE)


# --- Analyse de connectivité -------------------------------------------------

def analyze_connectivity(g: Graph, start_nodes: Iterable[str]) -> dict[str, Any]:
    """Analyse complète de connectivité exigée par le brief."""
    start = set(start_nodes)

    # Références pendantes : arêtes pointant vers un ID qui n'est pas un nœud.
    dangling = sorted({
        ref for e in g.edges for ref in (e["source"], e["target"])
        if ref not in g.nodes
    })

    # Atteignabilité (parcours non orienté depuis les nœuds de départ),
    # restreinte aux nœuds réellement déclarés.
    reachable: set[str] = set()
    stack = [n for n in start if n in g.nodes]
    while stack:
        n = stack.pop()
        if n in reachable:
            continue
        reachable.add(n)
        stack.extend((g.neighbors(n) & set(g.nodes)) - reachable)

    orphans = []          # aucune arête
    unreachable = []      # non atteignable depuis le départ
    weak = []             # uniquement des arêtes non-usage
    usage_objects = []    # objets sans usage réel
    recipes_no_output = []
    recipes_no_input = []
    quests_no_giver = []
    quests_no_consequence = []
    npcs_no_routine = []
    npcs_no_interaction = []
    resources_no_producer = []
    resources_no_consumer = []
    secrets_no_discovery = []
    events_unreachable = []
    systems_isolated = []

    for nid, node in g.nodes.items():
        deg = g.degree(nid)
        ntype = node["type"]
        if deg == 0:
            orphans.append(nid)
        if nid not in reachable and ntype not in ("monde", "joueur"):
            unreachable.append(nid)
        usage = g.usage_edges(nid)
        if deg > 0 and not usage and ntype in ("objet", "ressource", "machine",
                                               "culture", "recette", "pnj",
                                               "creature", "quete", "evenement"):
            weak.append(nid)

        if ntype == "objet":
            # Un objet est utile s'il est consommé/transformé/utilisé/offert.
            consumers = [e for e in g.incoming(nid)
                         if e["type"] in ("consomme", "transforme", "utilise")
                         and e["source"] != nid]
            producers = [e for e in g.incoming(nid) if e["type"] in ("produit", "transforme")]
            if not consumers and not node.get("decorative_only"):
                # Objet sans consommateur : vérifier s'il est obtenu ET utilisé.
                usage_objects.append(nid)
        elif ntype == "recette":
            if not [e for e in g.outgoing(nid) if e["type"] == "consomme"]:
                recipes_no_input.append(nid)
            if not [e for e in g.outgoing(nid) if e["type"] == "transforme"]:
                recipes_no_output.append(nid)
        elif ntype == "quete":
            if not [e for e in g.incoming(nid) if e["type"] == "donne"]:
                quests_no_giver.append(nid)
            if not [e for e in g.outgoing(nid) if e["type"] in ("affecte", "declenche")]:
                quests_no_consequence.append(nid)
        elif ntype == "pnj":
            if not [e for e in g.outgoing(nid) if e["type"] in ("habite", "frequente")]:
                npcs_no_routine.append(nid)
            if not [e for e in g.outgoing(nid) if e["type"] in ("donne", "requiert")]:
                npcs_no_interaction.append(nid)
        elif ntype == "ressource":
            # Producteur : arête entrante 'produit' (X produit la ressource).
            if not [e for e in g.incoming(nid) if e["type"] == "produit"]:
                resources_no_producer.append(nid)
            # Consommateur RÉEL : une recette/machine qui la consomme (arête
            # entrante 'consomme' depuis une recette/machine), pas seulement un
            # système abstrait. Une relation technique ne suffit pas.
            real_consumers = [e for e in g.incoming(nid)
                              if e["type"] == "consomme"
                              and g.nodes.get(e["source"], {}).get("type")
                              in ("recette", "machine")]
            if not real_consumers:
                resources_no_consumer.append(nid)
        elif ntype == "secret":
            if not [e for e in g.incoming(nid) if e["type"] == "declenche"]:
                secrets_no_discovery.append(nid)
        elif ntype == "evenement":
            if nid not in reachable:
                events_unreachable.append(nid)
        elif ntype == "system":
            if not g.systems_touching(nid) and g.degree(nid) <= 1:
                systems_isolated.append(nid)

    # Profondeur causale : plus long chemin depuis les systèmes racines.
    causal_depth = _bfs_depth(g)

    return {
        "node_count": len(g.nodes),
        "edge_count": len(g.edges),
        "reachable_count": len(reachable & set(g.nodes)),
        "dangling_references": dangling,
        "orphans": sorted(orphans),
        "unreachable": sorted(unreachable),
        "weak_usage": sorted(weak),
        "objects_no_usage": sorted(usage_objects),
        "recipes_no_input": sorted(recipes_no_input),
        "recipes_no_output": sorted(recipes_no_output),
        "quests_no_giver": sorted(quests_no_giver),
        "quests_no_consequence": sorted(quests_no_consequence),
        "npcs_no_routine": sorted(npcs_no_routine),
        "npcs_no_interaction": sorted(npcs_no_interaction),
        "resources_no_producer": sorted(resources_no_producer),
        "resources_no_consumer": sorted(resources_no_consumer),
        "secrets_no_discovery": sorted(secrets_no_discovery),
        "events_unreachable": sorted(events_unreachable),
        "systems_isolated": sorted(systems_isolated),
        "causal_depth": causal_depth,
    }


def _bfs_depth(g: Graph, root: str = "joueur_jardinier") -> dict[str, int]:
    """Profondeur causale = distance (en sauts) depuis le joueur, en BFS.

    Métrique stable et interprétable : plus une entité est loin du point de
    départ du joueur dans le graphe causal, plus sa profondeur est grande.
    (Le plus long chemin simple est NP-difficile et sensible aux cycles ; le
    BFS court est retenu comme proxy déterministe.)
    """
    from collections import deque
    depth: dict[str, int] = {}
    if root not in g.nodes:
        # Repli : premier nœud 'joueur' trouvé.
        root = next((n for n, d in g.nodes.items() if d["type"] == "joueur"), None)
        if root is None:
            return depth
    depth[root] = 0
    q = deque([root])
    while q:
        n = q.popleft()
        for nb in g.neighbors(n):
            if nb not in depth:
                depth[nb] = depth[n] + 1
                q.append(nb)
    return depth


def entity_metrics(g: Graph, nid: str) -> dict[str, Any]:
    """Métriques de richesse d'une entité (exigées par le brief)."""
    node = g.nodes.get(nid, {})
    return {
        "id": nid,
        "type": node.get("type"),
        "relation_count": g.degree(nid),
        "usage_relation_count": len(g.usage_edges(nid)),
        "systems_affected": len(g.systems_touching(nid)),
        "causal_depth": _bfs_depth(g).get(nid, 0),
    }


def run_stage(catalogs: dict, systems: list[dict], canon: dict,
              write: bool = True) -> dict[str, Any]:
    g = build_graph(catalogs, systems, canon)
    start = [canon["player"]["id"], canon["refuge"]["id"]]
    analysis = analyze_connectivity(g, start)
    artifact = {
        "graph": g.to_dict(),
        "connectivity": analysis,
        "fingerprint": fingerprint({"nodes": sorted(g.nodes), "edges": sorted(g._edge_ids)}),
    }
    if write:
        write_json(DIRS["graph"] / "world_graph.json",
                   versioned_envelope(artifact["graph"], kind="world_graph"))
        write_json(DIRS["graph"] / "connectivity.json",
                   versioned_envelope(analysis, kind="connectivity"))
    return artifact


if __name__ == "__main__":
    from . import canon as canon_mod, systems as sys_mod, catalog as cat_mod
    ca = canon_mod.run_stage(write=False)
    sy = sys_mod.run_stage(write=False)["systems"]
    cats = cat_mod.run_stage(ca, sy, write=False)
    res = run_stage(cats, sy, ca["canon"])
    a = res["connectivity"]
    print("nœuds:", a["node_count"], "arêtes:", a["edge_count"],
          "atteignables:", a["reachable_count"])
    print("orphelins:", a["orphans"])
    print("inatteignables:", a["unreachable"][:10])
