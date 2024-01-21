import os
import sys
import csv

filepath = sys.argv[1]
writer = csv.writer(open("Aggregation_results_formatted.csv", 'w', newline=''))
sets = ['commonsense', 'ai2', 'pubmed_lf', 'pubmed_mc', 'LongForm', 'databricks', 'sub', 'FinTalk', 'mmlu']
columns = []
styles = ['3-normal','3-researcher','3-persona','3-roundtable', '','4-normal','4-researcher','4-persona','4-roundtable', '']
rows = [[0 for _ in range(20)] for _ in range(10)]
for i in range(len(styles)):
	rows[i][0] = styles[i]
	rows[i][-1] = styles[i]
for st in sets:
	columns.append(st + "_mean")
	columns.append(st + "_perc")
columns.insert(0, "")
writer.writerow(columns)
# print(dir(columns))

	# pass

reader = csv.reader(open(filepath, 'r'))


for row in reader:
	print(row)
	if row[0] =="Style":
		continue
	style = row[0]
	dataset = row[1]
	model = row[2][:5]
	q_format = row[3]
	count = row[4]
	mean = row[5]
	percentage = row[6]

	if model == "None":
		model = "gpt-3"
	if dataset == "pubmed":
		if q_format == "long":
			dataset = "pubmed_lf"
		else:
			dataset = "pubmed_mc"
	print(dataset)
	mean_index = sets.index(dataset) * 2 + 1
	perc_index = mean_index + 1
	model_num = model[-1]
	new_style = f"{model_num}-{style}"
	style_index = styles.index(new_style)
	print(mean_index)
	print(len(rows))

	rows[style_index][mean_index] = mean
	rows[style_index][perc_index] = percentage


for row in rows:
	writer.writerow(row)


	
