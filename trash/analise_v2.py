import json

AIM = "C:/Users/Danilo/Projetos/matriz_horaria/matriz_input.json"
TARGET = "C:/Users/Danilo/Projetos/matriz_horaria/matriz_output.json"
FILE_M_SEMANAL = "C:/Users/Danilo/Projetos/matriz_horaria/modelo_semanal.json"

SCHEDULE = {'13h30-15h30': "I", '19h00-21h00': "N", '10h00-12h00': "I", '8h00-10h00': "I", '21h00-23h00': "N", '15h30-17h30': "I"}

SCHEDULE_PRIORITY = {"N": 1, "I": 0}
TERM_PRIORITY = {"3": 0, "2": 0, "1": 0, "4": 0, "5": 0}
TIME_PRIORITY = {'8h00-10h00': -0.0}

ALLOWED_TERMS = ["1", "2", "3", "4", "5", "Reofs", "7"]
ALLOWED_COURSES = ["BCT", "BCC"]

with open(TARGET, encoding="utf-8") as extracao:
    MATRIZ = json.load(extracao)

with open(AIM, encoding="utf-8") as entrada:
    INPUT = json.load(entrada)

with open(FILE_M_SEMANAL, encoding="utf-8") as m_semanal:
    MODELO_SEMANAL = json.load(m_semanal)

"""
I   - criar tabela auxiliar centrada nas materias
II  - criar tabela auxiiar centrada nos dias da semana

III - imprime as materias dentro de um determinado filtro, modelo p/ excel

IV  - prototipo inicial, le o input, pega a materia e coloca na grade
    V   - priorizar materias por horario (Noturno e Diurno), e criar status de prioridade geral
    VI  - priorizar por especificidades na entrada, e criar status de prioridade individual

VII - criar processo de incerteza, criando multiplos resultados ao enfrentar escolhas entre materias importantes (schrodinger)

"""

""" I """
MATERIAS = {}

for c in MATRIZ:
    for wk in c['week']: # iterate trough keys in dict
        for s in c['week'][wk]: # iterate trough subjects in weekday
            if not s is None:
                if s["professor"] is None:
                    s["professor"] = "nao_apresentado"

                code = s["subject"]+"|"+s["professor"]+"|"+c["course"]
                if not code in MATERIAS.keys():
                    data = {
                        "subject": s["subject"],
                        "professor": s["professor"],
                        "times": [], # {"weekday": wk, "time": c['time']}
                        "course": c['course'],
                        "term": c['term']
                    }
                    MATERIAS[code] = data

                MATERIAS[code]['times'].append({"weekday": wk, "time": c['time']})

""" II """
SEMANA = {"seg": {},
          "ter": {},
          "qua": {},
          "qui": {},
          "sex": {}}

for c in MATRIZ:
    for wk in c['week']: # iterate trough keys in dict
        for s in c['week'][wk]: # iterate trough subjects in weekday
            if not s is None:
                if s["professor"] is None:
                    s["professor"] = "nao_apresentado"

                if not c['time'] in SEMANA[wk].keys():
                    SEMANA[wk][c['time']] = []

                SEMANA[wk][c['time']].append({"subject": s['subject'], "professor": s['professor']})


""" III
print(MATERIAS)
for k in [m for m in MATERIAS.keys() if any(c in MATERIAS[m]['course'] for c in ALLOWED_COURSES) and any(t in ALLOWED_TERMS for t in MATERIAS[m]['term'])]:
    print('{}|{}|{}|{}'.format(MATERIAS[k]['subject'], MATERIAS[k]['professor'], ",".join(MATERIAS[k]['term']), MATERIAS[k]['course']))
"""

""" IV """
GRID = MODELO_SEMANAL.copy()

ENTRY_SUBJECTS = [e[0] for e in INPUT]
RAW_GRID = {k: s for (k, s) in MATERIAS.items() if any(s['subject'].find(es) != -1 for es in ENTRY_SUBJECTS)}

for code in RAW_GRID:
    entry_object = [e for e in INPUT if RAW_GRID[code]['subject'].find(e[0]) != -1][0]

    RAW_GRID[code]['entry'] = entry_object[0]
    RAW_GRID[code]['prio'] = entry_object[2]

    # PRIORIDADES GERAIS
    # schedule
    RAW_GRID[code]['prio'] += SCHEDULE_PRIORITY[SCHEDULE[RAW_GRID[code]['times'][0]['time']]]
    # term
    for t in RAW_GRID[code]["term"]:
        if t in TERM_PRIORITY:
            RAW_GRID[code]['prio'] += TERM_PRIORITY[t]
    # time
    for t in RAW_GRID[code]["times"]:
        if t['time'] in TIME_PRIORITY:
            RAW_GRID[code]['prio'] += TIME_PRIORITY[t['time']]

    # PRIORIDADES INDIVIDUAIS
    prio_score = 0
    for k, p in entry_object[1].items():
        # p[0] = valor do parametro
        # p[1] = IGUALDADE = 1, DESIGUALDADE = -1
            # serve pra especificar se a prioridade é um match ou um not-match
        # p[2] = OPCIONAL, é o parametro de multiplicação do valor prioritario
        m = 1
        if len(p) == 3:
            m = p[2]

        if k == "schedule": # se o schedule bater com o prioritario, soma +1, senao, soma -1
            if SCHEDULE[RAW_GRID[code]['times'][0]['time']] == p[0]:
                prio_score += 1 * p[1] * m
            else:
                prio_score += -1 * p[1] * m
        elif k == "professor": # se o professor bater com o prioritário, soma +1, senao, soma -1
            if RAW_GRID[code]['professor'] == p[0]:
                prio_score += 1 * p[1] * m
            else:
                prio_score += -1 * p[1] * m

    RAW_GRID[code]['prio'] += prio_score

PRIO_RAW_GRID = sorted(RAW_GRID.items(), key=lambda x: x[1]['prio'], reverse=True)

print(PRIO_RAW_GRID)

used_subjects = []
for code, subject in PRIO_RAW_GRID:
    # encontrar a entrada correspondente

    free_slot = True
    for time in subject['times']: # detectar se há espaço livre
        if len(GRID[time['weekday']][time['time']]) >= 1:
            free_slot = False

    if free_slot and not subject['entry'] in used_subjects:
        print(subject['entry'] + " (" + str(subject['prio']) + ")")
        for time in subject['times']: # para cada horario descrito no registro da aula, ocupar o horario
            GRID[time['weekday']][time['time']].append(code + " (" + str(subject['prio']) + ")")

        used_subjects.append(subject['entry'])

print(GRID)