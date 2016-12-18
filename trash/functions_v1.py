import json
import os
from time import strftime

from fuzzywuzzy import fuzz

from lib import auxiliar

""" AUXILIARES """

def clear_discipline_name(name, AURELIO, partial=False):
    cleared_name = auxiliar.clear_word(name.lower(), palavras_negadas=AURELIO['remocoes'])
    if any(cleared_name.find(a) != -1 for a in AURELIO['parciais']) and partial:
        cleared_name = auxiliar.replace_words(cleared_name, AURELIO['parciais'])

    return cleared_name

def count_matching_times(subject_code, RAW_GRID):
    i = 0
    subject = RAW_GRID[subject_code]
    used_entries = []
    matches = {}
    for code in RAW_GRID:
        # se algum horario entre o code e subject bater
        if RAW_GRID[code]['entry'] != subject['entry'] and  any(any(t['weekday']==st['weekday'] and t['time']==st['time'] for st in subject['times']) for t in RAW_GRID[code]['times']):
            if RAW_GRID[code]['entry'] not in used_entries:
                i += 1
                used_entries.append(RAW_GRID[code]['entry'])
                matches[RAW_GRID[code]['entry']] = []

            matches[RAW_GRID[code]['entry']].append(code)


    return i, matches

def get_subjects_by_time(weekday, time, entry, RAW_GRID):
    subjects = []
    RAW_ENTRY_GRID = {c: s for c, s in RAW_GRID.items() if s['entry'] == entry}
    for code in RAW_ENTRY_GRID:
        if any(t['weekday'] == weekday and t['time'] == time for t in RAW_GRID[code]['times']):
            subjects.append(RAW_GRID[code])

    return subjects

def compare_grids(g1, g2):
    tmp_g1 = g1.copy()
    del tmp_g1['data']

    tmp_g2 = g2.copy()
    del tmp_g2['data']

    return tmp_g1==tmp_g2

def check_professor_redundance(g1, g2, RAW_GRID):
    redundances = []
    diferences = []

    for weekday, times in g1.items():
        if weekday != 'data':
            for time, subjects in times.items():
                if len(subjects) == len(g2[weekday][time]) and len(subjects) > 0:
                    # captura os codigos pra cada horario da semana
                    slot_code = subjects[0]
                    g1_code = slot_code[:slot_code.rfind("(") - 1 - len(slot_code)]

                    slot_code = g2[weekday][time][0]
                    g2_code = slot_code[:slot_code.rfind("(") - 1 - len(slot_code)]

                    if g1_code != g2_code:  # se as aulas sao diferentes
                        # compara pra verificar o que da match
                        if RAW_GRID[g1_code]['entry'] == RAW_GRID[g2_code]['entry'] and RAW_GRID[g1_code]['times'] == RAW_GRID[g2_code]['times'] and RAW_GRID[g1_code]['professor'] != RAW_GRID[g2_code]['professor']:  # professores diferentes
                            solution = "{}/{}|{}/{}|{}".format(RAW_GRID[g1_code]['subject'], RAW_GRID[g2_code]['subject'], RAW_GRID[g1_code]['professor'], RAW_GRID[g2_code]['professor'], RAW_GRID[g1_code]['course'])
                            redundances.append({"weekday": weekday, "time": time, "solution": solution})
                        else:
                            diferences.append({"weekday": weekday, "time": time, "a": g1_code, "b": g2_code})

    return redundances, diferences




""" RAW DATA """


def get_subjects(MATRIZ):
    MATERIAS = {}

    for c in MATRIZ:
        for wk in c['week']:  # iterate trough keys in dict
            for s in c['week'][wk]:  # iterate trough subjects in weekday
                if s is not None:
                    if s["professor"] is None:
                        s["professor"] = "nao_apresentado"

                    code = s["subject"] + "|" + s["professor"] + "|" + c["course"]
                    if code not in MATERIAS.keys():
                        data = {
                            "subject": s["subject"],
                            "professor": s["professor"],
                            "times": [],  # {"weekday": wk, "time": c['time']}
                            "course": c['course'],
                            "term": c['term']
                        }
                        MATERIAS[code] = data

                    MATERIAS[code]['times'].append({"weekday": wk, "time": c['time']})

    return MATERIAS

