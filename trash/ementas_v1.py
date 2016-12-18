import json
import os
import shutil
import sys
import tempfile

import requests
from bs4 import BeautifulSoup as soup

from lib import auxiliar, pdf


def fetch_catalog(CATALOGO_DISCIPLINAS, UNIFESP):  # vai no site e sincroniza
    browser = requests.session()
    res = browser.get(CATALOGO_DISCIPLINAS)

    """ RECUPERA OS LINKS PARA PARA LETRA """
    categories = {}
    beau = soup(res.text, 'lxml')
    for cat in beau.select(".pd-subcategory"):
        cat_link = cat.select_one("a")
        cat_count= cat.select_one("small")
        # print('{}  [{}]'.format(cat_link.text, cat_link.get('href')))
        categories[cat_link.text] = {"count": int(cat_count.text.replace("(", "").replace(")", "")), "link": cat_link.get('href'), "subcats": {}}

    """ RECUPERA AS MATERIAS INDIVIDUAIS """
    i = 1
    for cat_letter in categories:
        print_log("   retrieving {} ({}), {} to go...".format(cat_letter, categories[cat_letter]['count'], len(categories) - i))
        i += 1

        if categories[cat_letter]['count'] == 0: continue

        res = browser.get(UNIFESP + categories[cat_letter]["link"])
        beau = soup(res.text, 'lxml')
        for cat_name in beau.select(".pd-category > .pd-filebox .pd-filename .pd-float a"):
            # print('{}  ({})'.format(cat_name.text, cat_name.get('href')))
            categories[cat_letter]['subcats'][cat_name.text] = cat_name.get('href')

    return categories


def get_catalog(DIRECTORY, CATALOGO_DISCIPLINAS, UNIFESP, override=False):  # recupera abstrativamente
    if not override and os.path.isfile(DIRECTORY + "/catalogo_de_disciplinas.json"):
        with open(DIRECTORY + "/catalogo_de_disciplinas.json", encoding="utf-8") as catalog:
            categories = json.load(catalog)
    else:
        categories = fetch_catalog(CATALOGO_DISCIPLINAS, UNIFESP)
        save_to_json(categories, DIRECTORY + "/catalogo_de_disciplinas.json", False)

    return categories


def save_to_json(DATA, TARGET, override, pretty=False):
    if not os.path.isfile(TARGET) or override:
        with open(TARGET, "wb") as trg:
            if pretty:
                compressed = (json.dumps(DATA, ensure_ascii=False, sort_keys=False, indent=3, separators=(',', ': ')))
            else:
                compressed = (json.dumps(DATA, ensure_ascii=False, sort_keys=False, indent=None, separators=None))

            trg.write(compressed.encode("utf-8"))

        return True

    return False


def download_disciplines(categories, SUBJECTS, SYLLABUS, UNIFESP):
    """ CRIA A PASTA PARA ORGANIZAR AS EMENTAS """
    if not os.path.exists(SYLLABUS):
        os.mkdir(SYLLABUS)

    disciplines = {}
    browser = requests.session()
    """ PARA CADA SUBJECT REQUISITADO, BAIXA A EMENTA """
    i = 1
    for subject in SUBJECTS:
        cat_letter = subject[0].upper()

        print_log("   retrieving .pdf for  [{}],  {} to go...".format(subject, len(SUBJECTS) - i))
        i += 1
        res = browser.get(UNIFESP + categories[cat_letter]['subcats'][subject])
        beau = soup(res.text, 'lxml')

        form = beau.select_one('form#phocadownloadform')
        form_data = {}
        # print("action: " + form.get("action"))
        for form_input in form.select('input[type="hidden"]'):
            # print(form_input.get("name") + ": " + form_input.get("value"))
            form_data[form_input.get("name")] = form_input.get("value")

        req = browser.post(form.get('action'), data=form_data) # bytes from pdf
        with open(SYLLABUS + subject + ".pdf", "wb") as file:
            file.write(req.content)

        disciplines[subject] = SYLLABUS + subject + ".pdf"

    return disciplines


def convert_discipline_data(disciplines, MODEL_DATA):
    materias = {}
    """ CONVERTER OS pdf'S EM DADOS JSON """
    i = 1
    for subject, file in disciplines.items():
        subject_data = MODEL_DATA.copy()

        print_log("   converting syllabus for  [{}], {} to go...".format(subject, len(disciplines) - i))
        i += 1
        ementa = pdf.read(file)
        ementa = [auxiliar.clear_word(l.lower(), ':') for l in ementa]

        dados_e_talz = {}
        for data, spec in subject_data.items():
            for line in ementa:
                if line.find(spec['pattern']) == -1: continue

                info = line.replace(spec['pattern'], '').strip()
                dados_e_talz[data] = info

        materias[subject] = dados_e_talz

    return materias


def print_log(log, command=True):
    if command:
        print(log)


def acquire_data(SUBJECTS, MODEL_DATA, DIRECTORY, CATALOGO_DISCIPLINAS, UNIFESP, override=False):
    LOG_STATE = True

    """ RECUPERAR O CATALOGO """
    print_log("Retrieving catalog...", LOG_STATE)

    categories = get_catalog(DIRECTORY, CATALOGO_DISCIPLINAS, UNIFESP, override)

    """ BAIXAS AS EMENTAS DAS DISCIPLINAS """
    print_log("Downloading discipline's syllabus...", LOG_STATE)

    EMENTAS = tempfile.mkdtemp("ementas") + "\\"
    disciplines = download_disciplines(categories, SUBJECTS, EMENTAS, UNIFESP)

    """ CONVERT PARA JSON """
    print_log("Converting data to json...", LOG_STATE)

    final_data = convert_discipline_data(disciplines, MODEL_DATA)
    save_to_json(final_data, DIRECTORY + "/dados_disciplinas.json", True)
    if os.path.exists(EMENTAS):
        shutil.rmtree(EMENTAS)

    print_log("Discipline's data acquired.", LOG_STATE)

    return final_data


def get_constants():
    UNIFESP = "https://www.unifesp.br"
    CATALOGO_DISCIPLINAS = "https://www.unifesp.br/campus/sjc/catalogo-de-disciplinas.html"

    return {"UNIFESP": UNIFESP,
            "CATALOGO_DISCIPLINAS": CATALOGO_DISCIPLINAS}


def get_data(SUBJECTS, override=False, regenerate=False):
    DIRECTORY = os.path.dirname(sys.argv[0])

    UNIFESP = get_constants()["UNIFESP"]
    CATALOGO_DISCIPLINAS = get_constants()["CATALOGO_DISCIPLINAS"]

    # SUBJECTS = ['Redes de Computadores']

    MODEL_DATA = {"Carga Horária": {"pattern": "carga horaria total:"},
                  "Pré-requisitos": {"pattern": "prerequisitos:"}}

    if regenerate or not os.path.isfile(DIRECTORY + "/dados_disciplinas.json"):
        return acquire_data(SUBJECTS, MODEL_DATA, DIRECTORY, CATALOGO_DISCIPLINAS, UNIFESP, override)
    else:
        with open(DIRECTORY + "/dados_disciplinas.json", encoding="utf-8") as extracao:
            DADOS = json.load(extracao)
        return DADOS