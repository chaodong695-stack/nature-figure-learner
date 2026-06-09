#!/usr/bin/env python3
"""
Self-evolution engine for the Figure Knowledge Base.

This script is a helper that an agent may run. It does not execute by itself
and it does not replace agent judgment. The agent remains responsible for
asking for feedback, deciding whether to write KB updates, and explaining
recommendations to the user.

Implemented mechanisms:
1. Memory scoring and learning artifact backfill
2. Pattern pruning with archive-first safety
3. Pattern generalization into meta-patterns
4. Style reflection synthesis
5. Relationship inference between patterns
6. Extraction failure analysis and active learning guidance
7. KB health scoring
"""

import json
import math
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, median


ALL_CHART_TYPES = [
    "grouped-bar", "stacked-bar", "horizontal-bar", "line-trend", "multi-line",
    "heatmap", "scatter", "bubble", "radar-polar", "forest-plot", "violin",
    "box", "density", "pie-donut", "fill-between", "sankey", "upset",
    "image-plate", "schematic", "network",
]


class EvolutionEngine:
    def __init__(self, kb_path):
        self.kb_path = Path(kb_path)
        self.index_file = self.kb_path / "index.json"
        self.archive_path = self.kb_path / "archive"
        self.meta_patterns_path = self.kb_path / "meta-patterns"
        self.reflections_path = self.kb_path / "reflections"

        (self.archive_path / "never-used").mkdir(parents=True, exist_ok=True)
        (self.archive_path / "low-quality").mkdir(parents=True, exist_ok=True)
        (self.archive_path / "superseded").mkdir(parents=True, exist_ok=True)
        self.meta_patterns_path.mkdir(parents=True, exist_ok=True)
        self.reflections_path.mkdir(parents=True, exist_ok=True)

    def load_index(self):
        """Load KB index."""
        if not self.index_file.exists():
            return []
        with open(self.index_file, encoding="utf-8") as f:
            return json.load(f)

    def save_index(self, index):
        """Save KB index."""
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Mechanism 1: memory scoring and learning artifact backfill
    # ------------------------------------------------------------------

    def compute_memory_score(self, entry, now=None):
        """
        Compute a composite 0-100 memory score.

        The score is a retrieval preference, not a truth claim. It combines
        user/system quality, self-validation, real reuse, feedback trend, and
        recency so agents can rank patterns without relying on a single field.
        """
        now = now or datetime.now()

        quality = self._bounded_number(entry.get("quality_rating"), 0, 5)
        validation = self._bounded_number(entry.get("validation_score"), 0, 5)
        uses = max(0, int(entry.get("application_count", 0) or 0))
        feedback = entry.get("application_feedback", []) or []

        feedback_ratings = [
            self._bounded_number(item.get("rating"), 0, 5)
            for item in feedback
            if item.get("rating") is not None
        ]
        avg_feedback = mean(feedback_ratings) if feedback_ratings else quality

        recency = self._recency_factor(entry.get("analysis_date"), now)
        usage_factor = min(1.0, math.log1p(uses) / math.log1p(10))

        components = {
            "quality": round((quality / 5) * 30, 2),
            "validation": round((validation / 5) * 25, 2),
            "reuse": round(usage_factor * 15, 2),
            "feedback": round((avg_feedback / 5) * 20, 2),
            "recency": round(recency * 10, 2),
        }
        total = round(sum(components.values()), 2)

        return {
            "total": total,
            "components": components,
            "formula": "quality30+validation25+reuse15+feedback20+recency10",
        }

    def enrich_memory_artifacts(self, index):
        """Backfill memory_score, success/failure cases, and relationships."""
        now = datetime.now()
        enriched = []
        for entry in index:
            if entry.get("type") == "meta_pattern":
                enriched.append(entry)
                continue

            item = dict(entry)
            item["memory_score"] = self.compute_memory_score(item, now=now)
            item["success_cases"] = self._extract_cases(item, positive=True)
            item["failure_cases"] = self._extract_cases(item, positive=False)
            item["recommendation_rationale"] = self._build_recommendation_rationale(item)
            enriched.append(item)

        for item in enriched:
            if item.get("type") == "meta_pattern":
                continue
            item["relations"] = self._infer_relations(item, enriched)

        self.save_index(enriched)
        return enriched

    def _extract_cases(self, entry, positive):
        cases = []
        for feedback in entry.get("application_feedback", []) or []:
            rating = feedback.get("rating")
            notes = (feedback.get("notes") or "").strip()
            if not notes:
                continue
            if positive and rating is not None and rating >= 4:
                cases.append({"date": feedback.get("date"), "note": notes})
            if not positive and rating is not None and rating <= 3:
                cases.append({"date": feedback.get("date"), "note": notes})
        return cases[:5]

    def _build_recommendation_rationale(self, entry):
        score = entry.get("memory_score") or self.compute_memory_score(entry)
        components = score.get("components", {})
        reasons = []

        if components.get("quality", 0) >= 24:
            reasons.append("high quality rating")
        if components.get("validation", 0) >= 20:
            reasons.append("high self-validation")
        if components.get("reuse", 0) >= 6:
            reasons.append("reused in prior figure work")
        if entry.get("success_cases"):
            reasons.append("positive user feedback")
        if entry.get("failure_cases"):
            reasons.append("has known caveats to check before reuse")

        if not reasons:
            reasons.append("available pattern with limited evidence")

        return "; ".join(reasons)

    def _infer_relations(self, entry, index):
        similar = []
        superseded_by = []
        contraindicated_for = []
        entry_score = (entry.get("memory_score") or {}).get("total", 0)

        for other in index:
            if other.get("id") == entry.get("id") or other.get("type") == "meta_pattern":
                continue
            if self._same_pattern_family(entry, other):
                similar.append(other["id"])
                other_score = (other.get("memory_score") or {}).get("total", 0)
                if other_score >= entry_score + 15:
                    superseded_by.append(other["id"])

        for case in entry.get("failure_cases", []):
            contraindicated_for.extend(self._extract_contraindications(case.get("note", "")))

        return {
            "similar_to": similar[:5],
            "superseded_by": superseded_by[:3],
            "contraindicated_for": sorted(set(contraindicated_for)),
        }

    def _same_pattern_family(self, left, right):
        return (
            left.get("chart_type") == right.get("chart_type")
            and left.get("layout_archetype") == right.get("layout_archetype")
            and left.get("color_scheme") == right.get("color_scheme")
        )

    def _extract_contraindications(self, note):
        note_l = note.lower()
        tags = []
        keyword_map = {
            "dense": "dense-panels",
            "small": "small-text",
            "legend": "legend-heavy",
            "color": "color-sensitive",
            "contrast": "low-contrast",
            "crowd": "crowded-layout",
        }
        for keyword, tag in keyword_map.items():
            if keyword in note_l:
                tags.append(tag)
        return tags

    # ------------------------------------------------------------------
    # Mechanism 2: pattern pruning
    # ------------------------------------------------------------------

    def prune_patterns(self, index):
        """
        Archive low-value patterns. Entries are removed from index only after
        their pattern file is successfully archived.
        """
        to_archive = []
        now = datetime.now()

        for entry in index:
            if entry.get("type") == "meta_pattern":
                continue
            pattern_id = entry.get("id")
            analysis_date = self._parse_date(entry.get("analysis_date"), now)
            age_days = (now - analysis_date).days
            quality = entry.get("quality_rating")
            feedback = entry.get("application_feedback", []) or []

            if age_days > 180 and entry.get("application_count", 0) == 0:
                to_archive.append((pattern_id, "never-used", entry))
                continue
            if quality is not None and quality < 2.5 and len(feedback) >= 3:
                to_archive.append((pattern_id, "low-quality", entry))
                continue

            similar = self._find_similar_patterns(entry, index)
            if len(similar) >= 2 and quality is not None:
                if all((s.get("quality_rating") or 0) > quality + 1.0 for s in similar):
                    to_archive.append((pattern_id, "superseded", entry))

        archived_ids = []
        for pattern_id, reason, entry in to_archive:
            if self._archive_pattern(entry, reason):
                archived_ids.append(pattern_id)

        if archived_ids:
            new_index = [e for e in index if e.get("id") not in archived_ids]
            self.save_index(new_index)

        return [(pid, reason, entry) for pid, reason, entry in to_archive if pid in archived_ids][:5]

    def _find_similar_patterns(self, pattern, index):
        return [
            entry for entry in index
            if entry.get("id") != pattern.get("id")
            and entry.get("type") != "meta_pattern"
            and pattern.get("chart_type") == entry.get("chart_type")
            and pattern.get("layout_archetype") == entry.get("layout_archetype")
        ]

    def _archive_pattern(self, entry, reason):
        pattern_file = self.kb_path / entry.get("file", "")
        if not pattern_file.exists():
            return False

        archive_dest = self.archive_path / reason / pattern_file.name
        archive_dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.move(str(pattern_file), str(archive_dest))
            return True
        except OSError as exc:
            print(f"Failed to archive {entry.get('id')}: {exc}")
            return False

    # ------------------------------------------------------------------
    # Mechanism 3: pattern generalization
    # ------------------------------------------------------------------

    def generalize_patterns(self, index):
        """Detect similar clusters and create meta-patterns."""
        clusters = defaultdict(list)
        for entry in index:
            if entry.get("type") == "meta_pattern":
                continue
            key = (
                entry.get("chart_type"),
                entry.get("color_scheme"),
                entry.get("layout_archetype"),
            )
            clusters[key].append(entry)

        meta_patterns = []
        for cluster in clusters.values():
            if len(cluster) >= 5:
                meta = self._synthesize_meta_pattern(cluster)
                if meta:
                    meta_patterns.append(meta)
                    self._save_meta_pattern(meta)

        return meta_patterns

    def _synthesize_meta_pattern(self, cluster):
        if not cluster:
            return None

        common_features = {
            "chart_type": cluster[0].get("chart_type"),
            "color_scheme": cluster[0].get("color_scheme"),
            "layout_archetype": cluster[0].get("layout_archetype"),
            "font_family": self._mode([p.get("font_family") for p in cluster if p.get("font_family")]),
            "base_font_size_pt": self._median([p.get("base_font_size_pt") for p in cluster if p.get("base_font_size_pt")]),
        }

        panel_counts = [p.get("panel_count") for p in cluster if p.get("panel_count")]
        scores = [
            (p.get("memory_score") or {}).get("total")
            for p in cluster
            if (p.get("memory_score") or {}).get("total") is not None
        ]
        qualities = [p.get("quality_rating") for p in cluster if p.get("quality_rating") is not None]

        variable_parameters = {
            "panel_count": {
                "range": [min(panel_counts), max(panel_counts)] if panel_counts else [1, 1],
                "typical": int(self._median(panel_counts)) if panel_counts else 1,
            }
        }

        meta_pattern = {
            "id": self._stable_meta_id(common_features, len(cluster)),
            "type": "meta_pattern",
            "name": self._generate_meta_name(common_features),
            "covers": [p["id"] for p in cluster],
            "common_features": common_features,
            "variable_parameters": variable_parameters,
            "usage_stats": {
                "total_uses": sum(p.get("application_count", 0) for p in cluster),
                "avg_quality": round(mean(qualities), 2) if qualities else None,
                "avg_memory_score": round(mean(scores), 2) if scores else None,
                "source_count": len(cluster),
            },
            "created": datetime.now().isoformat(timespec="seconds"),
        }

        return meta_pattern

    def _stable_meta_id(self, features, count):
        raw = "-".join(str(features.get(k) or "unknown") for k in ("color_scheme", "chart_type", "layout_archetype"))
        slug = re.sub(r"[^a-zA-Z0-9-]+", "-", raw).strip("-").lower()
        return f"meta-{slug}-{count}"

    def _generate_meta_name(self, features):
        chart_type = (features.get("chart_type") or "pattern").replace("-", " ").title()
        color_scheme = (features.get("color_scheme") or "unknown").replace("-", " ").title()
        return f"{color_scheme} {chart_type}"

    def _save_meta_pattern(self, meta):
        filename = self.meta_patterns_path / f"{meta['id']}.md"
        content = "\n".join([
            "---",
            json.dumps(meta, indent=2, ensure_ascii=False),
            "---",
            "",
            f"# Meta-Pattern: {meta['name']}",
            "",
            "## Summary",
            f"Generalized from {meta['usage_stats']['source_count']} specific instances.",
            "Use this as guidance only; the agent must still adapt it to the user's data and figure claim.",
            "",
            "## Common Features",
            self._format_features(meta["common_features"]),
            "",
            "## Variable Parameters",
            self._format_variables(meta["variable_parameters"]),
            "",
            "## Usage Statistics",
            f"- Total uses: {meta['usage_stats']['total_uses']}",
            f"- Average quality: {meta['usage_stats']['avg_quality']}/5",
            f"- Average memory score: {meta['usage_stats']['avg_memory_score']}/100",
            f"- Source patterns: {meta['usage_stats']['source_count']}",
            "",
            "## Adaptation Guide",
            "1. Choose parameter values within the documented ranges.",
            "2. Preserve the common features only when they support the current scientific claim.",
            "3. Ask the user for feedback after applying the meta-pattern.",
            "",
        ])
        filename.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Mechanism 4: style reflections
    # ------------------------------------------------------------------

    def synthesize_style_reflections(self, index):
        """Create short reusable style reflections for mature clusters."""
        clusters = defaultdict(list)
        for entry in index:
            if entry.get("type") == "meta_pattern":
                continue
            key = (
                entry.get("chart_type"),
                entry.get("color_scheme"),
                entry.get("layout_archetype"),
            )
            clusters[key].append(entry)

        reflections = []
        for key, cluster in clusters.items():
            if len(cluster) < 5:
                continue
            reflection = self._build_style_reflection(key, cluster)
            reflections.append(reflection)
            self._save_style_reflection(reflection)

        return reflections

    def _build_style_reflection(self, key, cluster):
        chart_type, color_scheme, layout = key
        successes = Counter()
        failures = Counter()
        for entry in cluster:
            for case in entry.get("success_cases", []):
                successes.update(self._keywords(case.get("note", "")))
            for case in entry.get("failure_cases", []):
                failures.update(self._keywords(case.get("note", "")))

        scores = [
            (entry.get("memory_score") or {}).get("total")
            for entry in cluster
            if (entry.get("memory_score") or {}).get("total") is not None
        ]

        return {
            "id": self._stable_reflection_id(chart_type, color_scheme, layout),
            "type": "style_reflection",
            "chart_type": chart_type,
            "color_scheme": color_scheme,
            "layout_archetype": layout,
            "source_patterns": [entry["id"] for entry in cluster],
            "avg_memory_score": round(mean(scores), 2) if scores else None,
            "what_works": [word for word, _ in successes.most_common(5)],
            "watch_out_for": [word for word, _ in failures.most_common(5)],
            "agent_guidance": (
                f"For {chart_type} with {color_scheme} in {layout}, start from the "
                "highest memory-score pattern, preserve validated layout/color choices, "
                "and check known failure cases before reuse."
            ),
            "created": datetime.now().isoformat(timespec="seconds"),
        }

    def _stable_reflection_id(self, chart_type, color_scheme, layout):
        raw = f"{chart_type}-{color_scheme}-{layout}"
        slug = re.sub(r"[^a-zA-Z0-9-]+", "-", raw).strip("-").lower()
        return f"reflection-{slug}"

    def _save_style_reflection(self, reflection):
        filename = self.reflections_path / f"{reflection['id']}.md"
        content = "\n".join([
            "---",
            json.dumps(reflection, indent=2, ensure_ascii=False),
            "---",
            "",
            f"# Style Reflection: {reflection['chart_type']}",
            "",
            f"- Color scheme: {reflection['color_scheme']}",
            f"- Layout archetype: {reflection['layout_archetype']}",
            f"- Average memory score: {reflection['avg_memory_score']}/100",
            f"- What works: {', '.join(reflection['what_works']) or 'not enough positive feedback yet'}",
            f"- Watch out for: {', '.join(reflection['watch_out_for']) or 'not enough failure feedback yet'}",
            "",
            "## Agent Guidance",
            reflection["agent_guidance"],
            "",
        ])
        filename.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Mechanism 5: extraction failure analysis and recommendations
    # ------------------------------------------------------------------

    def analyze_extraction_failures(self, index):
        failures = [e for e in index if e.get("validation_score", 5) < 3]
        if len(failures) < 5:
            return None

        failure_categories = {
            "color_extraction": [],
            "font_size_estimation": [],
            "layout_detection": [],
            "pattern_matching": [],
        }

        for entry in failures:
            notes = (entry.get("validation_notes") or "").lower()
            if any(kw in notes for kw in ["color", "palette", "saturation"]):
                failure_categories["color_extraction"].append(entry)
            if any(kw in notes for kw in ["font", "size", "typography", "pt"]):
                failure_categories["font_size_estimation"].append(entry)
            if any(kw in notes for kw in ["layout", "grid", "spacing", "proportion"]):
                failure_categories["layout_detection"].append(entry)
            if any(kw in notes for kw in ["pattern", "archetype", "match"]):
                failure_categories["pattern_matching"].append(entry)

        weakest_layer = max(failure_categories.items(), key=lambda item: len(item[1]))
        if not weakest_layer[1]:
            return None

        return {
            "weakest_layer": weakest_layer[0],
            "failure_count": len(weakest_layer[1]),
            "examples": weakest_layer[1][:3],
            "improvement_strategy": self._generate_correction_strategy(weakest_layer[0]),
        }

    def _generate_correction_strategy(self, layer):
        strategies = {
            "color_extraction": [
                "Sample colors from multiple panel regions.",
                "Compare saturation/luminance, not only dominant RGB counts.",
                "Check whether the palette is semantically consistent across panels.",
            ],
            "font_size_estimation": [
                "Estimate final print scaling before assigning point sizes.",
                "Use relative size ratios between panel labels, axis labels, and ticks.",
                "Flag sizes outside common journal ranges for manual review.",
            ],
            "layout_detection": [
                "Detect panel labels and whitespace before deciding grid structure.",
                "Validate the grid against the four known layout archetypes.",
                "Record aspect ratios for hero/support panels.",
            ],
            "pattern_matching": [
                "Weight chart type and layout higher than color.",
                "Allow novel-pattern classification when no close match exists.",
                "Use reuse success as evidence that a match is practical.",
            ],
        }
        return strategies.get(layer, ["No specific strategy available."])

    def generate_learning_recommendations(self, index):
        recommendations = []
        chart_types_present = {e.get("chart_type") for e in index if e.get("chart_type")}

        for chart_type in [t for t in ALL_CHART_TYPES if t not in chart_types_present][:3]:
            recommendations.append({
                "priority": "HIGH",
                "action": f"Analyze 1-2 {chart_type} examples",
                "reason": f"KB has zero {chart_type} patterns",
                "impact": "Fill a coverage gap",
            })

        quality_by_type = defaultdict(list)
        for entry in index:
            if entry.get("quality_rating") is not None:
                quality_by_type[entry.get("chart_type")].append(entry["quality_rating"])

        weak_types = [
            (chart_type, mean(ratings))
            for chart_type, ratings in quality_by_type.items()
            if chart_type and mean(ratings) < 3.5
        ]
        for chart_type, avg_quality in sorted(weak_types, key=lambda item: item[1])[:2]:
            recommendations.append({
                "priority": "MEDIUM",
                "action": f"Improve {chart_type} patterns",
                "reason": f"Current average quality is {avg_quality:.1f}/5",
                "impact": "Raise quality in a weak chart type",
            })

        declining = self._patterns_with_declining_feedback(index)
        for entry in declining[:2]:
            recommendations.append({
                "priority": "MEDIUM",
                "action": f"Review {entry['id']} before reusing it",
                "reason": "Recent feedback is lower than historical quality",
                "impact": "Avoid repeating known design issues",
            })

        best = sorted(
            [e for e in index if (e.get("memory_score") or {}).get("total") is not None],
            key=lambda e: e["memory_score"]["total"],
            reverse=True,
        )
        if best:
            top = best[0]
            recommendations.append({
                "priority": "INSIGHT",
                "action": f"Use {top['id']} as a reference for similar {top.get('chart_type')} figures",
                "reason": top.get("recommendation_rationale", "highest memory score"),
                "impact": "Leverage the strongest learned pattern",
            })

        return recommendations

    def _patterns_with_declining_feedback(self, index):
        declining = []
        for entry in index:
            feedback = entry.get("application_feedback", []) or []
            if len(feedback) < 3 or entry.get("quality_rating") is None:
                continue
            recent = [f.get("rating") for f in feedback[-3:] if f.get("rating") is not None]
            if recent and mean(recent) <= entry["quality_rating"] - 0.5:
                declining.append(entry)
        return declining

    # ------------------------------------------------------------------
    # Utilities and orchestration
    # ------------------------------------------------------------------

    def calculate_kb_health(self, index):
        if not index:
            return 0

        unique_types = len({e.get("chart_type") for e in index if e.get("chart_type")})
        coverage_score = (unique_types / len(ALL_CHART_TYPES)) * 30

        memory_scores = [
            (e.get("memory_score") or {}).get("total")
            for e in index
            if (e.get("memory_score") or {}).get("total") is not None
        ]
        memory_score = (mean(memory_scores) / 100) * 35 if memory_scores else 0

        active = len([e for e in index if e.get("application_count", 0) > 0])
        usage_score = (active / len(index)) * 20

        feedback_ready = len([
            e for e in index
            if e.get("success_cases") or e.get("failure_cases")
        ])
        feedback_score = (feedback_ready / len(index)) * 15

        return int(coverage_score + memory_score + usage_score + feedback_score)

    def run_full_evolution(self):
        print("Loading KB index...")
        index = self.load_index()
        if not index:
            return {"error": "KB is empty"}

        print("[1/6] Backfilling memory scores and learning artifacts...")
        index = self.enrich_memory_artifacts(index)

        print("[2/6] Running archive-first pattern pruning...")
        pruned = self.prune_patterns(index)
        index = self.load_index()

        print("[3/6] Running pattern generalization...")
        meta_patterns = self.generalize_patterns(index)

        print("[4/6] Synthesizing style reflections...")
        style_reflections = self.synthesize_style_reflections(index)

        print("[5/6] Analyzing extraction failures and learning recommendations...")
        correction = self.analyze_extraction_failures(index)
        recommendations = self.generate_learning_recommendations(index)

        print("[6/6] Calculating KB health...")
        health = self.calculate_kb_health(index)

        return {
            "pruned": pruned,
            "meta_patterns": meta_patterns,
            "style_reflections": style_reflections,
            "correction": correction,
            "recommendations": recommendations,
            "kb_health": health,
        }

    def _mode(self, values):
        if not values:
            return None
        return Counter(values).most_common(1)[0][0]

    def _median(self, values):
        if not values:
            return None
        return median(values)

    def _bounded_number(self, value, low, high):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return low
        return max(low, min(high, number))

    def _parse_date(self, value, fallback):
        if not value:
            return fallback
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            try:
                return datetime.fromisoformat(str(value)[:10])
            except ValueError:
                return fallback

    def _recency_factor(self, value, now):
        date = self._parse_date(value, now)
        age_days = max(0, (now - date).days)
        return max(0.0, 1.0 - (age_days / 180))

    def _keywords(self, text):
        words = re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", text.lower())
        stop = {
            "and", "the", "for", "with", "this", "that", "from", "too",
            "good", "bad", "figure", "panel", "panels",
        }
        return [word for word in words if word not in stop]

    def _format_features(self, features):
        return "\n".join(f"- **{key}**: {value}" for key, value in features.items())

    def _format_variables(self, variables):
        lines = []
        for key, value in variables.items():
            if isinstance(value, dict):
                lines.append(f"- **{key}**: {value.get('range', [])} (typical: {value.get('typical', 'N/A')})")
            else:
                lines.append(f"- **{key}**: {value}")
        return "\n".join(lines)


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scripts/self_evolution_engine.py <kb_path>")
        sys.exit(1)

    engine = EvolutionEngine(sys.argv[1])
    results = engine.run_full_evolution()

    print("")
    print("=" * 60)
    print("Self-Evolution Report")
    print("=" * 60)

    if "error" in results:
        print(results["error"])
        return

    print(f"Patterns pruned: {len(results.get('pruned', []))}")
    for pattern_id, reason, _entry in results.get("pruned", []):
        print(f"  - {pattern_id} (reason: {reason})")

    print(f"Meta-patterns created: {len(results.get('meta_patterns', []))}")
    for meta in results.get("meta_patterns", []):
        print(f"  - {meta['id']}: {meta['name']} ({meta['usage_stats']['source_count']} sources)")

    print(f"Style reflections created: {len(results.get('style_reflections', []))}")
    for reflection in results.get("style_reflections", []):
        print(f"  - {reflection['id']} (avg memory: {reflection['avg_memory_score']})")

    correction = results.get("correction")
    if correction:
        print("Extraction issues detected:")
        print(f"  - weak layer: {correction['weakest_layer']}")
        print(f"  - failure count: {correction['failure_count']}")

    print(f"Learning recommendations: {len(results.get('recommendations', []))}")
    for rec in results.get("recommendations", [])[:5]:
        print(f"  - {rec['priority']}: {rec['action']} ({rec['reason']})")

    print(f"KB health score: {results.get('kb_health', 0)}/100")
    print("=" * 60)


if __name__ == "__main__":
    main()
