"""Parse Alice in Wonderland dialogue and emit a GML graph of who-speaks-to-whom.

Nodes  = characters who appear as speaker or addressee in the text.
Edges  = directed (speaker -> addressee). Edge weight = number of utterances.
"""

import re
from collections import Counter, defaultdict
from pathlib import Path

SRC = Path(__file__).with_name("carroll_alice.txt")
OUT = Path(__file__).with_name("alice_dialogue.graphml")

# --- Character lexicon --------------------------------------------------------
# Maps a lowercase surface form (single token or short phrase) to a canonical
# character label. Order matters for multi-word forms (longest first when we
# match).
CHARACTERS = {
    "Alice": ["alice"],
    "White Rabbit": ["white rabbit", "the rabbit", "rabbit"],
    "Mouse": ["the mouse", "mouse"],
    "Dodo": ["the dodo", "dodo"],
    "Lory": ["the lory", "lory"],
    "Eaglet": ["the eaglet", "eaglet"],
    "Duck": ["the duck", "duck"],
    "Bill": ["bill", "the lizard", "lizard"],
    "Pat": ["pat"],
    "Caterpillar": ["the caterpillar", "caterpillar"],
    "Pigeon": ["the pigeon", "pigeon"],
    "Fish-Footman": ["fish-footman", "the fish-footman"],
    "Frog-Footman": ["frog-footman", "the frog-footman"],
    "Footman": ["the footman", "footman"],
    "Duchess": ["the duchess", "duchess"],
    "Cook": ["the cook", "cook"],
    "Cheshire Cat": ["cheshire cat", "the cat", "cat"],
    "March Hare": ["march hare", "the march hare", "hare"],
    "Hatter": ["the hatter", "hatter"],
    "Dormouse": ["the dormouse", "dormouse"],
    "Queen": ["the queen", "queen of hearts", "queen"],
    "King": ["the king", "king of hearts", "king"],
    "Knave": ["the knave", "knave of hearts", "knave"],
    "Gryphon": ["the gryphon", "gryphon"],
    "Mock Turtle": ["mock turtle", "the mock turtle"],
    "Father William": ["father william"],
    "Five": ["five"],
    "Seven": ["seven"],
    "Two": ["two"],
    "Sister": ["her sister", "the sister", "sister"],
    "Soldier": ["the soldier", "soldier", "the soldiers", "soldiers"],
    "Juror": ["the juror", "juror", "the jurors", "jurors"],
}

# Build a single regex of all surface forms (longest first), with canonical map.
SURFACE_TO_CANON = {}
for canon, forms in CHARACTERS.items():
    for f in forms:
        SURFACE_TO_CANON[f] = canon

SURFACES = sorted(SURFACE_TO_CANON.keys(), key=len, reverse=True)
NAME_RE = re.compile(
    r"\b(" + "|".join(re.escape(s) for s in SURFACES) + r")\b",
    re.IGNORECASE,
)

# Speech verbs we trust as clear narrator-of-speech cues.
SPEECH_VERBS = (
    "said|says|asked|replied|cried|exclaimed|answered|remarked|added|"
    "shouted|whispered|continued|murmured|sighed|repeated|interrupted|"
    "muttered|growled|grunted|sang|sobbed|screamed|roared|called|"
    "began|went on|put in|pleaded|ventured|inquired|panted"
)

# --- Patterns -----------------------------------------------------------------
# After a dialogue's closing quote, narrator can say:
#   ," said Alice."   ," Alice said."   ," asked the Hatter."   ," the Hatter asked."
POST_PATTERNS = [
    re.compile(
        r"^[\s,.;:!?\-—]*(?:" + SPEECH_VERBS + r")\s+([A-Z][^,.;:!?\n]{0,40})",
        re.IGNORECASE,
    ),
    re.compile(
        r"^[\s,.;:!?\-—]*([A-Z][^,.;:!?\n]{0,40})\s+(?:" + SPEECH_VERBS + r")",
        re.IGNORECASE,
    ),
]
# Before a dialogue's opening quote, narrator can say:
#   Alice said, "..."   The Hatter shouted: "..."
PRE_PATTERN = re.compile(
    r"([A-Z][^,.;:!?\n]{0,40}?)\s+(?:" + SPEECH_VERBS + r")[\s,.:;\-—]*$",
    re.IGNORECASE,
)


def canon_in(span: str):
    """Return canonical character names that appear in `span`, in order."""
    found = []
    for m in NAME_RE.finditer(span):
        canon = SURFACE_TO_CANON[m.group(1).lower()]
        if not found or found[-1] != canon:
            found.append(canon)
    return found


def find_speaker(post_text: str, pre_text: str):
    """Look for a speaker tag in the narration after / before a dialogue.

    Returns canonical name or None.
    """
    # Try after-dialogue patterns first; they are the most common in this book.
    for pat in POST_PATTERNS:
        m = pat.match(post_text)
        if m:
            cand = canon_in(m.group(0))
            if cand:
                return cand[0]
    # Try before-dialogue pattern (search from end of pre_text, look at last line).
    tail = pre_text.split("\n")[-1]
    m = PRE_PATTERN.search(tail)
    if m:
        cand = canon_in(m.group(0))
        if cand:
            return cand[0]
    # Last ditch: any character mentioned in nearby narration after the quote
    # within the first sentence (very common: ". The Hatter shook his head.").
    near = post_text[:200]
    cand = canon_in(near)
    if cand:
        return cand[0]
    return None


