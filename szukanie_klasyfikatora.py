import math
import random
from collections import Counter
import matplotlib.pyplot as plt

# =========================
# USTAWIENIA
# =========================

RANDOM_SEED = 42
BALANCED_SIZE_PER_CLASS = 500000  # ile domen z każdej klasy wziąć maksymalnie
TRAIN_RATIO = 0.8
NGRAM_N = 2
NGRAM_FALLBACK_PROB = 1e-6

LR_EPOCHS = 25
LR_LEARNING_RATE = 0.1
LR_L2 = 0.0001
LR_BATCH_SIZE = 1024

random.seed(RANDOM_SEED)


# =========================
# UI
# =========================

def print_header(title, width=72):
    print("\n" + title.center(width))
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
# WCZYTYWANIE DANYCH
# =========================

def load_domains(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip()]


# =========================
# BALANS DANYCH
# =========================

def create_balanced_dataset(legit_domains, dga_domains, size_per_class=50000):
    n = min(size_per_class, len(legit_domains), len(dga_domains))

    sampled_legit = random.sample(legit_domains, n)
    sampled_dga = random.sample(dga_domains, n)

    dataset = [(d, 0) for d in sampled_legit] + [(d, 1) for d in sampled_dga]
    random.shuffle(dataset)
    return dataset


def train_test_split(dataset, train_ratio=0.8):
    split_idx = int(len(dataset) * train_ratio)
    train_data = dataset[:split_idx]
    test_data = dataset[split_idx:]
    return train_data, test_data


# =========================
# METRYKI STATYSTYCZNE
# =========================

def shannon_entropy(domain):
    if not domain:
        return 0.0

    counts = Counter(domain)
    length = len(domain)

    entropy = 0.0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)

    return entropy


def extract_features(domain):
    vowels = "aeiouy"

    length = len(domain)
    if length == 0:
        return {
            "length": 0.0,
            "entropy": 0.0,
            "vowel_ratio": 0.0,
            "digit_ratio": 0.0,
            "unique_ratio": 0.0,
            "consonant_ratio": 0.0,
            "transitions_ratio": 0.0,
            "digit_clusters_ratio": 0.0,
            "suspicious_suffix": 0.0,
        }

    vowel_count = sum(c in vowels for c in domain)
    digit_count = sum(c.isdigit() for c in domain)
    unique_chars = len(set(domain))
    consonant_count = sum(c.isalpha() and c not in vowels for c in domain)

    transitions = 0
    for i in range(length - 1):
        current_is_vowel = domain[i] in vowels
        next_is_vowel = domain[i + 1] in vowels
        if current_is_vowel != next_is_vowel:
            transitions += 1

    digit_clusters = sum(
        1 for i in range(length - 1)
        if domain[i].isdigit() and domain[i + 1].isdigit()
    )

    suspicious_suffixes = (".ru", ".cn", ".biz", ".xyz")
    suspicious_suffix = 1.0 if domain.endswith(suspicious_suffixes) else 0.0

    return {
        "length": float(length),
        "entropy": shannon_entropy(domain),
        "vowel_ratio": vowel_count / length,
        "digit_ratio": digit_count / length,
        "unique_ratio": unique_chars / length,
        "consonant_ratio": consonant_count / length,
        "transitions_ratio": transitions / length,
        "digit_clusters_ratio": digit_clusters / max(1, length - 1),
        "suspicious_suffix": suspicious_suffix,
    }


# =========================
# N-GRAM MODEL
# =========================