def get_weekly(MATRIZ):
    SEMANA = {"seg": {},
              "ter": {},
              "qua": {},
              "qui": {},
              "sex": {}}

    for c in MATRIZ:
        for wk in c['week']:  # iterate trough keys in dict
            for s in c['week'][wk]:  # iterate trough subjects in weekday
                if s is not None:
                    if s["professor"] is None:
                        s["professor"] = "nao_apresentado"

                    if not c['time'] in SEMANA[wk].keys():
                        SEMANA[wk][c['time']] = []

                    SEMANA[wk][c['time']].append({"subject": s['subject'], "professor": s['professor'], "course": c['course']})

    return SEMANA

def get_weekly_model(WEEKLY_MODEL_FILE):
    with open(WEEKLY_MODEL_FILE, encoding="utf-8") as m_semanal:
        MODELO_SEMANAL = json.load(m_semanal)

    return MODELO_SEMANAL

# todo Criar um mecanismo pra avisar quando alguma comparacao fuzz chegar muito perto do limite (89%)
def get_input_related(INPUT, MATERIAS, AURELIO):
    ENTRY_SUBJECTS = [e[0] for e in INPUT['classes']]
    RAW_GRID = {k: s for (k, s) in MATERIAS.items() if any(fuzz.ratio(clear_discipline_name(s['subject'], AURELIO, partial=True), clear_discipline_name(es, AURELIO, partial=True)) > 89 for es in ENTRY_SUBJECTS)}

    """ PEGA OS DADOS DE- ENTRADA E MESCLA COM A MATRIZ """
    for code in RAW_GRID:
        entry_object = [e for e in INPUT['classes'] if fuzz.ratio(clear_discipline_name(RAW_GRID[code]['subject'], AURELIO, partial=True), clear_discipline_name(e[0], AURELIO, partial=True)) > 89][0]

        RAW_GRID[code]['entry'] = entry_object[0]
        RAW_GRID[code]['prio'] = entry_object[2]
        RAW_GRID[code]['uncertain'] = 0  # valor padrao, só muda se especificado na entrada

        RAW_GRID[code]['input'] = entry_object[1]

        RAW_GRID[code]['immortal'] = False
    return RAW_GRID

def analise_matching_times(RAW_GRID):  # precisa das prioridades-base ja definidas
    exclusion = {}
    fermions = []
    produtos = []

    fermions_map = {}
    SORTED_RAW_CODES = [c for c in RAW_GRID]
    SORTED_RAW_CODES.sort()
    for code in SORTED_RAW_CODES:
        if code.find("gitais I") != -1:
            asdawdqwe2dq = True

        fermions_map[code] = {}

        RAW_GRID[code]['fermion'], matching_entries = count_matching_times(code, RAW_GRID)
        fermions_map[code]['fermion'] = RAW_GRID[code]['fermion']
        fermions.append(RAW_GRID[code]['fermion'])

        fermions_map[code]['entries'] = {e: {c: RAW_GRID[c]['prio'] for c in s} for e, s in matching_entries.items()}
        if len(matching_entries) > 0:
            fermions_map[code]['produto'] = sum([max([RAW_GRID[c]['prio'] for c in s]) - RAW_GRID[code]['prio'] for e, s in matching_entries.items()])

            produtos.append(fermions_map[code]['produto'])
            RAW_GRID[code]['produto'] = fermions_map[code]['produto']

        # fermion = nº de aulas com horarios simultaneas
        # produto = o quao importante sao as aulas que tal materia fica no lugar

    for code in {c: s for c, s in RAW_GRID.items() if 'produto' not in s}:  # aqueles com fermion 0, nao tem simultaneidades, ganham o produto mínimo - 1
        RAW_GRID[code]['produto'] = min(produtos) - 1
        fermions_map[code]['produto'] = RAW_GRID[code]['produto']
    produtos.append(min(produtos) - 1)


    exclusion['fermion'] = {'maximum': max(fermions), 'minimum': min(fermions)}
    exclusion['produto'] = {'maximum': max(produtos), 'minimum': min(produtos)}
    exclusion['map'] = fermions_map

    return RAW_GRID, exclusion

