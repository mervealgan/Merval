# Here we plan to put all the steps of the process like in a jupyter notebook
# with each process checking if the input file is here, and that the output is not here to avoid accidental overwrite


# 010 getting random wikipedia page titles from a selection of categories.
# random_wikis.csv

# 020 getting a random sentence from each article and some metadata (url, categories list)
# random_wikipedia_articles.csv

# 030 sanitizing sentences from the previous set
# random_wikipedia_sanitized.csv

# 040 selecting 250 sentences from the previous set
# 250_wikiset.csv

# 050 autodownload latest version of the database poll_results.db
# poll_results.db

# 060 aggregating results (MOS) from the poll database
# aggregated_results.csv

# 070 adding the aggregated results (MOS) to the 250 sentences
# 250_wikiset_mos.csv

# 080 keeping only the data used in model training (sentences, MOS score)
# 500_sentences_mos.csv
