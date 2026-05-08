import math
import random
from collections import Counter
from collections import defaultdict
import matplotlib.pyplot as plt

# =========================
# PARAMETRY (Z MODELU ML)
# =========================

THRESHOLD = 0.524716

# ŚREDNIE
MEANS = {
    'length': 17.58790125,
    'entropy': 3.5035092617829844,
    'vowel_ratio': 0.3171020166405487,
    'digit_ratio': 0.021957822502129444,
    'unique_ratio': 0.7428660814850874,
    'consonant_ratio': 0.5888975596006817,
    'transitions_ratio': 0.5147290312809021,
    'digit_clusters_ratio': 0.0066888058037531655,
    'suspicious_suffix': 0.08693875,
    'ngram_score': -6.393525650460594
}

# ODCHYLENIA STANDARDOWE
STDS = {
    'length': 5.3703473696073365,
    'entropy': 0.37745929639501274,
    'vowel_ratio': 0.09641510445788971,
    'digit_ratio': 0.06931697780825018,
    'unique_ratio': 0.10865064666207169,
    'consonant_ratio': 0.09418703411308375,
    'transitions_ratio': 0.16578366434701902,
    'digit_clusters_ratio': 0.03171492578738712,
    'suspicious_suffix': 0.28174528167910373,
    'ngram_score': 1.165694832830794
}


# =========================
# WAGI Z MODELU
# =========================

WEIGHTS = {
    "consonant_ratio": 5.233182,
    "vowel_ratio": 5.120021,
    "ngram_score": -4.169638,
    "digit_ratio": 1.516126,
    "entropy": 1.009070,
    "length": -0.673221,
    "unique_ratio": -0.473939,
    "digit_clusters_ratio": 0.411217,
    "suspicious_suffix": -0.349693,
    "transitions_ratio": -0.027348
}

# =========================
# UI
# =========================

def print_header(title, width=48):
    print(title.center(width))
    print("=" * width)


def render_progress(current, total, prefix="Postep: ", bar_width=30):
    if total <= 0:
        return

    ratio = current / total
    filled = int(bar_width * ratio)
    bar = "#" * filled + "-" * (bar_width - filled)
    percent = ratio * 100

    print(
        f"\r{prefix}[{bar}] {percent:6.2f}% ({current}/{total})",
        end="",
        flush=True,
    )

    if current == total:
        print()

# =========================
# DANE
# =========================

def load_domains(file_path):
    with open(file_path, "r") as f:
        return [line.strip().lower() for line in f if line.strip()]

legit = load_domains("data/legit_train.txt")
mixed = load_domains("data/mixed.txt")

print_header("Wczytanie danych")
print(f"Wczytano rekordy mixed: {len(mixed)}")

# =========================
# ENTROPIA
# =========================

def shannon_entropy(domain):
    counts = Counter(domain)
    length = len(domain)

    entropy = 0.0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)

    return entropy

# =========================
# N-GRAM MODEL
# =========================

def build_ngram_model(domains, n=2):
    model = Counter()
    total_domains = len(domains)

    for idx, d in enumerate(domains, start=1):
        for i in range(len(d)-n+1):
            gram = d[i:i+n]
            model[gram] += 1

        if idx % 10000 == 0 or idx == total_domains:
            render_progress(idx, total_domains, prefix="Budowa n-gram: ")

    total = sum(model.values())

    for k in model:
        model[k] /= total

    return model


def ngram_score(domain, model, n=2):
    score = 0
    count = 0

    for i in range(len(domain)-n+1):
        gram = domain[i:i+n]
        prob = model.get(gram, 1e-6)
        score += math.log(prob)
        count += 1

    return score / count if count > 0 else -10

# =========================
# CECHY
# =========================

