"""Utilitaires partagés de la Pipeline V5 Graph-Driven.

Ce module ne dépend que de la bibliothèque standard Python 3.11+.
Il fournit : normalisation d'identifiants, statuts, versionnement,
gestion déterministe des graines, et lecture/écriture JSON sûre.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

# --- Versionnement de la pipeline -------------------------------------------

PIPELINE_VERSION = "5.0.0"
SCHEMA_VERSION = "5.0.0"

# Racine du dépôt de pipeline (deux niveaux au-dessus de tools/lib).
ROOT = Path(__file__).resolve().parents[2]

# Répertoires normalisés.
DIRS = {
    "input": ROOT / "INPUT",
    "contract": ROOT / "CONTRACT",
    "ontology": ROOT / "ONTOLOGY",
    "schemas": ROOT / "SCHEMAS",
    "canon": ROOT / "CANON",
    "systems": ROOT / "GAME" / "systems",
    "functional_catalog": ROOT / "GAME" / "functional_catalog",
    "graph": ROOT / "GAME" / "graph",
    "catalogs": ROOT / "GAME" / "catalogs",
    "manifests": ROOT / "GAME" / "manifests",
    "prompt_templates": ROOT / "PROMPTS" / "templates",
    "prompt_generated": ROOT / "PROMPTS" / "generated",
    "prompt_examples": ROOT / "PROMPTS" / "examples",
    "reports": ROOT / "REPORTS",
    "doc": ROOT / "DOC",
    "output": ROOT / "OUTPUT",
    "engine_out": ROOT / "ENGINE_OUT",
}


# --- Statuts d'information ---------------------------------------------------

class Status:
    """Les quatre statuts exigés par le brief de pipeline.

    CANONIQUE : information explicitement définie et non négociable.
    DEDUITE   : information dérivée logiquement du canon ou des systèmes.
    PROPOSEE  : recommandation technique ou créative proposée par la pipeline.
    A_VALIDER : décision qui dépend encore du propriétaire du projet.

    Le contrat V2 nomme ces statuts en anglais (CANONICAL, DERIVED, PROPOSED,
    TO_VALIDATE). Les valeurs internes restent françaises (aucun remplacement
    silencieux de l'existant) ; `EN`/`FR` fournissent la correspondance
    officielle pour les artefacts orientés V2 (traçabilité, maturité).
    """

    CANONIQUE = "CANONIQUE"
    DEDUITE = "DEDUITE"
    PROPOSEE = "PROPOSEE"
    A_VALIDER = "A_VALIDER"

    ALL = (CANONIQUE, DEDUITE, PROPOSEE, A_VALIDER)

    # Ordre de confiance décroissant (utile pour les rapports).
    ORDER = {CANONIQUE: 0, DEDUITE: 1, PROPOSEE: 2, A_VALIDER: 3}

    # Correspondance officielle V1 (FR) <-> V2 (EN).
    EN = {CANONIQUE: "CANONICAL", DEDUITE: "DERIVED",
          PROPOSEE: "PROPOSED", A_VALIDER: "TO_VALIDATE"}
    FR = {v: k for k, v in EN.items()}

    @classmethod
    def to_v2(cls, status: str) -> str:
        """Traduit un statut interne (FR) vers le vocabulaire du contrat V2."""
        return cls.EN.get(status, status)


class Maturity:
    """Échelle de maturité V2 (contrat d'architecture, section 'Statuts').

    Chaque entité/domaine progresse :
    SPECIFIED -> SCHEMA_VALIDATED -> IMPORTED -> CATALOGED -> GRAPH_CONNECTED
    -> COMPILED -> RUNTIME_TESTED -> PRODUCTION_READY.

    Règle dure du contrat : PRODUCTION_READY exige RUNTIME_TESTED (test
    d'intégration runtime réel). `promote()` refuse toute promotion qui saute
    un échelon ou déclare PRODUCTION_READY sans RUNTIME_TESTED.
    """

    SPECIFIED = "SPECIFIED"
    SCHEMA_VALIDATED = "SCHEMA_VALIDATED"
    IMPORTED = "IMPORTED"
    CATALOGED = "CATALOGED"
    GRAPH_CONNECTED = "GRAPH_CONNECTED"
    COMPILED = "COMPILED"
    RUNTIME_TESTED = "RUNTIME_TESTED"
    PRODUCTION_READY = "PRODUCTION_READY"

    LADDER = (SPECIFIED, SCHEMA_VALIDATED, IMPORTED, CATALOGED,
              GRAPH_CONNECTED, COMPILED, RUNTIME_TESTED, PRODUCTION_READY)
    RANK = {s: i for i, s in enumerate(LADDER)}

    @classmethod
    def from_evidence(cls, evidence: dict) -> str:
        """Calcule le statut le plus élevé JUSTIFIÉ par les preuves.

        `evidence` : dict échelon -> bool (preuves réelles : schéma présent et
        validé, import réel accepté, catalogue alimenté, nœuds dans le graphe,
        entités dans la sortie compilée, test runtime réel passé).
        Un échelon manquant arrête la progression (pas de saut).
        """
        reached = None
        for step in cls.LADDER:
            if evidence.get(step):
                reached = step
            else:
                break
        return reached or "SPECIFIED"

    @classmethod
    def promote(cls, current: str, target: str, *, runtime_tested: bool) -> str:
        """Promotion contrôlée : interdit les sauts et PRODUCTION_READY sans
        RUNTIME_TESTED (lève ValueError sinon)."""
        if cls.RANK[target] > cls.RANK[current] + 1:
            raise ValueError(f"promotion invalide {current} -> {target} (saut d'échelon)")
        if target == cls.PRODUCTION_READY and not runtime_tested:
            raise ValueError("PRODUCTION_READY interdit sans test d'intégration runtime")
        return target


# --- Normalisation d'identifiants -------------------------------------------

# Caractères sûrs pour un ID interne : lettres minuscules, chiffres, underscore.
_UNSAFE = re.compile(r"[^a-z0-9_]+")


def strip_accents(s: str) -> str:
    """Retire les diacritiques via décomposition Unicode (NFKD)."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Cas non décomposables courants en français.
    for a, b in (("œ", "oe"), ("Œ", "OE"), ("æ", "ae"), ("Æ", "AE"),
                 ("ß", "ss"), ("ø", "o"), ("Ø", "O"), ("ł", "l"), ("Ł", "L")):
        s = s.replace(a, b)
    return s


def slugify(text: str, prefix: str = "") -> str:
    """Produit un identifiant interne stable.

    Règles (imposées par le brief) :
    - stable, unique ;
    - minuscules ;
    - sans espaces ;
    - sans accents ;
    - uniquement caractères sûrs et underscores.

    Exemple : 'Arrosoir de cuivre' -> 'arrosoir_de_cuivre'.
    """
    if text is None:
        return ""
    s = strip_accents(str(text))
    s = s.lower()
    s = s.replace("'", "_").replace("-", "_").replace("’", "_")
    s = _UNSAFE.sub("_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if prefix:
        p = slugify(prefix)
        s = f"{p}_{s}" if s else p
    # Un ID ne doit jamais commencer par un chiffre (sécurité moteurs/JSON keys).
    if s and s[0].isdigit():
        s = "x_" + s
    return s


def make_id(category: str, name: str) -> str:
    """Construit un ID interne typé : 'objet_pioche_cuivre'."""
    return slugify(name, prefix=category)


def is_valid_id(value: str) -> bool:
    """Vérifie qu'une chaîne respecte les règles d'ID interne."""
    if not isinstance(value, str) or not value:
        return False
    if value != value.lower():
        return False
    if " " in value:
        return False
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*", value))


# --- Determinisme / graines --------------------------------------------------

DEFAULT_SEED = 20260922


def derive_seed(*parts: Any, base: int = DEFAULT_SEED) -> int:
    """Dérive une graine déterministe 32 bits à partir de parties stables.

    Garantit la reproductibilité des générations procédurales : mêmes
    entrées -> même graine -> même sortie.
    """
    joined = "|".join(str(p) for p in parts)
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % (2**31 - 1) ^ (base & 0xFFFF)


def fingerprint(obj: Any) -> str:
    """Empreinte stable et unique d'un objet JSON (pour dédoublonnage/assets)."""
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# --- I/O JSON sûre -----------------------------------------------------------

def read_json(path: Path, default: Any = None) -> Any:
    """Lit un JSON en UTF-8. Retourne `default` si absent."""
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data: Any, *, indent: int = 2) -> Path:
    """Écrit un JSON en UTF-8 (sans BOM), crée les dossiers parents.

    `sort_keys=True` garantit une sérialisation **déterministe** : à entrées et
    graines fixées, deux runs produisent des fichiers octet pour octet identiques
    (l'ordre d'insertion des dicts/sets ne fuite plus dans les artefacts).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=indent, sort_keys=True)
        fh.write("\n")
    return path


def read_text(path: Path, default: str = "") -> str:
    path = Path(path)
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def versioned_envelope(payload: dict, *, kind: str, version: str = SCHEMA_VERSION,
                       seed: int | None = None) -> dict:
    """Enveloppe standard versionnée pour tout artefact JSON de la pipeline.

    Permet le versionnement des données, les migrations et la
    reproductibilité (graine enregistrée).
    """
    env = {
        "pipeline_version": PIPELINE_VERSION,
        "schema_version": version,
        "kind": kind,
        "generated_deterministic": True,
    }
    if seed is not None:
        env["seed"] = seed
    env["payload"] = payload
    return env


def unwrap(envelope: dict) -> Any:
    """Extrait le payload d'une enveloppe versionnée (tolère le brut)."""
    if isinstance(envelope, dict) and "payload" in envelope:
        return envelope["payload"]
    return envelope


def now_iso() -> str:
    """Horodatage ISO stable (sans microsecondes) pour les rapports."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