def find_addressee(quote_text: str, prev_speaker: str | None,
                   speaker: str | None, post_text: str):
    """Best-effort addressee for an utterance.

    Priority:
      1. "said X to Y"  /  "to Y" right after the closing quote
      2. Vocative inside the quote (sentence-initial or after comma + name + ,/!)
      3. Previous speaker in the running back-and-forth
    """
    # 1. "to Y" in the immediate narration
    m = re.match(
        r"^[^\"\n]{0,80}?\bto\s+([A-Z][a-zA-Z' \-]{1,40})",
        post_text,
    )
    if m:
        cand = canon_in(m.group(0))
        cand = [c for c in cand if c != speaker]
        if cand:
            return cand[0]

    # 2. Vocative inside the quote: capitalised name set off by punctuation.
    voc_re = re.compile(
        r"(?:^|[\s,;:\-—])(" + "|".join(re.escape(s) for s in SURFACES) + r")(?=[\s,!?\.;:])",
        re.IGNORECASE,
    )
    for m in voc_re.finditer(quote_text):
        canon = SURFACE_TO_CANON[m.group(1).lower()]
        if canon != speaker:
            return canon

    # 3. Previous speaker (back-and-forth fallback).
    if prev_speaker and prev_speaker != speaker:
        return prev_speaker
    return None


def main():
    text = SRC.read_text()
    # Trim everything before the second "CHAPTER I." (skip ToC).
    first = text.find("CHAPTER I.")
    second = text.find("CHAPTER I.", first + 1)
    body = text[second:] if second != -1 else text

    # Find every "<open> ... <close>" dialogue. Carroll nests quotes occasionally;
    # we accept the simplest non-greedy pairing and let mismatches fall on the floor.
    dialogue_re = re.compile(r"“([^“”]+)”", re.DOTALL)

    edges = Counter()
    speaker_count = Counter()
    addressee_count = Counter()
    self_talk = Counter()
    unresolved_speaker = 0
    unresolved_addressee = 0
    total = 0

    prev_speaker = None
    last_two_speakers: list[str] = []  # rotating window for addressee fallback

    for m in dialogue_re.finditer(body):
        total += 1
        quote = m.group(1)
        # 200-char windows on each side are enough for tag detection.
        start, end = m.start(), m.end()
        pre = body[max(0, start - 200): start]
        post = body[end: end + 200]

        speaker = find_speaker(post, pre)

        # Detect "said Alice to herself" as soliloquy -> self-loop, not edge.
        soliloquy = bool(re.match(
            r"^[^\"\n]{0,80}?\bto\s+(herself|himself|itself)\b",
            post,
        ))

        if speaker is None:
            unresolved_speaker += 1
            continue

        speaker_count[speaker] += 1

        if soliloquy:
            self_talk[speaker] += 1
            prev_speaker = speaker
            continue

        addressee = find_addressee(quote, prev_speaker, speaker, post)
        if addressee is None:
            unresolved_addressee += 1
            prev_speaker = speaker
            continue

        addressee_count[addressee] += 1
        edges[(speaker, addressee)] += 1
        prev_speaker = speaker

    # --- Report -------------------------------------------------------------
    print(f"dialogue chunks       : {total}")
    print(f"speaker resolved      : {total - unresolved_speaker}")
    print(f"speaker unresolved    : {unresolved_speaker}")
    print(f"addressee unresolved  : {unresolved_addressee}")
    print(f"self-talk utterances  : {sum(self_talk.values())}")
    print(f"directed edges        : {sum(edges.values())}")
    print(f"unique pairs          : {len(edges)}")
    print()
    print("top speakers:")
    for n, c in speaker_count.most_common(10):
        print(f"  {n:20s} {c}")
    print()
    print("top edges:")
    for (a, b), c in edges.most_common(15):
        print(f"  {a} -> {b}: {c}")

    # --- Write GraphML ------------------------------------------------------
    nodes = sorted(set([s for s, _ in edges] + [t for _, t in edges]))
    node_id = {n: f"n{i}" for i, n in enumerate(nodes)}

    from xml.sax.saxutils import escape

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"',
        '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
        '         xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns'
        ' http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">',
        # Attribute keys.
        '  <key id="label"       for="node" attr.name="label"       attr.type="string"/>',
        '  <key id="utterances"  for="node" attr.name="utterances"  attr.type="int"/>',
        '  <key id="addressed"   for="node" attr.name="addressed"   attr.type="int"/>',
        '  <key id="soliloquies" for="node" attr.name="soliloquies" attr.type="int"/>',
        '  <key id="weight"      for="edge" attr.name="weight"      attr.type="int"/>',
        '  <graph id="alice_dialogue" edgedefault="directed">',
    ]
    for n in nodes:
        spoken = speaker_count[n]
        addressed = addressee_count[n]
        soliloquies = self_talk.get(n, 0)
        lines.append(f'    <node id="{node_id[n]}">')
        lines.append(f'      <data key="label">{escape(n)}</data>')
        lines.append(f'      <data key="utterances">{spoken}</data>')
        lines.append(f'      <data key="addressed">{addressed}</data>')
        lines.append(f'      <data key="soliloquies">{soliloquies}</data>')
        lines.append("    </node>")
    for i, ((s, t), w) in enumerate(edges.most_common()):
        lines.append(
            f'    <edge id="e{i}" source="{node_id[s]}" target="{node_id[t]}">'
        )
        lines.append(f'      <data key="weight">{w}</data>')
        lines.append("    </edge>")
    lines.append("  </graph>")
    lines.append("</graphml>")
    OUT.write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
