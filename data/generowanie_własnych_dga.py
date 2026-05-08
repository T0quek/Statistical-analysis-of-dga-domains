from __future__ import annotations
import os
import base64
import hashlib
import random
from datetime import date, datetime, timezone

SUFFIXES = [
    "com", "net", "org", "info", "io", "co", "app", "site", "online", "store", "pl",
    "xyz", "biz", "top", "ru", "cn", "pw", "click", "work", "live", "link", "ai",
]

ZODIAC_SIGNS = [ "aries", "taurus", "gemini", "cancer", "leo", "virgo",
                 "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
]

WEATHER_TOKENS = [ "sun", "rain", "storm", "fog", "cloud", "wind", "snow",
                   "heat", "cold", "humid", "dry", "mist",
]

MULTI_LANG_WORDS = [
    "dom", "haus", "casa", "maison", "home", "house", "cielo", "sky", "neve", "snow",
    "agua", "water", "wasser", "eau", "luna", "moon", "sol", "sun", "sole", "sonne",
    "noche", "night", "nacht", "amor", "love", "liebe", "stadt", "city", "ville",
    "tempo", "time", "zeit", "verde", "green", "grun", "blau", "blue", "bleu",
    "noir", "black", "nero", "vento", "wind", "terre", "earth", "terra", "mare",
    "sea", "meer", "fuego", "fire", "feuer", "flame", "arbre", "tree", "baum",
    "fiore", "flower", "fleur", "blume", "strada", "road", "route", "rue", "via",
    "berg", "mountain", "mont", "monte", "river", "fluss", "riviere", "rio",
    "gold", "oro", "argent", "silver", "silber", "jour", "day", "tag", "dia",
    "porte", "door", "tur", "fenster", "window", "finestra", "livre", "book",
    "buch", "libro", "chat", "cat", "gato", "hund", "dog", "chien", "oiseau",
    "bird", "vogel", "fish", "poisson", "pesce", "brot", "bread", "pain",
    "latte", "milk", "milch", "cafe", "kaffee", "coffee", "tea", "the", "cha",
    "rosa", "rose", "rouge", "red", "rot", "bianco", "white", "weiss", "gris",
    "gray", "grau", "yellow", "gelb", "jaune", "orange", "purple", "violet",
    "north", "sud", "south", "east", "ost", "west", "ouest", "nuevo", "new",
    "neu", "ancien", "old", "alto", "high", "hoch", "basso", "low", "klein",
    "small", "grand", "big", "forte", "strong", "stark", "soft", "doux",
    "rapido", "fast", "schnell", "slow", "lento", "calm", "ruhig",
]

SYLLABLES = [ "al", "be", "cor", "den", "ex", "fi", "gor", "hel", "in", "jo", "ka", "lu",
              "mor", "nu", "or", "pra", "qui", "ri", "sa", "tor", "ul", "ve", "win", "xor",
              "ya", "zen",
]

CONSONANTS = "bcdfghjklmnpqrstvwxyz"
VOWELS = "aeiou"

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

def _sanitize_label(label: str, min_len: int = 8, max_len: int = 24) -> str:
    cleaned = "".join(c for c in label.lower() if c.isalnum() or c == "-")
    cleaned = cleaned.strip("-")
    if not cleaned:
        cleaned = "seed0000"
    if len(cleaned) < min_len:
        cleaned += "x" * (min_len - len(cleaned))
    cleaned = cleaned[:max_len].strip("-")
    if not cleaned[0].isalnum():
        cleaned = "a" + cleaned[1:]
    if not cleaned[-1].isalnum():
        cleaned = cleaned[:-1] + "a"
    return cleaned

def _domain(label: str) -> str:
    return f"{_sanitize_label(label)}.{random.choice(SUFFIXES)}"

def _random_seed() -> int:
    now = _utc_now().isoformat()
    nonce = random.getrandbits(64)
    payload = f"{now}|{nonce}".encode("ascii", "ignore")
    return int(hashlib.sha256(payload).hexdigest()[:16], 16)


# 1) LCG + data

