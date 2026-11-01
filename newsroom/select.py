"""Pick this run's stories according to daily quotas, diversity caps and importance."""

# small fixed quotas first, so rounding never squeezes them out
ORDER = ["opinion", "awareness", "nba", "orgs", "top5", "other_sports", "world"]


def run_fraction(run_hours: list, hour_local: int) -> float:
    hours = sorted(run_hours)
    done = sum(1 for h in hours if h <= hour_local)
    return max(done, 1) / len(hours)


def targets(cats_cfg: dict, daily_total: int, used: dict, fraction: float) -> tuple:
    cats = cats_cfg["categories"]
    run_total = max(round(daily_total * fraction) - used["total"], 0)
    t = {}
    for c in ORDER:
        q = cats[c]["quota"]
        t[c] = max(round(q * fraction) - used["cats"].get(c, 0), 0)
    return run_total, t


def select(clusters: list, cats_cfg: dict, run_total: int, cat_targets: dict, used: dict) -> list:
    cats = cats_cfg["categories"]
    sub_used = dict(used.get("subs", {}))
    chosen, chosen_ids = [], set()

    def can_take(c, extra=0):
        cap = cats[c["category"]].get("max_per_sub", 99) + extra
        if c["sub"] in ("general", "other", "all"):
            cap += 2
        return sub_used.get(f'{c["category"]}:{c["sub"]}', 0) < cap

    def take(c, slot):
        c["slot"] = slot
        chosen.append(c)
        chosen_ids.add(c["id"])
        k = f'{c["category"]}:{c["sub"]}'
        sub_used[k] = sub_used.get(k, 0) + 1

    def floor(cat):
        return cats.get(cat, {}).get("min_score", 0)

    pool = sorted(clusters, key=lambda c: -c["score"])
    for cat in ORDER:
        need = cat_targets.get(cat, 0)
        for c in pool:
            if need == 0 or len(chosen) >= run_total:
                break
            if c["score"] < floor(cat):
                break                      # pool is score-sorted: nothing weaker qualifies
            if c["category"] == cat and c["id"] not in chosen_ids and can_take(c):
                take(c, cat)
                need -= 1
        # unfilled quota rolls into flex — but only strong stories may use it,
        # so a quiet day publishes fewer items instead of filler

    remaining = run_total - len(chosen)
    for c in pool:
        if remaining <= 0 or c["score"] < floor("flex"):
            break
        if c["id"] in chosen_ids or c["category"] == "opinion" or c["score"] < floor(c["category"]):
            continue
        if can_take(c, extra=1):
            take(c, "flex")
            remaining -= 1

    return sorted(chosen, key=lambda c: -c["score"])[:run_total]
