from random_wikipedia_api import *

titles = get_article_titles_from_categories(language='fr', categories=DESIRED_CATEGORIES, limit=500)
fetch_articles_and_save_to_csv(titles, language='fr', filename='random_wikipedia_articles.csv')

# process_csv('data/random_wikipedia_articles.csv', 'data/random_wikipedia_sanitized.csv')
# same as :
apply_to_column_csv(
    'data/random_wikipedia_articles.csv',
    'categories',
    'categories',
    sanitize_categories,
    'data/random_wikipedia_sanitized.csv')

# apply_to_column_csv(
#     '400_with_methods.csv',
#     'categories',
#     'categories',
#     lambda x: filter_main_categories(x, set(DESIRED_CATEGORIES)),
#     '250_rand_wiki_main_categories.csv')