def dga_lcg_date() -> str:
    today = date.today()
    x = (_random_seed() ^ int(today.strftime("%Y%m%d"))) & 0xFFFFFFFF
    out = []
    for _ in range(14):
        x = (1664525 * x + 1013904223) & 0xFFFFFFFF
        out.append(chr(ord("a") + (x % 26)))
    return _domain("".join(out))


# 2) Xorshift32
def dga_xorshift() -> str:
    x = _random_seed() & 0xFFFFFFFF
    out = []
    for _ in range(15):
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17) & 0xFFFFFFFF
        x ^= (x << 5) & 0xFFFFFFFF
        out.append(chr(ord("a") + (x % 26)))
    return _domain("".join(out))


# 3) SHA256(counter)
def dga_sha256_counter() -> str:
    token = f"{date.today().toordinal()}:{_random_seed()}:sha256".encode("ascii")
    digest = hashlib.sha256(token).hexdigest()
    label = "".join(c for c in digest if c.isalpha())[:12] + digest[-4:]
    return _domain(label)


# 4) MD5(seed+offset)
def dga_md5_seed() -> str:
    payload = f"{_random_seed()}:{date.today().isoformat()}:md5".encode("ascii")
    digest = hashlib.md5(payload).hexdigest()
    return _domain(digest[::2][:16])


# 5) BLAKE2s(rounds)
def dga_blake2_round() -> str:
    data = f"{_random_seed()}|{_utc_now().timestamp()}".encode("ascii")
    raw = hashlib.blake2s(data, digest_size=16).hexdigest()
    label = "".join("abcdefghijklmnopqrstuvwxyz0123456789"[int(c, 16) % 36] for c in raw[:18])
    return _domain(label)


# 6) Znaki zodiaku + data
def dga_zodiac_calendar() -> str:
    today = date.today()
    sign = random.choice(ZODIAC_SIGNS)
    label = f"{sign}{today.day:02d}{today.month:02d}{random.randint(100, 999)}"
    return _domain(label)


# 7) Adresy IP pseudo-losowe
def dga_ip_octets() -> str:
    octets = [str(random.randint(1, 254)) for _ in range(4)]
    return _domain("n" + "-".join(octets))


# 8) Pogoda + liczby
def dga_weather_blend() -> str:
    token_a, token_b = random.sample(WEATHER_TOKENS, 2)
    temp_like = random.randint(-20, 49)
    humid_like = random.randint(0, 99)
    label = f"{token_a}{temp_like:+d}{token_b}{humid_like}"
    return _domain(label)


# 9) Losowe slowa w roznych jezykach
def dga_multilang_words() -> str:
    words = random.sample(MULTI_LANG_WORDS, 3)
    label = f"{words[0]}-{words[1]}-{words[2]}{random.randint(0, 99):02d}"
    return _domain(label)


# 10) Permutacja slow + hash
def dga_word_permutation() -> str:
    words = MULTI_LANG_WORDS[:]
    random.shuffle(words)
    core = "".join(words[:2])
    digest = hashlib.sha1(f"{core}{_random_seed()}".encode("ascii")).hexdigest()[:6]
    return _domain(core + digest)


# 11) Lancuch sylab
def dga_syllable_chain() -> str:
    label = "".join(random.choice(SYLLABLES) for _ in range(5))
    return _domain(label)


# 12) Markov-lite (przejscia)
def dga_markov_lite() -> str:
    transitions = {
        "a": "eliorun",
        "e": "anrstl",
        "i": "norstl",
        "o": "nrstla",
        "u": "nrl",
        "r": "aeiou",
        "n": "aeiour",
        "t": "aeiour",
        "l": "aeiour",
        "s": "aeiour",
    }
    c = random.choice("aenrstloiu")
    out = [c]
    for _ in range(13):
        c = random.choice(transitions.get(c, "aeiourtnsl"))
        out.append(c)
    return _domain("".join(out))


# 13) Gesty spolgloskowy wzorzec
def dga_consonant_dense() -> str:
    label = "".join(random.choice(CONSONANTS) if i % 4 != 0 else random.choice(VOWELS) for i in range(16))
    return _domain(label)


# 14) Gesty samogloskowy wzorzec
def dga_vowel_dense() -> str:
    label = "".join(random.choice(VOWELS) if i % 3 != 0 else random.choice(CONSONANTS) for i in range(15))
    return _domain(label)


