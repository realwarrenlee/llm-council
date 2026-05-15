"""Core anonymization functionality for peer review.

This module provides tools for anonymizing responses during deliberation,
parsing rankings from LLM outputs, calculating aggregate rankings using
voting methods like Borda count, and mapping back to original roles.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_council.council import CouncilResult


@dataclass
class AnonymizedResult:
    """Container for a single anonymized response.

    This dataclass stores one anonymized response with its anonymous label,
    original role name, and content.

    Attributes:
        anonymous_id: The anonymous identifier (e.g., "A1", "Response A")
        role_name: The original role name
        content: The response content
        model: The model used
        tokens_used: Number of tokens used (if available)
        latency_ms: Generation latency (if available)
        error: Error message if generation failed

    Example:
        ```python
        result = AnonymizedResult(
            anonymous_id="A1",
            role_name="advocate",
            content="Content...",
            model="claude",
        )
        ```
    """

    anonymous_id: str
    role_name: str
    content: str
    model: str
    tokens_used: int | None = None
    latency_ms: float | None = None
    error: str | None = None


@dataclass
class AnonymizedCollection:
    """Container for a collection of anonymized responses with mapping tracking.

    This dataclass stores multiple anonymized responses along with the mapping
    between anonymous labels and original role names.

    Attributes:
        responses: Dictionary mapping anonymous labels to response content
        mapping: Dictionary mapping anonymous labels to original role names
        rankings: List of individual rankings from evaluators
        metadata: Additional metadata about the anonymization process
    """

    responses: dict[str, str] = field(default_factory=dict)
    mapping: dict[str, str] = field(default_factory=dict)
    rankings: list[list[str]] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def get_role_for_label(self, label: str) -> str | None:
        """Get the original role name for an anonymous label."""
        return self.mapping.get(label)

    def get_label_for_role(self, role_name: str) -> str | None:
        """Get the anonymous label for an original role name."""
        for label, role in self.mapping.items():
            if role == role_name:
                return label
        return None

    def add_ranking(self, ranking: list[str]) -> None:
        """Add a ranking from an evaluator."""
        self.rankings.append(ranking)


def anonymize_responses(
    results: list[CouncilResult],
    id_format: str = "{}{}",
    prefix: str = "A",
    shuffle: bool = True,
    seed: int | None = None,
) -> list[AnonymizedResult]:
    """Anonymize responses by assigning random labels.

    Takes a list of CouncilResult objects and assigns anonymous identifiers,
    with optional random shuffling.

    Args:
        results: List of CouncilResult objects from deliberation
        id_format: Format string for IDs, with {} for prefix and number
        prefix: Prefix for IDs (e.g., "A" for A1, A2, etc.)
        shuffle: Whether to shuffle the order of responses randomly
        seed: Optional random seed for reproducible shuffling

    Returns:
        List of AnonymizedResult objects with anonymous IDs

    Raises:
        ValueError: If results is empty or contains duplicate role names
        TypeError: If results is not a list or contains non-CouncilResult items

    Example:
        ```python
        results = [
            CouncilResult(role_name="advocate", content="Yes...", model="claude"),
            CouncilResult(role_name="critic", content="No...", model="claude"),
        ]
        anonymized = anonymize_responses(results)
        # Returns: [AnonymizedResult(anonymous_id="A1", ...), ...]
        ```
    """
    if results is None:
        raise ValueError("results cannot be None")

    if not isinstance(results, list):
        raise TypeError(f"results must be a list, got {type(results).__name__}")

    if not results:
        return []

    # Check all items are CouncilResult-like objects
    for i, r in enumerate(results):
        if not hasattr(r, 'role_name'):
            raise TypeError(f"Item at index {i} is not a CouncilResult object (missing role_name attribute)")
        if not hasattr(r, 'content'):
            raise TypeError(f"Item at index {i} is not a CouncilResult object (missing content attribute)")
        if not hasattr(r, 'model'):
            raise TypeError(f"Item at index {i} is not a CouncilResult object (missing model attribute)")

    # Check for duplicate role names - handle gracefully by appending suffix
    seen_names: dict[str, int] = {}
    for r in results:
        original_name = r.role_name
        if original_name in seen_names:
            seen_names[original_name] += 1
            r.role_name = f"{original_name}_{seen_names[original_name]}"
        else:
            seen_names[original_name] = 0

    # Generate anonymous IDs
    ids = [id_format.format(prefix, i + 1) for i in range(len(results))]

    # Create working list of (id, result) pairs
    pairs = list(zip(ids, results))

    # Shuffle if requested
    if shuffle:
        if seed is not None:
            random.seed(seed)
        random.shuffle(pairs)

    # Build the anonymized results
    anonymized_results: list[AnonymizedResult] = []

    for anon_id, result in pairs:
        anonymized_results.append(AnonymizedResult(
            anonymous_id=anon_id,
            role_name=result.role_name,
            content=result.content,
            model=result.model,
            tokens_used=result.tokens_used,
            latency_ms=result.latency_ms,
            error=result.error,
        ))

    return anonymized_results


def de_anonymize(
    anonymized_results: list[AnonymizedResult],
) -> list[CouncilResult]:
    """Map anonymized results back to original CouncilResults.

    Args:
        anonymized_results: List of AnonymizedResult objects

    Returns:
        List of CouncilResult objects with original role names

    Raises:
        ValueError: If anonymized_results is None
        TypeError: If anonymized_results is not a list
    """
    if anonymized_results is None:
        raise ValueError("anonymized_results cannot be None")

    if not isinstance(anonymized_results, list):
        raise TypeError(f"anonymized_results must be a list, got {type(anonymized_results).__name__}")

    if not anonymized_results:
        return []

    from llm_council.council import CouncilResult

    return [
        CouncilResult(
            role_name=ar.role_name,
            content=ar.content,
            model=ar.model,
            tokens_used=ar.tokens_used,
            latency_ms=ar.latency_ms,
            error=ar.error,
        )
        for ar in anonymized_results
    ]


def parse_ranking_from_text(
    text: str,
    valid_ids: list[str] | None = None,
    ensure_all_ids: bool = False,
) -> list[str]:
    """Extract a ranking from LLM output text.

    Parses various ranking formats commonly used by LLMs:
    - Arrow notation: "A1 > B2 > C3"
    - Numbered lists: "1. A1, 2. B2, 3. C3"
    - Comma-separated: "A1, B2, C3"
    - Space-separated: "A1 B2 C3"
    - Bulleted lists: "* A1\n* B2\n* C3"
    - Newline-separated with numbers or bullets
    - Response labels: "1. Response A" or "Response A: excellent"

    Args:
        text: The text to parse for rankings
        valid_ids: Optional list of valid IDs to filter/validate against
        ensure_all_ids: If True, append any missing valid_ids to the end

    Returns:
        List of IDs in ranked order (best first). Empty list if parsing fails.

    Example:
        ```python
        parse_ranking_from_text("A1 > B2 > C3", valid_ids=["A1", "B2", "C3"])
        # Returns: ["A1", "B2", "C3"]

        parse_ranking_from_text("1. C3\n2. A1\n3. B2", valid_ids=["A1", "B2", "C3"])
        # Returns: ["C3", "A1", "B2"]
        ```
    """
    if text is None:
        raise ValueError("text cannot be None")

    if not text or not text.strip():
        return []

    text = text.strip()

    # Try arrow notation first (A1 > B2 > C3)
    arrow_match = _parse_arrow_notation(text, valid_ids)
    if arrow_match:
        if ensure_all_ids and valid_ids:
            return _ensure_all_ids_included(arrow_match, valid_ids)
        return arrow_match

    # Try numbered list (1. A1, 2. B2, 3. C3)
    numbered_match = _parse_numbered_list(text, valid_ids)
    if numbered_match:
        if ensure_all_ids and valid_ids:
            return _ensure_all_ids_included(numbered_match, valid_ids)
        return numbered_match

    # Try reverse ranking labels (Best: A1, Second: A2, Worst: A3)
    reverse_match = _parse_reverse_ranking(text, valid_ids)
    if reverse_match:
        if ensure_all_ids and valid_ids:
            return _ensure_all_ids_included(reverse_match, valid_ids)
        return reverse_match

    # Try table format (| A1 | A2 |)
    table_match = _parse_table_format(text, valid_ids)
    if table_match:
        if ensure_all_ids and valid_ids:
            return _ensure_all_ids_included(table_match, valid_ids)
        return table_match

    # Try comma or newline separated
    simple_match = _parse_simple_list(text, valid_ids)
    if simple_match:
        if ensure_all_ids and valid_ids:
            return _ensure_all_ids_included(simple_match, valid_ids)
        return simple_match

    # Try "Response X" format (common in peer review)
    response_match = _parse_response_labels(text, valid_ids)
    if response_match:
        if ensure_all_ids and valid_ids:
            return _ensure_all_ids_included(response_match, valid_ids)
        return response_match

    # Try extracting IDs from natural language
    natural_match = _parse_natural_language(text, valid_ids)
    if natural_match:
        if ensure_all_ids and valid_ids:
            return _ensure_all_ids_included(natural_match, valid_ids)
        return natural_match

    # If ensure_all_ids is True, return all valid_ids even if no parsing worked
    if ensure_all_ids and valid_ids:
        return list(valid_ids)

    return []


def _parse_response_labels(text: str, valid_ids: list[str] | None) -> list[str] | None:
    """Parse 'Response X' format commonly used in peer review.

    Handles formats like:
    - "1. Response A" or "1) Response A"
    - "- Response B"
    - "Response A: excellent"
    """
    import re

    rankings: list[tuple[int, str]] = []  # (position, id)
    found_ids: set[str] = set()

    # Check if valid_ids use "Response X" format
    if valid_ids and any("Response" in vid for vid in valid_ids):
        # Match patterns like "1. Response A" or "Response A"
        patterns = [
            r"(?:^|\n)\s*\d+[:.)\s]+([Rr]esponse\s+[A-Z])",
            r"(?:^|\n)\s*[-*•]\s+([Rr]esponse\s+[A-Z])",
            r"([Rr]esponse\s+[A-Z])[:;\s]",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
                normalized = match.group(1).capitalize()
                if normalized in valid_ids and normalized not in found_ids:
                    found_ids.add(normalized)
                    rankings.append((match.start(), normalized))

        if rankings:
            rankings.sort(key=lambda x: x[0])
            return [r[1] for r in rankings]

    return None


def _ensure_all_ids_included(rankings: list[str], valid_ids: list[str]) -> list[str]:
    """Ensure all valid_ids are included in rankings.

    Appends any missing IDs to the end of the rankings list.
    """
    result = list(rankings)
    for vid in valid_ids:
        if vid not in result:
            result.append(vid)
    return result


def _parse_arrow_notation(text: str, valid_ids: list[str] | None) -> list[str] | None:
    """Parse arrow notation like 'A1 > B2 > C3'."""
    parts = re.split(r"\s*(?:>|→|>>)\s*", text)

    if len(parts) < 2:
        return None

    ids = []
    for part in parts:
        id_str = _extract_id(part.strip(), valid_ids)
        if id_str:
            ids.append(id_str)

    return ids if len(ids) >= 2 else None


def _parse_numbered_list(text: str, valid_ids: list[str] | None) -> list[str] | None:
    """Parse numbered, ordinal, and bulleted lists like '1. A1\n2. B2\n3. C3' or '* A1\n* B2'."""
    lines = text.split("\n")
    ranked_items: list[tuple[int, str]] = []
    bullet_items: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match ordinal patterns like "1st: A1", "2nd: A2", "3rd: A3"
        ordinal_match = re.match(r"^(\d+)(?:st|nd|rd|th)[:\.)\-]?\s+(.+)$", line, re.IGNORECASE)
        if ordinal_match:
            rank = int(ordinal_match.group(1))
            content = ordinal_match.group(2).strip()
            id_str = _extract_id(content, valid_ids)
            if id_str:
                ranked_items.append((rank, id_str))
            continue

        # Match patterns like "1. A1", "1) A1", "(1) A1", "1 - A1"
        match = re.match(r"^(?:\(?\d+[\.\)\-]?\s+|\d+\s*[-\.)]\s+)(.+)$", line)
        if match:
            content = match.group(1).strip()
            num_match = re.match(r"^(\d+)", line)
            if num_match:
                rank = int(num_match.group(1))
                id_str = _extract_id(content, valid_ids)
                if id_str:
                    ranked_items.append((rank, id_str))
            continue

        # Match bullet patterns like "* A1", "- B2", "+ C3"
        bullet_match = re.match(r"^[-\*\+•]\s+(.+)$", line)
        if bullet_match:
            content = bullet_match.group(1).strip()
            id_str = _extract_id(content, valid_ids)
            if id_str:
                bullet_items.append(id_str)

    # Return numbered list results if we have enough
    if len(ranked_items) >= 2:
        ranked_items.sort(key=lambda x: x[0])
        return [item[1] for item in ranked_items]

    # Return bulleted list results if we have enough
    if len(bullet_items) >= 2:
        return bullet_items

    return None


def _parse_simple_list(text: str, valid_ids: list[str] | None) -> list[str] | None:
    """Parse comma, space, or newline separated lists."""
    # First try comma, semicolon, equals, or newline separated
    # Equals signs are used for ties (e.g., "A1 = A2, A3")
    parts = re.split(r'[,;=]|\n', text)

    ids = []
    for part in parts:
        id_str = _extract_id(part.strip(), valid_ids)
        if id_str and id_str not in ids:
            ids.append(id_str)

    if len(ids) >= 2:
        return ids

    # Try space-separated
    if valid_ids:
        # With valid_ids, we can be more precise
        ids = []
        
        # Try to find all valid IDs in order of appearance
        for vid in valid_ids:
            # Look for the ID with word boundaries
            pattern = r'\b' + re.escape(vid) + r'\b'
            if re.search(pattern, text):
                if vid not in ids:
                    ids.append(vid)
        
        # If we found IDs, sort them by position in text
        if len(ids) >= 2:
            # Re-order by position in text
            id_positions = []
            for vid in ids:
                match = re.search(r'\b' + re.escape(vid) + r'\b', text)
                if match:
                    id_positions.append((match.start(), vid))
            
            id_positions.sort(key=lambda x: x[0])
            return [vid for _, vid in id_positions]
    else:
        # Without valid_ids, try to extract ID-like patterns from space-separated text
        # Look for patterns like A1, B2, C3 (letter followed by number)
        id_pattern = r'\b([A-Z]\d+)\b'
        matches = re.findall(id_pattern, text, re.IGNORECASE)
        
        if len(matches) >= 2:
            # Preserve order and remove duplicates
            seen = set()
            ids = []
            for match in matches:
                normalized = match.upper()
                if normalized not in seen:
                    seen.add(normalized)
                    ids.append(normalized)
            
            if len(ids) >= 2:
                return ids

    return ids if len(ids) >= 2 else None


def _parse_reverse_ranking(text: str, valid_ids: list[str] | None) -> list[str] | None:
    """Parse reverse ranking with labels like 'Best: A1', 'Second: A2', 'Worst: A3'."""
    import re
    
    # Define ranking labels in order (best to worst)
    labels = [
        r"(?:best|first|top|winner|1st)",
        r"(?:second|runner[- ]up|2nd)",
        r"(?:third|3rd)",
        r"(?:worst|last|bottom|loser)",
    ]
    
    ranked_items: list[tuple[int, str]] = []
    
    for rank, label_pattern in enumerate(labels):
        # Match patterns like "Best: A1" or "Best - A1" or "Best A1"
        pattern = rf"{label_pattern}\s*[:;\-]?\s*([A-Z]\d+|Response\s+[A-Z])"
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        for match in matches:
            id_str = _extract_id(match, valid_ids)
            if id_str:
                ranked_items.append((rank, id_str))
    
    if len(ranked_items) >= 2:
        ranked_items.sort(key=lambda x: x[0])
        return [item[1] for item in ranked_items]
    
    return None


def _parse_table_format(text: str, valid_ids: list[str] | None) -> list[str] | None:
    """Parse table format with pipes like '| A1 | A2 | A3 |'."""
    import re
    
    # Look for lines with pipes
    lines = text.split('\n')
    ids = []
    
    for line in lines:
        if '|' in line:
            # Skip header separator lines (like -----|-----)
            if re.match(r'^\s*\|?\s*[-:]+\s*\|', line):
                continue
            
            # Extract cells between pipes
            cells = [cell.strip() for cell in line.split('|')]
            
            for cell in cells:
                if not cell:
                    continue
                
                # Skip header labels
                if cell.lower() in ['rank', 'id', 'response', 'item']:
                    continue
                
                id_str = _extract_id(cell, valid_ids)
                if id_str and id_str not in ids:
                    ids.append(id_str)
    
    return ids if len(ids) >= 2 else None


def _parse_natural_language(text: str, valid_ids: list[str] | None) -> list[str] | None:
    """Extract IDs from natural language explanations."""
    import re
    
    if not valid_ids:
        return None
    
    # Find all occurrences of valid IDs in the text
    found_ids: list[tuple[int, str]] = []
    
    for vid in valid_ids:
        # Find all positions where this ID appears
        pattern = r'\b' + re.escape(vid) + r'\b'
        for match in re.finditer(pattern, text):
            found_ids.append((match.start(), vid))
    
    if len(found_ids) < 2:
        return None
    
    # Sort by position in text (assumes order of mention = ranking order)
    found_ids.sort(key=lambda x: x[0])
    
    # Remove duplicates while preserving order
    seen = set()
    result = []
    for _, vid in found_ids:
        if vid not in seen:
            seen.add(vid)
            result.append(vid)
    
    return result if len(result) >= 2 else None


def _extract_id(text: str, valid_ids: list[str] | None) -> str | None:
    """Extract an ID from text, optionally validating against valid IDs."""
    text = text.strip()

    if not text:
        return None

    # Strip common delimiters and punctuation
    # Remove parentheses, brackets, equals signs, colons, etc.
    cleaned = re.sub(r'[(){}\[\]=:;,]', ' ', text).strip()
    
    # Try to extract just the ID part (e.g., "A1" from "(A1)" or "A1 = A2")
    # Look for pattern like letter(s) followed by number(s)
    id_match = re.search(r'\b([A-Z]\d+)\b', cleaned, re.IGNORECASE)
    if id_match:
        extracted = id_match.group(1).upper()
        
        if valid_ids:
            # Check if extracted ID is in valid_ids (case-insensitive)
            for vid in valid_ids:
                if extracted.upper() == vid.upper():
                    return vid
        else:
            return extracted

    if valid_ids:
        # First try exact match
        if text in valid_ids:
            return text

        # Try case-insensitive match
        for vid in valid_ids:
            if text.lower() == vid.lower():
                return vid

        # Try to find valid ID within text
        for vid in valid_ids:
            if vid in text:
                return vid

        return None

    # No validation - return the text if it looks like an ID
    return text


def calculate_aggregate_rankings(
    rankings: list[list[str]],
    method: str = "borda",
    weights: list[float] | None = None,
) -> dict[str, float]:
    """Calculate aggregate rankings from multiple individual rankings.

    Supports multiple voting methods:
    - "borda": Borda count (n-1 points for 1st, n-2 for 2nd, etc.)
    - "average_position": Average position (lower is better)

    Args:
        rankings: List of rankings, each a list of IDs in ranked order
        method: Voting method to use ("borda" or "average_position")
        weights: Optional weights for each ranking

    Returns:
        Dictionary mapping IDs to their aggregate scores

    Raises:
        ValueError: If rankings is empty or method is invalid

    Example:
        ```python
        rankings = [
            ["A1", "B2", "C3"],
            ["B2", "A1", "C3"],
            ["A1", "C3", "B2"],
        ]
        scores = calculate_aggregate_rankings(rankings, method="borda")
        # Returns: {"A1": 5.0, "B2": 3.0, "C3": 1.0}
        ```
    """
    if rankings is None:
        raise ValueError("rankings cannot be None")

    if not rankings:
        return {}

    if method not in ("borda", "average_position"):
        raise ValueError(f"Unknown voting method: {method}")

    # Handle weights length mismatch gracefully by padding with 1.0 or truncating
    if weights:
        if len(weights) < len(rankings):
            # Pad with 1.0 for missing weights
            weights = list(weights) + [1.0] * (len(rankings) - len(weights))
        elif len(weights) > len(rankings):
            # Truncate extra weights
            weights = weights[:len(rankings)]

    # Determine all unique IDs
    all_ids: set[str] = set()
    for ranking in rankings:
        all_ids.update(ranking)

    if not all_ids:
        return {}

    num_items = len(all_ids)
    scores: dict[str, float] = {id_str: 0.0 for id_str in all_ids}

    for i, ranking in enumerate(rankings):
        weight = weights[i] if weights else 1.0

        # Track which IDs are in this ranking
        ranked_ids = set(ranking)
        unranked_ids = all_ids - ranked_ids

        if method == "borda":
            # Score ranked items
            for position, id_str in enumerate(ranking):
                if id_str in scores:
                    scores[id_str] += ((num_items - 1) - position) * weight
            # Unranked items get 0 points (worst score in Borda count)
            # This is the default, so no need to add anything
        elif method == "average_position":
            # Score ranked items
            for position, id_str in enumerate(ranking):
                if id_str in scores:
                    scores[id_str] += (position + 1) * weight
            # Unranked items get worst position (num_items)
            for id_str in unranked_ids:
                scores[id_str] += num_items * weight

    # For average_position, convert to actual average
    if method == "average_position":
        for id_str in scores:
            scores[id_str] /= len(rankings)

    return scores