def get_prioritary_grid(INPUT, MATERIAS, CONFIG, AURELIO):
    RAW_GRID = get_input_related(INPUT, MATERIAS, AURELIO)

    """ PEGA OS DADOS DE- ENTRADA E MESCLA COM A MATRIZ """
    SORTED_RAW_CODES = [c for c in RAW_GRID]
    SORTED_RAW_CODES.sort()
    for code in SORTED_RAW_CODES:
        parameters_register = []

        # PRIORIDADES GERAIS
        # schedule
        RAW_GRID[code]['prio'] += INPUT['general']['priorities']['schedule'][CONFIG['schedule'][RAW_GRID[code]['times'][0]['time']]]
        # term
        for t in RAW_GRID[code]["term"]:
            if t in INPUT['general']['priorities']['term']:
                RAW_GRID[code]['prio'] += INPUT['general']['priorities']['term'][t]
        # time
        for t in RAW_GRID[code]["times"]:
            if t['time'] in INPUT['general']['priorities']['time']:
                RAW_GRID[code]['prio'] += INPUT['general']['priorities']['time'][t['time']]

        # PRIORIDADES INDIVIDUAIS
        prio_score = 0
        for k, p in RAW_GRID[code]['input'].items():
            # p[0] = valor do parametro
            # p[1] = IGUALDADE = 1, DESIGUALDADE = -1
                # serve pra especificar se a prioridade é um match ou um not-match
            # p[2] = OPCIONAL, é o parametro de multiplicação do valor prioritario
            m = 1
            if len(p) == 3:
                m = p[2]

            if k == "schedule": # se o schedule bater com o prioritario, soma +1, senao, soma -1
                if CONFIG['schedule'][RAW_GRID[code]['times'][0]['time']] == p[0]:
                    prio_score += 1 * p[1] * m
                else:
                    prio_score += -1 * p[1] * m
            elif k == "professor": # se o professor bater com o prioritário, soma +1, senao, soma -1
                if RAW_GRID[code]['professor'] == p[0]:
                    prio_score += 1 * p[1] * m
                else:
                    prio_score += -1 * p[1] * m

            if prio_score > 0: # se cumpre as condições para a prioridade individual da vez
                parameters_register.append(k) # registar como prioridade cumprida para esse subject

        if "schrodinger" in RAW_GRID[code]['input']: # se for aplicavel ao processo de incerteza
            """ apesar do IF-ELSE poder ser refinado, caso o dicionario nao especifique parametros vai
                rodar um erro de size_of_array, entao vou fazer assim pra evitar um TRY-CATCH """

            apply = False
            if len(RAW_GRID[code]['input']["schrodinger"]) > 1: # se houver especificações de parametros prioritarios a serem cumpridos
                if all(ep in parameters_register for ep in RAW_GRID[code]['input']["schrodinger"][1:]): # se tais parametros forem cumpridos
                    apply = True
            else: # all and any subject correspondente à entrada for aplicavel
                    apply = True

            if apply: RAW_GRID[code]['uncertain'] = RAW_GRID[code]['input']["schrodinger"][0]

        RAW_GRID[code]['prio'] += prio_score

    # done Aplicar o principio da exclusao de Pauli para diferenciar materias de mesma prioridade
    """ o principio da exclusao precisa das prioridades-base de todos as aulas, entao deve ser um segundo loop """
    RAW_GRID, exclusion = analise_matching_times(RAW_GRID)

    for code in SORTED_RAW_CODES:
        if code.find("nuo IA") != -1:
            asdawerfe3vfa = True
        # pauli's exclusion principle | |fermion - max| * CTE_MAXIMA_PRIORITARIA / max
        prio_bruta_fermion = abs(RAW_GRID[code]['fermion'] - exclusion['fermion']['maximum']) * 0.5/ (exclusion['fermion']['maximum'] -  exclusion['fermion']['minimum'])
        prio_produto_fermion = abs(RAW_GRID[code]['produto'] - exclusion['produto']['maximum']) * 0.5/ (exclusion['produto']['maximum'] - exclusion['produto']['minimum'])
        RAW_GRID[code]['pauli_score'] = (prio_bruta_fermion + prio_produto_fermion)  # da a % de chance de ter espaço livre pra ele
        RAW_GRID[code]['prio'] += (prio_bruta_fermion + prio_produto_fermion) / 2

    PRIO_LIST = [(i[0], i[1]['prio']) for i in RAW_GRID.items()]
    PRIO_LIST.sort(key=lambda x: x[0])
    PRIO_LIST.sort(key=lambda x: x[1], reverse=True)
    prio_map = {c: {'prio': s['prio'], 'fermion': s['fermion'], 'produto': s['produto'], 'pauli': s['pauli_score']} for c, s in RAW_GRID.items()}

    return PRIO_LIST, RAW_GRID


