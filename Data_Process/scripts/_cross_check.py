"""
Helper module for multi-source cross-checking (used by 03_rf_validation).

Provides three async-ish source checkers with a unified return shape:
  {
    "source": "<short_name>",
    "matched": bool,
    "confidence": float (0.0-1.0),
    "evidence": str,          # short text snippet
    "url": str | None,
    "stale": bool,            # data > 5y old
    "country_match": bool|None,
  }

Sources:
  1. HF datasets — exact/fuzzy match on (freq, country, modulation)
  2. Wikipedia API — page section match for the band
  3. Web search — FCC/ITU/ANFR + RTL-SDR/Flipper forums

Auto-detects search backends:
  BRAVE_API_KEY → Brave Search API
  SERPER_API_KEY → Serper (Google) API
  GOOGLE_CSE_KEY + GOOGLE_CSE_CX → Google CSE
  fallback → DuckDuckGo HTML scrape (rate-limited, best-effort)
"""
import os, json, re, time, urllib.parse, urllib.request
from pathlib import Path
from typing import Optional

# ----------------- Lightweight HTTP -----------------
def _get(url: str, timeout: int = 8, headers: dict = None) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "Flipper-RF-DataSet/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None

# ----------------- 1) HF dataset match -----------------
_HF_CACHE = {}
def hf_dataset_match(freq_hz: float, country: str, modulation: Optional[str], cfg: dict) -> dict:
    """Cross-check against community HF dataset(s)."""
    if not cfg.get("hf_datasets"):
        return {"source": "hf_dataset", "matched": None, "confidence": 0.0,
                "evidence": "no HF dataset configured", "url": None, "stale": False, "country_match": None}
    try:
        from datasets import load_dataset
    except ImportError:
        return {"source": "hf_dataset", "matched": None, "confidence": 0.0,
                "evidence": "datasets lib not installed", "url": None, "stale": False, "country_match": None}

    for ds_spec in cfg["hf_datasets"]:
        name, split, ffield, mfield, pfield = ds_spec
        if name not in _HF_CACHE:
            try:
                _HF_CACHE[name] = list(load_dataset(name, split=split, streaming=True).take(20000))
            except Exception as e:
                _HF_CACHE[name] = []
        ds = _HF_CACHE[name]
        # Tolerant freq match: ±0.5 MHz
        for row in ds:
            try:
                row_freq = float(row.get(ffield, 0))
                if row_freq < 1e6: row_freq *= 1e6  # MHz → Hz
                if abs(row_freq - (freq_hz or 0)) < 500_000:
                    mod_ok = modulation is None or str(row.get(mfield, "")).lower() == modulation.lower()
                    return {
                        "source": f"hf:{name}", "matched": True, "confidence": 0.9 if mod_ok else 0.6,
                        "evidence": f"freq match {row_freq/1e6:.3f} MHz, mod={row.get(mfield)}, proto={row.get(pfield)}",
                        "url": f"https://huggingface.co/datasets/{name}",
                        "stale": False, "country_match": None,
                    }
            except Exception:
                continue
    return {"source": "hf_dataset", "matched": False, "confidence": 0.0,
            "evidence": "no match in HF datasets", "url": None, "stale": False, "country_match": None}

# ----------------- 2) Wikipedia API -----------------
def wikipedia_check(freq_hz: float, service: str, country: str, cfg: dict) -> dict:
    """Query Wikipedia for the frequency band / service combo."""
    if not cfg.get("enabled"):
        return {"source": "wikipedia", "matched": None, "confidence": 0.0,
                "evidence": "wikipedia disabled", "url": None, "stale": False, "country_match": None}
    freq_mhz = (freq_hz or 0) / 1e6
    queries = []
    if service:
        queries.append(f"{service} {freq_mhz:.0f} MHz")
    queries.append(f"{freq_mhz:.0f} MHz frequency allocation {country or ''}".strip())

    endpoint = cfg["endpoint"]
    for q in queries:
        params = {
            "action": "query", "list": "search", "srsearch": q,
            "srlimit": 3, "format": "json", "srprop": "snippet",
        }
        url = endpoint + "?" + urllib.parse.urlencode(params)
        body = _get(url, timeout=cfg.get("timeout", 8))
        if not body: continue
        try:
            data = json.loads(body)
            hits = data.get("query", {}).get("search", [])
            if not hits: continue
            top = hits[0]
            snippet = re.sub(r"<[^>]+>", "", top.get("snippet", ""))
            title = top.get("title", "")
            # Confidence: 0.7 if freq number appears in snippet, else 0.4
            conf = 0.7 if f"{freq_mhz:.0f}" in (snippet + title) else 0.4
            return {
                "source": "wikipedia", "matched": True, "confidence": conf,
                "evidence": f"{title}: {snippet[:200]}",
                "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}",
                "stale": False, "country_match": None,
            }
        except json.JSONDecodeError:
            continue
    return {"source": "wikipedia", "matched": False, "confidence": 0.0,
            "evidence": "no Wikipedia match", "url": None, "stale": False, "country_match": None}

