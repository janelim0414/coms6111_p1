#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
from googleapiclient.discovery import build
from collections import Counter
from nltk.corpus import stopwords

# Constants
GOOGLE_API_KEY = "AIzaSyD5f6JL4kwoZhmlZWCXrEFgFUxcFgsFn-U"
GOOGLE_ENGINE_ID = "c7b4796a0d02a4d2c"
STOPWORDS = set(stopwords.words('english'))

class CustomSearchEngine:
    def __init__(self, api_key, engine_id, query, precision):
        self.api_key = api_key
        self.engine_id = engine_id
        self.original_query = query
        self.query = query
        self.precision = precision

    def fetch_results(self):
        """Fetches top-10 search results for a given query."""
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        res = service.cse().list(q=self.query, cx=GOOGLE_ENGINE_ID, num=10).execute()
        return res.get("items", [])

    def get_relevance_feedback(self, results):
        """Prompts user for relevance feedback on each search result."""
        relevant_docs = []
        non_relevant_docs = []
        
        max_label_length = max(len("Client key"), len("Engine key"), len("Query"), len("Precision"))
        print(f"Parameters:")
        print(f"{'Client key'.ljust(max_label_length)} = {GOOGLE_API_KEY}")
        print(f"{'Engine key'.ljust(max_label_length)} = {GOOGLE_ENGINE_ID}")
        print(f"{'Query'.ljust(max_label_length)} = {self.query}")
        print(f"{'Precision'.ljust(max_label_length)} = {self.precision}")
        print("Search Results (Top 10):\n========================")

        for i, item in enumerate(results):
            print(f"Result {i+1}\n[\nURL: {item['link']}\nTitle: {item['title']}\nSummary: {item.get('snippet', '')}\n]")
            while True:  # Keep prompting until valid input is received
                feedback = input("Relevant (Y/N)? ").strip().upper()
                if feedback == "Y":
                    relevant_docs.append(item)
                    break
                elif feedback == "N":
                    non_relevant_docs.append(item)
                    break
                else:
                    print("Invalid input. Please enter 'Y' for Yes or 'N' for No.")
        return relevant_docs, non_relevant_docs
    
    def rocchio_algorithm(self, relevant_docs, non_relevant_docs):
        """Refine query using Rocchio's algo"""
        alpha, beta, gamma = 1, 0.75, 0.15  # Rocchio coefs
        query_terms = self.query.lower().split()

        # Calculate term weights for relevant and non-relevant docs
        term_weights = {}
        for doc in relevant_docs:
            for term in re.findall(r'\b[a-zA-Z]+\b', doc.get('title', '').lower()) + re.findall(r'\b[a-zA-Z]+\b', doc.get('snippet', '').lower()):
                if term not in set(self.original_query.lower().split()):
                    term_weights[term] = term_weights.get(term, 0) + beta / len(relevant_docs)

        for doc in non_relevant_docs:
            for term in re.findall(r'\b[a-zA-Z]+\b', doc.get('title', '').lower()) + re.findall(r'\b[a-zA-Z]+\b', doc.get('snippet', '').lower()):
                if term not in set(self.original_query.lower().split()):
                    term_weights[term] = term_weights.get(term, 0) - gamma / len(non_relevant_docs)

        # Add original query terms with alpha weight
        for term in query_terms:
            term_weights[term] = term_weights.get(term, 0) + alpha

        # Sort terms by weight, filter out those already in the query
        sorted_terms = sorted(term_weights.items(), key=lambda x: x[1], reverse=True)
        filtered_words = [(word, weight) for word, weight in sorted_terms if word not in STOPWORDS and word not in set(self.original_query.lower().split())] 
        self.keywords = filtered_words

    def refine_query(self):
        """Refines the query by adding new words from relevant documents."""
        prev_query_without_original = set(self.query.lower().split()) - set(self.original_query.lower().split())
        # Initialize query frequency mapping (initialize with keywords from previous query - original)
        query_freq_mapping = {word: dict(self.keywords).get(word, 0) for word in prev_query_without_original}
        # Add new keywords to query
        new_words = []
        for word, cnt in self.keywords: 
            if len(new_words) == 2:
                break
            if word not in prev_query_without_original:
                query_freq_mapping[word] = cnt
                new_words.append(word)
        if len(new_words) == 0:
            return new_words  # Query not updated
        ordered_query_mapping = Counter(query_freq_mapping).most_common()  # Sort by frequency
        self.query = f"{self.original_query} {' '.join([word for word, _ in ordered_query_mapping])}"  # Append ordered query to original
        return new_words  # Query updated

def main():
    if len(sys.argv) < 3:
        print("Usage: python search.py <precision> \"<query>\"")
        sys.exit(1)

    target_precision = float(sys.argv[1])
    init_query = " ".join(sys.argv[2:])  # Capture multi-word queries
    engine = CustomSearchEngine(GOOGLE_API_KEY, GOOGLE_ENGINE_ID, init_query, precision=target_precision)

    while True:
        results = engine.fetch_results()
        if not results:
            print("No results found. Exiting.")
            break

        relevant_docs, non_relevant_docs = engine.get_relevance_feedback(results)
        precision = len(relevant_docs) / 10.0

        print(f"\nCurrent Precision@10: {precision:.2f}")

        if precision >= target_precision:
            print("Target precision reached! Stopping.")
            break
        elif not relevant_docs:
            print("No relevant results found. Stopping.")
            break
        
        # Extract keywords and refine query
        engine.rocchio_algorithm(relevant_docs, non_relevant_docs)
        new_words = engine.refine_query()

        if not new_words:
            print("No further query refinement possible. Stopping.")
            break
        print(f"Augmenting query by: {' '.join(new_words)}")

if __name__ == "__main__":
    main()