""" GRID FUNCTIONS """


def append_grid(GRID, subject, code):
    for time in subject['times']:  # para cada horario descrito no registro da aula, ocupar o horario
        GRID[time['weekday']][time['time']].append(code + " (" + str(subject['prio']) + ")")

    GRID['data']['count'] += 1

    return GRID


def decide_grid(code, subject, used_subjects, GRID, DECISION_BASE, RAW_GRID):
    """
   -1 - AULA REPETIDA, IGNORAR
    0 - NAO INSERIR
    1 - INSERIR
    2 - SOBRE-INSERIR (ignorar o q tem no lugar)
    3 - NAO INSERIR, APLICAR PROCESSO DE INCERTEZA
    4 - SOBRE-INSERIR, mas o removido deve ser RE-INSERIDO imediatamente
    """
    ORDER_TIMES = {"8h00-10h00": 0,
                    "10h00-12h00": 1,
                    "13h30-15h30": 2,
                    "15h30-17h30": 3,
                    "19h00-21h00": 4,
                    "21h00-23h00": 5}
    ORDER_WEEKDAYS = {"seg": 0, "ter": 1, "qua": 2, "qui": 3, "sex": 4}

    freepass = False
    extra = ""
    repeated = subject["entry"] in used_subjects

    if repeated:
        return -1, [extra]  # NAO INSERIR

    sorted_times = [(t['weekday'], t['time']) for t in subject['times']]
    sorted_times.sort(key=lambda x: ORDER_TIMES[x[1]])
    sorted_times.sort(key=lambda x: ORDER_WEEKDAYS[x[0]])

    # todo Fazer as comparacoes nos dois horarios, nao só no primeiro
    for w, t in sorted_times:
        time = {'weekday': w, 'time': t}
        if len(GRID[time['weekday']][time['time']]) >= 1: # slot is not freeq
            slot_code = GRID[time['weekday']][time['time']][0]
            slot_code_pure = slot_code[:slot_code.rfind("(") - 1 - len(slot_code)]
            slot_subject = RAW_GRID[slot_code_pure]

            subject_related = [(i[0], i[1]['prio']) for i in RAW_GRID.items() if i[0] != code and i[1]['entry'] == subject['entry'] and i[1]['prio'] <= subject['prio']]
            subject_related.sort(key=lambda x: x[0])
            subject_related.sort(key=lambda x: x[1], reverse=True)

            slot_related = [(i[0], i[1]['prio']) for i in RAW_GRID.items() if i[0] != slot_code_pure and i[1]['entry'] == slot_subject['entry'] and i[1]['prio'] <= slot_subject['prio']]
            slot_related.sort(key=lambda x: x[0])
            slot_related.sort(key=lambda x: x[1], reverse=True)


            if slot_code_pure.find("nuo IB") != -1:
                asd322vc2r = True

            if not slot_subject['immortal']:  # if subject in slot is not an immortal object
                if code in DECISION_BASE:  # exists decisions for this subject
                    if slot_code_pure in DECISION_BASE[code]:  # check if bank has priority for CODE
                        if slot_subject['uncertain']: # if SLOT is uncertain
                            return 4, [slot_code_pure]  # SOBRE-INSERIR, com persistência do SLOT
                        return 4, [slot_code_pure]  # SOBRE INSERIR (no momento tudo persiste, mas nao to afim de alterar a estrutura do codigo)

                # ---- Aplicar PERFECTION THROUGH VARIANCE
                if len(slot_related):  # se o cara do slot tem outros horarios
                    if max([RAW_GRID[c]['pauli_score'] for c, p in slot_related]) >= 0.7:  # se o slot tem um related com 0.8 de na escala de exclusao
                        if len(subject_related):
                            if max([RAW_GRID[c]['pauli_score'] for c, p in subject_related]) < 0.7:  # se o cara q quer ser inserido nao tem um related com 0.8
                                freepass = True
                        elif subject['pauli_score'] > 0.0:
                            freepass = True

                # --- Se o subject for incerteza 2, ele pode nao ser inserido. Para tanto, checar:
                # 1 - se sua prioridade é maior que a do subject ocupando o espaço no momento
                # 2 - se empatarem, se a prioridade dos seus related for menor que a prioridade dos related do cara no espaço
                if subject["uncertain"] or freepass:  # if subject is uncertain OR tie-breaker
                    if subject['uncertain'] > 1:
                        if subject['prio'] < slot_subject['prio']: # A.prio < B.prio
                            return 0,[slot_code, subject['uncertain'] > 1]
                        elif subject['prio'] == slot_subject['prio']: # A.prio == B.prio
                            if max([r[1]['prio'] for r in subject_related]) >= max([r[1]['prio'] for r in slot_related]): # max(A.related.prio) > max(B.related.prio)
                                return 0, [slot_code, subject['uncertain'] > 1]


                    new_decision_base = DECISION_BASE.copy()

                    append_decision = True
                    if code in new_decision_base:
                        if slot_code_pure in new_decision_base[code]:
                            append_decision = False
                    else:
                        new_decision_base[code] = []

                    if append_decision:
                        new_decision_base[code].append(slot_code_pure)

                    # trava de segurança para nao gerar varios bangs iguais
                    if new_decision_base != DECISION_BASE:
                        return 3, [slot_code, new_decision_base, code]  # GERAR OUTRA GRADE

            #   NAO INSERIR, [codigo_obstaculo, eh_level2_incerto]
            return 0, [slot_code, subject['uncertain'] > 1]  # if there is no decisions for this code and slot_code, NAO INSERIR

    return 1, [extra]  # INSERIR

