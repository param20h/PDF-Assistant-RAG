# backend/app/rag/keywords.py
import math
import re
from collections import Counter
from typing import List

_STOPWORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with",
    "is","are","was","were","be","been","being","have","has","had","do","does",
    "did","will","would","could","should","may","might","shall","can","need",
    "that","this","these","those","it","its","from","by","as","into","through",
    "during","before","after","above","below","between","each","than","so",
    "also","not","no","nor","yet","both","either","neither","just","because",
    "if","then","else","when","where","how","all","any","both","few","more",
    "most","other","some","such","up","out","about","per","which","their",
    "our","your","my","his","her","they","we","you","he","she","i","me","us",
    "him","them","what","who","whom","whose","there","here","now","then",
}

def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return [t for t in tokens if t not in _STOPWORDS]

def extract_keywords(chunks: List[str], top_n: int = 10) -> List[str]:
    """
    Lightweight TF-IDF keyword extractor.
    chunks: list of raw text strings (already produced by chunker.py)
    Returns top_n keywords sorted by TF-IDF score.
    """
    if not chunks:
        return []

    # term frequency across the whole document
    all_tokens = []
    doc_token_sets = []
    for chunk in chunks:
        tokens = _tokenize(chunk)
        all_tokens.extend(tokens)
        doc_token_sets.append(set(tokens))

    tf = Counter(all_tokens)
    total = sum(tf.values()) or 1

    n_docs = len(chunks)
    scores: dict[str, float] = {}
    for term, count in tf.items():
        tf_score = count / total
        # document frequency = how many chunks contain this term
        df = sum(1 for s in doc_token_sets if term in s)
        idf = math.log((n_docs + 1) / (df + 1)) + 1
        scores[term] = tf_score * idf

    top = sorted(scores, key=lambda t: scores[t], reverse=True)[:top_n]
    return top
