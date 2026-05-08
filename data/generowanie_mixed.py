import random
from collections import defaultdict


def load_correct_domains(filename: str) -> list[str]:
    domains = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            domains.append(line.split(",")[0])
    return domains


def load_dga_domains(filename: str):
    with open(filename, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    # sprawdzamy format
    if len(lines[0].split(",")) == 3:
        categories = defaultdict(list)
        for line in lines:
            domain, _, category = line.split(",")
            categories[category].append((domain, category))
        return categories
    else:
        return [(line.split(",")[0], None) for line in lines]


def sample_dga(dga_data, count: int):
    if isinstance(dga_data, list):
        return random.sample(dga_data, min(count, len(dga_data)))

    # dict → równy podział
    categories = list(dga_data.keys())
    per_cat = count // len(categories)
    remainder = count % len(categories)

    result = []

    for i, cat in enumerate(categories):
        take = per_cat + (1 if i < remainder else 0)
        available = dga_data[cat]
        result.extend(random.sample(available, min(take, len(available))))

    return result


def create_mixed_file(
    correct_file="correct.txt",
    dga_file="data/dga_2.txt",
    output_file="data/mixed.txt",
    x=500,
    y=500
):
    correct = load_correct_domains(correct_file)
    dga = load_dga_domains(dga_file)

    sampled_correct = random.sample(correct, min(x, len(correct)))
    sampled_dga = sample_dga(dga, y)

    # correct → 2 kolumny
    labeled_correct = [f"{d},legit" for d in sampled_correct]

    # dga → 2 lub 3 kolumny
    labeled_dga = []
    for domain, category in sampled_dga:
        if category:
            labeled_dga.append(f"{domain},dga,{category}")
        else:
            labeled_dga.append(f"{domain},dga")

    mixed = labeled_correct + labeled_dga
    random.shuffle(mixed)

    with open(output_file, "w", encoding="utf-8") as f:
        for line in mixed:
            f.write(line + "\n")

    print(f"Zapisano {len(mixed)} domen do {output_file}")


if __name__ == "__main__":
    create_mixed_file(
        correct_file="legit_test.txt",
        dga_file="dga_2.txt",  # lub dga.txt
        output_file="mixed.txt",
        x=900000, # PRAWDIŁOWE DOMENY (LEGIT)
        y=900000  # BŁĘDNE DOMENY (DGA)
    )