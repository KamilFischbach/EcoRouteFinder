"""Rule-based trip extraction (English + Polish). The fallback when the LLM is unavailable.

Deliberately simple and predictable: regexes and keyword lists, no grammar. Polish place names
are returned as written ("z Gdyni" -> "Gdyni"); the geocoder usually copes with that.
"""

import re

from app.models.trip import TransportMode

_UPPER = "A-ZĄĆĘŁŃÓŚŹŻ"
# One or more capitalised words: "Kraków", "Nowy Sącz", "Bielsko-Biała".
_PLACE = rf"[{_UPPER}][\w'-]*(?:\s+[{_UPPER}][\w'-]*)*"

# (pattern, swapped): swapped patterns capture the destination first ("in Warsaw from Gdynia").
_ROUTE_PATTERNS: list[tuple[re.Pattern[str], bool]] = [
    (re.compile(rf"({_PLACE})\s*(?:→|->|=>|—>)\s*({_PLACE})"), False),
    (re.compile(rf"(?i:\bze?)\s+({_PLACE})\s+(?i:do)\s+({_PLACE})"), False),
    (re.compile(rf"(?i:\bfrom)\s+({_PLACE})\s+(?i:to)\s+({_PLACE})"), False),
    (re.compile(rf"({_PLACE})\s+(?i:to)\s+({_PLACE})"), False),
    (re.compile(rf"(?i:\b(?:in|to))\s+({_PLACE})\s+(?i:from)\s+({_PLACE})"), True),
]

_NUMBER_WORDS = {
    # English
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9,
    # Polish (cardinals and the forms used with "osoby/osób")
    "jedna": 1, "dwie": 2, "dwa": 2, "dwóch": 2, "trzy": 3, "trzech": 3, "cztery": 4,
    "czterech": 4, "pięć": 5, "pięciu": 5, "sześć": 6, "siedem": 7, "osiem": 8, "dziewięć": 9,
}  # fmt: skip
_COLLECTIVE_PL = {"dwoje": 2, "dwóch": 2, "dwie": 2, "troje": 3, "trzech": 3, "trzy": 3,
                  "czworo": 4, "czterech": 4, "pięcioro": 5, "pięciu": 5}  # fmt: skip
_NUM = r"(\d+|" + "|".join(sorted(_NUMBER_WORDS, key=len, reverse=True)) + r")"

_COMPANIONS_EN = (
    r"wife|husband|partner|friend|girlfriend|boyfriend|colleague|mum|mom|dad|brother|sister"
)
_COMPANIONS_PL = (
    r"żoną|mężem|partnerem|partnerką|kolegą|koleżanką|dziewczyną|chłopakiem|"
    r"przyjacielem|przyjaciółką|mamą|tatą|bratem|siostrą"
)

_GROUP_EN = r"(?:friends|colleagues|mates)"
_NOT_A_COUNT = r"(?!\s*(?:days?|nights?|hours?|weeks?|h|pln|zł)\b)"

# (pattern, fixed count or None to read group 1, people to add to the number in the text).
_PASSENGER_PATTERNS: list[tuple[re.Pattern[str], int | None, int]] = [
    (re.compile(rf"\b{_NUM}\s+(?:people|persons|passengers|adults|travell?ers|of us)\b"), None, 0),
    (re.compile(rf"\bwe(?:'re| are)\s+{_NUM}\b"), None, 0),
    (re.compile(rf"\b{_NUM}\s+(?:osoby|osób|osoba|os\.)"), None, 0),
    (re.compile(rf"\bjest nas\s+{_NUM}\b"), None, 0),
    (re.compile(r"\bwe\s+(" + "|".join(_COLLECTIVE_PL) + r")\b"), None, 0),
    # "with 3 friends" = the speaker + 3; a bare "4 friends" is read as the whole group.
    (re.compile(rf"\bwith\s+{_NUM}\s+{_GROUP_EN}\b"), None, 1),
    (re.compile(rf"\b{_NUM}\s+{_GROUP_EN}\b"), None, 0),
    (re.compile(rf"\bfor\s+{_NUM}\b{_NOT_A_COUNT}"), None, 0),
    (re.compile(rf"\bwith (?:my|a) (?:{_COMPANIONS_EN})\b"), 2, 0),
    (re.compile(rf"\bz (?:{_COMPANIONS_PL})\b"), 2, 0),
    (re.compile(r"\b(?:alone|solo|by myself|on my own|sam|sama)\b"), 1, 0),
]

