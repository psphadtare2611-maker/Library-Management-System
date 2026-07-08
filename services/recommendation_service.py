# ============================================================================
# services/recommendation_service.py
# ----------------------------------------------------------------------------
# RECOMMENDATION SERVICE — content-based "You might also like…" suggestions.
#
# APPROACH (classic ML, no training data or network needed):
#   1. For every book, build a short text document from its metadata
#      (title + author + category). Author and category are repeated so they
#      carry more weight — books by the same author / in the same category are
#      the most intuitive recommendations.
#   2. Turn those documents into numeric vectors with TF-IDF
#      (Term Frequency-Inverse Document Frequency): common words count for
#      little, distinctive words count for a lot.
#   3. Measure how similar two books are with COSINE SIMILARITY — the angle
#      between their vectors (1.0 = identical direction, 0.0 = unrelated).
#   4. Return the top-N most similar books to the one the user picked.
#
# This is "content-based" filtering: it recommends items similar to a given
# item, using only the items' own attributes. It works with very little data
# (unlike collaborative filtering, which needs lots of borrowing history).
#
# The heavy lifting is done by scikit-learn; this class just prepares the data
# and returns the standard {success, message, data} envelope.
# ============================================================================

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from services.service_base import ServiceBase
from services.book_service import BookService
from utils.logger import logger


class RecommendationService(ServiceBase):
    """Suggests books similar to a chosen book (content-based filtering)."""

    def __init__(self, book_service=None):
        # Composition: the recommender HAS-A BookService to fetch the catalog.
        self.book_service = book_service or BookService()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def recommend(self, book_id, top_n=5):
        """
        Recommend up to `top_n` books similar to the book with `book_id`.

        Returns data = list of {"book": Book, "score": float%}  (best first),
        where score is the cosine-similarity match as a percentage.
        """
        try:
            result = self.book_service.get_all_books()
            if not result["success"]:
                return self._response(False, result["message"])

            books = result["data"] or []
            if len(books) < 2:
                return self._response(True, "Not enough books to recommend from.", [])

            # Locate the chosen book within the catalog.
            id_to_index = {b.book_id: i for i, b in enumerate(books)}
            if book_id not in id_to_index:
                return self._response(False, "That book is not in the catalog.")
            target_index = id_to_index[book_id]

            # (1)+(2) Build the TF-IDF matrix from every book's metadata text.
            corpus = [self._book_text(b) for b in books]
            vectorizer = TfidfVectorizer(stop_words="english")
            tfidf_matrix = vectorizer.fit_transform(corpus)

            # (3) Cosine similarity of the chosen book vs. all books.
            similarities = cosine_similarity(
                tfidf_matrix[target_index], tfidf_matrix
            ).flatten()

            # (4) Rank all others by similarity, drop the book itself and any
            #     zero-similarity (nothing in common) results.
            ranked = sorted(
                ((i, score) for i, score in enumerate(similarities) if i != target_index),
                key=lambda pair: pair[1],
                reverse=True,
            )
            recommendations = [
                {"book": books[i], "score": round(float(score) * 100, 1)}
                for i, score in ranked[:top_n]
                if score > 0
            ]

            msg = (f"{len(recommendations)} recommendation(s)."
                   if recommendations else "No similar books found.")
            return self._response(True, msg, recommendations)
        except Exception as error:
            logger.error(f"recommend failed (book_id={book_id}): {error}")
            return self._response(False, "Could not generate recommendations.")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _book_text(book):
        """
        Build the text document for a book. Author and category are repeated
        so TF-IDF weights them more heavily than individual title words.
        """
        parts = [book.title or ""]
        if book.author:
            parts += [book.author, book.author]        # weight author x2
        if book.category:
            parts += [book.category, book.category]     # weight category x2
        return " ".join(parts)
