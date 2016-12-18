# todo Criar codigo para sugerir aulas baseado no curso e nas aulas já feitas
# import Tkinter as tk
from collections import OrderedDict

if 1==1:
    #root = tk.Tk()
    #root.withdraw()

    print("Select file to convert:\n")
    file_path = "trace.trace"
    filetrc = open(file_path, 'r')
    lines = filetrc.readlines()
    filetrc.close()
    filepath = file_path.split('.')
    output_file = open(filepath[0] + "_txt.txt", "w")

    dicEvents = {}
    for i in range(len(lines)):

        if '%EventDef' in lines[i]:

            ln = lines[i].split(' ')
            id = ln[2].split('\n')
            id = id[0]
            dicEv = OrderedDict()

            output_file.write(ln[1] + ' ' + ln[2])

            i += 1
            while not lines[i].startswith('%EndEventDef'):

                ln = lines[i].split(' ')
                typ = ln[2].split('\n')
                typ = typ[0]
                dicEv[str(ln[1])] = typ
                i += 1

            dicEvents[str(id)] = dicEv

# lines = ['1 "CT_Program" 0 "Program"']
for i in range(len(lines)):

	if not lines[i].startswith('%'):

		ln = lines[i].split(' ')
		fileLine = ""
		print(lines[i])

		j = 0
		fileLine += 'ID: ' + ln[j]
		# print('ln[' + str(j) + '] = ' + str(ln[j]) + ' Type: ', type(ln[j]))
		for item in dicEvents[ln[0]]:

			it = ' ' + item.upper() + ':'

			j += 1
			if dicEvents[ln[0]][item] == 'string' and ln[j] != '0':

                    while True:
                        it += ' ' + ln[j]
                        if ln[j][-1] == '"' or ln[j][-3:] == '"\n':
                            print('break')
                            break
                        j += 1
            else:
             it += ' ' + ln[j]

			fileLine += it

		print(fileLine)

