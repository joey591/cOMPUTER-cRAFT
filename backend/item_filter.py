"""Fuzzy item name matching and filtering."""
from difflib import SequenceMatcher
from config import ABBREVIATION_MAP, FUZZY_MATCH_THRESHOLD


def similarity(a, b):
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def expand_abbreviation(item_input):
    """Expand common abbreviations in item names.
    
    Examples:
        iron_b -> iron_block
        iron_i -> iron_ingot
        gold_n -> gold_nugget
    """
    parts = item_input.split('_')
    if len(parts) >= 2:
        last_part = parts[-1]
        if last_part in ABBREVIATION_MAP:
            parts[-1] = ABBREVIATION_MAP[last_part]
            return '_'.join(parts)
    return item_input


def fuzzy_match_item(item_input, item_list):
    """Find best matching item from list using fuzzy matching.
    
    Priority:
    1. Exact match (case-insensitive)
    2. Expanded abbreviation match
    3. Prefix match
    4. Fuzzy match (similarity > threshold)
    
    Returns: (matched_item, match_type) or (None, None)
    """
    item_input = item_input.lower().strip()
    item_list_lower = {item.lower(): item for item in item_list}
    
    # 1. Exact match
    if item_input in item_list_lower:
        return item_list_lower[item_input], 'exact'
    
    # 2. Expanded abbreviation match
    expanded = expand_abbreviation(item_input)
    if expanded != item_input and expanded.lower() in item_list_lower:
        return item_list_lower[expanded.lower()], 'abbreviation'
    
    # 3. Prefix match (item_input is a prefix of item)
    prefix_matches = []
    for item_lower, item_original in item_list_lower.items():
        if item_lower.startswith(item_input):
            prefix_matches.append((item_original, item_lower))
    
    if prefix_matches:
        # Return shortest match (most specific)
        prefix_matches.sort(key=lambda x: len(x[1]))
        return prefix_matches[0][0], 'prefix'
    
    # 4. Fuzzy match
    best_match = None
    best_score = 0
    for item_lower, item_original in item_list_lower.items():
        score = similarity(item_input, item_lower)
        if score > best_score and score >= FUZZY_MATCH_THRESHOLD:
            best_score = score
            best_match = item_original
    
    if best_match:
        return best_match, 'fuzzy'
    
    return None, None


def filter_items_by_name(item_input, item_list):
    """Filter items from list that match the input.
    
    Returns list of matching items sorted by match quality.
    """
    if not item_input:
        return item_list
    
    item_input = item_input.lower().strip()
    matches = []
    
    # Try exact match first
    for item in item_list:
        item_lower = item.lower()
        if item_lower == item_input:
            matches.append((item, 'exact', 1.0))
        elif item_lower.startswith(item_input):
            matches.append((item, 'prefix', 0.8))
        else:
            # Check expanded abbreviation
            expanded = expand_abbreviation(item_input)
            if expanded != item_input and item_lower == expanded.lower():
                matches.append((item, 'abbreviation', 0.9))
            else:
                # Fuzzy match
                score = similarity(item_input, item_lower)
                if score >= FUZZY_MATCH_THRESHOLD:
                    matches.append((item, 'fuzzy', score))
    
    # Sort by match quality: exact > abbreviation > prefix > fuzzy (by score)
    match_priority = {'exact': 4, 'abbreviation': 3, 'prefix': 2, 'fuzzy': 1}
    matches.sort(key=lambda x: (match_priority.get(x[1], 0), x[2]), reverse=True)
    
    return [item for item, _, _ in matches]


def get_common_minecraft_items():
    """Get a list of common Minecraft item names for testing/filtering."""
    # This is a sample list - in production, you might want to load from a file
    # or query from the actual game/mod data
    return [
        'iron_ingot', 'iron_block', 'iron_nugget', 'iron_ore',
        'gold_ingot', 'gold_block', 'gold_nugget', 'gold_ore',
        'diamond', 'diamond_block', 'diamond_ore',
        'coal', 'coal_block', 'coal_ore',
        'redstone', 'redstone_block', 'redstone_ore',
        'emerald', 'emerald_block', 'emerald_ore',
        'lapis_lazuli', 'lapis_block', 'lapis_ore',
        'copper_ingot', 'copper_block', 'copper_ore',
        'netherite_ingot', 'netherite_block', 'netherite_scrap',
        'wooden_planks', 'oak_planks', 'spruce_planks',
        'stone', 'cobblestone', 'gravel', 'sand',
        'glass', 'glass_pane', 'obsidian',
    ]

