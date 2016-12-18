import os
import sys

from lib import auxiliar, exportador, functions

""" setar root """
DIRECTORY = os.path.dirname(sys.argv[0])
sys.path.extend([DIRECTORY])

CONFIG = auxiliar.load_json("./config.json")

""" GENERATE GRID """
GRIDS, history = functions.get_grids(CONFIG, save=True)


""" PRINT RESULTS """
i = 0
for GRID in GRIDS:
    print("=====  GRID #{}  =====".format(i))
    print("")

    print("REGISTRO DE INSERÇÕES =====================")
    for l in GRID['data']['logs']['append']['list']:
        print(l)
    """
    print("\nREGISTRO DE DECISÕES =====================")
    for l in GRID['data']['logs']['decision']['list']:
        print(l)"""

    print("")
    print("(CONTAGEM DE MATÉRIAS) " + str(GRID['data']['count']))
    del GRID['data']  # remove data values, make it easy to read later
    print(GRID)

    print("")
    print("=====  GRID #{}  =====".format(i))
    print("")
    i += 1
    
print("")

print("data registered in {}".format(history))
print("")
ipt = input("Export grid to csv? (-1 for NO, index for YES, ALL for worksheet)\n")
print("")
if ipt.upper() == "ALL":
    print("exporting all grids to matriz_horaria.xls...")
    exportador.export_grid(history, type='xls')
else:
    index = int(ipt)
    if index != -1:
        print("exporting grid #{} to matriz_horaria.csv...".format(index))
        exportador.export_grid(history, index=index, type='csv')