def extract_features(domain):
    vowels = "aeiouy"
    length = len(domain)

    vowel_count = sum(c in vowels for c in domain)
    digit_count = sum(c.isdigit() for c in domain)
    unique_chars = len(set(domain))
    consonant_count = sum(c.isalpha() and c not in vowels for c in domain)

    transitions = 0
    for i in range(length - 1):
        if (domain[i] in vowels) != (domain[i+1] in vowels):
            transitions += 1

    digit_clusters = sum(
        1 for i in range(length-1)
        if domain[i].isdigit() and domain[i+1].isdigit()
    )

    return {
        "length": length,
        "entropy": shannon_entropy(domain),
        "vowel_ratio": vowel_count / length,
        "digit_ratio": digit_count / length,
        "unique_ratio": unique_chars / length,
        "consonant_ratio": consonant_count / length,
        "transitions_ratio": transitions / length,
        "digit_clusters_ratio": digit_clusters,
        "suspicious_suffix": 1 if domain.endswith((".ru",".cn",".biz",".xyz")) else 0
    }

# =========================
# NORMALIZACJA
# =========================

def normalize(x, key):
    return (x - MEANS[key]) / STDS[key]

# =========================
# FINAL SCORE
# =========================

def stat_score(domain):
    f = extract_features(domain)
    ng = ngram_score(domain, ngram_model)

    raw = {
        **f,
        "ngram_score": ng
    }

    # NORMALIZACJA
    z = {k: normalize(raw[k], k) for k in raw}

    # MODEL
    score = sum(WEIGHTS[k] * z[k] for k in WEIGHTS)

    prob = 1 / (1 + math.exp(-score))
    return prob

# =========================
# TEST
# =========================

scores = []

def test_scoring():
    correct = 0
    fp = 0
    fn = 0

    total = len(mixed)

    # statystyki per funkcja DGA
    dga_stats = defaultdict(lambda: {"tp": 0, "fn": 0, "total": 0})

    for idx, line in enumerate(mixed, start=1):
        parts = line.split(",")

        domain = parts[0].strip()
        label = parts[1].strip()
        func = parts[2].strip() if len(parts) == 3 else None

        prob = stat_score(domain)
        scores.append(prob)

        pred_is_dga = prob >= THRESHOLD

        # GLOBALNE STATYSTYKI
        if pred_is_dga and label == "dga":
            correct += 1
            if func:
                dga_stats[func]["tp"] += 1

        elif not pred_is_dga and label == "legit":
            correct += 1

        elif pred_is_dga and label == "legit":
            fp += 1

        elif not pred_is_dga and label == "dga":
            fn += 1
            if func:
                dga_stats[func]["fn"] += 1

        # ZLICZANIE TOTALI PER FUNKCJA
        if label == "dga" and func:
            dga_stats[func]["total"] += 1

        if idx % 10000 == 0 or idx == total:
            render_progress(idx, total, prefix="Test: ")

    accuracy = correct / total

    print_header("Wyniki globalne")
    print(f"Accuracy: {accuracy*100:.4f}%")
    print(f"False Positive: {fp} ({fp/total*100:.4f}%)")
    print(f"False Negative: {fn} ({fn/total*100:.4f}%)")

    # =========================
    # STATYSTYKI PER DGA
    # =========================

    print_header("Skuteczność per algorytm DGA")

    for func, stats in sorted(dga_stats.items()):
        tp = stats["tp"]
        fn_local = stats["fn"]
        total_local = stats["total"]

        if total_local == 0:
            continue

        recall = tp / total_local  # wykrywalność DGA

        print(f"{func:20s} | wykrywalność: {recall*100:6.2f}% | ({tp}/{total_local})")

# =========================
# MAIN
# =========================

print("Tworzenie modelu n-gram")
ngram_model = build_ngram_model(legit)

print_header("Start analizy")
test_scoring()

plt.figure(figsize=(10, 6))

# histogram
plt.hist(scores, bins=100, alpha=0.75, edgecolor='black', label='Wyniki modelu')
plt.axvline(THRESHOLD, color='red', linestyle='--', linewidth=2, label=f'Threshold = {THRESHOLD:.3f}')
plt.title("Rozkład prawdopodobieństwa klasyfikacji domen (DGA vs Legit)", fontsize=14)
plt.xlabel("Prawdopodobieństwo bycia domeną DGA", fontsize=12)
plt.ylabel("Liczba domen", fontsize=12)
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend()
plt.tight_layout()
plt.show()