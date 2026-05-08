import random


def load_domains(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip()]


def save_domains(domains, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        for d in domains:
            f.write(d + "\n")


def split_domains(
    input_file="correct.txt",
    train_file="legit_train.txt",
    test_file="legit_test.txt",
    train_ratio=0.9,
    seed=42,
):
    # wczytanie
    domains = load_domains(input_file)

    # opcjonalnie usunięcie duplikatów
    domains = list(set(domains))

    print(f"Załadowano domen: {len(domains)}")

    # powtarzalność
    random.seed(seed)

    # losowe mieszanie
    random.shuffle(domains)

    # split
    split_idx = int(len(domains) * train_ratio)

    train = domains[:split_idx]
    test = domains[split_idx:]

    # zapis
    save_domains(train, train_file)
    save_domains(test, test_file)

    print(f"Train: {len(train)} domen -> {train_file}")
    print(f"Test:  {len(test)} domen -> {test_file}")


if __name__ == "__main__":
    split_domains(
        input_file="correct_2.txt",
        train_file="legit_train.txt",
        test_file="legit_test.txt",
        train_ratio=0.9,
        seed=42
    )