def build_ngram_model(domains, n=2):
    counts = Counter()
    total_domains = len(domains)

    progress_step = max(1, total_domains // 100)

    for idx, domain in enumerate(domains, start=1):
        if len(domain) >= n:
            for i in range(len(domain) - n + 1):
                gram = domain[i:i + n]
                counts[gram] += 1

        if idx % progress_step == 0 or idx == total_domains:
            render_progress(idx, total_domains, prefix="Budowa modelu n-gram: ")

    total_ngrams = sum(counts.values())
    model = {}

    if total_ngrams == 0:
        return model

    for gram, count in counts.items():
        model[gram] = count / total_ngrams

    return model


def ngram_score(domain, model, n=2, fallback_prob=1e-6):
    if len(domain) < n:
        return math.log(fallback_prob)

    score = 0.0
    count = 0

    for i in range(len(domain) - n + 1):
        gram = domain[i:i + n]
        prob = model.get(gram, fallback_prob)
        score += math.log(prob)
        count += 1

    return score / count if count > 0 else math.log(fallback_prob)


# =========================
# PRZYGOTOWANIE WEKTORÓW CECH
# =========================

FEATURE_NAMES = [
    "length",
    "entropy",
    "vowel_ratio",
    "digit_ratio",
    "unique_ratio",
    "consonant_ratio",
    "transitions_ratio",
    "digit_clusters_ratio",
    "suspicious_suffix",
    "ngram_score",
]


def prepare_raw_feature_rows(dataset, ngram_model, n=2):
    rows = []
    total = len(dataset)
    progress_step = max(1, total // 100)

    for idx, (domain, label) in enumerate(dataset, start=1):
        basic = extract_features(domain)
        ng = ngram_score(domain, ngram_model, n=n, fallback_prob=NGRAM_FALLBACK_PROB)

        row = {
            "length": basic["length"],
            "entropy": basic["entropy"],
            "vowel_ratio": basic["vowel_ratio"],
            "digit_ratio": basic["digit_ratio"],
            "unique_ratio": basic["unique_ratio"],
            "consonant_ratio": basic["consonant_ratio"],
            "transitions_ratio": basic["transitions_ratio"],
            "digit_clusters_ratio": basic["digit_clusters_ratio"],
            "suspicious_suffix": basic["suspicious_suffix"],
            "ngram_score": ng,
            "label": label,
            "domain": domain,
        }
        rows.append(row)

        if idx % progress_step == 0 or idx == total:
            render_progress(idx, total, prefix="Ekstrakcja cech: ")

    return rows


def fit_standardizer(rows, feature_names):
    means = {}
    stds = {}

    n = len(rows)
    if n == 0:
        for name in feature_names:
            means[name] = 0.0
            stds[name] = 1.0
        return means, stds

    for name in feature_names:
        mean = sum(row[name] for row in rows) / n
        means[name] = mean

    for name in feature_names:
        variance = sum((row[name] - means[name]) ** 2 for row in rows) / n
        std = math.sqrt(variance)
        stds[name] = std if std > 1e-12 else 1.0

    return means, stds


def transform_rows_to_matrix(rows, feature_names, means, stds):
    X = []
    y = []

    for row in rows:
        vector = []
        for name in feature_names:
            z = (row[name] - means[name]) / stds[name]
            vector.append(z)

        X.append(vector)
        y.append(row["label"])

    return X, y


# =========================
# MINI LOGISTIC REGRESSION
# =========================

def sigmoid(z):
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    else:
        ez = math.exp(z)
        return ez / (1.0 + ez)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def predict_proba_single(x, weights, bias):
    return sigmoid(dot(x, weights) + bias)


def predict_proba_batch(X, weights, bias):
    return [predict_proba_single(x, weights, bias) for x in X]


def binary_cross_entropy(y_true, y_prob):
    eps = 1e-12
    total = 0.0
    n = len(y_true)

    for yt, yp in zip(y_true, y_prob):
        yp = min(max(yp, eps), 1.0 - eps)
        total += -(yt * math.log(yp) + (1 - yt) * math.log(1 - yp))

    return total / max(1, n)


def train_logistic_regression(X, y, epochs=25, lr=0.1, l2=0.0001, batch_size=1024):
    n_samples = len(X)
    n_features = len(X[0]) if X else 0

    weights = [0.0] * n_features
    bias = 0.0

    indices = list(range(n_samples))

    print_header("Trening mini logistic regression")

    for epoch in range(1, epochs + 1):
        random.shuffle(indices)

        for batch_start in range(0, n_samples, batch_size):
            batch_indices = indices[batch_start:batch_start + batch_size]

            grad_w = [0.0] * n_features
            grad_b = 0.0
            m = len(batch_indices)

            for idx in batch_indices:
                x = X[idx]
                yi = y[idx]
                pi = predict_proba_single(x, weights, bias)
                error = pi - yi

                for j in range(n_features):
                    grad_w[j] += error * x[j]
                grad_b += error

            if m > 0:
                for j in range(n_features):
                    grad_w[j] = grad_w[j] / m + l2 * weights[j]
                grad_b = grad_b / m

                for j in range(n_features):
                    weights[j] -= lr * grad_w[j]
                bias -= lr * grad_b

        probs = predict_proba_batch(X, weights, bias)
        loss = binary_cross_entropy(y, probs)

        print(f"Epoka {epoch:2d}/{epochs} - loss: {loss:.6f}")

    return weights, bias


# =========================
# EWALUACJA
# =========================

def confusion_counts(y_true, y_prob, threshold=0.5):
    tp = fp = fn = tn = 0

    for yt, yp in zip(y_true, y_prob):
        pred = 1 if yp >= threshold else 0

        if pred == 1 and yt == 1:
            tp += 1
        elif pred == 1 and yt == 0:
            fp += 1
        elif pred == 0 and yt == 1:
            fn += 1
        else:
            tn += 1

    return tp, fp, fn, tn


def classification_metrics(y_true, y_prob, threshold=0.5):
    tp, fp, fn, tn = confusion_counts(y_true, y_prob, threshold=threshold)

    precision = tp / (tp + fp + 1e-12)
    recall = tp / (tp + fn + 1e-12)
    accuracy = (tp + tn) / max(1, tp + fp + fn + tn)
    f1 = 2 * precision * recall / (precision + recall + 1e-12)

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "accuracy": accuracy,
        "f1": f1,
    }


def find_best_threshold(y_true, y_prob):
    best = {
        "threshold": 0.5,
        "f1": -1.0,
        "precision": 0.0,
        "recall": 0.0,
        "accuracy": 0.0,
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "tn": 0,
    }

    candidate_thresholds = sorted(set(round(p, 6) for p in y_prob))

    if len(candidate_thresholds) > 2000:
        step = max(1, len(candidate_thresholds) // 2000)
        candidate_thresholds = candidate_thresholds[::step]

    if 0.5 not in candidate_thresholds:
        candidate_thresholds.append(0.5)

    candidate_thresholds = sorted(set(candidate_thresholds))

    total = len(candidate_thresholds)
    for idx, threshold in enumerate(candidate_thresholds, start=1):
        metrics = classification_metrics(y_true, y_prob, threshold)

        if metrics["f1"] > best["f1"]:
            best = {
                "threshold": threshold,
                **metrics,
            }

        if idx % max(1, total // 100) == 0 or idx == total:
            render_progress(idx, total, prefix="Szukam najlepszego progu: ")

    return best


# =========================
# ROC I AUC
# =========================

def roc_curve_points(y_true, y_prob):
    thresholds = sorted(set(y_prob), reverse=True)

    if len(thresholds) > 2000:
        step = max(1, len(thresholds) // 2000)
        thresholds = thresholds[::step]

    roc_points = []

    total = len(thresholds)
    for idx, threshold in enumerate(thresholds, start=1):
        tp, fp, fn, tn = confusion_counts(y_true, y_prob, threshold=threshold)

        tpr = tp / (tp + fn + 1e-12)  # recall / sensitivity
        fpr = fp / (fp + tn + 1e-12)

        roc_points.append((fpr, tpr, threshold))

        if idx % max(1, total // 100) == 0 or idx == total:
            render_progress(idx, total, prefix="Wyznaczanie ROC: ")

    roc_points.append((0.0, 0.0, 1.0))
    roc_points.append((1.0, 1.0, 0.0))

    roc_points = sorted(set(roc_points), key=lambda x: (x[0], x[1]))
    return roc_points


def auc_from_roc_points(roc_points):
    area = 0.0
    for i in range(1, len(roc_points)):
        x1, y1, _ = roc_points[i - 1]
        x2, y2, _ = roc_points[i]
        area += (x2 - x1) * (y1 + y2) / 2.0
    return area


# =========================
# RAPORT CECH
# =========================

def print_model_weights(weights, feature_names):
    print_header("Wagi modelu logistic regression")

    pairs = list(zip(feature_names, weights))
    pairs.sort(key=lambda x: abs(x[1]), reverse=True)

    for name, weight in pairs:
        print(f"{name:22s}: {weight: .6f}")


# =========================
# WYKRESY
# =========================

def plot_score_histograms(y_true, y_prob, threshold):
    legit_scores = [p for yt, p in zip(y_true, y_prob) if yt == 0]
    dga_scores = [p for yt, p in zip(y_true, y_prob) if yt == 1]

    plt.figure(figsize=(10, 6))
    plt.hist(legit_scores, bins=100, alpha=0.6, label="Domain", edgecolor="black")
    plt.hist(dga_scores, bins=100, alpha=0.6, label="DGA", edgecolor="black")
    plt.axvline(threshold, color="red", linestyle="--", linewidth=2, label=f"Prog = {threshold:.4f}")
    plt.xlabel("Prawdopodobienstwo klasy DGA")
    plt.ylabel("Liczba domen")
    plt.title("Rozklad wynikow modelu")
    plt.grid(axis="y", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


def plot_roc_curve(roc_points, auc_value):
    fpr = [p[0] for p in roc_points]
    tpr = [p[1] for p in roc_points]

    plt.figure(figsize=(8, 8))
    plt.plot(fpr, tpr, linewidth=2, label=f"ROC (AUC = {auc_value:.4f})")
    plt.plot([0, 1], [0, 1], linestyle="--", linewidth=1, label="Losowy klasyfikator")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("Krzywa ROC")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


# =========================
# MAIN
# =========================

def main():
    print_header("TEST SKUTECZNOSCI NARZEDZI STATYSTYCZNYCH")

    legit = load_domains("data/correct.txt")
    dga = load_domains("data/dga.txt")

    print_header("Wczytanie danych")
    print(f"Wczytano domeny prawidlowe: {len(legit)}")
    print(f"Wczytano domeny DGA:        {len(dga)}")

    dataset = create_balanced_dataset(
        legit_domains=legit,
        dga_domains=dga,
        size_per_class=BALANCED_SIZE_PER_CLASS
    )

    print_header("Balanced dataset")
    print(f"Liczba rekordow lacznie:   {len(dataset)}")
    print(f"Klasa domain:              {len(dataset) // 2}")
    print(f"Klasa dga:                 {len(dataset) // 2}")

    train_data, test_data = train_test_split(dataset, train_ratio=TRAIN_RATIO)

    print_header("Podzial train / test")
    print(f"Train: {len(train_data)}")
    print(f"Test:  {len(test_data)}")

    print_header("Budowa modelu n-gram na train")
    legit_train_domains = [domain for domain, label in train_data if label == 0]
    ngram_model = build_ngram_model(legit_train_domains, n=NGRAM_N)

    print_header("Ekstrakcja cech train")
    train_rows = prepare_raw_feature_rows(train_data, ngram_model, n=NGRAM_N)

    print_header("Ekstrakcja cech test")
    test_rows = prepare_raw_feature_rows(test_data, ngram_model, n=NGRAM_N)

    print_header("Normalizacja cech")
    means, stds = fit_standardizer(train_rows, FEATURE_NAMES)
    print(means)
    print(stds)
    X_train, y_train = transform_rows_to_matrix(train_rows, FEATURE_NAMES, means, stds)
    X_test, y_test = transform_rows_to_matrix(test_rows, FEATURE_NAMES, means, stds)

    weights, bias = train_logistic_regression(
        X_train,
        y_train,
        epochs=LR_EPOCHS,
        lr=LR_LEARNING_RATE,
        l2=LR_L2,
        batch_size=LR_BATCH_SIZE,
    )

    print_model_weights(weights, FEATURE_NAMES)

    print_header("Predykcja na zbiorze testowym")
    y_prob_test = predict_proba_batch(X_test, weights, bias)

    print_header("Szukam najlepszego progu na test")
    best = find_best_threshold(y_test, y_prob_test)

    print_header("Najlepszy prog i metryki")
    print(f"Najlepszy prog:            {best['threshold']:.6f}")
    print(f"Accuracy:                  {best['accuracy'] * 100:.4f}%")
    print(f"Precision:                 {best['precision'] * 100:.4f}%")
    print(f"Recall:                    {best['recall'] * 100:.4f}%")
    print(f"F1 score:                  {best['f1'] * 100:.4f}%")
    print(f"TP:                        {best['tp']}")
    print(f"FP:                        {best['fp']}")
    print(f"FN:                        {best['fn']}")
    print(f"TN:                        {best['tn']}")

    print_header("Wyznaczanie krzywej ROC")
    roc_points = roc_curve_points(y_test, y_prob_test)
    auc_value = auc_from_roc_points(roc_points)

    print_header("ROC / AUC")
    print(f"AUC:                       {auc_value:.6f}")

    plot_score_histograms(y_test, y_prob_test, best["threshold"])
    plot_roc_curve(roc_points, auc_value)


if __name__ == "__main__":
    main()