def remove_grid(GRID, used_subjects, slot_code):
    to_remove = []

    for key, day in GRID.items():
        if key == "data": continue

        for time, subject in day.items():
            if len(subject) > 0:
                if subject[0].find(slot_code) != -1:
                    to_remove.append({"weekday": key, "time": time})

    for i in to_remove:
        GRID[i['weekday']][i['time']].clear()

    GRID['data']['count'] += -1

    used_subjects = [us for us in used_subjects if slot_code.find(us) == -1]

    return GRID, used_subjects

# todo Adicionar funcao de ficar aula (immortal object do inicio)
# todo Adicionar máximo de aulas
# todo Adicionar invalidador de aulas, descartando desde o inicio o que cair nessa malha (dados da malha fina informados no input)
def insert_grid(code, subject, used_subjects, GRID, DECISION_BASE, RAW_GRID, PERSISTENT_REPEATED_GRID, label=""):
    ext = {}

    if code.find("ormais e ") != -1:
        asd3fvcf32r2 = True

    decision, extras = decide_grid(code, subject, used_subjects, GRID, DECISION_BASE, RAW_GRID)
    command = "keep_inserting"

    if decision == 1 or decision == 2 or decision == 4:  # INSERIR | SOBRE INSERIR | SOBRE-INSERIR persistente // extras = [slot_code_pure]
        GRID['data']['logs']['append']['count'] += 1

        if decision == 2 or decision == 4:
            GRID, used_subjects = remove_grid(GRID, used_subjects, extras[0])

            # como houve uma remocao, aumentar o contator retroativo de repeticoes
            PERSISTENT_REPEATED_GRID['repetitions'] += 1

            # registro de logs
            j = GRID['data']['logs']['decision']['count']
            i = GRID['data']['logs']['append']['count']
            GRID['data']['logs']['decision']['list'].append("[{}] {}|{}-{}    to_put   {} ({})   killed   {}".format(j + i, j, i, i + 1, code, subject['prio'], extras[0]))
            GRID['data']['logs']['append']['list'].append("[{}] -    removing  {}  in  {}".format(j+i, extras[0], ', '.join([t['weekday'] for t in subject['times']])))

            label += '  [persistent_by_uncertainty] '
            # registro de logs

        GRID = append_grid(GRID, subject, code)
        used_subjects.append(subject['entry'])

        # registro de logs
        j = GRID['data']['logs']['decision']['count']
        i = GRID['data']['logs']['append']['count']
        GRID['data']['logs']['append']['list'].append("[{}] {}  {} | {}  ({})  {}".format(j+i, i, subject["entry"], subject['professor'], subject['prio'], label))
        # registro de logs

        if decision == 4:  # persistir o removido por re-inserção
            # PERSISTENT = todos os subjects com a mesma entrada que aquele que foi removido (mas diferentes do que foi removido)
            PERSISTENT_LIST = [(code, subject['prio']) for code, subject in RAW_GRID.items() if code != extras[0] and subject['entry'] == RAW_GRID[extras[0]]['entry']]
            PERSISTENT_LIST.sort(key=lambda x: x[0])
            PERSISTENT_LIST.sort(key=lambda x: x[1], reverse=True)

            # --- Para executar o Processo de Incerteza recursivamente, escolher entre as materias restantes
            """ METODO DE ESCOLHA
                1 - começar com a maior prioridade, setar incerteza para 2 (consequencia de re-inserir um incerto puro)

                problema: ao terminar de inserir o primeiro persistente, como impedir que ele insira o resto? caso a decisao opte por nao inserir, testar o resto
                problema: impedir que os subjects que derivaram um novo universo por incerteza sejam removidos
            """
            for persistent_code, persistent_prio in PERSISTENT_LIST:
                RAW_GRID[persistent_code]['uncertain'] = 2
                GRID, PERSISTENT_REPEATED_GRID, used_subjects, command, extras = insert_grid(persistent_code, RAW_GRID[persistent_code], used_subjects, GRID, DECISION_BASE, RAW_GRID, PERSISTENT_REPEATED_GRID)
                ext.update(extras)

                if command != "subject_rejected":  # somente continua o loop se o subject foi rejeitado na decisao
                    break

    elif decision == 3 or decision == 0:  # GERAR OUTRA GRADE || NAO INSERIR (mesmo log) // 3-> extras = [slot_code, new_decision_bank, cornerstones]
                                            #                                               0->extras = [slot_code, is_level2_uncertain]
        if decision == 3:
            # GRIDS += generate_grid(PRIO_RAW_GRID, WEEKLY_MODEL_FILE, extras[1])
            command = "generate_another_grid"
            ext['decision_base'] = extras[1]
            ext['cornerstone'] = extras[2]
            # used_subjects.append(subject["entry"])
        elif decision == 0:  # informar se o incerto nivel 2 nao foi inserido
            if extras[1]:  # se a aula nao inserida é incerta em nivel 2
                command = "subject_rejected"

        # registro de logs
        GRID['data']['logs']['decision']['count'] += 1
        j = GRID['data']['logs']['decision']['count']
        i = GRID['data']['logs']['append']['count']
        GRID['data']['logs']['decision']['list'].append("[{}] {}|{}-{}  {}   over   {} ({})".format(j + i, j, i, i + 1, extras[0], code, subject['prio']))
        # registro de logs
    elif decision == -1: # REPETIDO, ADICIONAR NA LISTA DE REPETICAO E REVER DEPOIS
        PERSISTENT_REPEATED_GRID['list'].append((code, subject['prio']))

    return GRID, PERSISTENT_REPEATED_GRID, used_subjects, command, ext

