#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
from googleapiclient.discovery import build
from collections import Counter
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer

# -------------------------------
# Constants and Global Variables
# -------------------------------
GOOGLE_API_KEY = "AIzaSyD5f6JL4kwoZhmlZWCXrEFgFUxcFgsFn-U"
GOOGLE_ENGINE_ID = "c7b4796a0d02a4d2c"
STOPWORDS = set(stopwords.words('english'))

# -------------------------------
# Custom Search Engine Class
# -------------------------------
class CustomSearchEngine:
    """
    This class implements a custom search engine that uses Google's Custom Search API.
    It supports relevance feedback using a Rocchio algorithm with TF-IDF weighting for query expansion.
    """

    def __init__(self, api_key, engine_id, query, precision):
        self.api_key = api_key
        self.engine_id = engine_id
        self.original_query = query  # Original query provided by the user
        self.query = query           # Current (possibly expanded) query
        self.precision = precision   # Target precision value

    def fetch_results(self):
        """
        Fetches the top-10 search results for the current query using Google Custom Search API.
        """
        service = build("customsearch", "v1", developerKey=self.api_key)
        res = service.cse().list(q=self.query, cx=self.engine_id, num=10).execute()
        return res.get("items", [])

    def get_relevance_feedback(self, results):
        """
        Prompts the user to provide relevance feedback for each search result.
        Returns two lists: relevant_docs and non_relevant_docs.
        """
        relevant_docs = []
        non_relevant_docs = []

        # Display query parameters and results for user feedback
        max_label_length = max(len("Client key"), len("Engine key"), len("Query"), len("Precision"))
        print("Parameters:")
        print(f"{'Client key'.ljust(max_label_length)} = {self.api_key}")
        print(f"{'Engine key'.ljust(max_label_length)} = {self.engine_id}")
        print(f"{'Query'.ljust(max_label_length)} = {self.query}")
        print(f"{'Precision'.ljust(max_label_length)} = {self.precision}")
        print("Google Search Results:\n========================")

        # Iterate through results and ask user for feedback
        for i, item in enumerate(results):
            print(f"Result {i+1}\n[\nURL: {item['link']}\nTitle: {item['title']}\nSummary: {item.get('snippet', '')}\n]")
            while True:  # Loop until valid input is received
                feedback = input("\nRelevant (Y/N)? ").strip().upper()
                if feedback == "Y":
                    relevant_docs.append(item)
                    break
                elif feedback == "N":
                    non_relevant_docs.append(item)
                    break
                else:
                    print("Invalid input. Please enter 'Y' for Yes or 'N' for No.")
        return relevant_docs, non_relevant_docs

    # -------------------------------
    # Helper Method: TF-IDF Computation
    # -------------------------------
    def _compute_tf_idf_scores(self, docs):
        """
        Given a list of document texts, computes the normalized sum of TF-IDF scores for each term.
        Returns a dictionary mapping term to its average TF-IDF score.
        """
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(docs)
        feature_names = vectorizer.get_feature_names_out()
        # Sum TF-IDF scores over all documents and normalize by number of documents
        scores = tfidf_matrix.sum(axis=0).A1
        return {term: score / len(docs) for term, score in zip(feature_names, scores)}

    def rocchio_algorithm(self, relevant_docs, non_relevant_docs):
        """
        Refines the query using the Rocchio algorithm with TF-IDF weighting.
        Documents are built by concatenating each result's title and snippet.
        """
        # Rocchio coefficients
        alpha, beta, gamma = 1, 0.75, 0.15
        query_terms = self.query.lower().split()
        term_weights = {}

        # -------------------------------
        # Process Relevant Documents
        # -------------------------------
        relevant_texts = []
        for doc in relevant_docs:
            # Concatenate title and snippet for each document
            doc_text = f"{doc.get('title', '')} {doc.get('snippet', '')}"
            relevant_texts.append(doc_text)
        if relevant_texts:
            relevant_scores = self._compute_tf_idf_scores(relevant_texts)
            for term, score in relevant_scores.items():
                # Do not modify weights for original query terms
                if term not in set(self.original_query.lower().split()):
                    term_weights[term] = term_weights.get(term, 0) + beta * score

        # -------------------------------
        # Process Non-Relevant Documents
        # -------------------------------
        non_relevant_texts = []
        for doc in non_relevant_docs:
            doc_text = f"{doc.get('title', '')} {doc.get('snippet', '')}"
            non_relevant_texts.append(doc_text)
        if non_relevant_texts:
            non_relevance_scores = self._compute_tf_idf_scores(non_relevant_texts)
            for term, score in non_relevance_scores.items():
                if term not in set(self.original_query.lower().split()):
                    term_weights[term] = term_weights.get(term, 0) - gamma * score

        # -------------------------------
        # Incorporate Original Query Terms
        # -------------------------------
        for term in query_terms:
            term_weights[term] = term_weights.get(term, 0) + alpha

        # -------------------------------
        # Prepare Keyword List for Query Expansion
        # -------------------------------
        # Sort terms by their computed weight (highest first)
        sorted_terms = sorted(term_weights.items(), key=lambda x: x[1], reverse=True)
        # Filter out stopwords and terms that are already in the original query
        original_query_terms = set(self.original_query.lower().split())
        filtered_words = [
            (word, weight) for word, weight in sorted_terms
            if word not in STOPWORDS and word not in original_query_terms
        ]
        self.keywords = filtered_words

    def refine_query(self):
        """
        Refines the current query by appending up to two new words from the updated keyword list.
        New words are chosen from those not already present in the current query.
        """
        current_new_terms = set(self.query.lower().split()) - set(self.original_query.lower().split())
        # Map current new terms to their weights (if any)
        query_freq_mapping = {word: dict(self.keywords).get(word, 0) for word in current_new_terms}
        new_words = []
        # Choose up to 2 new words from the sorted keyword list
        for word, cnt in self.keywords:
            if len(new_words) == 2:
                break
            if word not in current_new_terms:
                query_freq_mapping[word] = cnt
                new_words.append(word)
        if not new_words:
            return new_words  # No new words found; query remains unchanged

        # Order terms by their weights and update the query by appending them to the original query
        ordered_query_mapping = Counter(query_freq_mapping).most_common()
        self.query = f"{self.original_query} {' '.join([word for word, _ in ordered_query_mapping])}"
        return new_words

