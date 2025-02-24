#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pprint
import sys
import re
from googleapiclient.discovery import build
from collections import Counter

# Constants
GOOGLE_API_KEY = "AIzaSyD5f6JL4kwoZhmlZWCXrEFgFUxcFgsFn-U"
GOOGLE_ENGINE_ID = "c7b4796a0d02a4d2c"

class CustomSearchEngine:
    def __init__(self, api_key, engine_id, query, precision):
        self.api_key = api_key
        self.engine_id = engine_id
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

    def extract_keywords(self, docs):
        """Extracts frequently occurring words from relevant documents."""
        word_counter = Counter()
        for doc in docs:
            text = f"{doc['title']} {doc.get('snippet', '')}"
            words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())  # Filter out short words
            word_counter.update(words)
        return [word for word, _ in word_counter.most_common(5)]  # Take top-5 frequent words

    def refine_query(self, keywords):
        """Refines the query by adding new words from relevant documents."""
        original_words = set(self.query.split())
        new_keywords = [word for word in keywords if word not in original_words]
        
        if new_keywords:
            new_query = f"{self.query} {' '.join(new_keywords[:2])}"  # Add top-2 new keywords
            print(f"\nRefining query to: \"{new_query}\"\n")
            self.query = new_query
            return True
        return False

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
        keywords = engine.extract_keywords(relevant_docs)
        has_refinement = engine.refine_query(keywords)

        if not has_refinement:
            print("No further query refinement possible. Stopping.")
            break

if __name__ == "__main__":
    main()