def generate_grid(PRIO_LIST, RAW_GRID, WEEKLY_MODEL_FILE, DECISION_BANK={}):
    GRIDS = []

    # banco de decisoes =  CHOOSE_THIS_DUDE, OVER_THIS_GUYS[n]
    # DECISION_BANK = {"Química Geral NA|Silvia|BCT-N": ["Circuitos Digitais N|Denise|BCT-N"]}
    MODEL_GRID = get_weekly_model(WEEKLY_MODEL_FILE)
    PERSISTENT_REPEATED_GRID = {"repetitions": 0, "list": []}

    used_subjects = []
    CURRENT_LIST = PRIO_LIST.copy()
    label = ""

    while not CURRENT_LIST is None:
        for code, code_prio in CURRENT_LIST:
            MODEL_GRID, PERSISTENT_REPEATED_GRID, used_subjects, cmd, extras = insert_grid(code, RAW_GRID[code], used_subjects, MODEL_GRID, DECISION_BANK, RAW_GRID, PERSISTENT_REPEATED_GRID, label=label) #  NOT TRYING TO DO THIS

            if cmd == "generate_another_grid":  # extras = new_decision_base
                # secure cornerstone persistency
                SECURED_RAW_GRID = RAW_GRID.copy()
                SECURED_RAW_GRID[extras['cornerstone']]['immortal'] = True
                SECURED_PRIO_LIST = [(i[0], i[1]['prio']) for i in SECURED_RAW_GRID.items()]
                SECURED_PRIO_LIST.sort(key=lambda x: x[0])
                SECURED_PRIO_LIST.sort(key=lambda x: x[1], reverse=True)

                GRIDS += generate_grid(SECURED_PRIO_LIST, SECURED_RAW_GRID, WEEKLY_MODEL_FILE, extras['decision_base'])

        if PERSISTENT_REPEATED_GRID['repetitions'] > 0: # funcional com base no teste de persistencia pra fecont
            PERSISTENT_REPEATED_GRID['repetitions'] -= 1
            CURRENT_LIST = PERSISTENT_REPEATED_GRID['list'].copy()
            CURRENT_LIST.sort(key=lambda x: x[0])
            CURRENT_LIST.sort(key=lambda x: x[1], reverse=True)
            PERSISTENT_REPEATED_GRID['list'] = []
            label = "  [persistent_by_repetition] "
        else:
            CURRENT_LIST = None

    GRIDS.append(MODEL_GRID)

    return GRIDS