# 15) Hex stream z czasu
def dga_hex_stream() -> str:
    ts = int(_utc_now().timestamp())
    raw = f"{_random_seed() ^ ts ^ random.getrandbits(32):x}" * 2
    return _domain("h" + raw[:17])


# 16) Base32 stream
def dga_base32_stream() -> str:
    payload = f"{_random_seed()}:{_utc_now().isoformat()}:b32".encode("ascii")
    encoded = base64.b32encode(hashlib.sha256(payload).digest()).decode("ascii").lower().rstrip("=")
    return _domain(encoded[:18])


# 17) Wstawianie cyfr
def dga_digit_infix() -> str:
    today = date.today()
    letters = [random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(10)]
    digits = f"{today.day:02d}{today.month:02d}{random.randint(0, 9)}"
    label = "".join(letters[:4]) + digits + "".join(letters[4:])
    return _domain(label)


# 18) Permutacje daty
def dga_date_permutation() -> str:
    today = date.today()
    forms = [
        f"{today.year}{today.month:02d}{today.day:02d}",
        f"{today.day:02d}{today.month:02d}{today.year}",
        f"{today.month:02d}{today.day:02d}{today.year % 100:02d}",
    ]
    label = random.choice(SYLLABLES) + random.choice(SYLLABLES) + random.choice(forms) + random.choice(SYLLABLES)
    return _domain(label)


# 19) Keyboard walk
def dga_keyboard_walk() -> str:
    rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
    row = list(random.choice(rows))
    pos = random.randint(0, len(row) - 1)
    step = random.choice([-1, 1])
    out = []
    for _ in range(12):
        out.append(row[pos])
        pos = (pos + step) % len(row)
        if random.random() < 0.25:
            step *= -1
    return _domain("".join(out) + str(random.randint(10, 99)))


# 20) Affix shuffle
def dga_affix_shuffle() -> str:
    prefixes = ["cdn", "img", "api", "data", "edge", "srv", "mail", "mx", "sync", "cache"]
    stems = ["core", "node", "point", "proxy", "host", "gate", "mesh", "vault", "panel", "clock"]
    suffixes = ["safe", "global", "zone", "prime", "delta", "alpha", "nova", "flux", "shift", "line"]
    label = f"{random.choice(prefixes)}-{random.choice(stems)}-{random.choice(suffixes)}{random.randint(10, 999)}"
    return _domain(label)


DGA_FUNCTIONS = {
    "lcg_date": dga_lcg_date,
    "xorshift": dga_xorshift,
    "sha256_counter": dga_sha256_counter,
    "md5_seed": dga_md5_seed,
    "blake2_round": dga_blake2_round,
    "zodiac_calendar": dga_zodiac_calendar,
    "ip_octets": dga_ip_octets,
    "weather_blend": dga_weather_blend,
    "multilang_words": dga_multilang_words,
    "word_permutation": dga_word_permutation,
    "syllable_chain": dga_syllable_chain,
    "markov_lite": dga_markov_lite,
    "consonant_dense": dga_consonant_dense,
    "vowel_dense": dga_vowel_dense,
    "hex_stream": dga_hex_stream,
    "base32_stream": dga_base32_stream,
    "digit_infix": dga_digit_infix,
    "date_permutation": dga_date_permutation,
    "keyboard_walk": dga_keyboard_walk,
    "affix_shuffle": dga_affix_shuffle,
}






def generate_domains_per_dga(total_count: int = 1000) -> dict[str, list[str]]:
    per_dga = total_count // len(DGA_FUNCTIONS)

    return {
        name: [generator() for _ in range(per_dga)]
        for name, generator in DGA_FUNCTIONS.items()
    }


def save_to_file(data: dict[str, list[str]], filename: str = "dga_2.txt"):
    os.makedirs("", exist_ok=True)

    with open(filename, "w", encoding="utf-8") as f:
        for name, domains in data.items():
            for domain in domains:
                f.write(f"{domain},dga,{name}\n")


if __name__ == "__main__":
    N = 1000000  # ile domen chcesz łącznie

    generated = generate_domains_per_dga(N)
    save_to_file(generated)

    print(f"Zapisano {N} domen do dga_2.txt")