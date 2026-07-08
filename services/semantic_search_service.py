# ============================================================================
# services/semantic_search_service.py
# ----------------------------------------------------------------------------
# SEMANTIC SEARCH SERVICE — search books by MEANING, not just matching letters.
#
# The problem with plain (lexical) search: searching "wizards and magic" finds
# nothing, because those exact words aren't in any title. Semantic search fixes
# that by comparing MEANING.
#
# HOW IT WORKS:
#   1. A pretrained sentence-embedding model (all-MiniLM-L6-v2) turns any text
#      into a 384-dimensional vector where similar MEANINGS sit close together.
#   2. We embed every book's text (title + author + category + remarks) once
#      and cache the vectors.
#   3. We embed the user's query the same way.
#   4. Cosine similarity (dot product of normalized vectors) ranks the books by
#      how close their meaning is to the query.
#
# No training and no API key — the model is pretrained and runs locally. It is
# loaded once (module-level cache) because loading is the slow part; encoding a
# query afterwards is milliseconds.
# ============================================================================

import numpy as np

from services.service_base import ServiceBase
from services.book_service import BookService
from utils.logger import logger


# The embedding model is expensive to load, so keep ONE shared instance for the
# whole app (loaded lazily on first use).
_MODEL = None


def _get_model():
    """Load (once) and return the shared sentence-embedding model."""
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


class SemanticSearchService(ServiceBase):
    """Meaning-based book search using sentence embeddings."""

    def __init__(self, book_service=None):
        self.book_service = book_service or BookService()
        # Cache so we only re-embed the catalog when it actually changes.
        self._cache_signature = None
        self._cache_books = []
        self._cache_embeddings = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def search(self, query, top_n=8, min_score=0.15):
        """
        Return books whose meaning is closest to `query`.

        top_n     : max results.
        min_score : cosine-similarity floor (0-1); drops weak matches.
        data      : list of {"book": Book, "score": float%} best-first.
        """
        text = (query or "").strip()
        if not text:
            return self._response(True, "Type something to search by meaning…", [])

        try:
            result = self.book_service.get_all_books()
            if not result["success"]:
                return self._response(False, result["message"])
            books = result["data"] or []
            if not books:
                return self._response(True, "No books to search yet.", [])

            model = _get_model()
            self._refresh_cache(model, books)

            # Embed the query and score against the cached catalog vectors.
            # Vectors are normalized, so a dot product IS the cosine similarity.
            query_vec = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
            scores = self._cache_embeddings @ query_vec

            ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
            results = [
                {"book": self._cache_books[i], "score": round(float(s) * 100, 1)}
                for i, s in ranked[:top_n]
                if s >= min_score
            ]
            msg = (f"{len(results)} result(s) by meaning."
                   if results else "No semantically similar books found.")
            return self._response(True, msg, results)
        except Exception as error:
            logger.error(f"semantic search failed (query={text!r}): {error}")
            return self._response(False, "Semantic search failed.")

    # ------------------------------------------------------------------ #
    # Caching
    # ------------------------------------------------------------------ #
    def _refresh_cache(self, model, books):
        """(Re)compute catalog embeddings only when the catalog has changed."""
        signature = tuple((b.book_id, self._book_text(b)) for b in books)
        if signature == self._cache_signature:
            return
        corpus = [text for _bid, text in signature]
        self._cache_embeddings = model.encode(
            corpus, convert_to_numpy=True, normalize_embeddings=True
        )
        self._cache_books = books
        self._cache_signature = signature

    @staticmethod
    def _book_text(book):
        """The text that represents a book for embedding."""
        parts = [book.title or ""]
        if book.author:
            parts.append(book.author)
        if book.category:
            parts.append(book.category)
        if book.remarks:
            parts.append(book.remarks)
        return " — ".join(parts)
