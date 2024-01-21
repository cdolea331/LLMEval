import sys
import os
import csv

styles= ['roundtable', 'normal', 'persona', 'researcher']
low_estimate = 50
models = ['gpt-3.5-turboquestions.csv','gpt-3questions.csv','gpt-4questions.csv']
datasets = ['FinTalk', 'LongForm', 'mmlu', 'pubmed', 'commonsense', 'ai2', 'sub', 'databricks']

filepath = sys.argv[1]
writer = csv.writer(open("Aggregation_results.csv", 'w', newline=''))
writer.writerow(['Style', 'dataset', 'model', 'answer style', 'quantity', 'mean', 'percentage'])

files = [f for f in os.listdir(filepath) if f[-3:] =='csv']
entries = []
for file in files:
	name_chunks = file.split("_")
	style = None
	quantity = 0
	model = None
	dataset = None
	a_format = 'mc'
	for chunk in name_chunks:
		model = chunk if chunk in models else model
		style = chunk if chunk in styles else style
		dataset = chunk if chunk in datasets else dataset
		a_format = chunk if chunk == 'long' else a_format
		if chunk.isnumeric():
			quantity = int(chunk) if int(chunk) >= low_estimate else quantity

	with open(filepath + "/" +file, "r", encoding="utf-8", errors="ignore") as scraped:
		# print(file)
		lines = scraped.readlines()
		if len(lines) < quantity:
			os.remove(filepath + "/" +file)
			continue
		# print(len(lines))
		final_line = lines[-1]
		penultimate_line = lines[-2]
		cells = final_line.split(',')

		if cells[0] == 'Mean score':
			pen_cells = penultimate_line.split(',')
			entries.append([style, dataset, model, quantity, float(cells[1]), float(pen_cells[3]), a_format])
		elif a_format == 'mc' and cells[0] == 'Total' and not model == None:
			# print(cells)
			entries.append([style, dataset, model, quantity, -1, float(cells[3]), a_format])

final_output = {}

for entry in entries:
	entry_string = f"{entry[0]}_{entry[1]}_{entry[2]}_{entry[-1]}"
	if entry_string in final_output.keys():
		current = final_output[entry_string]
		new_total = current[0] + entry[3]
		# new_mean = 'N/A'
		# if entry[-1] =='long':
		# print(entry)
		new_mean = (current[0] * current[1] + entry[3] * entry[4])/new_total
		new_percentage = (current[0] * current[2] + entry[3] * entry[5])/new_total
		final_output[entry_string] = [new_total, new_mean,new_percentage]
	else:
		final_output[entry_string] = [entry[3], entry[4], entry[5]]


for key in final_output.keys():
	identifiers = key.split('_')
	values = final_output[key]
	[identifiers.append(value) for value in values]
	writer.writerow(identifiers)

		




# print(files)