_MODE_KEYWORDS: dict[TransportMode, re.Pattern[str]] = {
    TransportMode.CAR_EV: re.compile(
        r"\b(?:ev|electric (?:car|vehicle)|tesla|elektryk\w*|(?:autem|samochodem) elektrycznym)\b"
    ),
    TransportMode.TRAIN: re.compile(r"\b(?:train|rail|pociąg\w*|kolej\w*|pkp|intercity)\b"),
    TransportMode.PLANE: re.compile(r"\b(?:plane|fly|flying|flight|samolot\w*|lecę|lecimy)\b"),
    TransportMode.COACH: re.compile(r"\b(?:coach|bus|autobus\w*|autokar\w*|busem|flixbus)\b"),
    TransportMode.BIKE: re.compile(r"\b(?:bike|bicycle|cycling|cycle|rower\w*)\b"),
    TransportMode.CAR_PETROL: re.compile(
        r"\b(?:car|drive|driving|auto|autem|samochód|samochodem|samochod\w*)\b"
    ),
}


# Words that mark a travel need (luggage, equipment, comfort, budget, speed, pets, children).
# English + Polish; each alternative matches from the start of a word.
PREFERENCE_KEYWORDS = (
    r"luggage|baggage|suitcases?|bags?\b|backpacks?|ski\w*|snowboard\w*|equipment|gear\b"
    r"|comfort\w*|cheap\w*|budget|fast\w*|quick\w*|dogs?\b|pets?\b|kids?\b|child\w*"
    r"|bab(?:y|ies)\b|bagaż\w*|walizk\w*|plecak\w*|nart\w*|sprzęt\w*|wygod\w*|komfort\w*"
    r"|tani\w*|najtan\w*|szybk\w*|najszyb\w*|psem|psami|pies\w*|dzieck\w*|dzieć\w*|dzieci\w*"
)
_PREFERENCE_RE = re.compile(rf"\b(?:{PREFERENCE_KEYWORDS})", re.IGNORECASE)
_FRAGMENT_SPLIT_RE = re.compile(r"[.;!?,\n]+")
MAX_PREFERENCES_LENGTH = 300  # same limit as AdviceCreate.preferences


def _route_match(text: str) -> tuple[re.Match[str], bool] | None:
    for pattern, swapped in _ROUTE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match, swapped
    return None


def find_route(text: str) -> tuple[str | None, str | None]:
    found = _route_match(text)
    if found is None:
        return None, None
    match, swapped = found
    first, second = match.group(1).strip(), match.group(2).strip()
    return (second, first) if swapped else (first, second)


def find_preferences(text: str) -> str | None:
    """Fragments of the user's own text that mention a travel need, without the route."""
    found = _route_match(text)
    if found is not None:
        match = found[0]
        text = f"{text[: match.start()]} {text[match.end() :]}"
    fragments = (" ".join(part.split()) for part in _FRAGMENT_SPLIT_RE.split(text))
    kept = [fragment for fragment in fragments if _PREFERENCE_RE.search(fragment)]
    return "; ".join(kept)[:MAX_PREFERENCES_LENGTH].strip() or None


def _to_int(token: str) -> int | None:
    if token.isdigit():
        return int(token)
    return _NUMBER_WORDS.get(token) or _COLLECTIVE_PL.get(token)


def find_passengers(text: str) -> int | None:
    lowered = text.lower()
    for pattern, fixed, extra in _PASSENGER_PATTERNS:
        match = pattern.search(lowered)
        if not match:
            continue
        count = fixed if fixed is not None else _to_int(match.group(1))
        if count is None:
            return None
        count += extra
        return count if 1 <= count <= 9 else None
    return None


def find_mode(text: str) -> TransportMode | None:
    """The mode only when exactly one is mentioned (an EV also says "car", so EV wins)."""
    lowered = text.lower()
    found = {mode for mode, pattern in _MODE_KEYWORDS.items() if pattern.search(lowered)}
    if TransportMode.CAR_EV in found:
        found.discard(TransportMode.CAR_PETROL)
    return found.pop() if len(found) == 1 else None
