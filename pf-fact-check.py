import requests
from bs4 import BeautifulSoup
import json
import argparse
import re
import os

def get_article_text(url):
    """
    Fetches statements from the article text within double quotes.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        article_text = ' '.join(p.text for p in soup.find_all('p'))
        statements = re.findall(r'"([^"]*)"', article_text)
        return statements
    except requests.RequestException as e:
        print(f"Error fetching article: {e}")
        return None

def identify_speakers(article_text):
    """
    Extracts speaker names from the article text using regular expressions to find capitalized words.
    """
    matches = re.findall(r'\b[A-Z][a-z]*\s[A-Z][a-z]*\b', ' '.join(article_text))
    speakers = list(set(matches))
    return speakers

def scrape_politifact_for_speaker(speaker_name):
    """
    Scrapes Politifact for statements made by the given speaker across multiple pages.
    """
    statements = []
    page = 1
    try:
        while True:
            search_url = f"https://www.politifact.com/factchecks/list/?page={page}&speaker={speaker_name}"
            response = requests.get(search_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            results = soup.find_all('li', class_='o-listicle__item')
            if not results:
                break
            for result in results:
                title = result.find('a', class_='m-statement__quote').text.strip()
                rating = result.find('div', class_='m-statement__meter').find('picture').find('img')['alt'].strip()
                statements.append({'title': title, 'rating': rating})
            page += 1
    except requests.RequestException as e:
        print(f"Error scraping Politifact for speaker {speaker_name}: {e}")
        return statements
    return statements

def calculate_speaker_score(statements):
    """
    Calculates a score for the speaker based on the truthfulness of their statements.
    """
    rating_values = {"True": 1, "Mostly True": 0.8, "Half True": 0.5, "Mostly False": 0.2, "False": 0, "Pants on Fire!": -1}
    scores = [rating_values.get(statement['rating'], 0) for statement in statements]
    return sum(scores) / len(scores) if scores else 0

def analyze_speakers_in_article(url):
    """
    Analyzes speakers mentioned in the article by scraping Politifact for their statements and calculating scores.
    """
    article_text = get_article_text(url)
    if article_text is None:
        return {}
    speakers = identify_speakers(' '.join(article_text))
    speaker_scores = {}
    for speaker in speakers:
        statements = scrape_politifact_for_speaker(speaker)
        score = calculate_speaker_score(statements)
        speaker_scores[speaker] = score
    return speaker_scores

def main():
    parser = argparse.ArgumentParser(description='Analyze speakers in a news article against Politifact.')
    parser.add_argument('-u', '--url', type=str, help='URL of the article to analyze', required=True)
    parser.add_argument('-o', '--output', type=str, help='Output directory for the speaker scores file', default='.')
    args = parser.parse_args()
    
    speaker_scores = analyze_speakers_in_article(args.url)
    file_path = os.path.join(args.output, 'speaker_scores.json')
    os.makedirs(args.output, exist_ok=True)
    
    with open(file_path, 'w') as file:
        json.dump(speaker_scores, file, indent=4)
    
    print(f"Speaker scores saved to {file_path}")

if __name__ == "__main__":
    main()
