"""Parsing of highway names."""
import re

from fuzzywuzzy import fuzz, process

from catatom2osm import config

MATCH_THR = 60


def normalize(text):
    return re.sub(r" *\(.*\)", "", text.lower().strip())


def parse(name):
    """Transform the name of a street from Cadastre conventions to OSM ones."""
    name = name.split(";")[0]  # Remove additional information
    name = re.sub(r"[,]+", ", ", name).strip()  # Avoids comma without trailing space
    result = []
    for (i, word) in enumerate(re.split(r"[ ]+", name.strip())):
        nude_word = re.sub(r"^\(|\)$", "", word)  # Remove enclosing parenthesis
        if i == 0:
            if word in config.excluded_types:
                return ""
            else:
                new_word = config.highway_types.get(word, word.title())
        elif nude_word in config.lowcase_words:  # Articles
            new_word = word.lower()
        elif "'" in word[1:-1]:  # Articles with aphostrope
            left = word.split("'")[0]
            right = word.split("'")[-1]
            if left in ["C", "D", "L", "N", "S"]:
                new_word = left.lower() + "'" + right.title()
            elif right in ["S", "N", "L", "LA", "LS"]:
                new_word = left.title() + "'" + right.lower()
            else:
                new_word = word.title()
        else:
            new_word = word.title()
        new_word = new_word.replace("·L", "·l")  # Letra ele geminada
        new_word = new_word.replace(".L", "·l")  # Letra ele geminada
        result.append(new_word)
    return " ".join(result).strip()


def match(name, choices):
    """
    Fuzzy search best match for string name in iterable choices.

    If the result is not good enough returns the name parsed.

    Args:
        name (str): String to look for
        choices (list): Iterable with choices
    """
    parsed_name = parse(name)
    if fuzz and parsed_name:
        normalized = [normalize(c) for c in choices]
        try:
            matching = process.extractOne(
                normalize(parsed_name), normalized, scorer=fuzz.token_sort_ratio
            )
            if matching and matching[1] > MATCH_THR:
                return choices[normalized.index(matching[0])]
        except RuntimeError:
            pass
    return parsed_name


def dsmatch(name, dataset, fn):
    """
    Fuzzy search best matching object for string name in dataset.

    Args:
        name (str): String to look for
        dataset (list): List of objects to search for
        fn (function): Function to obtain a string from a element of the dataset

    Returns:
        First element with the maximun fuzzy ratio.
    """
    max_ratio = 0
    matching = None
    for e in dataset:
        if fuzz and name:
            ratio = fuzz.token_sort_ratio(normalize(name), normalize(fn(e)))
            if ratio > max_ratio:
                max_ratio = ratio
                matching = e
        elif normalize(name) == normalize(fn(e)):
            matching = e
            break
    return matching