""" GENERAL FUNCTIONS """


def get_grids(CONFIG, save=False):
    # IMPORTAR DADOS
    with open(CONFIG['files']['input'], encoding="utf-8") as entrada:
        INPUT = json.load(entrada)

    with open(CONFIG['files']['matrix'], encoding="utf-8") as entrada:
        MATRIZ = json.load(entrada)

    with open(CONFIG['files']['aurelio'], encoding="utf-8") as entrada:
        AURELIO = json.load(entrada)

    MATERIAS = get_subjects(MATRIZ)

    # GERAR GRADE(s)
    PRIO_LIST, RAW_GRID = get_prioritary_grid(INPUT, MATERIAS, CONFIG, AURELIO)

    GRIDS = generate_grid(PRIO_LIST, RAW_GRID, CONFIG['files']['weekly_model'])

    GRIDS = clear_repetitions(GRIDS)
    GRIDS = reduce_redundance(GRIDS, RAW_GRID)

    if save:
        if not os.path.exists('./history'):
            os.mkdir('./history')

        # file = grade_horaria_inputNome_diaMesAno horaMinutoSegundo.json
        result_file = './history/grade_horaria{}_' + strftime("%d%m%Y %H%M%S") + ".json"
        if "name" in INPUT['general']:
            result_file = result_file.format('_' + INPUT['general']['name'])
        else:
            result_file = result_file.format('')

        for g in GRIDS:
            g['data']['file'] = result_file

        result = json.dumps({"RAW_GRID": RAW_GRID, "GRIDS": GRIDS}, ensure_ascii=False, sort_keys=True, indent=None, separators=None)
        with open(result_file, "wb") as trg:
            trg.write(result.encode("utf-8"))

    return GRIDS

def clear_repetitions(GRIDS):
    repetitions = []

    for g in range(0, len(GRIDS)-1):
        for h in range(0, len(GRIDS)-1-g):
            if g != h+g:  # nao esta comparando um cara consigo mesmo
                if compare_grids(GRIDS[g], GRIDS[h+g]):  # se são iguais, marca o segundo
                    repetitions.append(h+g)

    repetitions = list(set(repetitions))
    repetitions.sort(reverse=True)

    for i in repetitions:
        del GRIDS[i]

    return GRIDS

# ---? Remover a grade q escolha CD Cappa ao inves de CD Denise no mesmo horario
"""
    Essas aulas tem a mesma materia no mesmo horario, mas professores diferentes.
    Se especificado na entrada, escolher o professor preferido. Se nao, mescla em Cappa / Denise (exmplo)

"""
def reduce_redundance(GRIDS, RAW_GRID):
    exclusion_pool = []

    for g in range(0, len(GRIDS)-1):
        for h in range(0, len(GRIDS)-1-g):
            if g in exclusion_pool:  # se o g é reduntante de um outro, nao adianta comparar ele
                continue

            if g != h+g:  # nao esta comparando um cara consigo mesmo
                if not compare_grids(GRIDS[g], GRIDS[h+g]):  # se nao sao iguais
                    redundances, diferences = check_professor_redundance(GRIDS[g], GRIDS[h+g], RAW_GRID)

                    if len(diferences):  # se registrou diferenças, as grades nao sao semelhantes o suficiente
                        continue

                    for r in redundances:
                        GRIDS[g][r['weekday']][r['time']] = r['solution']

                    exclusion_pool.append(h+g)

    exclusion_pool = list(set(exclusion_pool))
    exclusion_pool.sort(reverse=True)
    for i in exclusion_pool:
        del GRIDS[i]

    return GRIDS