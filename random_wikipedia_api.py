import os
import wikipediaapi
import random
import re
import pandas as pd

USER_AGENT = 'RandomWikiFetcher/1.0'

# Desired categories
DESIRED_CATEGORIES = [
    "Architecture", "Cinéma", "Design", "Littérature", "Musique", "Photographie", "Sculpture",
    "Arts du spectacle", "Artiste", "Histoire de l'art", "Institution artistique", "Œuvre d'art",
    "Technique artistique", "Alimentation", "Croyance", "Culture", "Divertissement", "Droit", "Éducation", "Idéologie",
    "Langue", "Médias", "Mode", "Organisation", "Groupe social", "Politique", "Santé", "Sexualité", "Sport", "Tourisme",
    "Travail", "Urbanisme", "Astronomie", "Biologie", "Chimie", "Mathématiques", "Physique", "Sciences de la Terre",
    "Anthropologie", "Archéologie", "Économie", "Géographie", "Histoire", "Linguistique", "Information", "Philosophie",
    "Psychologie", "Sociologie", "Aéronautique", "Agriculture", "Astronautique", "Électricité", "Électronique",
    "Énergie", "Industrie", "Ingénierie", "Informatique", "Mécanique", "Médecine", "Métallurgie", "Plasturgie",
    "Robotique", "Télécommunications", "Transports", "Ville", "Continent", "Pays"
]


def get_subcategories(category, language):
    wiki = wikipediaapi.Wikipedia(user_agent=USER_AGENT, language=language)
    cat_page = wiki.page(f"Catégorie:{category}")

    return [member.title.replace("Catégorie:", "") for member
            in cat_page.categorymembers.values() if member.ns == 14]

# TODO mek we should later use this instead : https://en.wikipedia.org/wiki/Special:RandomInCategory
def get_article_titles_from_categories(language, categories, limit=500):
    wiki = wikipediaapi.Wikipedia(user_agent=USER_AGENT, language=language)
    titles = []
    subcategories = []

    for category in categories:
        subcategories.extend(get_subcategories(category, language))

    all_categories = categories + subcategories

    for category in all_categories:
        cat_page = wiki.page(f"Catégorie:{category}")
        titles.extend([member.title for member in cat_page.categorymembers.values() if member.ns == 0])

    random.shuffle(titles)

    return titles[:limit]


def fetch_articles_and_save_to_csv(titles, language, filename):
    wiki = wikipediaapi.Wikipedia(user_agent=USER_AGENT, language=language)

    os.makedirs('data', exist_ok=True)
    filename = os.path.join('data', filename)

    if os.path.exists(filename):
        df_existing = pd.read_csv(filename)
        index_start = df_existing.index.max() + 1
    else:
        index_start = 1

    for i, title in enumerate(titles, start=index_start):
        try:
            page = wiki.page(title)

            article_info = {
                'index': i,
                'title': page.title,
                'random_sentence': get_random_sentence(page.text),
                'url': page.fullurl.replace("https://", ""),
                'categories': ', '.join(page.categories)
            }

            save_article_to_csv(article_info, filename)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


def save_article_to_csv(article, filename):
    df = pd.DataFrame([article])
    df.to_csv(filename, mode='a', index=False, header=not os.path.exists(filename))
    print(f"Article '{article['title']}' saved to {filename}")


def get_random_sentence(text, min_sentence_length=95, max_sentence_length=250):
    sentences = re.split(r'(?<=[.!?]) +|\n', text)
    long_sentences = [sentence.strip() for sentence in
                      sentences if min_sentence_length <= len(sentence.strip()) <= max_sentence_length]
    if long_sentences:
        return random.choice(long_sentences)
    raise Exception("No sentences found")


def sanitize_categories(categories):
    sanitized = [cat.replace("Catégorie:", "") for cat in categories.split(', ')]
    return ', '.join(sanitized)


def process_csv(input_file, output_file):
    df = pd.read_csv(input_file)
    df['categories'] = df['categories'].apply(sanitize_categories)
    df.to_csv(output_file, index=False)


def apply_to_column_csv(input_file, input_col, output_col, lamda_to_apply, output_file):
    df = pd.read_csv(input_file)
    df[output_col] = df[input_col].apply(lamda_to_apply)
    df.to_csv(output_file, index=False)


def filter_main_categories(categories, main_categories):
    category_set = set(categories.split(', '))
    filtered_categories = category_set.intersection(main_categories)
    return ', '.join(filtered_categories)