# ----------------- 3) Web search -----------------
def _ddg_html_search(query: str, max_results: int = 5, timeout: int = 10) -> list:
    """DuckDuckGo HTML fallback — best-effort scraping, rate-limited."""
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    body = _get(url, timeout=timeout)
    if not body: return []
    results = []
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>.*?<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
                         body, re.DOTALL):
        href = m.group(1)
        title = re.sub(r"<[^>]+>", "", m.group(2))
        snippet = re.sub(r"<[^>]+>", "", m.group(3))
        results.append({"url": href, "title": title, "snippet": snippet})
        if len(results) >= max_results: break
    return results

def _brave_search(query: str, key: str, max_results: int = 5, timeout: int = 10) -> list:
    url = "https://api.search.brave.com/res/v1/web/search?q=" + urllib.parse.quote(query) + f"&count={max_results}"
    body = _get(url, timeout=timeout, headers={"X-Subscription-Token": key, "Accept": "application/json"})
    if not body: return []
    try:
        data = json.loads(body)
        return [{"url": w["url"], "title": w["title"], "snippet": w.get("description", "")}
                for w in data.get("web", {}).get("results", [])[:max_results]]
    except Exception:
        return []

def _serper_search(query: str, key: str, max_results: int = 5, timeout: int = 10) -> list:
    try:
        req = urllib.request.Request(
            "https://google.serper.dev/search",
            data=json.dumps({"q": query, "num": max_results}).encode(),
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        return [{"url": r["link"], "title": r["title"], "snippet": r.get("snippet", "")}
                for r in data.get("organic", [])[:max_results]]
    except Exception:
        return []

def web_search(query: str, max_results: int = 5, timeout: int = 10) -> list:
    """Auto-detect backend, return [{url, title, snippet}, ...]."""
    if os.environ.get("BRAVE_API_KEY"):
        return _brave_search(query, os.environ["BRAVE_API_KEY"], max_results, timeout)
    if os.environ.get("SERPER_API_KEY"):
        return _serper_search(query, os.environ["SERPER_API_KEY"], max_results, timeout)
    return _ddg_html_search(query, max_results, timeout)

def web_cross_check(freq_hz: float, service: str, country: str, cfg: dict) -> dict:
    """Web search against trusted regulators + forums."""
    if not cfg.get("enabled"):
        return {"source": "websearch", "matched": None, "confidence": 0.0,
                "evidence": "websearch disabled", "url": None, "stale": False, "country_match": None}

    freq_mhz = (freq_hz or 0) / 1e6
    country_term = country or ""
    query = f"{freq_mhz:.2f} MHz {service or ''} {country_term} allocation"

    results = web_search(query, max_results=cfg.get("max_results_per_claim", 5), timeout=cfg.get("timeout", 10))
    if not results:
        return {"source": "websearch", "matched": False, "confidence": 0.0,
                "evidence": "no web results", "url": None, "stale": False, "country_match": None}

    trusted = set(cfg.get("trusted_domains", []))
    forums = set(cfg.get("forum_domains", []))

    best = None
    for r in results:
        host = urllib.parse.urlparse(r["url"]).netloc.lower()
        is_official = any(d in host for d in trusted)
        is_forum = any(d in r["url"] for d in forums)
        if is_official:
            best = {"r": r, "weight": "official"}
            break  # official always wins
        elif is_forum and not best:
            best = {"r": r, "weight": "forum"}
        elif not best:
            best = {"r": r, "weight": "other"}

    r = best["r"]
    weight = best["weight"]
    text = (r["title"] + " " + r["snippet"]).lower()

    # Heuristic: did the snippet mention the frequency? service? country?
    freq_in_text = f"{freq_mhz:.0f}" in text or f"{freq_mhz:.1f}" in text
    country_in_text = (country or "").lower() in text if country else None
    service_in_text = (service or "").split()[0].lower() in text if service else False

    if weight == "official":
        conf = 0.9 if (freq_in_text and service_in_text) else 0.6
    elif weight == "forum":
        conf = 0.5 if (freq_in_text and service_in_text) else 0.3
    else:
        conf = 0.3 if freq_in_text else 0.15

    return {
        "source": f"websearch:{weight}",
        "matched": True,
        "confidence": conf,
        "evidence": (r["title"] + " — " + r["snippet"])[:300],
        "url": r["url"],
        "stale": False,
        "country_match": country_in_text,
    }

# ----------------- Confidence aggregation -----------------
def aggregate_confidence(source_results: list, weights_cfg: dict) -> dict:
    """
    Combine multiple source results into a single confidence percentage.

    Logic:
      - Start at 0
      - For each source that MATCHED, add its weight × confidence
      - Apply penalties:
          - contradiction: ≥2 matched but at least one mismatches another's verdict
          - no_source_found: zero matches at all
          - single_source_only: only 1 matched
          - country_mismatch: any source has country_match=False
      - Apply bonuses:
          - triangulation_3plus: ≥3 matched
          - official_plus_forum: at least 1 official + 1 forum

    Returns: {"confidence": float (0-1), "confidence_pct": int, "bucket": str, "rationale": [...]}
    """
    weights = weights_cfg["source_weights"]
    penalties = weights_cfg["penalties"]
    bonuses = weights_cfg["bonuses"]
    buckets = weights_cfg["buckets"]

    score = 0.0
    rationale = []
    matched_sources = []
    contradictions = 0
    official_count = 0
    forum_count = 0
    country_mismatches = 0

    for sr in source_results:
        if sr["matched"] is not True:
            continue
        matched_sources.append(sr)
        # Map source label to weight key
        src = sr["source"]
        if src.startswith("hf"):
            w = weights.get("hf_dataset_match", 0.25)
            key = "hf_dataset_match"
        elif src == "wikipedia":
            w = weights.get("wikipedia_match", 0.20)
            key = "wikipedia_match"
        elif "official" in src:
            w = weights.get("official_regulator", 0.35)
            key = "official_regulator"
            official_count += 1
        elif "forum" in src:
            w = weights.get("forum_community", 0.10)
            key = "forum_community"
            forum_count += 1
        else:
            w = weights.get("trusted_standard", 0.20)
            key = "trusted_standard"

        contribution = w * sr["confidence"]
        score += contribution
        rationale.append(f"+{contribution:.2f} ({key}, conf={sr['confidence']:.2f}, evidence={sr['evidence'][:60]})")

        if sr.get("country_match") is False:
            country_mismatches += 1

    # Penalties
    if not matched_sources:
        score += penalties["no_source_found"]
        rationale.append(f"{penalties['no_source_found']:.2f} no_source_found")
    elif len(matched_sources) == 1:
        score += penalties["single_source_only"]
        rationale.append(f"{penalties['single_source_only']:.2f} single_source_only")

    if country_mismatches > 0:
        score += penalties["country_mismatch"]
        rationale.append(f"{penalties['country_mismatch']:.2f} country_mismatch×{country_mismatches}")

    # Contradiction detection: if at least 2 matched but ANY one has low conf (<0.3)
    # while another has high conf (>0.7), call it a contradiction
    if len(matched_sources) >= 2:
        confs = [sr["confidence"] for sr in matched_sources]
        if max(confs) - min(confs) > 0.4:
            score += penalties["source_contradiction"]
            rationale.append(f"{penalties['source_contradiction']:.2f} source_contradiction")

    # Bonuses
    if len(matched_sources) >= 3:
        score += bonuses["triangulation_3plus"]
        rationale.append(f"+{bonuses['triangulation_3plus']:.2f} triangulation_3plus")
    if official_count >= 1 and forum_count >= 1:
        score += bonuses["official_plus_forum"]
        rationale.append(f"+{bonuses['official_plus_forum']:.2f} official_plus_forum")

    score = max(0.0, min(1.0, score))

    # Bucket
    bucket = "no_confidence"
    for b_name, b_thresh in sorted(buckets.items(), key=lambda x: -x[1]):
        if score >= b_thresh:
            bucket = b_name
            break

    return {
        "confidence": round(score, 3),
        "confidence_pct": int(round(score * 100)),
        "bucket": bucket,
        "matched_sources": len(matched_sources),
        "official_sources": official_count,
        "forum_sources": forum_count,
        "rationale": rationale,
    }
