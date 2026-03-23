import difflib
from typing import List, Dict, Any


def generate_section_diff(old_content: str, new_content: str) -> List[str]:
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))
    return [line for line in diff if line.startswith('+') or line.startswith('-')]


def detect_terminology_swaps(removals: List[str], additions: List[str]) -> List[Dict[str, str]]:
    swaps = []

    for rem in removals:
        for add in additions:
            ratio = difflib.SequenceMatcher(None, rem.lower(), add.lower()).ratio()
            if 0.5 < ratio < 0.95 and len(rem) > 10 and len(add) > 10:
                rem_words = set(rem.lower().split())
                add_words = set(add.lower().split())
                removed_words = rem_words - add_words
                added_words = add_words - rem_words

                if removed_words and added_words and len(removed_words) <= 5:
                    swaps.append({
                        "old_text": ' '.join(sorted(removed_words)),
                        "new_text": ' '.join(sorted(added_words)),
                        "context_old": rem[:100],
                        "context_new": add[:100]
                    })

    seen = set()
    unique_swaps = []
    for s in swaps:
        key = (s["old_text"], s["new_text"])
        if key not in seen:
            seen.add(key)
            unique_swaps.append(s)

    return unique_swaps[:10]


def summarize_comparison_with_ollama(
    alignment: Dict[str, Any],
    doc_name: str
) -> Dict[str, Any]:
    summary = {
        "document": doc_name,
        "structural_changes": [],
        "content_changes": [],
        "statistics": {
            "total_matched": len(alignment["matched"]),
            "total_added": len(alignment["added"]),
            "total_removed": len(alignment["removed"]),
            "total_split": len(alignment["split"]),
            "total_merged": len(alignment["merged"])
        }
    }

    for pair in alignment["matched"]:
        diff_lines = generate_section_diff(pair["old_content"], pair["new_content"])

        additions = [l[1:].strip() for l in diff_lines if l.startswith('+') and not l.startswith('+++')]
        removals = [l[1:].strip() for l in diff_lines if l.startswith('-') and not l.startswith('---')]

        change_detail = {
            "old_section": pair["old_section"],
            "new_section": pair["new_section"],
            "old_title": pair["old_title"],
            "new_title": pair["new_title"],
            "similarity": pair["similarity"],
            "change_type": pair["change_type"],
            "additions_count": len(additions),
            "removals_count": len(removals),
            "sample_additions": additions[:5],
            "sample_removals": removals[:5]
        }

        terminology_changes = detect_terminology_swaps(removals, additions)
        if terminology_changes:
            change_detail["terminology_changes"] = terminology_changes

        summary["content_changes"].append(change_detail)

    for added in alignment["added"]:
        summary["structural_changes"].append({
            "type": "added",
            "section": added["section"],
            "title": added["title"],
            "content_preview": added["content"][:300]
        })

    for removed in alignment["removed"]:
        summary["structural_changes"].append({
            "type": "removed",
            "section": removed["section"],
            "title": removed["title"],
            "content_preview": removed["content"][:300]
        })

    for split in alignment["split"]:
        summary["structural_changes"].append({
            "type": "split",
            "old_section": split["old_section"],
            "old_title": split["old_title"],
            "new_sections": split["new_sections"]
        })

    for merged in alignment["merged"]:
        summary["structural_changes"].append({
            "type": "merged",
            "new_section": merged["new_section"],
            "new_title": merged["new_title"],
            "old_sections": merged["old_sections"]
        })

    return summary


def generate_fewshot_examples(comparisons: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    examples = []

    for comp in comparisons:
        doc_name = comp["document"]

        for change in comp.get("content_changes", []):
            term_changes = change.get("terminology_changes", [])
            if term_changes and len(examples) < 1:
                tc = term_changes[0]
                examples.append({
                    "type": "terminology",
                    "document": doc_name,
                    "description": (
                        f"In {doc_name}, Section {change['old_section']} ('{change['old_title']}'), "
                        f"the terminology '{tc['old_text']}' was replaced with '{tc['new_text']}'. "
                        f"Old text: \"{tc['context_old']}\". "
                        f"New text: \"{tc['context_new']}\". "
                        f"This reflects RLPM's updated naming conventions and stage definitions."
                    )
                })
                break

        for change in comp.get("content_changes", []):
            if change["change_type"] == "modified" and change["additions_count"] > 0 and len(examples) < 2:
                sample_add = change["sample_additions"][0] if change["sample_additions"] else ""
                sample_rem = change["sample_removals"][0] if change["sample_removals"] else ""
                examples.append({
                    "type": "content_modification",
                    "document": doc_name,
                    "description": (
                        f"In {doc_name}, Section {change['old_section']} ('{change['old_title']}') "
                        f"was significantly modified. The section was renumbered to {change['new_section']} "
                        f"('{change['new_title']}'). "
                        f"Key removals included: \"{sample_rem[:150]}\". "
                        f"Key additions included: \"{sample_add[:150]}\". "
                        f"This change aligns the procedure with RLPM stage-gate requirements."
                    )
                })
                break

        for sc in comp.get("structural_changes", []):
            if sc["type"] == "added" and len(examples) < 3:
                examples.append({
                    "type": "structural",
                    "document": doc_name,
                    "description": (
                        f"In {doc_name}, a new Section {sc['section']} ('{sc['title']}') was added. "
                        f"This section was not present in the pre-RLPM version. "
                        f"Preview: \"{sc['content_preview'][:200]}...\". "
                        f"When analyzing other procedures, look for missing RLPM-specific sections "
                        f"that may need to be added, such as stage-gate deliverables, "
                        f"RLPM phase references, or lifecycle management requirements."
                    )
                })
                break
            elif sc["type"] == "removed" and len(examples) < 3:
                examples.append({
                    "type": "structural",
                    "document": doc_name,
                    "description": (
                        f"In {doc_name}, Section {sc['section']} ('{sc['title']}') was removed "
                        f"during RLPM alignment. "
                        f"Preview of removed content: \"{sc['content_preview'][:200]}...\". "
                        f"This indicates legacy passport/phase-gate content that was replaced "
                        f"by RLPM stage-gate structure."
                    )
                })
                break

    if len(examples) < 2:
        examples.append({
            "type": "generic",
            "document": "General",
            "description": (
                "When procedures reference 'Passport Phases' or 'Phase Gates', these should be "
                "evaluated for replacement with RLPM terminology: 'RLPM Stages' (Pursuit-to-Startup, "
                "Development, Production, Sustainment) and 'Stage Gates' per GCP-59. "
                "Deliverable checklists, gate review requirements, and lifecycle references "
                "should align with the corresponding RLPM stage document."
            )
        })

    return examples
