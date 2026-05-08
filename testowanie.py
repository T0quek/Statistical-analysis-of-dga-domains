import socket
import dns.resolver
import whois
import requests
from datetime import datetime
from statystyka import *


# =========================
# DNS
# =========================

def get_dns_features(domain):
    features = {
        "num_ips": 0,
        "has_mx": 0,
        "has_ns": 0,
        "ttl": 0
    }

    try:
        answers = dns.resolver.resolve(domain, 'A')
        features["num_ips"] = len(answers)
        features["ttl"] = answers.rrset.ttl
    except:
        pass

    try:
        dns.resolver.resolve(domain, 'MX')
        features["has_mx"] = 1
    except:
        pass

    try:
        dns.resolver.resolve(domain, 'NS')
        features["has_ns"] = 1
    except:
        pass

    return features

# =========================
# BAZA WHOIS
# =========================

def get_whois_features(domain):
    features = {"domain_age_days": 0}

    try:
        w = whois.whois(domain)
        creation_date = w.creation_date

        if isinstance(creation_date, list):
            creation_date = creation_date[0]

        if creation_date:
            age = (datetime.now() - creation_date).days
            features["domain_age_days"] = age
    except:
        pass

    return features

# =========================
# GEO/IP
# =========================

def get_ip_features(domain):
    features = {
        "is_cloud": 0
    }

    try:
        ip = socket.gethostbyname(domain)
        response = requests.get(f"https://ipinfo.io/{ip}/json").json()

        org = response.get("org", "").lower()

        if any(x in org for x in ["cloud", "amazon", "google", "microsoft"]):
            features["is_cloud"] = 1

    except:
        pass

    return features

# =========================
# NETWORK SCORE
# =========================

def network_score(domain):
    dns_f = get_dns_features(domain)
    whois_f = get_whois_features(domain)
    ip_f = get_ip_features(domain)

    score = 0

    # młoda domena
    if whois_f["domain_age_days"] < 30:
        score += 0.2
    elif whois_f["domain_age_days"] < 180:
        score += 0.1

    # DNS
    if dns_f["num_ips"] <= 1:
        score += 0.02

    if dns_f["has_mx"] == 0:
        score += 0.02

    if dns_f["has_ns"] == 0:
        score += 0.02

    # TTL
    if dns_f["ttl"] != 0 and dns_f["ttl"] < 300:
        score += 0.05

    return min(score, 1.0)


def final_score(row_limit = 100):
    correct_stat = 0
    correct_stat_net = 0
    correct_stat_mixed = 0

    i = 0
    for line in mixed:
        if i > row_limit:
            break
        domain, label = line.split(",")
        domain = domain.strip()
        label = label.strip()

        score = stat_score(domain)
        score_net = network_score(domain)
        score_mixed = 0.5*(score + score_net)
        print(domain, label, score, score_net, score_mixed)

        if score >= 0.3 and label == "dga":
            correct_stat += 1
        elif score < 0.3 and label == "domain":
            correct_stat += 1

        if score_net >= 0.5 and label == "dga":
            correct_stat_net += 1
        elif score_net < 0.5 and label == "domain":
            correct_stat_net += 1

        if score_mixed >= 0.4 and label == "dga":
            correct_stat_mixed += 1
        elif score_mixed < 0.4 and label == "domain":
            correct_stat_mixed += 1

        i += 1

    accuracy = correct_stat / len(mixed)
    accuracy_net = correct_stat_net / len(mixed)
    accuracy_mixed = correct_stat_mixed / len(mixed)

    ####

    print(f"Accuracy: {accuracy*100:.2f}%")
    print(f"Accuracy (net): {accuracy_net*100:.2f}%")
    print(f"Accuracy (overall): {accuracy_mixed*100:.2f}%")

final_score(50)

#domain = "google.com"
#score = stat_score(domain)
#score_net = network_score(domain)
#score_mixed = 0.5*(score + score_net)
#print(f"Score: {score:.4f}")
#print(f"Score (net): {score_net:.4f}")
#print(f"Score (overall): {score_mixed:.4f}")