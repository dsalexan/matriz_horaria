import json

AIM = "C:/Users/Danilo/Projetos/matriz_horaria/matriz_input.json"
TARGET = "C:/Users/Danilo/Projetos/matriz_horaria/matriz_output.json"
FILE_M_SEMANAL = "C:/Users/Danilo/Projetos/matriz_horaria/modelo_semanal.json"


SCHEDULE = {'13h30-15h30': "I", '19h00-21h00': "N", '10h00-12h00': "I", '8h00-10h00': "I", '21h00-23h00': "N", '15h30-17h30': "I"}

SCHEDULE_PRIORITY = {0: ["N"], 1: ["I"]}
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
V   - priorizar materias por horario (Noturno e Diurno)

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

used_subjects = []
for i in range(0, len(SCHEDULE_PRIORITY)):
    PRIORITARY_RAW_GRID = {k: s for k, s in RAW_GRID.items() if any(SCHEDULE[t['time']] in SCHEDULE_PRIORITY[i] for t in s['times'])}
    for code in PRIORITARY_RAW_GRID:# percorre materia por materia para inserir os dados de entrada e refinar a busca
        entry_object = [e for e in INPUT if PRIORITARY_RAW_GRID[code]['subject'].find(e[0]) != -1][0]

        PRIORITARY_RAW_GRID[code]['entry'] = entry_object[0]
        PRIORITARY_RAW_GRID[code]['prio'] = entry_object[2]



    SORTED_PRIO_RAW_GRID = sorted(PRIORITARY_RAW_GRID.items(), key=lambda x: x[1]['prio'])

    for code, subject in SORTED_PRIO_RAW_GRID:
        # encontrar a entrada correspondente

        free_slot = True
        for time in subject['times']: # detectar se há espaço livre
            if len(GRID[time['weekday']][time['time']]) >= 1:
                free_slot = False

        if free_slot and not subject['entry'] in used_subjects:
            print(subject['entry'])
            for time in subject['times']: # para cada horario descrito no registro da aula, ocupar o horario
                GRID[time['weekday']][time['time']].append(code)

            used_subjects.append(subject['entry'])

print(GRID)