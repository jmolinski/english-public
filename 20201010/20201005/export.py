import json
import os.path
import random
from typing import List, Tuple

import genanki
import gtts
import slugify

from card_styles import BASE_MODEL

DECK_ID = 1201381843


def text_to_speech(text: str, filename: str) -> None:
    if not os.path.exists(filename):
        gtts.gTTS(text=text, lang="en-us", slow=False).save(filename)


def make_random_id() -> int:
    return random.randrange(1 << 30, 1 << 31)


class AnkiNoteGuidOfIdAndKey(genanki.Note):
    @property
    def guid(self) -> int:
        # Use only english word/phrase and type (verb/noun...) for guid
        return genanki.guid_for(self.fields[0], self.fields[7])


def get_sentence_with_colored_term(item: dict) -> str:
    return (
        item["sentence"]
        .replace(item["gap_term"], f'<font color="#ff4c4c">{item["gap_term"]}</font>')
        .replace(
            item["gap_term"].capitalize(),
            f'<font color="#ff4c4c">{item["gap_term"].capitalize()}</font>',
        )
    )


def make_note(item: dict, sentence_fname: str) -> AnkiNoteGuidOfIdAndKey:
    return AnkiNoteGuidOfIdAndKey(
        model=BASE_MODEL,
        fields=[
            item["word"],
            item["translated"],
            item["explanation"],
            item["pronunciation"],
            get_sentence_with_colored_term(item),
            f"[sound:{item['media_fname']}]",
            f"[sound:{sentence_fname}]",
            item["type"],
            item["sentence_gap"],
            item["gap_term"],
            item.get("picture", ""),  # empty
            item.get("synonyms", ""),  # empty
        ],
    )


def export(processed_items: List[dict]) -> None:
    my_deck = genanki.Deck(DECK_ID, "Niepoważny angielski")
    my_deck.add_model(BASE_MODEL)

    media_list = []
    for item in processed_items:
        print(f'Item ({len(media_list) // 2}): "{item["word"]}"')

        sentence_fname = item["media_fname"].replace(".mp3", "_sentence.mp3")
        text_to_speech(item["word"], f"sounds/{item['media_fname']}")
        text_to_speech(item["sentence"], f"sounds/{sentence_fname}")

        note = make_note(item, sentence_fname)

        media_list.append(f"sounds/{item['media_fname']}")
        media_list.append(f"sounds/{sentence_fname}")
        my_deck.add_note(note)

    my_package = genanki.Package(my_deck)
    my_package.media_files = media_list
    my_package.write_to_file("deck.apkg")


def replace_term_with_underscores(sentence: str, term: str) -> str:
    return sentence.replace(term, "_" * len(term))


def make_gapped_sentence(item: dict) -> Tuple[str, str]:
    word = item["key"].strip()
    capitalized_word = word.capitalize()
    sentence = item["sentence"].strip()
    cleaned_sentence = f" {sentence} "
    for token in [".", ",", ";", "?", "!", '"', "'"]:
        cleaned_sentence = cleaned_sentence.replace(token, " ")

    print(f'\nTerm "{word}"')
    print(sentence)

    manual = False

    if word not in cleaned_sentence and capitalized_word not in cleaned_sentence:
        manual = True
    if (
        f" {word} " not in cleaned_sentence
        and f" {capitalized_word} " not in cleaned_sentence
    ):
        manual = True

    if not manual:
        gapped_sentence = replace_term_with_underscores(
            replace_term_with_underscores(sentence, word), capitalized_word
        )
        print(gapped_sentence)

        while True:
            print("\nacceptable>", end=" ")
            txt = input().strip()
            if txt == "y":
                return gapped_sentence, word
            if txt == "n":
                break
            if txt == "q":
                exit()

    while True:
        print("\nmanual-key>", end=" ")
        new_term = input().strip().lower()
        gapped_sentence = replace_term_with_underscores(
            replace_term_with_underscores(sentence, new_term), new_term.capitalize()
        )
        print(gapped_sentence)

        while True:
            print("\nacceptable>", end=" ")
            txt = input().strip()
            if txt == "y":
                return gapped_sentence, new_term
            if txt == "n":
                break
            if txt == "q":
                exit()


def process_item(item: dict, processed_list: List[dict]) -> None:
    media_fname = f'{slugify.slugify(item["key"])}.mp3'

    polish_word, *explanation = item["translation"].replace("]", "").split("[")
    polish_word = polish_word.strip()
    if explanation:
        explanation = explanation[0].strip()
    else:
        explanation = ""

    print("\nProcessed terms", len(processed_list))
    sentence_gap, gap_term = make_gapped_sentence(item)

    data = {
        "word": item["key"],
        "translated": polish_word,
        "explanation": explanation,
        "pronunciation": item["phonetic"],
        "sentence": item["sentence"],
        "media_fname": media_fname,
        "type": item["type"],
        "sentence_gap": sentence_gap,
        "gap_term": gap_term,
        "picture": "",
        "synonyms": "",
    }
    processed_list.append(data)


def process_items() -> None:
    with open("exported.json") as f:
        items = json.loads(f.read())
    with open("processed.json") as f:
        processed = json.loads(f.read())

    for item in items:
        if any(processed_item["word"] == item["key"] for processed_item in processed):
            continue

        process_item(item, processed)

        with open("processed.json", "w") as f:
            f.write("[\n")
            f.write(",\n".join([json.dumps(item) for item in processed]))
            f.write("\n]")


def export_processed():
    with open("processed.json") as f:
        export(json.loads(f.read()))


def refresh_exported_data():
    with open("db.json") as f:
        db = json.loads(f.read())
    with open("exported.json") as f:
        keys = [item["key"] for item in json.loads(f.read())]
    with open("exported.json", "w") as f:
        f.write(json.dumps([r for r in db if r["key"] in keys]))


if __name__ == "__main__":
    refresh_exported_data()
    process_items()
    export_processed()
