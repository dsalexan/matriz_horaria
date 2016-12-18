import json
import os
import sys

from fuzzywuzzy import fuzz

from lib import auxiliar, ementas, functions


def get_order(letter):
    ab = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    new_ab = ab[ab.find(letter):] + ab[:ab.find(letter)]
    order = {key: i for i, key in enumerate(list(new_ab))}

    return order


def set_discipline(subject, LISTA_DISCIPLINAS, AURELIO, minimum_ratio=70, maximum_trying=15):
    matches = []

    i = 0
    cleared_subject = functions.clear_discipline_name(subject['subject'], AURELIO, True)

    # --- COMEÇAR AS COMPARAÇÕES POR ORDEM ALFABETICA, SENDO QUE COMEÇA COM A 1ª LETRA DO SUBJECT
    LISTA_DISCIPLINAS = sorted(LISTA_DISCIPLINAS, key= lambda x: get_order(cleared_subject[0].upper())[
        auxiliar.clear_word(x[0].upper())])

    for d in LISTA_DISCIPLINAS:
        cleared_d = functions.clear_discipline_name(d, AURELIO)

        if cleared_d.find("laboratorio") != -1 and cleared_subject.find('torio circuitos') != -1:
            asdaecas2 = True

        ratio = fuzz.ratio(cleared_d, cleared_subject)
        if ratio > minimum_ratio:  # batem os nomes parcialmente
            # subject['discipline'] = d
            matches.append([ratio, {"name": d, "simple_name": cleared_d}])

        if len(matches) > 0:
            i += 1

        if i == maximum_trying:
            break

    if len(matches) > 0:
        matches.sort(key=lambda x: x[0], reverse=True)
        subject['discipline'] = matches[0][1]['name']

    return subject


DIRECTORY = os.path.dirname(sys.argv[0])
TARGET = DIRECTORY + "/matriz_output.json"
FILE_AURELIO = DIRECTORY + "/aurelio.json"
ORDER_WEEKDAYS = ["seg", "ter", "qua", "qui", "sex"]
ORDER_TIMES = ["8h00-10h00",
                    "10h00-12h00",
                    "13h30-15h30",
                    "15h30-17h30",
                    "19h00-21h00",
                    "21h00-23h00"]
ORDER_CARGO = {"36h": 1, "72h": 2, "108h": 3}


with open(TARGET, encoding="utf-8") as extracao:
    MATRIZ_BRUTA = json.load(extracao)

with open(FILE_AURELIO, encoding="utf-8") as extracao:
    AURELIO = json.load(extracao)

MATRIZ = functions.get_subjects(MATRIZ_BRUTA)
SEMANA = functions.get_weekly(MATRIZ_BRUTA)
# CRIAR UM ANALISADOR DE MATRIZ_HORARIA PARA BUSCAR INCONSISTENCIAS E ERROS NA IMPORTACAO DOS DADOS (certamente causados pela formatacao fonte)

CATALOGO = ementas.get_catalog(DIRECTORY, ementas.get_constants()["CATALOGO_DISCIPLINAS"], ementas.get_constants()["UNIFESP"])
LISTA_DISCIPLINAS = [s for l in CATALOGO for s in CATALOGO[l]['subcats']]
LISTA_DISCIPLINAS.sort()

index = {}
to_check = []

for weekday in ORDER_WEEKDAYS:
    for time in ORDER_TIMES:
        for subject in SEMANA[weekday][time]:
            code = subject["subject"] + "|" + subject["professor"] + "|" + subject["course"]
            if len(MATRIZ[code]['times']) != 2:
                if code.find("Lab de Cir") != -1:
                    ASDASDEcASD = True

                subject = set_discipline(subject, LISTA_DISCIPLINAS, AURELIO)
                disc = 'nao_consta'
                if "discipline" in subject:
                    disc = subject['discipline']
                    to_check.append(disc)

                index[code] = disc

to_check = list(set(to_check))
# todo CRIAR CRITÉRIOS PARA REGENERAÇÃO DAS EMENTAS, considerando data da ultima lista, data atual, itens do to_check e itens na ultima lista armazenada
SYLLABUS = ementas.get_data(to_check, force_regenerate=False)

# done SÓ MOSTRAR DIAS DA SEMANA E HORARIOS COM ERRO
print('')
errors = 0
for weekday in ORDER_WEEKDAYS:
    #print("{}".format(weekday))
    weekday_printed = False
    for time in ORDER_TIMES:
        #print("   {}".format(time))
        time_printed = False
        for subject in SEMANA[weekday][time]:
            code = subject["subject"] + "|" + subject["professor"] + "|" + subject["course"]
            if len(MATRIZ[code]['times']) != 2:
                state = ""
                if not "discipline" in subject:
                    state = "NÃO_CONSTA_NO_CATALOGO"
                else:
                    if len(MATRIZ[code]['times']) != int(ORDER_CARGO[SYLLABUS[subject['discipline']]["Carga Horária"]]):
                        state = "{}|{}".format(subject['discipline'], SYLLABUS[subject['discipline']]["Carga Horária"])

                if state != "":
                    if not weekday_printed: print("{}".format(weekday))
                    if not time_printed: print("   {}".format(time))

                    weekday_printed = True
                    time_printed = True

                    errors += 1
                    print("               {}, {}   [{}]  [{}]".format(subject['subject'], subject['professor'].upper(), len(MATRIZ[code]['times']), state))


print("\n\n")
print("Accounted for {} errors.".format(errors))