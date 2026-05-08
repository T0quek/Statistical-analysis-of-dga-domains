import csv

INPUT_FILE = "top10milliondomains.csv"
OUTPUT_FILE = "correct_2.txt"

with open(INPUT_FILE, newline='', encoding="utf-8") as csvfile, \
     open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:

    reader = csv.DictReader(csvfile)

    for row in reader:
        domain = row["Domain"].strip().lower()

        # opcjonalnie usuwamy www.
        if domain.startswith("www."):
            domain = domain[4:]

        outfile.write(domain + "\n")

print("Zapisano plik correct_2.txt")