# -------------------------------
# Main Execution Function
# -------------------------------
def main():
    """
    Main function for running the search and query expansion process.
    Expects command-line arguments: precision and query string.
    """
    if len(sys.argv) < 3:
        print("Usage: python search.py <precision> \"<query>\"")
        sys.exit(1)

    target_precision = float(sys.argv[1])
    init_query = " ".join(sys.argv[2:])  # Supports multi-word queries
    engine = CustomSearchEngine(GOOGLE_API_KEY, GOOGLE_ENGINE_ID, init_query, precision=target_precision)

    while True:
        results = engine.fetch_results()
        
        if not results:
            print("No results found. Exiting.")
            break
        
        if len(results) < 10:
            print("Fewer than 10 results returned. Terminating.")
            break

        # Get user feedback on search results
        relevant_docs, non_relevant_docs = engine.get_relevance_feedback(results)
        precision = len(relevant_docs) / 10.0
        print("========================")
        print("FEEDBACK SUMMARY")
        print("Query " + init_query)
        print(f"Current Precision@10: {precision:.2f}")

        if precision >= target_precision:
            print("Target precision reached! Stopping.")
            break
        elif not relevant_docs:
            print("No relevant results found. Stopping.")
            break
        elif precision < target_precision:
            print("Still below the desired precision of " + str(target_precision))

        # Apply the Rocchio algorithm with TF-IDF weighting for query expansion
        engine.rocchio_algorithm(relevant_docs, non_relevant_docs)
        new_words = engine.refine_query()

        if not new_words:
            print("No further query refinement possible. Stopping.")
            break
        print(f"Augmenting query by: {' '.join(new_words)}")
        print("------------------------")

if __name__ == "__main__":
    main()
