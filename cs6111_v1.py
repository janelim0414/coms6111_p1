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

def fetch_results(query):
    """Fetches top-10 search results for a given query."""
    service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
    res = service.cse().list(q=query, cx=GOOGLE_ENGINE_ID, num=10).execute()
    return res.get("items", [])

def get_relevance_feedback(results):
    """Prompts user for relevance feedback on each search result."""
    relevant_docs = []
    non_relevant_docs = []

    print("\nSearch Results (Top 10):")
    for i, item in enumerate(results):
        print(f"\n[{i+1}] {item['title']}\n{item.get('snippet', '')}")
        feedback = input("Is this relevant? (1 for Yes, 0 for No): ").strip()
        if feedback == "1":
            relevant_docs.append(item)
        else:
            non_relevant_docs.append(item)
    
    return relevant_docs, non_relevant_docs

def extract_keywords(docs):
    """Extracts frequently occurring words from relevant documents."""
    word_counter = Counter()
    for doc in docs:
        text = f"{doc['title']} {doc.get('snippet', '')}"
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())  # Filter out short words
        word_counter.update(words)

    return [word for word, _ in word_counter.most_common(5)]  # Take top-5 frequent words

def refine_query(original_query, keywords):
    """Refines the query by adding new words from relevant documents."""
    original_words = set(original_query.split())
    new_keywords = [word for word in keywords if word not in original_words]
    
    if new_keywords:
        new_query = f"{original_query} {' '.join(new_keywords[:2])}"  # Add top-2 new keywords
        print(f"\nRefining query to: \"{new_query}\"\n")
        return new_query
    return original_query  # No change if no new words found

def main():
    if len(sys.argv) < 3:
        print("Usage: python search.py <precision> \"<query>\"")
        sys.exit(1)

    target_precision = float(sys.argv[1])
    query = " ".join(sys.argv[2:])  # Capture multi-word queries

    while True:
        results = fetch_results(query)
        if not results:
            print("No results found. Exiting.")
            break

        relevant_docs, non_relevant_docs = get_relevance_feedback(results)
        precision = len(relevant_docs) / 10.0

        print(f"\nCurrent Precision@10: {precision:.2f}")

        if precision >= target_precision:
            print("Target precision reached! Stopping.")
            break
        elif not relevant_docs:
            print("No relevant results found. Stopping.")
            break
        
        # Extract keywords and refine query
        keywords = extract_keywords(relevant_docs)
        new_query = refine_query(query, keywords)

        if new_query == query:
            print("No further query refinement possible. Stopping.")
            break
        
        query = new_query  # Update query and repeat


if __name__ == "__main__":
    main()
